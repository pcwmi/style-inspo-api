"""
Analyze evaluation results and generate summary statistics.

Usage:
    python analyze_results.py --ratings results/eval_20251123_143022/ratings.json
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List


def load_ratings(ratings_path: str) -> Dict:
    """Load ratings from JSON file."""
    with open(ratings_path, 'r') as f:
        return json.load(f)


def parse_outfit_id(outfit_id: str) -> Dict:
    """Parse outfit ID to extract metadata."""
    parts = outfit_id.split('_')
    return {
        'scenario_id': '_'.join(parts[:-3]),
        'model_id': parts[-3],
        'iteration': int(parts[-2]),
        'outfit_idx': int(parts[-1])
    }


def analyze_by_model(ratings: Dict) -> Dict:
    """Analyze ratings grouped by model."""
    model_stats = defaultdict(lambda: {'ratings': [], 'count': 0})

    for outfit_id, data in ratings.items():
        if 'rating' not in data:
            continue

        meta = parse_outfit_id(outfit_id)
        model_id = meta['model_id']

        model_stats[model_id]['ratings'].append(data['rating'])
        model_stats[model_id]['count'] += 1

    # Calculate averages
    results = {}
    for model_id, stats in model_stats.items():
        if stats['ratings']:
            avg_rating = sum(stats['ratings']) / len(stats['ratings'])
            results[model_id] = {
                'avg_rating': avg_rating,
                'count': stats['count'],
                'ratings': stats['ratings']
            }

    return results


def analyze_by_scenario(ratings: Dict) -> Dict:
    """Analyze ratings grouped by scenario."""
    scenario_stats = defaultdict(lambda: {'ratings': [], 'count': 0})

    for outfit_id, data in ratings.items():
        if 'rating' not in data:
            continue

        meta = parse_outfit_id(outfit_id)
        scenario_id = meta['scenario_id']

        scenario_stats[scenario_id]['ratings'].append(data['rating'])
        scenario_stats[scenario_id]['count'] += 1

    # Calculate averages
    results = {}
    for scenario_id, stats in scenario_stats.items():
        if stats['ratings']:
            avg_rating = sum(stats['ratings']) / len(stats['ratings'])
            results[scenario_id] = {
                'avg_rating': avg_rating,
                'count': stats['count'],
                'ratings': stats['ratings']
            }

    return results


def print_summary_table(model_results: Dict, title: str = "Model Performance"):
    """Print formatted summary table."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

    # Print header
    print(f"{'Model ID':<30} {'Avg Rating':<12} {'Count':<8} {'Distribution'}")
    print(f"{'-'*30} {'-'*12} {'-'*8} {'-'*20}")

    # Sort by average rating (descending)
    sorted_models = sorted(model_results.items(), key=lambda x: x[1]['avg_rating'], reverse=True)

    for model_id, stats in sorted_models:
        avg_rating = stats['avg_rating']
        count = stats['count']

        # Calculate rating distribution
        ratings = stats['ratings']
        dist = [ratings.count(i) for i in range(1, 6)]
        dist_str = ' '.join(f"{i+1}★:{dist[i]}" for i in range(5))

        # Print row
        rating_str = f"{avg_rating:.2f}/5.0"
        stars = "★" * int(avg_rating) + "☆" * (5 - int(avg_rating))
        print(f"{model_id:<30} {rating_str:<12} {count:<8} {dist_str}")

    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze evaluation results')
    parser.add_argument('--ratings', required=True, help='Path to ratings.json file')
    args = parser.parse_args()

    ratings_path = Path(args.ratings)

    if not ratings_path.exists():
        print(f"\n❌ Error: Ratings file not found: {ratings_path}")
        print(f"\n💡 Did you export ratings from the HTML review page?")
        return

    print(f"\n📊 Loading ratings from: {ratings_path}")

    # Load ratings
    ratings = load_ratings(ratings_path)

    # Count rated vs total
    total_outfits = len(ratings)
    rated_outfits = sum(1 for data in ratings.values() if 'rating' in data)

    print(f"  ✅ Loaded {total_outfits} outfits")
    print(f"  ⭐ Rated: {rated_outfits}/{total_outfits} ({(rated_outfits/total_outfits*100):.1f}%)")

    if rated_outfits == 0:
        print(f"\n⚠️  No ratings found. Please rate outfits in the HTML review page first.")
        return

    # Analyze by model
    model_results = analyze_by_model(ratings)
    print_summary_table(model_results, "Model Performance Comparison")

    # Analyze by scenario
    scenario_results = analyze_by_scenario(ratings)
    print_summary_table(scenario_results, "Performance by Test Scenario")

    # Find best model
    if model_results:
        best_model = max(model_results.items(), key=lambda x: x[1]['avg_rating'])
        print(f"{'='*80}")
        print(f"🏆 Best Performing Model: {best_model[0]}")
        print(f"   Average Rating: {best_model[1]['avg_rating']:.2f}/5.0")
        print(f"   Based on {best_model[1]['count']} rated outfits")
        print(f"{'='*80}\n")

    # Extract common feedback themes
    print(f"📝 Sample Feedback Notes:\n")
    notes_samples = []
    for outfit_id, data in ratings.items():
        if data.get('notes') and len(data['notes']) > 10:
            notes_samples.append((outfit_id, data['rating'], data['notes']))
            if len(notes_samples) >= 5:
                break

    for outfit_id, rating, notes in notes_samples:
        meta = parse_outfit_id(outfit_id)
        print(f"  [{meta['model_id']}] ⭐{rating}/5: {notes[:80]}...")

    print()


if __name__ == '__main__':
    main()
