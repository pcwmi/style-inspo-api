# SPEC: Buy Smarter Feature

**Version**: 1.0
**Date**: 2025-11-22
**Status**: Ready for Implementation
**Estimated Time**: 2-3 days

---

## Overview

"Buy Smarter" helps users decide whether to buy new clothing items by:
1. Extracting product details from URLs or screenshots
2. Finding similar items in their existing wardrobe (duplicate detection)
3. Generating outfits to show how the new item works with their closet
4. Tracking purchasing decisions and savings over time

**Value proposition**: "See how it works with your closet before you buy" + "Stop buying duplicates"

---

## User Flow

```
User browsing online → Sees item they want →
  ↓
Opens Style Inspo app → Dashboard → "Buy Smarter" card →
  ↓
Pastes product link (or uploads screenshot if extraction fails) →
  ↓
[1-3 sec] Extracting item details...
  ↓
✓ Extracted: "Grey Oversized Sweater - $89"
  ↓
[< 1 sec] Checking closet for similar items...
  ↓
BRANCH A: Similar items found (duplicate detection)
  💭 You already own 2 similar items:
  [Grey Sweater] [Charcoal Pullover]

  User decides:
    → "Show outfits with my existing items" (prevent duplicate)
    → "Continue with new item" (still want to see)

BRANCH B: No similar items found
  ✓ No similar items in your closet
  → Auto-proceed to outfit generation

  ↓
[20-30 sec] Creating outfits...
  ↓
Outfits revealed (3 combinations)
  ↓
User decides:
  → "I bought it!" → Save to wardrobe + save outfits
  → "Not buying" → Track savings + reason
  → "Decide later" → Keep in "considering" bucket
```

---

## Storage Architecture

### S3 Bucket Structure

```
s3://style-inspo-wardrobe/{user_id}/
  wardrobe/
    regular_wear/
      item_abc.jpg
    styling_challenges/
      item_xyz.jpg
  consider_buying/           ← NEW: Staging area for items under consideration
    item_123.jpg
    item_456.jpg
```

### JSON Metadata Files

**`consider_buying.json`** (NEW):
```json
{
  "items": [
    {
      "id": "consider_abc123",
      "added_date": "2025-11-22T10:30:00",
      "status": "considering",  // considering | bought | passed
      "source_url": "https://zara.com/product/12345",
      "price": 89.99,
      "styling_details": {
        "name": "Grey Oversized Sweater",
        "category": "tops",
        "sub_category": "tops_sweater",
        "colors": ["grey", "charcoal"],
        "fabric": "wool",
        "cut": "oversized, dropped shoulders",
        "texture": "chunky knit",
        "style": "cozy minimalist",
        "fit": "oversized",
        "sleeve_length": "long_sleeve",
        "waist_level": null,
        "brand": "Zara"
      },
      "structured_attrs": {
        "subcategory": "tops_sweater",
        "fabric": "wool",
        "silhouette": "oversized",
        "sleeve_length": "long_sleeve",
        "waist_level": null
      },
      "image_path": "s3://.../consider_buying/item_abc123.jpg",
      "similar_items_in_wardrobe": ["wardrobe_item_xyz", "wardrobe_item_789"]
    }
  ]
}
```

**`buying_decisions.json`** (NEW):
```json
{
  "decisions": [
    {
      "item_id": "consider_abc123",
      "decision": "passed",  // bought | passed | later
      "decision_date": "2025-11-23T15:45:00",
      "reason": "Already own similar grey sweater",
      "price_saved": 89.99
    }
  ],
  "stats": {
    "total_considered": 12,
    "total_bought": 3,
    "total_passed": 7,
    "total_deciding_later": 2,
    "total_saved": 534.93
  }
}
```

---

## Backend Implementation

### File Structure

```
backend/
  api/
    consider_buying.py         ← NEW: API endpoints
  services/
    consider_buying_manager.py ← NEW: Business logic
    product_extractor.py       ← NEW: URL/image extraction
    image_analyzer.py          ← UPDATED: Enhanced prompt (DONE)
    wardrobe_manager.py        ← UPDATED: structured_attrs (DONE)
  scripts/
    restructure_metadata.py    ← DONE: Backfill script
```

### NEW FILE: `backend/services/product_extractor.py`

```python
"""
Product Extractor - Extract product images and metadata from URLs or screenshots
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ProductExtractor:
    """Extract product information from URLs or screenshots"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
        }

    def extract_from_url(self, url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Extract product image and metadata from URL using Open Graph tags

        Returns: (success, data, error_message)
        data = {
            'image_url': str,
            'title': str,
            'price': float or None,
            'brand': str or None
        }
        """
        try:
            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract Open Graph tags
            og_image = soup.find('meta', property='og:image')
            og_title = soup.find('meta', property='og:title')
            og_price = soup.find('meta', property='og:price:amount')

            if not og_image:
                return False, None, "No product image found (no Open Graph tags)"

            data = {
                'image_url': og_image['content'],
                'title': og_title['content'] if og_title else None,
                'price': float(og_price['content']) if og_price else None,
                'brand': self._extract_brand(soup),
                'source_url': url
            }

            return True, data, None

        except requests.Timeout:
            return False, None, "Request timed out"
        except requests.RequestException as e:
            return False, None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return False, None, "Could not extract product information"

    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        """Attempt to extract brand name from page"""
        # Try Open Graph brand
        og_brand = soup.find('meta', property='og:brand')
        if og_brand:
            return og_brand['content']

        # Try schema.org markup
        schema_brand = soup.find('span', {'itemprop': 'brand'})
        if schema_brand:
            return schema_brand.text.strip()

        return None

    def download_image(self, image_url: str) -> Tuple[bool, Optional[Image.Image], Optional[str]]:
        """
        Download image from URL

        Returns: (success, PIL.Image, error_message)
        """
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            return True, image, None

        except Exception as e:
            logger.error(f"Image download error: {str(e)}")
            return False, None, f"Could not download image: {str(e)}"
```

### NEW FILE: `backend/services/consider_buying_manager.py`

```python
"""
Consider Buying Manager - Manage items user is considering purchasing
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from services.storage_manager import StorageManager
from services.image_analyzer import create_image_analyzer

logger = logging.getLogger(__name__)


def colors_are_similar(colors1: List[str], colors2: List[str]) -> bool:
    """Check if two color lists are similar"""
    # Define color families
    color_families = {
        'neutrals': ['black', 'white', 'grey', 'gray', 'charcoal', 'cream', 'beige', 'taupe', 'ivory'],
        'blues': ['navy', 'blue', 'light blue', 'denim', 'cobalt', 'royal blue'],
        'reds': ['red', 'burgundy', 'wine', 'maroon', 'pink', 'rose'],
        'greens': ['green', 'olive', 'forest', 'emerald', 'mint'],
        'yellows': ['yellow', 'gold', 'mustard', 'ochre'],
        'purples': ['purple', 'lavender', 'plum', 'violet'],
        'browns': ['brown', 'tan', 'camel', 'chocolate', 'coffee'],
    }

    # Normalize colors
    colors1_lower = [c.lower() for c in colors1]
    colors2_lower = [c.lower() for c in colors2]

    # Check for exact matches
    for color1 in colors1_lower:
        if color1 in colors2_lower:
            return True

    # Check for same family matches
    for family in color_families.values():
        family_matches_1 = [c for c in colors1_lower if c in family]
        family_matches_2 = [c for c in colors2_lower if c in family]
        if family_matches_1 and family_matches_2:
            return True

    return False


def are_items_similar(item1: Dict, item2: Dict) -> Tuple[bool, float, str]:
    """
    Check similarity based on physical attributes only

    Returns: (is_similar, similarity_score, reason)

    Similarity criteria:
    - MUST match: subcategory
    - MUST match: color (similar)
    - Score on: silhouette (30%), fabric (30%), sleeve_length/waist_level (20%)
    - Threshold: 60% or higher = similar
    """
    attrs1 = item1.get('structured_attrs', {})
    attrs2 = item2.get('structured_attrs', {})

    styling1 = item1.get('styling_details', {})
    styling2 = item2.get('styling_details', {})

    # MUST match: subcategory
    if attrs1.get('subcategory') != attrs2.get('subcategory'):
        return False, 0.0, "Different subcategory"

    # MUST match: color (similar)
    colors1 = styling1.get('colors', [])
    colors2 = styling2.get('colors', [])
    if not colors_are_similar(colors1, colors2):
        return False, 0.0, "Different colors"

    # Calculate similarity score
    score = 0.0
    matching_attrs = []

    # Silhouette (30%)
    if attrs1.get('silhouette') == attrs2.get('silhouette'):
        score += 0.3
        matching_attrs.append('silhouette')

    # Fabric (30%)
    if attrs1.get('fabric') == attrs2.get('fabric'):
        score += 0.3
        matching_attrs.append('fabric')

    # Sleeve length for tops (20%)
    if styling1.get('category') == 'tops':
        if attrs1.get('sleeve_length') == attrs2.get('sleeve_length'):
            score += 0.2
            matching_attrs.append('sleeve length')

    # Waist level for bottoms (20%)
    if styling1.get('category') == 'bottoms':
        if attrs1.get('waist_level') == attrs2.get('waist_level'):
            score += 0.2
            matching_attrs.append('waist level')

    # For other categories, give partial credit for cut similarity
    if styling1.get('category') not in ['tops', 'bottoms']:
        cut1 = styling1.get('cut', '').lower()
        cut2 = styling2.get('cut', '').lower()
        if cut1 and cut2:
            words1 = set(cut1.split())
            words2 = set(cut2.split())
            if words1 & words2:  # Any word overlap
                overlap_ratio = len(words1 & words2) / max(len(words1), len(words2))
                if overlap_ratio > 0.5:
                    score += 0.2
                    matching_attrs.append('cut details')

    # Consider similar if score >= 0.6 (60%)
    is_similar = score >= 0.6
    reason = f"Matching: {', '.join(matching_attrs)}" if matching_attrs else "No significant matches"

    return is_similar, score, reason


class ConsiderBuyingManager:
    """Manage items user is considering purchasing"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = StorageManager(storage_type=os.getenv("STORAGE_TYPE", "local"), user_id=user_id)
        self.metadata_file = "consider_buying.json"
        self.decisions_file = "buying_decisions.json"

        # Load existing data
        self.consider_buying_data = self._load_consider_buying_data()
        self.decisions_data = self._load_decisions_data()

    def _load_consider_buying_data(self) -> Dict:
        """Load consider_buying.json"""
        try:
            return self.storage.load_json(self.metadata_file)
        except:
            return {"items": []}

    def _load_decisions_data(self) -> Dict:
        """Load buying_decisions.json"""
        try:
            return self.storage.load_json(self.decisions_file)
        except:
            return {
                "decisions": [],
                "stats": {
                    "total_considered": 0,
                    "total_bought": 0,
                    "total_passed": 0,
                    "total_deciding_later": 0,
                    "total_saved": 0.0
                }
            }

    def _save_consider_buying_data(self):
        """Save consider_buying.json"""
        self.storage.save_json(self.consider_buying_data, self.metadata_file)

    def _save_decisions_data(self):
        """Save buying_decisions.json"""
        self.storage.save_json(self.decisions_data, self.decisions_file)

    def add_item(self, analysis_data: Dict, image, price: Optional[float] = None, source_url: Optional[str] = None) -> Dict:
        """
        Add item to consider_buying bucket

        Returns: item_data with id
        """
        # Generate unique ID
        item_id = f"consider_{uuid.uuid4().hex[:12]}"

        # Save image to consider_buying/ folder
        image_filename = f"{item_id}.jpg"
        image_path = self.storage.save_image(image, image_filename, subfolder="consider_buying")

        # Create item data
        item_data = {
            "id": item_id,
            "added_date": datetime.now().isoformat(),
            "status": "considering",
            "source_url": source_url,
            "price": price,
            "styling_details": {
                "name": analysis_data.get('name', 'Unnamed Item'),
                "category": analysis_data.get('category', 'tops'),
                "sub_category": analysis_data.get('sub_category', 'Unknown'),
                "colors": analysis_data.get('colors', ['Unknown']) if isinstance(analysis_data.get('colors'), list) else [analysis_data.get('colors', 'Unknown')],
                "cut": analysis_data.get('cut', 'Unknown'),
                "texture": analysis_data.get('texture', 'Unknown'),
                "style": analysis_data.get('style', 'casual'),
                "fit": analysis_data.get('fit', 'Unknown'),
                "brand": analysis_data.get('brand'),
                "trend_status": analysis_data.get('trend_status', 'Unknown'),
                "styling_notes": analysis_data.get('styling_notes', '')
            },
            "structured_attrs": {
                "subcategory": analysis_data.get('sub_category', 'Unknown'),
                "fabric": analysis_data.get('fabric', 'unknown'),
                "silhouette": analysis_data.get('fit', 'Unknown').lower() if analysis_data.get('fit') else 'unknown',
                "sleeve_length": analysis_data.get('sleeve_length'),
                "waist_level": analysis_data.get('waist_level'),
            },
            "image_path": image_path,
            "similar_items_in_wardrobe": []
        }

        # Add to consider_buying data
        self.consider_buying_data["items"].append(item_data)
        self._save_consider_buying_data()

        # Update stats
        self.decisions_data["stats"]["total_considered"] += 1
        self._save_decisions_data()

        return item_data

    def find_similar_items(self, consider_item: Dict, wardrobe_items: List[Dict]) -> List[Dict]:
        """
        Find similar items in wardrobe

        Returns: List of dicts with {item, similarity_score, reason}
        """
        similar = []

        for wardrobe_item in wardrobe_items:
            is_similar, score, reason = are_items_similar(consider_item, wardrobe_item)

            if is_similar:
                similar.append({
                    'item': wardrobe_item,
                    'similarity_score': score,
                    'reason': reason
                })

        # Sort by similarity score (highest first)
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)

        return similar[:5]  # Return top 5

    def record_decision(self, item_id: str, decision: str, reason: Optional[str] = None):
        """
        Record user's buying decision

        decision: "bought" | "passed" | "later"
        """
        # Find item in consider_buying
        item = next((i for i in self.consider_buying_data["items"] if i["id"] == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Record decision
        decision_record = {
            "item_id": item_id,
            "decision": decision,
            "decision_date": datetime.now().isoformat(),
            "reason": reason,
            "price_saved": item.get("price", 0) if decision == "passed" else 0
        }

        self.decisions_data["decisions"].append(decision_record)

        # Update stats
        stats = self.decisions_data["stats"]
        if decision == "bought":
            stats["total_bought"] += 1
        elif decision == "passed":
            stats["total_passed"] += 1
            stats["total_saved"] += item.get("price", 0)
        elif decision == "later":
            stats["total_deciding_later"] += 1

        self._save_decisions_data()

        # Update item status
        item["status"] = decision
        self._save_consider_buying_data()

        return decision_record

    def get_items(self, status: Optional[str] = None) -> List[Dict]:
        """Get items, optionally filtered by status"""
        items = self.consider_buying_data.get("items", [])

        if status:
            return [i for i in items if i.get("status") == status]

        return items

    def get_stats(self) -> Dict:
        """Get buying decision stats"""
        return self.decisions_data.get("stats", {})

    def delete_item(self, item_id: str):
        """Delete item from consider_buying"""
        items = self.consider_buying_data.get("items", [])
        item = next((i for i in items if i["id"] == item_id), None)

        if item:
            # Delete image
            image_path = item.get("image_path")
            if image_path:
                # TODO: Implement storage.delete_file()
                pass

            # Remove from list
            items.remove(item)
            self._save_consider_buying_data()
```

### NEW FILE: `backend/api/consider_buying.py`

```python
"""
Consider Buying API Endpoints
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging

from services.consider_buying_manager import ConsiderBuyingManager
from services.product_extractor import ProductExtractor
from services.wardrobe_manager import WardrobeManager
from services.image_analyzer import create_image_analyzer
from services.style_engine import StyleGenerationEngine
from core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consider-buying", tags=["consider-buying"])


class ExtractRequest(BaseModel):
    url: str


class DecisionRequest(BaseModel):
    item_id: str
    decision: str  # bought | passed | later
    reason: Optional[str] = None


@router.post("/extract-url")
async def extract_from_url(request: ExtractRequest, user_id: str = get_current_user()):
    """
    Extract product information from URL

    Returns: {
        success: bool,
        data: {image_url, title, price, brand} or None,
        error: str or None
    }
    """
    extractor = ProductExtractor()
    success, data, error = extractor.extract_from_url(request.url)

    if success:
        return {"success": True, "data": data, "error": None}
    else:
        return {"success": False, "data": None, "error": error}


@router.post("/add-item")
async def add_item(
    image_file: UploadFile = File(...),
    price: Optional[float] = Form(None),
    source_url: Optional[str] = Form(None),
    user_id: str = get_current_user()
):
    """
    Add item to consider_buying bucket

    Steps:
    1. Analyze image with AI
    2. Save to consider_buying/
    3. Find similar items in wardrobe
    4. Return item data + similar items
    """
    try:
        # Analyze image
        analyzer = create_image_analyzer(use_real_ai=True)
        analysis_data = analyzer.analyze_clothing_item(image_file.file)

        # Add to consider_buying
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        item_data = cb_manager.add_item(
            analysis_data=analysis_data,
            image=image_file.file,
            price=price,
            source_url=source_url
        )

        # Find similar items in wardrobe
        wardrobe_manager = WardrobeManager(user_id=user_id)
        wardrobe_items = wardrobe_manager.get_wardrobe_items("all")

        similar_items = cb_manager.find_similar_items(item_data, wardrobe_items)

        # Store similar item IDs in item data
        item_data["similar_items_in_wardrobe"] = [s["item"]["id"] for s in similar_items]
        cb_manager._save_consider_buying_data()

        return {
            "item": item_data,
            "similar_items": similar_items
        }

    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-outfits")
async def generate_outfits(
    item_id: str = Form(...),
    use_existing_similar: bool = Form(False),
    user_id: str = get_current_user()
):
    """
    Generate outfits with consider_buying item

    If use_existing_similar=True, use similar items from wardrobe instead
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        wardrobe_manager = WardrobeManager(user_id=user_id)

        # Get consider_buying item
        consider_item = next((i for i in cb_manager.get_items() if i["id"] == item_id), None)
        if not consider_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Get wardrobe items
        wardrobe_items = wardrobe_manager.get_wardrobe_items("all")

        # Get user profile (TODO: implement profile loading)
        user_profile = {}  # Placeholder

        # Determine anchor items
        if use_existing_similar:
            # Use similar items from wardrobe
            similar_item_ids = consider_item.get("similar_items_in_wardrobe", [])
            anchor_items = [item for item in wardrobe_items if item["id"] in similar_item_ids]
        else:
            # Use consider_buying item as anchor
            anchor_items = [consider_item]

        # Generate outfits
        engine = StyleGenerationEngine()
        combinations = engine.generate_outfit_combinations(
            user_profile=user_profile,
            available_items=wardrobe_items,
            styling_challenges=anchor_items,
            occasion=None,
            weather_condition=None,
            temperature_range=None
        )

        return {
            "outfits": combinations,
            "anchor_items": anchor_items
        }

    except Exception as e:
        logger.error(f"Error generating outfits: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decide")
async def record_decision(request: DecisionRequest, user_id: str = get_current_user()):
    """
    Record user's buying decision

    decision: "bought" | "passed" | "later"
    """
    try:
        cb_manager = ConsiderBuyingManager(user_id=user_id)
        decision_record = cb_manager.record_decision(
            item_id=request.item_id,
            decision=request.decision,
            reason=request.reason
        )

        # If bought, move to wardrobe
        if request.decision == "bought":
            # TODO: Move item from consider_buying to wardrobe
            pass

        return {
            "success": True,
            "decision": decision_record,
            "stats": cb_manager.get_stats()
        }

    except Exception as e:
        logger.error(f"Error recording decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_items(status: Optional[str] = None, user_id: str = get_current_user()):
    """
    List items in consider_buying bucket

    Optional filter by status: "considering" | "bought" | "passed"
    """
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    items = cb_manager.get_items(status=status)
    return {"items": items}


@router.get("/stats")
async def get_stats(user_id: str = get_current_user()):
    """Get buying decision stats"""
    cb_manager = ConsiderBuyingManager(user_id=user_id)
    return cb_manager.get_stats()
```

### UPDATE FILE: `backend/main.py`

Add the new router:

```python
from api import consider_buying

app.include_router(consider_buying.router)
```

---

## Frontend Implementation

### File Structure

```
frontend/src/
  app/
    consider-buying/
      page.tsx                    ← NEW: Paste link / upload screenshot
      similar/page.tsx            ← NEW: Similar items view
      outfits/page.tsx            ← NEW: Outfit reveal
    dashboard/
      page.tsx                    ← UPDATE: Add "Buy Smarter" card
    closet/
      page.tsx                    ← UPDATE: Add "Considering" tab
  components/
    SimilarItemsCard.tsx          ← NEW
    DecisionModal.tsx             ← NEW
```

### NEW FILE: `frontend/src/app/consider-buying/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function ConsiderBuyingPage() {
  const router = useRouter()
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showScreenshotUpload, setShowScreenshotUpload] = useState(false)

  const handlePasteLink = async () => {
    if (!url) return

    setLoading(true)
    setError('')

    try {
      // Step 1: Extract from URL
      const extractRes = await fetch('/api/consider-buying/extract-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      })

      const extractData = await extractRes.json()

      if (!extractData.success) {
        // Extraction failed - show screenshot upload
        setError(extractData.error || "Couldn't extract image from link")
        setShowScreenshotUpload(true)
        setLoading(false)
        return
      }

      // Step 2: Download image and analyze
      const imageUrl = extractData.data.image_url

      // Download image as blob
      const imageRes = await fetch(imageUrl)
      const imageBlob = await imageRes.blob()

      // Create FormData
      const formData = new FormData()
      formData.append('image_file', imageBlob, 'product.jpg')
      formData.append('price', extractData.data.price?.toString() || '')
      formData.append('source_url', url)

      // Step 3: Add item
      const addRes = await fetch('/api/consider-buying/add-item', {
        method: 'POST',
        body: formData
      })

      const addData = await addRes.json()

      // Navigate to similar items view
      router.push(`/consider-buying/similar?item_id=${addData.item.id}`)

    } catch (err) {
      setError('An error occurred. Please try again.')
      setShowScreenshotUpload(true)
    } finally {
      setLoading(false)
    }
  }

  const handleScreenshotUpload = async (file: File) => {
    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('image_file', file)
      formData.append('source_url', url || '')

      const res = await fetch('/api/consider-buying/add-item', {
        method: 'POST',
        body: formData
      })

      const data = await res.json()

      // Navigate to similar items view
      router.push(`/consider-buying/similar?item_id=${data.item.id}`)

    } catch (err) {
      setError('An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">Buy Smarter</h1>
      <p className="text-gray-600 mb-8">
        See how it works with your closet before you buy
      </p>

      {!showScreenshotUpload ? (
        <div className="max-w-2xl">
          <label className="block mb-2 font-medium">
            Paste product link
          </label>
          <div className="flex gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://zara.com/product/..."
              className="flex-1 px-4 py-3 border rounded-lg"
            />
            <button
              onClick={handlePasteLink}
              disabled={loading || !url}
              className="px-6 py-3 bg-black text-white rounded-lg disabled:opacity-50"
            >
              {loading ? 'Extracting...' : 'Extract'}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-orange-800">{error}</p>
              <button
                onClick={() => setShowScreenshotUpload(true)}
                className="mt-2 text-orange-600 underline"
              >
                Upload screenshot instead
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="max-w-2xl">
          <label className="block mb-2 font-medium">
            Upload screenshot
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleScreenshotUpload(file)
            }}
            className="block w-full"
          />
        </div>
      )}
    </div>
  )
}
```

### NEW FILE: `frontend/src/app/consider-buying/similar/page.tsx`

```typescript
'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function SimilarItemsPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const itemId = searchParams.get('item_id')

  const [item, setItem] = useState<any>(null)
  const [similarItems, setSimilarItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch item data (stored in sessionStorage from previous page)
    const itemData = sessionStorage.getItem('consider_buying_item')
    if (itemData) {
      const parsed = JSON.parse(itemData)
      setItem(parsed.item)
      setSimilarItems(parsed.similar_items || [])
      setLoading(false)
    }
  }, [itemId])

  const handleShowExisting = () => {
    // Generate outfits with existing similar items
    router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=true`)
  }

  const handleContinueWithNew = () => {
    // Generate outfits with new item
    router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=false`)
  }

  if (loading) return <div>Loading...</div>

  if (similarItems.length === 0) {
    // No similar items - auto-proceed to outfit generation
    router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=false`)
    return null
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold mb-2">You already own similar items</h2>
      <p className="text-gray-600 mb-6">
        These might work for what you're looking for
      </p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {similarItems.map((similar, idx) => (
          <div key={idx} className="border rounded-lg p-4">
            <img
              src={similar.item.system_metadata.image_path}
              alt={similar.item.styling_details.name}
              className="w-full h-48 object-cover rounded mb-2"
            />
            <h3 className="font-medium">{similar.item.styling_details.name}</h3>
            <p className="text-sm text-gray-500">
              {Math.round(similar.similarity_score * 100)}% similar
            </p>
            <p className="text-xs text-gray-400">{similar.reason}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleShowExisting}
          className="flex-1 px-6 py-3 border border-black rounded-lg hover:bg-gray-50"
        >
          Show outfits with my existing items
        </button>
        <button
          onClick={handleContinueWithNew}
          className="flex-1 px-6 py-3 bg-black text-white rounded-lg"
        >
          Continue with new item
        </button>
      </div>
    </div>
  )
}
```

### NEW FILE: `frontend/src/app/consider-buying/outfits/page.tsx`

Similar to existing outfit reveal page, but with decision buttons at the end:
- "I bought it!" → Save to wardrobe
- "Not buying" → Track savings
- "Decide later" → Keep in considering bucket

---

## Testing Checklist

### Backend Tests

- [ ] Product extraction works with common sites (Zara, Everlane, etc.)
- [ ] Screenshot fallback works when extraction fails
- [ ] Similarity detection correctly identifies duplicates
- [ ] Similarity detection doesn't false-positive on different items
- [ ] Items save to consider_buying/ bucket
- [ ] Buying decisions tracked correctly
- [ ] Stats calculated correctly

### Frontend Tests

- [ ] Paste link flow works end-to-end
- [ ] Screenshot fallback triggers on extraction failure
- [ ] Similar items displayed correctly
- [ ] "Show existing" vs "Continue with new" both work
- [ ] Outfit generation completes
- [ ] Decision buttons work (bought/passed/later)
- [ ] "Considering" tab shows items correctly

### Integration Tests

- [ ] Full flow: Paste link → See duplicates → Generate outfits → Buy decision
- [ ] Full flow: Screenshot → No duplicates → Generate outfits → Pass decision
- [ ] Stats update correctly after decisions
- [ ] Images stored in correct S3 buckets

---

## Deployment Steps

1. Deploy backend changes to Railway
2. Deploy frontend changes to Vercel
3. Test with real product URLs
4. Ask Mia to test with her next shopping trip

---

## Success Metrics (Week 1)

- [ ] Mia pastes at least 1 product link
- [ ] Duplicate detection shows her existing items
- [ ] She makes a buying decision (bought or passed)
- [ ] Stats tracked correctly

---

## Future Enhancements (Phase 2)

- Mobile share sheet integration (PWA)
- AI recommendation ("We think you should/shouldn't buy this because...")
- Price tracking and alerts
- Bookmark/save for later management
- Multi-item consideration ("I want to buy jeans AND a blazer together")

---

**End of Spec**

This spec is ready for Cursor/Antigravity to implement. Estimated build time: 2-3 days.
