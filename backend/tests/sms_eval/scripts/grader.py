#!/usr/bin/env python3
"""
Assertion grader for SMS agent eval cases.

Turns the visual-review harness into a pass/fail gate. Each scenario in
`fixtures/assertion_cases.json` carries an `expectations` block:

    "expectations": {
        "tier": "guard" | "target",
        "assertions": [ {"id": ..., "type": ..., ...}, ... ]
    }

- GUARD  = behavior that works today and must never regress. A GUARD failure
           should block a push (run_assertions.py exits non-zero).
- TARGET = behavior we are actively fixing. Expected to FAIL until shipped;
           flips to a GUARD once green.

The grader is a set of pure functions over the `raw_results.json` produced by
run_sms_eval.py, so it is independently unit-testable (see --self-test) without
hitting any API. The one exception is the `llm_judge` assertion, which calls
OpenAI; it degrades to "skip" when OPENAI_API_KEY is absent.
"""

import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# status constants
PASS = "pass"
FAIL = "fail"
SKIP = "skip"


# ---------------------------------------------------------------------------
# Helpers to read the turn-result structure produced by run_sms_eval.py
# ---------------------------------------------------------------------------

def _turns(result: Dict) -> List[Dict]:
    return result.get("turns", [])


def _select_turns(result: Dict, turn) -> List[Dict]:
    """Resolve a turn selector to a list of turn dicts.

    turn may be an int (1-based), "any"/"all" (every turn), or "last".
    """
    turns = _turns(result)
    if turn in (None, "any", "all"):
        return turns
    if turn == "last":
        return turns[-1:] if turns else []
    return [t for t in turns if t.get("turn") == turn]


def _turn_text(turn: Dict) -> str:
    """All user-visible text for a turn: final response + every output message."""
    parts = [turn.get("agent_text_response") or ""]
    for m in turn.get("output_messages", []):
        if m.get("text"):
            parts.append(m["text"])
    return "\n".join(parts)


def _tool_names(turn: Dict) -> List[str]:
    return [tc.get("tool", "") for tc in turn.get("tool_calls", [])]


def _outfit_messages(turn: Dict) -> List[Dict]:
    return [m for m in turn.get("output_messages", []) if m.get("tool") == "present_outfit"]


def _has_any_image(turn: Dict) -> bool:
    return any(m.get("images") for m in turn.get("output_messages", []))


# ---------------------------------------------------------------------------
# Deterministic assertion implementations
# Each returns (status, detail).
# ---------------------------------------------------------------------------

def _a_tool_called(a, result) -> Tuple[str, str]:
    tool = a["tool"]
    for t in _select_turns(result, a.get("turn", "any")):
        if tool in _tool_names(t):
            return PASS, f"{tool} called in turn {t['turn']}"
    return FAIL, f"{tool} never called (turn={a.get('turn', 'any')})"


def _a_tool_not_called(a, result) -> Tuple[str, str]:
    tool = a["tool"]
    for t in _select_turns(result, a.get("turn", "any")):
        if tool in _tool_names(t):
            return FAIL, f"{tool} was called in turn {t['turn']} (should not be)"
    return PASS, f"{tool} not called"


def _a_no_tools(a, result) -> Tuple[str, str]:
    """Acknowledgment turns must call no tools and send no images."""
    for t in _select_turns(result, a.get("turn", "any")):
        if _tool_names(t):
            return FAIL, f"turn {t['turn']} called tools: {_tool_names(t)}"
        if _has_any_image(t):
            return FAIL, f"turn {t['turn']} sent images on an acknowledgment"
    return PASS, "no tools / no images"


def _a_tool_order(a, result) -> Tuple[str, str]:
    """`before` must appear before the first `after` within the same turn."""
    before, after = a["before"], a["after"]
    for t in _select_turns(result, a.get("turn", "any")):
        names = _tool_names(t)
        if after not in names:
            continue
        first_after = names.index(after)
        before_idxs = [i for i, n in enumerate(names) if n == before]
        if not before_idxs:
            return FAIL, f"turn {t['turn']}: {after} present but {before} never called"
        if min(before_idxs) < first_after:
            return PASS, f"turn {t['turn']}: {before} precedes {after}"
        return FAIL, f"turn {t['turn']}: {before} came after {after}"
    return FAIL, f"{after} never occurred, cannot check order"


def _a_text_contains_any(a, result) -> Tuple[str, str]:
    patterns = a["patterns"]
    for t in _select_turns(result, a.get("turn", "any")):
        text = _turn_text(t)
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return PASS, f"turn {t['turn']} matched /{p}/"
    return FAIL, f"none of {patterns} found"


def _a_text_not_matches(a, result) -> Tuple[str, str]:
    """Negative check — must hold for ALL selected turns."""
    pattern = a["pattern"]
    for t in _select_turns(result, a.get("turn", "any")):
        if re.search(pattern, _turn_text(t)):
            return FAIL, f"turn {t['turn']} matched forbidden /{pattern}/"
    return PASS, f"no turn matched /{pattern}/"


def _a_tool_arg_contains_any(a, result) -> Tuple[str, str]:
    """At least one call to `tool` has args matching one of `patterns`."""
    tool, patterns = a["tool"], a["patterns"]
    for t in _select_turns(result, a.get("turn", "any")):
        for tc in t.get("tool_calls", []):
            if tc.get("tool") != tool:
                continue
            blob = json.dumps(tc.get("args", {}), default=str)
            for p in patterns:
                if re.search(p, blob, re.IGNORECASE):
                    return PASS, f"turn {t['turn']} {tool} args matched /{p}/"
    return FAIL, f"no {tool} call had args matching {patterns}"


def _a_outfit_present(a, result) -> Tuple[str, str]:
    for t in _select_turns(result, a.get("turn", "any")):
        if _outfit_messages(t):
            return PASS, f"turn {t['turn']} presented an outfit"
    return FAIL, "no present_outfit in selected turns"


def _a_outfit_visualized(a, result) -> Tuple[str, str]:
    for t in _select_turns(result, a.get("turn", "any")):
        if any(m.get("visualize") for m in _outfit_messages(t)):
            return PASS, f"turn {t['turn']} has on-person visualization"
    return FAIL, "no visualize=true outfit found"


def _a_outfit_uses_wardrobe(a, result) -> Tuple[str, str]:
    """Outfit must be built from real wardrobe items (non-empty item_names)."""
    for t in _select_turns(result, a.get("turn", "any")):
        for m in _outfit_messages(t):
            if m.get("item_names"):
                return PASS, f"turn {t['turn']} used items {m['item_names'][:3]}..."
    return FAIL, "no outfit had resolved wardrobe item_names"


def _a_every_outfit_has_rationale(a, result) -> Tuple[str, str]:
    """Every presented outfit must ship with surviving 'why' text.

    Rationale survives if the present_outfit call itself carries text, OR a
    send_message with text immediately precedes it (the packing pattern).
    This is the assertion that catches the sms.py suppression bug.
    """
    checked = 0
    for t in _select_turns(result, a.get("turn", "any")):
        msgs = t.get("output_messages", [])
        for i, m in enumerate(msgs):
            if m.get("tool") != "present_outfit":
                continue
            checked += 1
            own = (m.get("text") or "").strip()
            prev = msgs[i - 1] if i > 0 else {}
            prev_text = prev.get("text") if prev.get("tool") == "send_message" else None
            if not own and not (prev_text and prev_text.strip()):
                return FAIL, f"turn {t['turn']} outfit #{i} shipped with no rationale text"
    if checked == 0:
        return FAIL, "no outfits found to check"
    return PASS, f"all {checked} outfit(s) had rationale"


def _a_max_length(a, result) -> Tuple[str, str]:
    limit = a["chars"]
    for t in _select_turns(result, a.get("turn", "any")):
        n = len(_turn_text(t))
        if n > limit:
            return FAIL, f"turn {t['turn']} is {n} chars (> {limit})"
    return PASS, f"within {limit} chars"


def _a_llm_judge(a, result) -> Tuple[str, str]:
    """Subjective rubric scored 1-5 by an LLM. Pass if score >= threshold.

    Degrades to SKIP when no OPENAI_API_KEY (so it never silently passes).
    """
    if not os.getenv("OPENAI_API_KEY"):
        return SKIP, "no OPENAI_API_KEY — judge skipped"

    threshold = a.get("threshold", 4)
    rubric = a["rubric"]
    turns = _select_turns(result, a.get("turn", "any"))
    transcript = _render_transcript(result, turns)

    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = (
            "You are grading a personal-styling SMS agent against ONE rubric.\n"
            f"RUBRIC: {rubric}\n\n"
            "Score 1-5 where 5 = fully satisfies the rubric, 1 = clearly violates.\n"
            "Respond ONLY as JSON: {\"score\": <int>, \"reason\": \"<one sentence>\"}\n\n"
            f"CONVERSATION:\n{transcript}"
        )
        resp = client.chat.completions.create(
            model=a.get("model", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        score = int(data.get("score", 0))
        reason = data.get("reason", "")
        status = PASS if score >= threshold else FAIL
        return status, f"score={score}/{threshold} — {reason}"
    except Exception as e:  # noqa: BLE001
        return SKIP, f"judge error: {e}"


def _render_transcript(result: Dict, turns: List[Dict]) -> str:
    lines = []
    for t in turns:
        lines.append(f"USER: {t.get('user_message', '')}")
        if t.get("image_url"):
            lines.append(f"[user sent a {t.get('image_type') or 'photo'}]")
        for m in t.get("output_messages", []):
            tag = m.get("tool", "msg")
            txt = (m.get("text") or "").strip()
            imgs = len(m.get("images", []))
            extra = f" [{imgs} image(s){', visualized' if m.get('visualize') else ''}]" if imgs else ""
            if txt or extra:
                lines.append(f"AGENT({tag}): {txt}{extra}")
        if t.get("agent_text_response") and not t.get("output_messages"):
            lines.append(f"AGENT: {t['agent_text_response']}")
    return "\n".join(lines)


DISPATCH = {
    "tool_called": _a_tool_called,
    "tool_not_called": _a_tool_not_called,
    "no_tools": _a_no_tools,
    "tool_order": _a_tool_order,
    "text_contains_any": _a_text_contains_any,
    "text_not_matches": _a_text_not_matches,
    "tool_arg_contains_any": _a_tool_arg_contains_any,
    "outfit_present": _a_outfit_present,
    "outfit_visualized": _a_outfit_visualized,
    "outfit_uses_wardrobe": _a_outfit_uses_wardrobe,
    "every_outfit_has_rationale": _a_every_outfit_has_rationale,
    "max_length": _a_max_length,
    "llm_judge": _a_llm_judge,
}


def grade_assertion(assertion: Dict, result: Dict) -> Dict:
    fn = DISPATCH.get(assertion["type"])
    if not fn:
        return {"id": assertion.get("id"), "type": assertion["type"],
                "status": FAIL, "detail": f"unknown assertion type '{assertion['type']}'"}
    if result.get("turns") and all(not t.get("success", True) for t in result["turns"]):
        return {"id": assertion.get("id"), "type": assertion["type"],
                "status": FAIL, "detail": "scenario run errored before grading"}
    status, detail = fn(assertion, result)
    return {"id": assertion.get("id"), "type": assertion["type"],
            "status": status, "detail": detail}


def grade_scenario(result: Dict, expectations: Dict) -> Dict:
    tier = expectations.get("tier", "guard")
    graded = [grade_assertion(a, result) for a in expectations.get("assertions", [])]
    n_fail = sum(1 for g in graded if g["status"] == FAIL)
    n_skip = sum(1 for g in graded if g["status"] == SKIP)
    # A scenario passes when nothing failed (skips are reported, not fatal).
    passed = n_fail == 0
    return {
        "scenario_id": result.get("scenario_id"),
        "scenario_name": result.get("scenario_name"),
        "tier": tier,
        "passed": passed,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "assertions": graded,
    }


# ---------------------------------------------------------------------------
# Self-test: synthetic results prove the deterministic graders, no API needed.
# ---------------------------------------------------------------------------

def _self_test() -> int:
    good = {
        "scenario_id": "syn", "scenario_name": "synthetic",
        "turns": [{
            "turn": 1, "user_message": "outfit for today", "success": True,
            "agent_text_response": "",
            "tool_calls": [{"tool": "web_search", "args": {"query": "Seattle weather today"}},
                           {"tool": "resolve_items", "args": {}},
                           {"tool": "present_outfit", "args": {}}],
            "output_messages": [
                {"tool": "send_message", "text": "Mild and dry today — here's the look", "images": []},
                {"tool": "present_outfit", "text": "", "images": ["c.jpg"],
                 "item_names": ["white shirt", "jeans"], "visualize": True},
            ],
        }],
    }
    bad = {
        "scenario_id": "syn2", "scenario_name": "synthetic-bad",
        "turns": [{
            "turn": 1, "user_message": "outfit for today", "success": True,
            "agent_text_response": "Here you go **bold**",
            "tool_calls": [{"tool": "present_outfit", "args": {}},
                           {"tool": "web_search", "args": {"query": "weather"}}],
            "output_messages": [
                {"tool": "present_outfit", "text": "", "images": ["c.jpg"],
                 "item_names": [], "visualize": False},
            ],
        }],
    }
    cases = [
        ("tool_called web_search", {"type": "tool_called", "tool": "web_search"}, good, PASS),
        ("tool_order ws<outfit (good)", {"type": "tool_order", "before": "web_search", "after": "present_outfit"}, good, PASS),
        ("tool_order ws<outfit (bad)", {"type": "tool_order", "before": "web_search", "after": "present_outfit"}, bad, FAIL),
        ("seattle default", {"type": "tool_arg_contains_any", "tool": "web_search", "patterns": ["seattle"]}, good, PASS),
        ("rationale survives (good)", {"type": "every_outfit_has_rationale"}, good, PASS),
        ("rationale survives (bad)", {"type": "every_outfit_has_rationale"}, bad, FAIL),
        ("uses wardrobe (good)", {"type": "outfit_uses_wardrobe"}, good, PASS),
        ("uses wardrobe (bad)", {"type": "outfit_uses_wardrobe"}, bad, FAIL),
        ("visualized (good)", {"type": "outfit_visualized"}, good, PASS),
        ("visualized (bad)", {"type": "outfit_visualized"}, bad, FAIL),
        ("no bold markdown (good)", {"type": "text_not_matches", "pattern": r"\*\*"}, good, PASS),
        ("no bold markdown (bad)", {"type": "text_not_matches", "pattern": r"\*\*"}, bad, FAIL),
    ]
    failures = 0
    for name, a, res, expected in cases:
        got = grade_assertion(a, res)["status"]
        ok = got == expected
        failures += not ok
        print(f"  [{'OK' if ok else 'XX'}] {name}: got={got} want={expected}")
    print(f"\nself-test: {len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print("Use --self-test, or import grade_scenario/grade_assertion.")
