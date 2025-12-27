"""
Diagnostic Tests for Understanding Model Outfit Generation Reasoning

This script executes comprehensive tests to understand:
1. Item frequency patterns in outfit generation
2. Model substitution behavior when items are excluded
3. Model self-evaluation and reasoning
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from services.style_engine import StyleGenerationEngine
from services.wardrobe_manager import WardrobeManager


class DiagnosticTest:
    """Orchestrates diagnostic testing for outfit generation"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.wardrobe = self._load_wardrobe()
        self.scenario = self._get_outdoor_wedding_scenario()
        self.findings = {
            "test_1a": [],  # Baseline generations
            "test_1b": [],  # Forced exclusion generations
            "test_1c": [],  # Evaluation comparison
            "test_2": {},   # Self-report Q&A
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "total_wardrobe_items": len(self.wardrobe)
            }
        }

    def _load_wardrobe(self) -> List[Dict]:
        """Load wardrobe for testing"""
        print(f"📦 Loading wardrobe for user: {self.user_id}")
        wm = WardrobeManager(user_id=self.user_id)
        wardrobe_data = wm.load_wardrobe_data()
        items = wardrobe_data.get('items', [])

        if not items:
            raise ValueError(f"No wardrobe items found for user {self.user_id}")

        print(f"✅ Loaded {len(items)} items")
        return items

    def _get_outdoor_wedding_scenario(self) -> Dict:
        """Get outdoor wedding test scenario"""
        return {
            "id": "occasion_wedding_diagnostic",
            "name": "Outdoor Wedding - Diagnostic Test",
            "occasion": "outdoor wedding in the afternoon",
            "weather": "sunny and warm",
            "temperature_range": "75-85°F",
            "style_profile": {
                "three_words": {
                    "current": "classic",
                    "aspirational": "relaxed",
                    "feeling": "playful"
                }
            }
        }

    def _create_engine(self, model: str = "gpt-4o", temperature: float = 0.7) -> StyleGenerationEngine:
        """Create a style generation engine"""
        return StyleGenerationEngine(
            model=model,
            temperature=temperature,
            max_tokens=2000,
            prompt_version="baseline_v1"
        )

    def _generate_outfits(
        self,
        engine: StyleGenerationEngine,
        num_outfits: int = 3,
        exclusion_constraint: str = None
    ) -> List[Dict]:
        """Generate outfits with optional exclusion constraint"""

        # Build custom prompt with exclusion if needed
        if exclusion_constraint:
            # We'll inject this into the occasion field temporarily
            modified_occasion = f"{self.scenario['occasion']} (CONSTRAINT: {exclusion_constraint})"
            occasion = modified_occasion
        else:
            occasion = self.scenario['occasion']

        try:
            outfits = engine.generate_outfit_combinations(
                user_profile=self.scenario['style_profile'],
                available_items=self.wardrobe,
                styling_challenges=[],
                occasion=occasion,
                weather_condition=self.scenario['weather'],
                temperature_range=self.scenario['temperature_range']
            )
            return outfits
        except Exception as e:
            print(f"❌ Error generating outfits: {e}")
            return []

    def _ask_model_question(self, question: str, context: str = "") -> str:
        """Ask the model a direct question"""
        from services.ai_provider import AIProvider

        provider = AIProvider()
        messages = []

        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            })
        else:
            messages.append({
                "role": "user",
                "content": question
            })

        try:
            response = provider.chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.7
            )
            return response['content']
        except Exception as e:
            return f"Error: {str(e)}"

    def run_test_1a_baseline(self, iterations: int = 5):
        """Test 1A: Baseline Generation (5 outfits)"""
        print("\n" + "="*80)
        print("TEST 1A: Baseline Generation (5 outfit sets)")
        print("="*80)

        engine = self._create_engine()

        for i in range(iterations):
            print(f"\n🎨 Generating outfit set {i+1}/{iterations}...")

            outfits = self._generate_outfits(engine, num_outfits=3)

            result = {
                "iteration": i + 1,
                "timestamp": datetime.now().isoformat(),
                "num_outfits": len(outfits),
                "outfits": []
            }

            for idx, outfit in enumerate(outfits):
                # Handle OutfitCombination objects (Pydantic models)
                if hasattr(outfit, 'items'):
                    items = [item.name if hasattr(item, 'name') else str(item) for item in outfit.items]
                    styling_notes = outfit.styling_notes if hasattr(outfit, 'styling_notes') else ''
                    why_it_works = outfit.why_it_works if hasattr(outfit, 'why_it_works') else ''
                else:
                    # Fallback to dict access
                    items = outfit.get('items', [])
                    styling_notes = outfit.get('styling_notes', '')
                    why_it_works = outfit.get('why_it_works', '')

                # Check for target items
                has_white_sneakers = any('white' in item.lower() and 'sneaker' in item.lower() for item in items)
                has_white_button_down = any('white' in item.lower() and ('button' in item.lower() or 'shirt' in item.lower()) for item in items)

                outfit_result = {
                    "outfit_num": idx + 1,
                    "items": items,
                    "has_white_sneakers": has_white_sneakers,
                    "has_white_button_down": has_white_button_down,
                    "styling_notes": styling_notes,
                    "why_it_works": why_it_works
                }

                result["outfits"].append(outfit_result)

                print(f"  Outfit {idx+1}: {len(items)} items")
                for item in items:
                    marker = ""
                    if 'white' in item.lower() and 'sneaker' in item.lower():
                        marker = " 🔴 WHITE SNEAKERS"
                    elif 'white' in item.lower() and ('button' in item.lower() or 'shirt' in item.lower()):
                        marker = " 🔴 WHITE SHIRT"
                    print(f"    - {item}{marker}")

            self.findings["test_1a"].append(result)
            time.sleep(1)  # Rate limiting

    def run_test_1b_forced_exclusion(self, iterations: int = 5):
        """Test 1B: Forced Exclusion (5 outfit sets)"""
        print("\n" + "="*80)
        print("TEST 1B: Forced Exclusion (5 outfit sets)")
        print("="*80)

        exclusion = "Do NOT use white sneakers with red Nike logo OR white button-down shirt with ruffled details"
        print(f"Constraint: {exclusion}\n")

        engine = self._create_engine()

        for i in range(iterations):
            print(f"\n🎨 Generating constrained outfit set {i+1}/{iterations}...")

            outfits = self._generate_outfits(engine, num_outfits=3, exclusion_constraint=exclusion)

            result = {
                "iteration": i + 1,
                "timestamp": datetime.now().isoformat(),
                "num_outfits": len(outfits),
                "exclusion_constraint": exclusion,
                "outfits": []
            }

            for idx, outfit in enumerate(outfits):
                # Handle OutfitCombination objects (Pydantic models)
                if hasattr(outfit, 'items'):
                    items = [item.name if hasattr(item, 'name') else str(item) for item in outfit.items]
                    styling_notes = outfit.styling_notes if hasattr(outfit, 'styling_notes') else ''
                    why_it_works = outfit.why_it_works if hasattr(outfit, 'why_it_works') else ''
                else:
                    items = outfit.get('items', [])
                    styling_notes = outfit.get('styling_notes', '')
                    why_it_works = outfit.get('why_it_works', '')

                # Check for target items (should NOT appear)
                has_white_sneakers = any('white' in item.lower() and 'sneaker' in item.lower() for item in items)
                has_white_button_down = any('white' in item.lower() and ('button' in item.lower() or 'shirt' in item.lower()) for item in items)

                # Find substitutes
                shoes = [item for item in items if any(shoe_word in item.lower() for shoe_word in ['shoe', 'boot', 'sneaker', 'heel', 'sandal', 'loafer'])]
                tops = [item for item in items if any(top_word in item.lower() for top_word in ['shirt', 'top', 'blouse', 't-shirt', 'tee'])]

                outfit_result = {
                    "outfit_num": idx + 1,
                    "items": items,
                    "has_white_sneakers": has_white_sneakers,
                    "has_white_button_down": has_white_button_down,
                    "shoe_substitutes": shoes,
                    "top_substitutes": tops,
                    "styling_notes": styling_notes,
                    "why_it_works": why_it_works
                }

                result["outfits"].append(outfit_result)

                print(f"  Outfit {idx+1}: {len(items)} items")
                if shoes:
                    print(f"    Shoes: {', '.join(shoes)}")
                if tops:
                    print(f"    Tops: {', '.join(tops)}")

            self.findings["test_1b"].append(result)
            time.sleep(1)  # Rate limiting

    def run_test_1c_evaluation(self):
        """Test 1C: Model evaluation of two outfits"""
        print("\n" + "="*80)
        print("TEST 1C: Model Evaluation Comparison")
        print("="*80)

        if not self.findings["test_1a"]:
            print("⚠️  No baseline results to evaluate")
            return

        # Find one outfit with white items and one without
        outfit_with = None
        outfit_without = None

        for result in self.findings["test_1a"]:
            for outfit in result["outfits"]:
                if outfit["has_white_sneakers"] or outfit["has_white_button_down"]:
                    if not outfit_with:
                        outfit_with = outfit
                else:
                    if not outfit_without:
                        outfit_without = outfit

                if outfit_with and outfit_without:
                    break
            if outfit_with and outfit_without:
                break

        if not outfit_with or not outfit_without:
            print("⚠️  Could not find suitable outfits to compare")
            return

        # Ask model to compare
        context = f"""
Scenario: {self.scenario['occasion']}, {self.scenario['weather']}, {self.scenario['temperature_range']}
Style Profile: Classic (current), Relaxed (aspirational), Playful (feeling)

Outfit A:
{', '.join(outfit_with['items'])}

Outfit B:
{', '.join(outfit_without['items'])}
"""

        question = "Which outfit do you think is better for this outdoor wedding? Why?"

        print("\n📝 Asking model to evaluate two outfits...")
        print(f"Outfit A includes: {', '.join([i for i in outfit_with['items'] if 'white' in i.lower()])}")
        print(f"Outfit B: Different items")

        response = self._ask_model_question(question, context)

        self.findings["test_1c"] = {
            "outfit_a": outfit_with,
            "outfit_b": outfit_without,
            "question": question,
            "model_response": response
        }

        print(f"\n💭 Model's response:\n{response}")

    def run_test_2_self_report(self):
        """Test 2: Self-report questions about creative process"""
        print("\n" + "="*80)
        print("TEST 2: Self-Report Questions")
        print("="*80)

        if not self.findings["test_1a"]:
            print("⚠️  No baseline results to query")
            return

        # Find an outfit with high-frequency items
        target_outfit = None
        for result in self.findings["test_1a"]:
            for outfit in result["outfits"]:
                if outfit["has_white_sneakers"] or outfit["has_white_button_down"]:
                    target_outfit = outfit
                    break
            if target_outfit:
                break

        if not target_outfit:
            print("⚠️  No outfit with target items found")
            return

        # Prepare context
        context = f"""
I asked you to create an outfit for an outdoor wedding in the afternoon (sunny and warm, 75-85°F).
The user's style profile: Classic (current), Relaxed (aspirational), Playful (feeling).

You created this outfit:
{', '.join(target_outfit['items'])}

Styling notes: {target_outfit['styling_notes']}
Why it works: {target_outfit['why_it_works']}
"""

        # Q1: Creative process
        print("\n📝 Question 1: Creative process...")
        q1 = "Thank you for this outfit. I'm curious about your creative process. How did you put this outfit together? Walk me through your thinking."
        a1 = self._ask_model_question(q1, context)
        print(f"💭 Response:\n{a1}\n")

        # Q2: Specific item choice
        print("\n📝 Question 2: White sneaker choice...")
        has_sneakers = target_outfit["has_white_sneakers"]
        if has_sneakers:
            q2 = "I notice you selected white sneakers for this outfit. What made you choose these sneakers for an afternoon wedding?"
            a2 = self._ask_model_question(q2, context)
            print(f"💭 Response:\n{a2}\n")
        else:
            q2 = "I notice you didn't use white sneakers for this outfit. Was that a deliberate choice?"
            a2 = self._ask_model_question(q2, context)
            print(f"💭 Response:\n{a2}\n")

        # Q3: Constraint awareness
        print("\n📝 Question 3: Constraint awareness...")

        # Show baseline vs constrained comparison
        baseline_items = []
        constrained_items = []

        if self.findings["test_1a"] and self.findings["test_1b"]:
            baseline_items = self.findings["test_1a"][0]["outfits"][0]["items"]
            constrained_items = self.findings["test_1b"][0]["outfits"][0]["items"]

        comparison_context = f"""
When I asked for wedding outfits with no constraints, you created:
{', '.join(baseline_items)}

When I asked you to avoid white sneakers and white button-down shirts, you created:
{', '.join(constrained_items)}
"""

        q3 = "I see when I asked you to avoid certain pieces, you created different outfits. What do you notice changed about the overall feeling or vibe?"
        a3 = self._ask_model_question(q3, comparison_context)
        print(f"💭 Response:\n{a3}\n")

        self.findings["test_2"] = {
            "target_outfit": target_outfit,
            "q1_creative_process": {"question": q1, "answer": a1},
            "q2_item_choice": {"question": q2, "answer": a2},
            "q3_constraint_awareness": {"question": q3, "answer": a3}
        }

    def analyze_frequency_patterns(self) -> Dict:
        """Analyze item frequency patterns across all tests"""
        print("\n" + "="*80)
        print("ANALYZING FREQUENCY PATTERNS")
        print("="*80)

        # Count white sneakers and white button-down appearances
        baseline_sneakers = 0
        baseline_button_down = 0
        baseline_total = 0

        constrained_sneakers = 0
        constrained_button_down = 0
        constrained_total = 0

        for result in self.findings["test_1a"]:
            for outfit in result["outfits"]:
                baseline_total += 1
                if outfit["has_white_sneakers"]:
                    baseline_sneakers += 1
                if outfit["has_white_button_down"]:
                    baseline_button_down += 1

        for result in self.findings["test_1b"]:
            for outfit in result["outfits"]:
                constrained_total += 1
                if outfit["has_white_sneakers"]:
                    constrained_sneakers += 1
                if outfit["has_white_button_down"]:
                    constrained_button_down += 1

        analysis = {
            "baseline": {
                "total_outfits": baseline_total,
                "white_sneakers_count": baseline_sneakers,
                "white_sneakers_frequency": baseline_sneakers / baseline_total if baseline_total > 0 else 0,
                "white_button_down_count": baseline_button_down,
                "white_button_down_frequency": baseline_button_down / baseline_total if baseline_total > 0 else 0
            },
            "constrained": {
                "total_outfits": constrained_total,
                "white_sneakers_count": constrained_sneakers,
                "white_sneakers_frequency": constrained_sneakers / constrained_total if constrained_total > 0 else 0,
                "white_button_down_count": constrained_button_down,
                "white_button_down_frequency": constrained_button_down / constrained_total if constrained_total > 0 else 0
            }
        }

        print(f"\n📊 Baseline Results ({baseline_total} outfits):")
        print(f"  White sneakers: {baseline_sneakers} appearances ({analysis['baseline']['white_sneakers_frequency']:.1%})")
        print(f"  White button-down: {baseline_button_down} appearances ({analysis['baseline']['white_button_down_frequency']:.1%})")

        print(f"\n📊 Constrained Results ({constrained_total} outfits):")
        print(f"  White sneakers: {constrained_sneakers} appearances ({analysis['constrained']['white_sneakers_frequency']:.1%})")
        print(f"  White button-down: {constrained_button_down} appearances ({analysis['constrained']['white_button_down_frequency']:.1%})")

        return analysis

    def save_findings(self, output_path: str):
        """Save all findings to markdown file"""
        print(f"\n💾 Saving findings to {output_path}")

        # Add frequency analysis
        self.findings["frequency_analysis"] = self.analyze_frequency_patterns()

        # Generate markdown report
        md = self._generate_markdown_report()

        with open(output_path, 'w') as f:
            f.write(md)

        # Also save raw JSON
        json_path = output_path.replace('.md', '_raw.json')
        with open(json_path, 'w') as f:
            json.dump(self.findings, f, indent=2, default=str)

        print(f"✅ Saved findings to {output_path}")
        print(f"✅ Saved raw data to {json_path}")

    def _generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        md = "# Diagnostic Findings: Model Outfit Generation Reasoning\n\n"
        md += f"**Generated:** {self.findings['metadata']['timestamp']}\n"
        md += f"**User ID:** {self.findings['metadata']['user_id']}\n"
        md += f"**Total Wardrobe Items:** {self.findings['metadata']['total_wardrobe_items']}\n\n"

        md += "---\n\n"

        # Frequency Analysis Summary
        if "frequency_analysis" in self.findings:
            fa = self.findings["frequency_analysis"]
            md += "## Executive Summary: Frequency Patterns\n\n"

            baseline = fa["baseline"]
            constrained = fa["constrained"]

            md += f"### Baseline Generation ({baseline['total_outfits']} outfits)\n"
            md += f"- **White sneakers:** {baseline['white_sneakers_count']} appearances ({baseline['white_sneakers_frequency']:.1%})\n"
            md += f"- **White button-down:** {baseline['white_button_down_count']} appearances ({baseline['white_button_down_frequency']:.1%})\n\n"

            md += f"### Constrained Generation ({constrained['total_outfits']} outfits)\n"
            md += f"- **White sneakers:** {constrained['white_sneakers_count']} appearances ({constrained['white_sneakers_frequency']:.1%})\n"
            md += f"- **White button-down:** {constrained['white_button_down_count']} appearances ({constrained['white_button_down_frequency']:.1%})\n\n"

            # Observations
            md += "### Key Observations\n\n"

            if constrained['white_sneakers_count'] > 0 or constrained['white_button_down_count'] > 0:
                md += "⚠️ **Constraint violation detected:** Model used excluded items even when explicitly told not to.\n\n"

            if baseline['white_sneakers_frequency'] > 0.5 or baseline['white_button_down_frequency'] > 0.5:
                md += f"📈 **High baseline frequency:** Target items appeared in >50% of baseline outfits.\n\n"

        md += "---\n\n"

        # Test 1A: Baseline
        md += "## Test 1A: Baseline Generation\n\n"
        md += "**Objective:** Generate 5 outfit sets (15 total outfits) for outdoor wedding scenario without constraints.\n\n"

        for result in self.findings.get("test_1a", []):
            md += f"### Iteration {result['iteration']}\n\n"
            for outfit in result["outfits"]:
                md += f"#### Outfit {outfit['outfit_num']}\n\n"
                md += "**Items:**\n"
                for item in outfit["items"]:
                    marker = ""
                    if 'white' in item.lower() and 'sneaker' in item.lower():
                        marker = " 🔴 **[TARGET: WHITE SNEAKERS]**"
                    elif 'white' in item.lower() and ('button' in item.lower() or 'shirt' in item.lower()):
                        marker = " 🔴 **[TARGET: WHITE SHIRT]**"
                    md += f"- {item}{marker}\n"
                md += f"\n**Styling Notes:** {outfit['styling_notes']}\n\n"
                md += f"**Why It Works:** {outfit['why_it_works']}\n\n"

        md += "---\n\n"

        # Test 1B: Constrained
        md += "## Test 1B: Forced Exclusion Generation\n\n"
        md += "**Objective:** Generate 5 outfit sets with explicit constraint to avoid white sneakers and white button-down.\n\n"

        if self.findings.get("test_1b"):
            md += f"**Constraint:** {self.findings['test_1b'][0].get('exclusion_constraint', 'N/A')}\n\n"

        for result in self.findings.get("test_1b", []):
            md += f"### Iteration {result['iteration']}\n\n"
            for outfit in result["outfits"]:
                md += f"#### Outfit {outfit['outfit_num']}\n\n"
                md += "**Items:**\n"
                for item in outfit["items"]:
                    marker = ""
                    if 'white' in item.lower() and 'sneaker' in item.lower():
                        marker = " ⚠️ **[CONSTRAINT VIOLATION: WHITE SNEAKERS]**"
                    elif 'white' in item.lower() and ('button' in item.lower() or 'shirt' in item.lower()):
                        marker = " ⚠️ **[CONSTRAINT VIOLATION: WHITE SHIRT]**"
                    md += f"- {item}{marker}\n"

                md += "\n**Substitutes:**\n"
                md += f"- Shoes: {', '.join(outfit['shoe_substitutes']) if outfit['shoe_substitutes'] else 'None identified'}\n"
                md += f"- Tops: {', '.join(outfit['top_substitutes']) if outfit['top_substitutes'] else 'None identified'}\n\n"

                md += f"**Styling Notes:** {outfit['styling_notes']}\n\n"
                md += f"**Why It Works:** {outfit['why_it_works']}\n\n"

        md += "---\n\n"

        # Test 1C: Evaluation
        md += "## Test 1C: Model Self-Evaluation\n\n"
        md += "**Objective:** Ask model to compare and evaluate two outfits.\n\n"

        if self.findings.get("test_1c"):
            tc = self.findings["test_1c"]
            md += f"**Question:** {tc.get('question', 'N/A')}\n\n"

            md += "### Outfit A (with target items)\n"
            for item in tc["outfit_a"]["items"]:
                md += f"- {item}\n"
            md += "\n"

            md += "### Outfit B (without target items)\n"
            for item in tc["outfit_b"]["items"]:
                md += f"- {item}\n"
            md += "\n"

            md += f"### Model's Response\n\n{tc.get('model_response', 'N/A')}\n\n"

        md += "---\n\n"

        # Test 2: Self-Report
        md += "## Test 2: Self-Report Questions\n\n"
        md += "**Objective:** Probe model's reasoning about its creative process.\n\n"

        if self.findings.get("test_2"):
            t2 = self.findings["test_2"]

            md += "### Target Outfit\n\n"
            for item in t2["target_outfit"]["items"]:
                md += f"- {item}\n"
            md += "\n"

            md += "### Q1: Creative Process\n\n"
            md += f"**Question:** {t2['q1_creative_process']['question']}\n\n"
            md += f"**Answer:** {t2['q1_creative_process']['answer']}\n\n"

            md += "### Q2: Item Choice\n\n"
            md += f"**Question:** {t2['q2_item_choice']['question']}\n\n"
            md += f"**Answer:** {t2['q2_item_choice']['answer']}\n\n"

            md += "### Q3: Constraint Awareness\n\n"
            md += f"**Question:** {t2['q3_constraint_awareness']['question']}\n\n"
            md += f"**Answer:** {t2['q3_constraint_awareness']['answer']}\n\n"

        md += "---\n\n"

        # Analysis Section
        md += "## Analysis and Observations\n\n"
        md += "### Substitution Patterns\n\n"
        md += "_What items did the model choose instead when constrained?_\n\n"

        # Collect substitutes
        all_shoe_subs = set()
        all_top_subs = set()
        for result in self.findings.get("test_1b", []):
            for outfit in result["outfits"]:
                all_shoe_subs.update(outfit.get("shoe_substitutes", []))
                all_top_subs.update(outfit.get("top_substitutes", []))

        if all_shoe_subs:
            md += "**Shoe substitutes:**\n"
            for sub in sorted(all_shoe_subs):
                md += f"- {sub}\n"
            md += "\n"

        if all_top_subs:
            md += "**Top substitutes:**\n"
            for sub in sorted(all_top_subs):
                md += f"- {sub}\n"
            md += "\n"

        md += "### Quality Comparison\n\n"
        md += "_Did constrained outfits seem better, worse, or similar to baseline?_\n\n"
        md += "TODO: Add qualitative assessment after manual review.\n\n"

        md += "### Model Reasoning Insights\n\n"
        md += "_What do the self-report answers reveal about model reasoning?_\n\n"
        md += "TODO: Add analysis of Q&A responses.\n\n"

        return md


def main():
    parser = argparse.ArgumentParser(description='Run diagnostic tests for outfit generation')
    parser.add_argument('--user-id', default='default', help='User ID for wardrobe (default: default)')
    parser.add_argument('--output', default=None, help='Output markdown file path')

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_dir = Path(__file__).parent.parent
        output_path = output_dir / 'DIAGNOSTIC_FINDINGS.md'

    print("\n" + "="*80)
    print("DIAGNOSTIC TEST SUITE: Model Outfit Generation Reasoning")
    print("="*80)
    print(f"User ID: {args.user_id}")
    print(f"Output: {output_path}")
    print("="*80 + "\n")

    # Initialize test
    test = DiagnosticTest(user_id=args.user_id)

    # Run all tests
    test.run_test_1a_baseline(iterations=5)
    test.run_test_1b_forced_exclusion(iterations=5)
    test.run_test_1c_evaluation()
    test.run_test_2_self_report()

    # Save findings
    test.save_findings(str(output_path))

    print("\n" + "="*80)
    print("✅ DIAGNOSTIC TEST SUITE COMPLETE")
    print("="*80)
    print(f"\n📄 Report: {output_path}")
    print(f"📄 Raw data: {str(output_path).replace('.md', '_raw.json')}")
    print("\nNext steps:")
    print("1. Review the markdown report for patterns and insights")
    print("2. Analyze the self-report Q&A for reasoning transparency")
    print("3. Compare baseline vs constrained quality")


if __name__ == '__main__':
    main()
