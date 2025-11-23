"""
Backfill script to add structured attributes to existing wardrobe items.

This script processes existing wardrobe_metadata.json files and extracts:
- subcategory (e.g., tops_tshirt, tops_buttonup)
- fabric (e.g., cotton, wool, leather)
- silhouette (e.g., fitted, oversized, relaxed)
- sleeve_length (for tops: short_sleeve, long_sleeve, etc.)
- waist_level (for bottoms: high_waisted, mid_rise, low_rise)

Run: python backend/scripts/restructure_metadata.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


def extract_fabric(texture: str) -> str:
    """Extract fabric type from texture field"""
    if not texture:
        return 'unknown'

    texture_lower = texture.lower()

    fabric_keywords = {
        'cotton': ['cotton', 'jersey'],
        'wool': ['wool', 'cashmere', 'merino'],
        'leather': ['leather'],
        'suede': ['suede'],
        'silk': ['silk', 'satin'],
        'denim': ['denim', 'jean'],
        'linen': ['linen'],
        'polyester': ['polyester', 'synthetic'],
        'knit': ['knit', 'knitted'],
        'blend': ['blend'],
    }

    for fabric, keywords in fabric_keywords.items():
        if any(kw in texture_lower for kw in keywords):
            return fabric

    return 'unknown'


def extract_silhouette(fit: str) -> str:
    """Extract silhouette from fit field"""
    if not fit:
        return 'unknown'

    fit_lower = fit.lower()

    if 'oversized' in fit_lower or 'loose' in fit_lower or 'baggy' in fit_lower:
        return 'oversized'
    elif 'fitted' in fit_lower or 'slim' in fit_lower or 'tight' in fit_lower or 'tailored' in fit_lower:
        return 'fitted'
    elif 'relaxed' in fit_lower or 'comfortable' in fit_lower:
        return 'relaxed'
    elif 'structured' in fit_lower:
        return 'structured'
    elif 'cropped' in fit_lower or 'short' in fit_lower:
        return 'cropped'
    elif 'flowy' in fit_lower or 'flowing' in fit_lower or 'draped' in fit_lower:
        return 'flowy'

    return 'unknown'


def infer_subcategory(item: dict) -> str:
    """Infer subcategory from category + name + cut"""
    styling_details = item.get('styling_details', {})
    category = styling_details.get('category', '')
    name = styling_details.get('name', '').lower()
    cut = styling_details.get('cut', '').lower()
    sub_category = styling_details.get('sub_category', '').lower()

    # If sub_category already set and not "unknown", use it
    if sub_category and sub_category != 'unknown':
        # Normalize to our format (e.g., "boots" -> "shoes_boots")
        if '_' not in sub_category:
            # Map common subcategories
            subcategory_map = {
                # Tops
                'tee': 'tops_tshirt',
                't-shirt': 'tops_tshirt',
                'tshirt': 'tops_tshirt',
                'shirt': 'tops_buttonup',
                'blouse': 'tops_blouse',
                'sweater': 'tops_sweater',
                'knit': 'tops_sweater',
                'cardigan': 'tops_cardigan',
                'tank': 'tops_tank',
                'camisole': 'tops_tank',
                'sweatshirt': 'tops_sweatshirt',

                # Bottoms
                'jeans': 'bottoms_jeans',
                'trousers': 'bottoms_trousers',
                'culottes': 'bottoms_trousers',
                'skirt': 'bottoms_skirt',
                'shorts': 'bottoms_shorts',
                'leggings': 'bottoms_leggings',

                # Shoes
                'boots': 'shoes_boots',
                'sneakers': 'shoes_sneakers',
                'loafers': 'shoes_flats',
                'heels': 'shoes_heels',
                'sandals': 'shoes_sandals',

                # Accessories
                'belt': 'accessories_belt',
                'scarf': 'accessories_scarf',
                'necklace': 'accessories_jewelry',
                'earrings': 'accessories_jewelry',
                'rings': 'accessories_jewelry',
                'hat': 'accessories_hat',
                'sunglasses': 'accessories_sunglasses',

                # Bags
                'tote': 'bags_tote',
                'crossbody': 'bags_crossbody',
                'clutch': 'bags_clutch',

                # Outerwear
                'blazer': 'outerwear_blazer',
                'coat': 'outerwear_coat',
                'jacket': 'outerwear_jacket',
            }

            if sub_category in subcategory_map:
                return subcategory_map[sub_category]

    combined = f"{name} {cut}"

    # Infer from name and cut
    if category == 'tops':
        if any(kw in combined for kw in ['t-shirt', 'tee', 'tshirt']):
            return 'tops_tshirt'
        elif any(kw in combined for kw in ['button', 'shirt']):
            return 'tops_buttonup'
        elif any(kw in combined for kw in ['sweater', 'pullover', 'knit']):
            return 'tops_sweater'
        elif 'cardigan' in combined:
            return 'tops_cardigan'
        elif 'blouse' in combined:
            return 'tops_blouse'
        elif any(kw in combined for kw in ['tank', 'camisole', 'sleeveless']):
            return 'tops_tank'
        elif any(kw in combined for kw in ['sweatshirt', 'hoodie']):
            return 'tops_sweatshirt'

    elif category == 'bottoms':
        if any(kw in combined for kw in ['jean', 'denim']):
            return 'bottoms_jeans'
        elif any(kw in combined for kw in ['trouser', 'pant', 'culottes']):
            return 'bottoms_trousers'
        elif 'skirt' in combined:
            return 'bottoms_skirt'
        elif 'short' in combined:
            return 'bottoms_shorts'
        elif 'legging' in combined:
            return 'bottoms_leggings'

    elif category in ['shoes', 'footwear']:
        if 'boot' in combined:
            return 'shoes_boots'
        elif any(kw in combined for kw in ['sneaker', 'trainer']):
            return 'shoes_sneakers'
        elif any(kw in combined for kw in ['heel', 'pump']):
            return 'shoes_heels'
        elif any(kw in combined for kw in ['flat', 'ballet', 'loafer']):
            return 'shoes_flats'
        elif 'sandal' in combined:
            return 'shoes_sandals'

    elif category == 'accessories':
        if 'belt' in combined:
            return 'accessories_belt'
        elif 'scarf' in combined:
            return 'accessories_scarf'
        elif any(kw in combined for kw in ['necklace', 'earring', 'ring', 'bracelet', 'jewelry']):
            return 'accessories_jewelry'
        elif any(kw in combined for kw in ['hat', 'cap', 'beanie']):
            return 'accessories_hat'
        elif any(kw in combined for kw in ['sunglasses', 'glasses']):
            return 'accessories_sunglasses'

    elif category in ['bags', 'bag']:
        if 'tote' in combined:
            return 'bags_tote'
        elif any(kw in combined for kw in ['crossbody', 'shoulder']):
            return 'bags_crossbody'
        elif 'clutch' in combined:
            return 'bags_clutch'

    elif category == 'outerwear':
        if 'blazer' in combined:
            return 'outerwear_blazer'
        elif 'coat' in combined:
            return 'outerwear_coat'
        elif 'jacket' in combined:
            return 'outerwear_jacket'

    # Fallback
    return f"{category}_other"


def extract_sleeve_length(item: dict) -> Optional[str]:
    """Extract sleeve length for tops"""
    styling_details = item.get('styling_details', {})
    category = styling_details.get('category', '')

    if category != 'tops':
        return None

    name = styling_details.get('name', '').lower()
    cut = styling_details.get('cut', '').lower()
    combined = f"{name} {cut}"

    if any(kw in combined for kw in ['short-sleeve', 'short sleeve', 'short sleeves']):
        return 'short_sleeve'
    elif any(kw in combined for kw in ['long-sleeve', 'long sleeve', 'long sleeves']):
        return 'long_sleeve'
    elif any(kw in combined for kw in ['sleeveless', 'tank', 'camisole']):
        return 'sleeveless'
    elif any(kw in combined for kw in ['3/4', 'three-quarter', 'three quarter']):
        return 'three_quarter'

    return 'unknown'


def extract_waist_level(item: dict) -> Optional[str]:
    """Extract waist level for pants"""
    styling_details = item.get('styling_details', {})
    category = styling_details.get('category', '')

    if category != 'bottoms':
        return None

    name = styling_details.get('name', '').lower()
    cut = styling_details.get('cut', '').lower()
    combined = f"{name} {cut}"

    if any(kw in combined for kw in ['high-waist', 'high waist', 'high-rise', 'high rise']):
        return 'high_waisted'
    elif any(kw in combined for kw in ['mid-rise', 'mid rise', 'medium rise']):
        return 'mid_rise'
    elif any(kw in combined for kw in ['low-rise', 'low rise', 'low waist']):
        return 'low_rise'

    return 'unknown'


def restructure_item(item: dict) -> dict:
    """Add structured attributes to item"""
    styling_details = item.get('styling_details', {})

    # Extract structured fields
    item['structured_attrs'] = {
        'subcategory': infer_subcategory(item),
        'fabric': extract_fabric(styling_details.get('texture', '')),
        'silhouette': extract_silhouette(styling_details.get('fit', '')),
        'sleeve_length': extract_sleeve_length(item),
        'waist_level': extract_waist_level(item),
    }

    # Also update sub_category field for consistency
    item['styling_details']['sub_category'] = item['structured_attrs']['subcategory']

    return item


def process_metadata_file(metadata_path: str, dry_run: bool = False) -> Dict:
    """Process a single wardrobe_metadata.json file"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {metadata_path}")

    with open(metadata_path, 'r') as f:
        data = json.load(f)

    items = data.get('items', [])
    processed_count = 0
    skipped_count = 0

    for item in items:
        # Skip if already has structured_attrs
        if 'structured_attrs' in item:
            skipped_count += 1
            continue

        restructure_item(item)
        processed_count += 1

        # Show example output
        if processed_count <= 3:
            name = item.get('styling_details', {}).get('name', 'Unknown')
            attrs = item.get('structured_attrs', {})
            print(f"  ✓ {name}")
            print(f"    - Subcategory: {attrs.get('subcategory')}")
            print(f"    - Fabric: {attrs.get('fabric')}")
            print(f"    - Silhouette: {attrs.get('silhouette')}")
            if attrs.get('sleeve_length'):
                print(f"    - Sleeve: {attrs.get('sleeve_length')}")
            if attrs.get('waist_level'):
                print(f"    - Waist: {attrs.get('waist_level')}")

    print(f"\n  Processed: {processed_count} items")
    print(f"  Skipped (already restructured): {skipped_count} items")

    if not dry_run and processed_count > 0:
        # Write back to file
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ Saved to {metadata_path}")

    return {
        'file': metadata_path,
        'processed': processed_count,
        'skipped': skipped_count
    }


def find_metadata_files(base_path: str) -> List[str]:
    """Find all wardrobe_metadata.json files"""
    metadata_files = []

    for root, dirs, files in os.walk(base_path):
        if 'wardrobe_metadata.json' in files:
            metadata_files.append(os.path.join(root, 'wardrobe_metadata.json'))

    return metadata_files


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Restructure wardrobe metadata with structured attributes')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving changes')
    parser.add_argument('--path', default='backend/wardrobe_photos', help='Base path to search for metadata files')

    args = parser.parse_args()

    print("=" * 60)
    print("WARDROBE METADATA RESTRUCTURING SCRIPT")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be saved\n")

    # Find all metadata files
    metadata_files = find_metadata_files(args.path)

    if not metadata_files:
        print(f"\n❌ No metadata files found in {args.path}")
        return

    print(f"\nFound {len(metadata_files)} metadata file(s):")
    for f in metadata_files:
        print(f"  - {f}")

    # Process each file
    results = []
    for metadata_file in metadata_files:
        result = process_metadata_file(metadata_file, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_processed = sum(r['processed'] for r in results)
    total_skipped = sum(r['skipped'] for r in results)

    print(f"\nTotal items processed: {total_processed}")
    print(f"Total items skipped: {total_skipped}")

    if args.dry_run:
        print("\n⚠️  This was a DRY RUN - run without --dry-run to save changes")
    else:
        print("\n✅ All metadata files updated successfully!")


if __name__ == '__main__':
    main()
