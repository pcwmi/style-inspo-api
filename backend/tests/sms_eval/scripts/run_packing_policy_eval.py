#!/usr/bin/env python3
"""
Run SMS-modality packing policy evals with MockOutput.

This uses the real StylingAgent loop and real wardrobe context, but patches
web_search to deterministic trip conditions so the eval validates packing
behavior instead of depending on live weather search.

Usage:
    cd backend
    python tests/sms_eval/scripts/run_packing_policy_eval.py
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

load_dotenv(backend_path / ".env")
os.environ["STORAGE_TYPE"] = "s3"

from agent.agent import StylingAgent
from agent.output import MockOutput
from api.sms import preload_user_context


SCENARIOS = [
    {
        "id": "sf_work_interview",
        "destination_terms": ("sf", "san francisco", "interview", "meeting", "walking", "layer"),
        "min_outfits": 2,
        "message": (
            "Pack me for a two day SF work trip. Monday is an all day interview "
            "and I may walk between meetings. Tuesday is casual work with friends."
        ),
        "weather": (
            "San Francisco next two days: 58-66F, breezy, possible fog, light hill "
            "walking between work locations. Indoor offices can run cool."
        ),
    },
    {
        "id": "montana_cabin",
        "destination_terms": ("montana", "cabin", "trail", "outdoor", "cold", "layer"),
        "min_outfits": 3,
        "message": (
            "Pack me for a long weekend in Montana. Cabin dinners, coffee runs, "
            "and maybe easy trails. I want to still feel like myself."
        ),
        "weather": (
            "Montana long weekend: 42-62F, cold mornings, dry gravel paths, easy "
            "trails, casual cabin dinners. Layers and practical shoes matter."
        ),
    },
    {
        "id": "hawaii_resort",
        "destination_terms": ("hawaii", "beach", "resort", "dinner", "sand", "warm"),
        "min_outfits": 3,
        "message": (
            "Pack me for 4 days in Hawaii: beach time, casual lunches, and one "
            "nicer resort dinner. I do not want it to feel costume-y."
        ),
        "weather": (
            "Hawaii four day forecast: 76-84F, humid, beach sand, casual lunches, "
            "one polished resort dinner, brief warm showers possible."
        ),
    },
]


def _fake_web_search(query: str, count: int = 5, freshness: str | None = None) -> dict[str, Any]:
    query_lower = query.lower()
    for scenario in SCENARIOS:
        if scenario["id"].split("_")[0] in query_lower or any(term in query_lower for term in scenario["destination_terms"]):
            snippet = scenario["weather"]
            break
    else:
        snippet = (
            "Trip context: mild variable weather, mixed indoor/outdoor terrain. "
            "Build a reusable capsule with practical shoes and layers."
        )

    return {
        "query": query,
        "result_count": 1,
        "results": [
            {
                "title": "Mock destination weather and terrain",
                "url": "https://example.test/mock-weather",
                "snippet": snippet,
            }
        ],
    }


def _patch_web_search() -> None:
    import services.web_search as web_search_module

    web_search_module.web_search = _fake_web_search


def _texts(response: str, messages: list[dict[str, Any]]) -> list[str]:
    texts = [message.get("text") or "" for message in messages]
    if response:
        texts.append(response)
    return texts


def _present_calls(agent: StylingAgent) -> list[dict[str, Any]]:
    return [
        entry
        for entry in agent.turn_log
        if entry.get("type") == "tool_result" and entry.get("tool") == "present_outfit"
    ]


def _wof_names(text: str) -> list[str]:
    names = []
    collecting = False
    for line in text.splitlines():
        line_lower = line.lower()
        if "wof" in line_lower or "without fail" in line_lower:
            collecting = True
            names.extend(re.findall(r"\*([^*]+)\*", line))
            continue
        if collecting:
            if not line.strip():
                if names:
                    break
                continue
            names.extend(re.findall(r"\*([^*]+)\*", line))
    return [name.strip() for name in names if name.strip()]


def _validate_scenario(scenario: dict[str, Any], response: str, output: MockOutput, agent: StylingAgent) -> dict[str, Any]:
    messages = output.messages
    texts = _texts(response, messages)
    combined = "\n".join(texts).lower()
    present_calls = _present_calls(agent)
    send_indexes = [index for index, message in enumerate(messages) if message.get("tool") == "send_message" and message.get("text")]
    outfit_indexes = [index for index, message in enumerate(messages) if message.get("tool") == "present_outfit"]
    first_send_text = messages[send_indexes[0]].get("text", "") if send_indexes else ""

    item_lists = [call.get("args", {}).get("item_names") or [] for call in present_calls]
    item_counts = Counter(item for items in item_lists for item in items)
    repeated_items = [item for item, count in item_counts.items() if count >= 2]
    lower_item_counts = Counter(item.lower() for item, count in item_counts.items() for _ in range(count))
    wof_names = _wof_names(first_send_text)
    repeated_wof_names = [
        name
        for name in wof_names
        if lower_item_counts.get(name.lower(), 0) >= 2
    ]

    checks = {
        "used_web_search": any(
            entry.get("type") == "tool_result" and entry.get("tool") == "web_search"
            for entry in agent.turn_log
        ),
        "capsule_before_outfits": bool(send_indexes and outfit_indexes and send_indexes[0] < outfit_indexes[0]),
        "capsule_names_wofs": "wof" in first_send_text.lower() or "without fail" in first_send_text.lower(),
        "wof_names_repeat": bool(wof_names) and len(repeated_wof_names) == len(wof_names),
        "capsule_explains_why": any(
            term in first_send_text.lower()
            for term in (
                "style dna",
                "identity",
                "yourself",
                "destination",
                "weather",
                "terrain",
                "breezy",
                "foggy",
                "cold",
                "warm",
                "humid",
                "trail",
                "beach",
                "classic",
                "playful",
                "relaxed",
                "polished",
            )
        ),
        "mentions_reuse": any(term in first_send_text.lower() for term in ("reuse", "re-use", "repeat", "re-wear", "rewear", "orbit", "anchor", "again")),
        "enough_outfits": len(present_calls) >= scenario["min_outfits"],
        "all_visualize": bool(present_calls) and all(call.get("args", {}).get("visualize") is True for call in present_calls),
        "all_have_item_names": bool(present_calls) and all(call.get("args", {}).get("item_names") for call in present_calls),
        "reuses_items": len(repeated_items) >= 1 if len(present_calls) >= 2 else True,
        "no_rigid_transit_question": "transit or uber" not in combined and "ubering" not in combined,
        "destination_specific": any(term in combined for term in scenario["destination_terms"]),
        "no_individual_item_dump": not any(
            message.get("tool") == "send_message" and message.get("images")
            for message in messages
        ),
    }

    return {
        "scenario_id": scenario["id"],
        "passed": all(checks.values()),
        "checks": checks,
        "message_count": len(messages),
        "present_outfit_count": len(present_calls),
        "repeated_items": repeated_items[:8],
        "wof_names": wof_names,
        "capsule_text": first_send_text,
        "response": response,
        "output_messages": messages,
        "tool_trace": [
            {
                "tool": entry.get("tool"),
                "args": entry.get("args"),
            }
            for entry in agent.turn_log
            if entry.get("type") == "tool_result"
        ],
    }


def run_eval(scenario_filter: str | None = None) -> list[dict[str, Any]]:
    _patch_web_search()
    preloaded = preload_user_context("peichin")
    results = []

    scenarios = [
        scenario
        for scenario in SCENARIOS
        if not scenario_filter or scenario_filter.lower() in scenario["id"].lower()
    ]
    if not scenarios:
        raise ValueError(f"No packing scenario matched: {scenario_filter}")

    for scenario in scenarios:
        output = MockOutput()
        agent = StylingAgent(
            user_id="peichin",
            provider="openai",
            model=os.getenv("PACKING_EVAL_MODEL") or None,
            output=output,
            preloaded_context=preloaded,
        )

        start = time.time()
        response = agent.run(scenario["message"])
        result = _validate_scenario(scenario, response, output, agent)
        result["latency_seconds"] = round(time.time() - start, 1)
        result["token_usage"] = {
            "input": agent.total_input_tokens,
            "output": agent.total_output_tokens,
            "cached": agent.total_cached_tokens,
        }
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n[{status}] {scenario['id']} ({result['latency_seconds']}s)")
        print(json.dumps(result["checks"], indent=2))
        if result["repeated_items"]:
            print("Repeated items:", ", ".join(result["repeated_items"]))
        print("Capsule:", result["capsule_text"][:500].replace("\n", " / "))

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", help="Run only scenarios whose id contains this text")
    args = parser.parse_args()

    results = run_eval(args.scenario)
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"packing_policy_eval_{int(time.time())}.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote results: {output_path}")

    failed = [result for result in results if not result["passed"]]
    if failed:
        print("\nFailed scenarios:", ", ".join(result["scenario_id"] for result in failed))
        return 1

    print("\nAll packing policy scenarios passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
