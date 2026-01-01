"""
Streaming Time Study
====================
Measures when each part of the outfit generation response arrives during streaming.

This helps us understand:
1. How quickly do tokens start arriving?
2. When does outfit 1 reasoning complete vs outfit 2 vs outfit 3?
3. When does the JSON section start?
4. Is streaming worth implementing?

Run from backend directory:
    python tests/streaming_time_study.py
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from services.ai.providers.openai import OpenAIProvider
from services.ai.providers.base import AIProviderConfig

# Markers to detect in the stream
MARKERS = [
    # Outfit boundaries - look for FUNCTION: which starts each outfit's reasoning
    ("OUTFIT_1_START", "FUNCTION:"),  # First FUNCTION: = outfit 1
    ("OUTFIT_2_START", "\n\nFUNCTION:"),  # Second FUNCTION: after newlines = outfit 2
    ("OUTFIT_3_START", None),  # Will detect 3rd FUNCTION: programmatically

    # Other key sections
    ("JSON_SEPARATOR", "===JSON OUTPUT==="),
    ("JSON_START", "["),  # First [ after separator
    ("JSON_END", "]"),  # Final ]

    # Reasoning sections (to see granular timing)
    ("ANCHOR_1", "ANCHOR:"),
    ("SUPPORTING_1", "SUPPORTING PIECES:"),
    ("UNEXPECTED_1", "UNEXPECTED ELEMENT:"),
    ("STORY_1", "STORY:"),
    ("FINAL_OUTFIT_1", "FINAL OUTFIT:"),
]


def create_test_prompt():
    """Create a realistic outfit generation prompt with minimal wardrobe"""
    return """You are a fashion editor styling real people for a "Best Dressed" feature. Your signature is the "unexpected perfect" - outfits that are completely appropriate but have one element that makes people stop and say "I wouldn't have thought of that, but it works."

---

## USER CONTEXT

Style DNA: classic + edgy + wants to feel confident
Occasion: casual weekend brunch

---

## AVAILABLE WARDROBE

TOPS:
- White linen button-down shirt (relaxed fit, lightweight)
- Black silk camisole (delicate straps, subtle sheen)
- Cream chunky knit sweater (oversized, cozy)
- Navy breton stripe tee (boat neck, classic)

BOTTOMS:
- High-waisted wide-leg jeans (medium wash, cropped)
- Black leather midi skirt (A-line, knee length)
- Khaki chinos (straight leg, ankle length)
- Navy pleated trousers (tailored, full length)

OUTERWEAR:
- Camel wool coat (structured, knee length)
- Black leather moto jacket (cropped, silver hardware)
- Denim jacket (classic wash, slightly oversized)

SHOES:
- White leather sneakers (minimal, clean)
- Black ankle boots (pointed toe, block heel)
- Tan suede loafers (classic penny style)
- Black strappy sandals (kitten heel)

ACCESSORIES:
- Gold hoop earrings (medium size)
- Silk scarf (cream with navy pattern)
- Black leather belt (silver buckle)
- Brown leather crossbody bag

---

## OUTFIT CONSTRUCTION PROCESS

For each outfit, think through these steps:

**STEP 1: FUNCTION**
What must this outfit accomplish? Name the ONE primary job.

**STEP 2: ANCHOR**
Select the HERO piece - the one that makes this outfit worth photographing.
Note which style word(s) this piece carries.

**STEP 3: SUPPORTING PIECES**
Select 2-4 pieces that complete the outfit.

**STEP 4: IDENTIFY THE UNEXPECTED ELEMENT**
From your supporting pieces, identify THE ONE that breaks a conventional expectation.

**STEP 5: STYLE DNA CHECK**
Verify all three words are present.

**STEP 6: COMPLETE THE LOOK**
Every outfit MUST include footwear.

**STEP 7: STORY**
Complete: "This outfit says: I'm someone who ___"

**STEP 8: FINAL CHECK**
Physical and function verification.

---

## REQUIREMENTS

1. Create 3 outfits
2. Each outfit MUST have an explicitly named unexpected element
3. Anchor pieces must be DIFFERENT across all 3 outfits
4. No item can appear in more than 2 of the 3 outfits
5. Each outfit must carry ALL THREE style words
6. Each outfit must be COMPLETE - including shoes
7. Show reasoning for each step

---

## OUTPUT FORMAT

For each outfit, first show your reasoning:

FUNCTION: [What this outfit needs to accomplish]

ANCHOR: [Item name]
- Why it's the hero: [One sentence]
- Style words: [Which it carries]

SUPPORTING PIECES:
- [Item]: [How it supports] - carries [style word]
- [Item]: [How it supports] - carries [style word]
- Contrast created: [Texture/volume/structure contrast]

UNEXPECTED ELEMENT: [One of the items listed above]
- Breaks: [Convention]
- Works because: [Resolution]

STYLE DNA: classic ✓ [item] | edgy ✓ [item] | confident ✓ [item]

COMPLETING THE LOOK:
- [Any items added to complete the silhouette and why]

STORY: "I'm someone who ___"

PHYSICAL CHECK: [Brief confirmation pieces work together]

FINAL OUTFIT:
- [Item 1]
- [Item 2]
- [etc.]

STYLING: [Concrete details - tucked/untucked, sleeves, etc.]

---

## FINAL OUTPUT

First, show your complete reasoning for all 3 outfits using the format above.

Then, you MUST include this exact line:
===JSON OUTPUT===

After that line, output ONLY the JSON array:

[
  {
    "items": ["item name 1", "item name 2", ...],
    "styling_notes": "Specific instructions",
    "why_it_works": "2-4 sentences explaining the outfit"
  }
]

CRITICAL: You MUST include both the reasoning AND the JSON.
"""


def run_streaming_time_study():
    """Run the streaming time study and collect timing data"""

    print("=" * 70)
    print("STREAMING TIME STUDY")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print()

    # Setup provider
    config = AIProviderConfig(
        model='gpt-4o',
        api_key=os.getenv('OPENAI_API_KEY'),
        temperature=0.7,
        max_tokens=4000
    )
    provider = OpenAIProvider(config)

    prompt = create_test_prompt()
    system_message = "You are a fashion editor. Show your reasoning for each step, then return valid JSON."

    # Tracking variables
    start_time = time.time()
    chunks = []  # List of (timestamp, chunk_text, cumulative_text)
    cumulative_text = ""

    # Marker tracking
    marker_times = {}
    function_count = 0
    json_section_started = False

    print("Starting stream...")
    print("-" * 70)

    # Stream and collect all chunks with timestamps
    first_chunk_time = None

    for chunk in provider.generate_text_stream(prompt, system_message=system_message):
        chunk_time = time.time() - start_time

        if first_chunk_time is None:
            first_chunk_time = chunk_time
            marker_times["FIRST_TOKEN"] = chunk_time
            print(f"\n[{chunk_time:6.2f}s] FIRST TOKEN RECEIVED")

        cumulative_text += chunk
        chunks.append((chunk_time, chunk, cumulative_text))

        # Print chunk with timestamp (abbreviated for readability)
        chunk_display = chunk.replace('\n', '\\n')[:50]
        print(f"[{chunk_time:6.2f}s] {chunk_display}")

        # Detect markers
        # Track FUNCTION: occurrences (each outfit starts with FUNCTION:)
        if "FUNCTION:" in chunk:
            function_count += 1
            if function_count == 1 and "OUTFIT_1_START" not in marker_times:
                marker_times["OUTFIT_1_START"] = chunk_time
                print(f"\n>>> [{chunk_time:6.2f}s] OUTFIT 1 REASONING STARTED <<<\n")
            elif function_count == 2 and "OUTFIT_2_START" not in marker_times:
                marker_times["OUTFIT_2_START"] = chunk_time
                print(f"\n>>> [{chunk_time:6.2f}s] OUTFIT 2 REASONING STARTED <<<\n")
            elif function_count == 3 and "OUTFIT_3_START" not in marker_times:
                marker_times["OUTFIT_3_START"] = chunk_time
                print(f"\n>>> [{chunk_time:6.2f}s] OUTFIT 3 REASONING STARTED <<<\n")

        # Track JSON section
        if "===JSON OUTPUT===" in cumulative_text and "JSON_SEPARATOR" not in marker_times:
            marker_times["JSON_SEPARATOR"] = chunk_time
            json_section_started = True
            print(f"\n>>> [{chunk_time:6.2f}s] JSON SECTION STARTED <<<\n")

        # Track JSON array start (first [ after separator)
        if json_section_started and "[" in chunk and "JSON_ARRAY_START" not in marker_times:
            marker_times["JSON_ARRAY_START"] = chunk_time

    end_time = time.time() - start_time
    marker_times["COMPLETE"] = end_time

    print("-" * 70)
    print()

    # Summary
    print("=" * 70)
    print("TIMING SUMMARY")
    print("=" * 70)
    print()

    print(f"Total generation time: {end_time:.2f}s")
    print(f"Total chunks received: {len(chunks)}")
    print(f"Total characters: {len(cumulative_text)}")
    print()

    print("KEY MILESTONES:")
    print("-" * 40)

    milestones = [
        ("First token", "FIRST_TOKEN"),
        ("Outfit 1 reasoning", "OUTFIT_1_START"),
        ("Outfit 2 reasoning", "OUTFIT_2_START"),
        ("Outfit 3 reasoning", "OUTFIT_3_START"),
        ("JSON section", "JSON_SEPARATOR"),
        ("JSON array start", "JSON_ARRAY_START"),
        ("Complete", "COMPLETE"),
    ]

    prev_time = 0
    for label, key in milestones:
        if key in marker_times:
            t = marker_times[key]
            delta = t - prev_time
            print(f"  {label:25} {t:6.2f}s  (+{delta:.2f}s)")
            prev_time = t
        else:
            print(f"  {label:25} NOT DETECTED")

    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    # Calculate useful metrics
    if "OUTFIT_1_START" in marker_times and "OUTFIT_2_START" in marker_times:
        outfit1_duration = marker_times["OUTFIT_2_START"] - marker_times["OUTFIT_1_START"]
        print(f"Outfit 1 reasoning duration: {outfit1_duration:.2f}s")

    if "OUTFIT_2_START" in marker_times and "OUTFIT_3_START" in marker_times:
        outfit2_duration = marker_times["OUTFIT_3_START"] - marker_times["OUTFIT_2_START"]
        print(f"Outfit 2 reasoning duration: {outfit2_duration:.2f}s")

    if "OUTFIT_3_START" in marker_times and "JSON_SEPARATOR" in marker_times:
        outfit3_duration = marker_times["JSON_SEPARATOR"] - marker_times["OUTFIT_3_START"]
        print(f"Outfit 3 reasoning duration: {outfit3_duration:.2f}s")

    if "JSON_SEPARATOR" in marker_times:
        reasoning_total = marker_times["JSON_SEPARATOR"]
        json_duration = end_time - marker_times["JSON_SEPARATOR"]
        print(f"\nTotal reasoning time: {reasoning_total:.2f}s")
        print(f"JSON generation time: {json_duration:.2f}s")

    print()

    # Streaming value assessment
    if "OUTFIT_1_START" in marker_times:
        first_outfit_time = marker_times.get("OUTFIT_2_START", end_time) - marker_times["OUTFIT_1_START"]
        print("STREAMING VALUE ASSESSMENT:")
        print("-" * 40)
        print(f"Time to first meaningful content: {marker_times.get('FIRST_TOKEN', 0):.2f}s")
        print(f"Time to complete outfit 1 reasoning: {marker_times.get('OUTFIT_2_START', end_time):.2f}s")

        if marker_times.get('OUTFIT_2_START', end_time) < end_time * 0.5:
            print("\n✅ HIGH VALUE: Outfit 1 completes in first half of generation")
            print("   Users could see outfit 1 reasoning while 2 & 3 generate")
        elif marker_times.get('OUTFIT_2_START', end_time) < end_time * 0.75:
            print("\n⚠️  MEDIUM VALUE: Outfit 1 completes in first 75% of generation")
        else:
            print("\n❌ LOW VALUE: Outfit 1 takes most of the generation time")

    # Save raw data
    output_file = "tests/streaming_time_study_results.txt"
    with open(output_file, "w") as f:
        f.write("STREAMING TIME STUDY RAW DATA\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Model: gpt-4o\n")
        f.write(f"Total time: {end_time:.2f}s\n")
        f.write(f"Total chunks: {len(chunks)}\n\n")

        f.write("MARKER TIMES:\n")
        for key, t in sorted(marker_times.items(), key=lambda x: x[1]):
            f.write(f"  {key}: {t:.3f}s\n")

        f.write("\n\nALL CHUNKS:\n")
        f.write("-" * 70 + "\n")
        for t, chunk, _ in chunks:
            chunk_escaped = chunk.replace('\n', '\\n')
            f.write(f"[{t:8.3f}s] {chunk_escaped}\n")

        f.write("\n\nFULL RESPONSE:\n")
        f.write("-" * 70 + "\n")
        f.write(cumulative_text)

    print(f"\nRaw data saved to: {output_file}")

    return marker_times, chunks


if __name__ == "__main__":
    run_streaming_time_study()
