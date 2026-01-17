"""
Side-by-side prompt comparison for Runway visualization.

Compares current prompt (landscape, no single-model instruction) vs
revised prompt (portrait, explicit single-model instruction).

Run: cd backend && python test_prompt_comparison.py
"""

import os
import sys
import time
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Runway config
API_KEY = os.getenv('RUNWAY_API_KEY')
BASE_URL = "https://api.dev.runwayml.com/v1"
MODEL = "gen4_image"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "X-Runway-Version": "2024-11-06"
}

# Test cases from the plan
TEST_CASES = [
    {
        "id": 1,
        "outfit": "Plaid blazer, grey tee, jeans, sneakers, earrings",
        "descriptor": '5\'4", Asian, chest length wavy black hair'
    },
    {
        "id": 2,
        "outfit": "Black dress, heels, gold necklace",
        "descriptor": '5\'8", white, brunette, athletic'
    },
    {
        "id": 3,
        "outfit": "Casual hoodie, joggers, chunky sneakers",
        "descriptor": '5\'5", black, medium build, natural curls'
    }
]


def create_current_prompt(outfit: str, descriptor: str) -> str:
    """Current prompt structure (landscape, no single-model instruction)."""
    duplication_guard = (
        "Use each referenced garment exactly once. "
        "Do not duplicate accessories or add extra items."
    )

    prompt = (
        f"{descriptor}\n\n"
        f"A confident woman wearing {outfit}.\n\n"
        f"{duplication_guard} "
        "Fashion photography, editorial style, clean background, professional lighting."
    )
    return prompt.strip()


def create_revised_prompt(outfit: str, descriptor: str) -> str:
    """Revised prompt structure (portrait orientation, explicit single-model)."""
    duplication_guard = (
        "Use each referenced garment exactly once. "
        "Do not duplicate accessories or add extra items."
    )

    prompt = (
        f"{descriptor}\n\n"
        f"A single confident woman, full-body shot, wearing {outfit}.\n\n"
        f"ONE person only. Full body from head to toe. "
        f"{duplication_guard} "
        "Fashion photography, editorial style, clean background, professional lighting."
    )
    return prompt.strip()


def submit_generation(prompt: str, ratio: str) -> str:
    """Submit generation task to Runway and return task_id."""
    payload = {
        "model": MODEL,
        "promptText": prompt,
        "ratio": ratio,
    }

    response = requests.post(
        f"{BASE_URL}/text_to_image",
        headers=HEADERS,
        json=payload,
        timeout=60
    )

    if response.status_code == 200:
        data = response.json()
        return data.get('id')
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def poll_task(task_id: str, timeout: int = 120) -> dict:
    """Poll task until completion."""
    start_time = time.time()
    poll_interval = 3

    while time.time() - start_time < timeout:
        response = requests.get(
            f"{BASE_URL}/tasks/{task_id}",
            headers=HEADERS,
            timeout=10
        )

        if response.status_code == 200:
            task_data = response.json()
            status = task_data.get('status', '').upper()

            if 'SUCCEED' in status or status == 'COMPLETED':
                return task_data
            elif 'FAIL' in status or status == 'ERROR':
                raise Exception(f"Task failed: {task_data}")

        elapsed = time.time() - start_time
        print(f"  Polling... ({elapsed:.0f}s)")
        time.sleep(poll_interval)

    raise TimeoutError(f"Task {task_id} timed out after {timeout}s")


def extract_image_url(task_data: dict) -> str:
    """Extract image URL from completed task."""
    for field in ['output', 'url', 'result', 'imageUrl', 'image_url']:
        if field in task_data:
            output = task_data[field]
            if isinstance(output, list) and len(output) > 0:
                return output[0]
            elif isinstance(output, str):
                return output
    raise ValueError(f"No image URL found in task data")


def download_image(url: str, filename: str):
    """Download image to file."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(response.content)
    print(f"  Saved: {filename}")


def run_test_case(test_case: dict, output_dir: str):
    """Run a single test case with both prompts."""
    case_id = test_case['id']
    outfit = test_case['outfit']
    descriptor = test_case['descriptor']

    print(f"\n{'='*60}")
    print(f"TEST CASE {case_id}")
    print(f"{'='*60}")
    print(f"Outfit: {outfit}")
    print(f"Descriptor: {descriptor}")

    # Current prompt (landscape)
    print(f"\n[CURRENT] Landscape 1920:1080, no single-model instruction")
    current_prompt = create_current_prompt(outfit, descriptor)
    print(f"Prompt ({len(current_prompt)} chars):\n{current_prompt[:200]}...")

    task_id_current = submit_generation(current_prompt, "1920:1080")
    if not task_id_current:
        print("  Failed to submit current prompt")
        return
    print(f"  Task ID: {task_id_current}")

    # Revised prompt (portrait)
    print(f"\n[REVISED] Portrait 1080:1920, single-model instruction")
    revised_prompt = create_revised_prompt(outfit, descriptor)
    print(f"Prompt ({len(revised_prompt)} chars):\n{revised_prompt[:200]}...")

    task_id_revised = submit_generation(revised_prompt, "1080:1920")
    if not task_id_revised:
        print("  Failed to submit revised prompt")
        return
    print(f"  Task ID: {task_id_revised}")

    # Poll both tasks (they run in parallel)
    print(f"\nPolling tasks...")

    try:
        print(f"\n[CURRENT] Waiting for completion...")
        task_current = poll_task(task_id_current)
        url_current = extract_image_url(task_current)
        download_image(url_current, f"{output_dir}/test_{case_id}_current.jpg")
    except Exception as e:
        print(f"  Current prompt failed: {e}")

    try:
        print(f"\n[REVISED] Waiting for completion...")
        task_revised = poll_task(task_id_revised)
        url_revised = extract_image_url(task_revised)
        download_image(url_revised, f"{output_dir}/test_{case_id}_revised.jpg")
    except Exception as e:
        print(f"  Revised prompt failed: {e}")


def main():
    if not API_KEY:
        print("Error: RUNWAY_API_KEY not set")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"prompt_comparison_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Save test case info
    with open(f"{output_dir}/test_cases.txt", 'w') as f:
        f.write("PROMPT COMPARISON TEST\n")
        f.write(f"Date: {datetime.now().isoformat()}\n\n")
        f.write("CURRENT: Landscape 1920:1080, 'A confident woman wearing...'\n")
        f.write("REVISED: Portrait 1080:1920, 'A single confident woman, full-body shot... ONE person only.'\n\n")
        for tc in TEST_CASES:
            f.write(f"Test {tc['id']}:\n")
            f.write(f"  Outfit: {tc['outfit']}\n")
            f.write(f"  Descriptor: {tc['descriptor']}\n\n")

    # Run tests
    print(f"\nRunning {len(TEST_CASES)} test cases...")
    print(f"Each test generates 2 images (~$0.16 total per test case)")
    print(f"Total cost: ~${0.16 * len(TEST_CASES):.2f}")

    for test_case in TEST_CASES:
        run_test_case(test_case, output_dir)

    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"Results saved to: {output_dir}/")
    print(f"\nValidation criteria:")
    print(f"  - [ ] Single person (not multi-figure)")
    print(f"  - [ ] Full body visible (head to toe)")
    print(f"  - [ ] Portrait orientation")
    print(f"  - [ ] Garments recognizable")


if __name__ == "__main__":
    main()
