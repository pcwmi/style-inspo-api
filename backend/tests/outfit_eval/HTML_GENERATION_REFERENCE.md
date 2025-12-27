# HTML Review Generation Reference

## Problem
HTML reviews generated without images loading because wardrobe wasn't loaded from S3 to get image paths.

## Correct Approach

### For Diagnostic Reviews

Use the script: `/Users/peichin/Projects/style-inspo-api/backend/tests/outfit_eval/scripts/generate_diagnostic_html.py`

**Key Requirements:**
1. Must load wardrobe from S3 using WardrobeManager
2. Must match item names from results to wardrobe items to get image paths
3. Must construct proper S3 URLs

**Running the script:**
```bash
cd /Users/peichin/Projects/style-inspo-api/backend
source venv/bin/activate
STORAGE_TYPE=s3 python3 tests/outfit_eval/scripts/generate_diagnostic_html.py
```

### Critical Code Pattern

```python
import sys
from pathlib import Path

# Add backend to path (REQUIRED for imports to work)
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Set storage to S3 BEFORE importing
import os
os.environ['STORAGE_TYPE'] = 's3'

from services.wardrobe_manager import WardrobeManager

def get_image_url(item_name, wardrobe_items):
    """Find image URL for an item by name"""
    for item in wardrobe_items:
        name = item.get('styling_details', {}).get('name', '')
        if name == item_name:
            image_path = item.get('system_metadata', {}).get('image_path', '')
            if image_path:
                # Extract just the filename
                if '/' in image_path:
                    filename = image_path.split('/')[-1]
                else:
                    filename = image_path
                return f"https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}"
    return None

# Load wardrobe from S3
wm = WardrobeManager(user_id='peichin')
wardrobe_data = wm.load_wardrobe_data()
wardrobe_items = wardrobe_data.get('items', [])

# Then use get_image_url() when building HTML
```

### Image HTML Format

```html
<img src="https://style-inspo.s3.us-east-2.amazonaws.com/peichin/items/{filename}.jpg"
     alt="{item_name}"
     class="item-image"
     title="{item_name}">
```

### Fallback for Missing Images

```html
<div class="item-placeholder">{item_name}</div>
```

## For Future Eval Reviews

When agents generate `review.html` files, they should:
1. Use same wardrobe loading pattern
2. Match outfit item names to wardrobe items to get image URLs
3. Never hardcode image paths or assume they're in results JSON
4. Always test that images load before considering task complete

## Common Mistakes to Avoid

❌ **Don't:** Generate HTML without loading wardrobe
❌ **Don't:** Assume image URLs are in the results JSON
❌ **Don't:** Forget to set `STORAGE_TYPE=s3` before importing
❌ **Don't:** Forget to add backend to Python path (`sys.path.insert`)

✅ **Do:** Load wardrobe from S3 explicitly
✅ **Do:** Match item names to get image paths
✅ **Do:** Construct S3 URLs from image paths
✅ **Do:** Test the HTML file opens with images before marking complete
