#!/usr/bin/env python3
"""Generate filtered review page showing only fit_constraints outfits matching baseline ratings."""

import json
import sys
from pathlib import Path

# Load existing baseline ratings
baseline_ratings_path = Path("results/eval_20251125_123127/ratings.json")
with open(baseline_ratings_path) as f:
    baseline_ratings = json.load(f)

# Load new eval results (with both baseline and fit_constraints)
new_results_path = Path("results/eval_20251128_124930/raw_results.json")
with open(new_results_path) as f:
    new_results = json.load(f)

# Extract scenario names and iterations from baseline ratings
rated_keys = set()
for outfit_id in baseline_ratings.keys():
    # outfit_id format: "eval_0_outfit_0", "eval_1_outfit_0", etc.
    # We need to map this back to scenario + iteration
    parts = outfit_id.split('_')
    eval_idx = parts[1]
    rated_keys.add(eval_idx)

print(f"Found {len(rated_keys)} unique evaluations in baseline ratings: {sorted(rated_keys)}")

# Load original baseline results to see what these map to
baseline_results_path = Path("results/eval_20251125_123127/raw_results.json")
with open(baseline_results_path) as f:
    baseline_results = json.load(f)

# Map eval indices to scenario/iteration
eval_map = {}
for idx, result in enumerate(baseline_results):
    eval_map[str(idx)] = {
        'scenario_name': result['scenario_name'],
        'iteration': result['iteration']
    }

print(f"\nBaseline evaluations rated:")
for eval_idx in sorted(rated_keys, key=int):
    if eval_idx in eval_map:
        print(f"  Eval {eval_idx}: {eval_map[eval_idx]['scenario_name']} (iteration {eval_map[eval_idx]['iteration']})")

# Filter new results to only fit_constraints versions matching these scenarios/iterations
filtered_results = []
for idx, result in enumerate(new_results):
    # Only include fit_constraints prompts
    if "fit_constraints" not in result.get("prompt_version", "").lower():
        continue
    
    # Check if this matches a rated baseline evaluation
    for eval_idx in rated_keys:
        if eval_idx in eval_map:
            baseline_eval = eval_map[eval_idx]
            if (result["scenario_name"] == baseline_eval["scenario_name"] and 
                result["iteration"] == baseline_eval["iteration"]):
                filtered_results.append(result)
                print(f"  Matched: {result['scenario_name']} iter {result['iteration']} - {result['model_name']}")
                break

print(f"\nFiltered to {len(filtered_results)} fit_constraints evaluations")
print(f"This represents ~{sum(r['num_outfits'] for r in filtered_results)} outfits to review")

# Save filtered results
filtered_path = Path("results/eval_20251128_124930/filtered_results.json")
with open(filtered_path, 'w') as f:
    json.dump(filtered_results, f, indent=2)

print(f"\nSaved filtered results to: {filtered_path}")
