# Consider Item Actions - Design & Data Flow

## Revised UI Sketch

### Layout (Consider Item Detail Page)

```
┌─────────────────────────────────────┐
│  ← Back to Closet        Edit       │  ← Header (sticky)
├─────────────────────────────────────┤
│                                     │
│  [Item Image - 3:4 aspect ratio]    │
│                                     │
├─────────────────────────────────────┤
│  Item Name                          │
│  Category                           │
│                                     │
│  [Source URL] [Price]               │  ← If available
│                                     │
│  Metadata Grid (Colors, Texture...) │
│  Styling Notes                      │
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ✨ Show me possible outfits    ││  ← PRIMARY (terracotta)
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ✓ Bought it                    ││  ← Secondary (outlined)
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  ✕ Not interested anymore      ││  ← Secondary (outlined)
│  └─────────────────────────────────┘│
│                                     │
│  ┌─────────────────────────────────┐│
│  │  Delete from Considering       ││  ← Danger (red outlined)
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

### Button Styles (Design System)

**1. "Show me possible outfits" (Primary CTA)**
- Background: `bg-[var(--accent-terracotta)]` (#C85A3E)
- Text: White
- Icon: ✨ (sparkles) or 🎨
- Full width, rounded, shadow on hover
- Min height: 48px (mobile-friendly)

**2. "Bought it" (Secondary)**
- Border: `border-2 border-[var(--text-ink)]` (#1a1614)
- Background: Transparent
- Text: `text-[var(--text-ink)]`
- Icon: ✓ (checkmark)
- Hover: `hover:bg-[var(--accent-sand)]` (#E8DED2)

**3. "Not interested anymore" (Secondary)**
- Same style as "Bought it"
- Icon: ✕ (X) or 🚫
- Hover: `hover:bg-[var(--accent-sand)]`

**4. "Delete from Considering" (Danger)**
- Existing red outlined style
- Keep as-is

---

## Data Flow: "Bought it" Action

### User Journey
```
User clicks "Bought it"
    ↓
Frontend: POST /api/consider-buying/decide
    Body: { item_id: "consider_xxx", decision: "bought" }
    ↓
Backend: record_decision()
    ↓
1. Fetch consider_item from ConsiderBuyingManager
2. Download/copy image file
3. Convert consider_item → analysis_data format
4. Call WardrobeManager.add_wardrobe_item()
5. Remove from consider_buying list
6. Record decision in decisions.json
    ↓
Response: { success: true, decision: {...}, stats: {...} }
    ↓
Frontend: Redirect to /closet?user=xxx
```

### Backend Flow (Detailed)

```python
# 1. Get considering item
consider_item = {
    "id": "consider_fb49c4715146",
    "styling_details": {...},
    "structured_attrs": {...},
    "image_path": "s3://... or local path",
    "source_url": "https://...",
    "price": 89.99,
    "similar_items_in_wardrobe": ["item_123", "item_456"]
}

# 2. Download image
image_file = download_from_storage(consider_item["image_path"])

# 3. Convert to analysis_data
analysis_data = {
    'name': consider_item['styling_details']['name'],
    'category': consider_item['styling_details']['category'],
    'sub_category': consider_item['styling_details']['sub_category'],
    'colors': consider_item['styling_details']['colors'],
    'cut': consider_item['styling_details']['cut'],
    'texture': consider_item['styling_details']['texture'],
    'style': consider_item['styling_details']['style'],
    'fit': consider_item['styling_details']['fit'],
    'brand': consider_item['styling_details']['brand'],
    'trend_status': consider_item['styling_details']['trend_status'],
    'styling_notes': consider_item['styling_details']['styling_notes'],
    'fabric': consider_item['structured_attrs']['fabric'],
    'sleeve_length': consider_item['structured_attrs']['sleeve_length'],
    'waist_level': consider_item['structured_attrs']['waist_level'],
}

# 4. Add to wardrobe
wardrobe_item = WardrobeManager.add_wardrobe_item(
    uploaded_file=image_file,
    analysis_data=analysis_data,
    is_styling_challenge=False
)

# 5. Result: New wardrobe item with new ID
wardrobe_item = {
    "id": "abc123def456",  # NEW ID (not consider_xxx)
    "styling_details": {...},  # ✅ Preserved
    "structured_attrs": {...},  # ✅ Preserved
    "usage_metadata": {
        "is_styling_challenge": False,
        "tags": [],
        ...
    },
    "system_metadata": {
        "image_path": "new/path/to/image.jpg",  # ✅ New path
        "source": "unknown",  # ⚠️ Could preserve "consider_buying"
        ...
    }
}
```

---

## Metadata Mapping: Considering → Wardrobe

### ✅ Preserved Fields

| Considering Item Field | Wardrobe Item Field | Notes |
|------------------------|---------------------|-------|
| `styling_details.name` | `styling_details.name` | ✅ Direct mapping |
| `styling_details.category` | `styling_details.category` | ✅ Direct mapping |
| `styling_details.sub_category` | `styling_details.sub_category` | ✅ Direct mapping |
| `styling_details.colors` | `styling_details.colors` | ✅ Direct mapping |
| `styling_details.cut` | `styling_details.cut` | ✅ Direct mapping |
| `styling_details.texture` | `styling_details.texture` | ✅ Direct mapping |
| `styling_details.style` | `styling_details.style` | ✅ Direct mapping |
| `styling_details.fit` | `styling_details.fit` | ✅ Direct mapping |
| `styling_details.brand` | `styling_details.brand` | ✅ Direct mapping |
| `styling_details.trend_status` | `styling_details.trend_status` | ✅ Direct mapping |
| `styling_details.styling_notes` | `styling_details.styling_notes` | ✅ Direct mapping |
| `structured_attrs.fabric` | `structured_attrs.fabric` | ✅ Direct mapping |
| `structured_attrs.sleeve_length` | `structured_attrs.sleeve_length` | ✅ Direct mapping |
| `structured_attrs.waist_level` | `structured_attrs.waist_level` | ✅ Direct mapping |
| `image_path` | `system_metadata.image_path` | ✅ New path after copy |

### ⚠️ Potentially Lost Fields

| Considering Item Field | Current Status | Recommendation |
|------------------------|----------------|----------------|
| `source_url` | ❌ Not preserved | **Add to `system_metadata.source_url`** |
| `price` | ❌ Not preserved | **Add to `system_metadata.purchase_price`** |
| `similar_items_in_wardrobe` | ❌ Not preserved | **Optional: Add to `usage_metadata.tags` or new field** |
| `added_date` | ❌ Not preserved | **Optional: Add to `system_metadata.considered_at`** |
| `id` (consider_xxx) | ❌ New ID generated | **Optional: Add to `system_metadata.original_consider_id`** |

### 📝 Recommended Backend Changes

**Option 1: Preserve in system_metadata (Recommended)**
```python
# In consider_buying.py record_decision()
wardrobe_item = wardrobe_manager.add_wardrobe_item(...)

# After creation, update system_metadata
wardrobe_item["system_metadata"]["source_url"] = consider_item.get("source_url")
wardrobe_item["system_metadata"]["purchase_price"] = consider_item.get("price")
wardrobe_item["system_metadata"]["original_consider_id"] = consider_item.get("id")
wardrobe_item["system_metadata"]["source"] = "consider_buying"  # Instead of "unknown"
```

**Option 2: Extend add_wardrobe_item() signature**
```python
def add_wardrobe_item(
    uploaded_file,
    analysis_data: Dict,
    is_styling_challenge: bool = False,
    source_metadata: Optional[Dict] = None  # New parameter
):
    # ... existing code ...
    if source_metadata:
        item_data["system_metadata"].update({
            "source_url": source_metadata.get("source_url"),
            "purchase_price": source_metadata.get("price"),
            "source": "consider_buying"
        })
```

---

## Use Cases & Display Requirements

### 1. Wardrobe Display
- ✅ Item appears in closet grid
- ✅ All styling details visible
- ✅ Image displays correctly
- ⚠️ Source URL not shown (if not preserved)
- ⚠️ Purchase price not shown (if not preserved)

### 2. Outfit Generation
- ✅ Item can be used as anchor item
- ✅ All styling attributes available for matching
- ✅ Similar items logic works (if similar_items_in_wardrobe preserved)

### 3. Item Detail Page
- ✅ All metadata displays correctly
- ⚠️ "Source URL" section missing (if not preserved)
- ⚠️ "Purchase Price" section missing (if not preserved)

### 4. Analytics/Tracking
- ⚠️ Can't track which items came from "consider buying" (if source not preserved)
- ⚠️ Can't show purchase price history (if price not preserved)

---

## Implementation Checklist

### Frontend (`/closet/[item_id]/page.tsx`)
- [ ] Add "Show me possible outfits" button (primary, top)
- [ ] Add "Bought it" button (secondary)
- [ ] Add "Not interested anymore" button (secondary)
- [ ] Add API method `api.recordConsiderDecision(userId, itemId, decision)`
- [ ] Handle redirect after "bought it" → `/closet?user=xxx`
- [ ] Handle redirect after "not interested" → `/closet?user=xxx&category=Considering`
- [ ] Handle "show outfits" → `/consider-buying/outfits?item_id=xxx&user=xxx`

### Backend (`/api/consider-buying/decide`)
- [ ] Verify all styling_details fields preserved
- [ ] Verify all structured_attrs fields preserved
- [ ] **OPTIONAL**: Preserve source_url in system_metadata
- [ ] **OPTIONAL**: Preserve price in system_metadata
- [ ] **OPTIONAL**: Preserve original_consider_id in system_metadata

### API Client (`/lib/api.ts`)
- [ ] Add `recordConsiderDecision(userId, itemId, decision, reason?)` method

---

## Notes

- **"Show me possible outfits"** uses existing `/api/consider-buying/generate-outfits` endpoint
- **"Bought it"** uses existing `/api/consider-buying/decide` endpoint with `decision: "bought"`
- **"Not interested anymore"** uses existing `/api/consider-buying/decide` endpoint with `decision: "passed"`
- Current implementation already handles most metadata preservation
- Optional enhancements (source_url, price) can be added later without breaking changes



