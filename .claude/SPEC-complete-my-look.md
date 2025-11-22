# SPEC: Complete My Look (P1)

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Ready for Implementation
**Estimated Time**: 4-5 hours
**Dependencies**: Should be implemented after P0 (Occasion-Based) lands

---

## Overview

Transform the existing "challenge item" flow into "Complete My Look" by:
1. **Remove "challenge" concept entirely** - no more marking items as challenging
2. **Enable multi-select** (pick 1-2+ items instead of single item)
3. **Add shared weather component** (reusable across all flows)
4. **Update dashboard entry point** to "Complete My Look"
5. **Simplify onboarding** to remove challenge marking step

**Key Insight**: Tap into emotional desire for feeling "put-together" - common need for women. No negative framing about struggling with items.

---

## User Stories

**Story 1: Refresh an Item**
> "I want to wear this cute sweater today, but I want to wear it in a refreshing way"

**Story 2: Finish a Partial Outfit**
> "I already picked out the sweater and the jeans, but I need help finishing the outfit"

**Story 3: Feel Put-Together**
> "I know what pieces I like, but I want to look more polished/intentional"

---

## Success Criteria

- [ ] Dashboard card renamed: "Complete My Look" with copy about feeling put-together
- [ ] Multi-select enabled: User can select 1, 2, or more items
- [ ] All "challenge" language removed from UX copy
- [ ] Weather selection using shared component
- [ ] Shared `_render_weather_section()` helper used by both flows
- [ ] Onboarding simplified: Upload → Choose Path (Occasion vs Complete)
- [ ] Works E2E: Dashboard → Select Items → Weather → Reveal → Save/Dislike

---

## Architecture Changes

### 1. Shared Weather Component (NEW)
- Create `_render_weather_section()` helper function
- Stores weather in `st.session_state["weather_context"]`
- Reusable across occasion flow + complete flow

### 2. Dashboard Card (UPDATE)
- Change col1 from "Generate New Outfit" → "Complete My Look"
- New copy: "Feel put-together, effortlessly"

### 3. Pick One Page → Complete My Look Page (MORPH)
- Rename `_page_pick_one()` → `_page_complete_my_look()`
- Remove dependency on "marked challenges"
- Show ALL wardrobe items (not just challenges)
- Change single-select → multi-select (checkboxes)
- Add weather section using `_render_weather_section()`
- Update all copy to remove "challenge" language

### 4. Onboarding Flow (SIMPLIFY)
- Remove `_page_mark_challenges()` step entirely
- After upload, show path choice: Occasion vs Complete
- Both paths lead to dashboard after first generation

### 5. Reveal Page (MINOR UPDATE)
- Pass weather context from session state
- Support multiple anchor items

---

## Detailed Implementation

### PART 1: Shared Weather Component

**File**: `new_onboarding.py`
**Insert Before**: Any page functions (around line 400)

```python
def _render_weather_section() -> Dict:
    """Shared weather selection component that persists in session state.

    Returns dict with 'condition' and 'temperature' keys.
    Can be called from any page - stores/reads from session state for consistency.
    """

    # Initialize weather context if not set
    if "weather_context" not in st.session_state:
        st.session_state["weather_context"] = {
            "condition": "Sunny",
            "temperature": "Cool (50-65°F)"
        }

    st.markdown("### 🌤️ Weather")
    st.caption("Help me choose weather-appropriate pieces")

    col1, col2 = st.columns(2)

    weather_options = ["Sunny", "Cloudy", "Rainy", "Snowy", "Windy"]
    temp_options = ["Cold (<50°F)", "Cool (50-65°F)", "Mild (65-75°F)", "Warm (75-85°F)", "Hot (85°F+)"]

    with col1:
        # Get current value from session state
        current_condition = st.session_state["weather_context"]["condition"]
        try:
            condition_index = weather_options.index(current_condition)
        except ValueError:
            condition_index = 0

        condition = st.selectbox(
            "Weather Condition",
            weather_options,
            index=condition_index,
            key="weather_condition_select"
        )

    with col2:
        # Get current value from session state
        current_temp = st.session_state["weather_context"]["temperature"]
        try:
            temp_index = temp_options.index(current_temp)
        except ValueError:
            temp_index = 1  # Default to "Cool"

        temperature = st.selectbox(
            "Temperature",
            temp_options,
            index=temp_index,
            key="weather_temperature_select"
        )

    # Update session state
    st.session_state["weather_context"] = {
        "condition": condition,
        "temperature": temperature
    }

    return st.session_state["weather_context"]
```

---

### PART 2: Update Occasion Flow to Use Shared Weather

**File**: `new_onboarding.py`
**Function**: `_page_plan_outfit()`

**Find the weather section** (currently duplicated code):
```python
# Weather Selection Section
st.markdown("### 🌤️ Weather")
st.caption("Help me choose weather-appropriate pieces")

col1, col2 = st.columns(2)
# ... full weather dropdown code ...
```

**Replace with**:
```python
# Weather Selection Section (shared component)
st.divider()
weather_context = _render_weather_section()
weather_condition = weather_context["condition"]
temperature_range = weather_context["temperature"]
```

---

### PART 3: Morph Pick One → Complete My Look

**File**: `new_onboarding.py`
**Current Function**: `_page_pick_one(user_id: str)`
**New Function Name**: `_page_complete_my_look(user_id: str)`

#### A. Function Signature and Back Button

**Current** (line 931-935):
```python
def _page_pick_one(user_id: str) -> None:
    wm = WardrobeManager(user_id=user_id)

    if st.button("← Back", key="pick_back"):
        _nav_to("mark_challenges")
```

**New**:
```python
def _page_complete_my_look(user_id: str) -> None:
    wm = WardrobeManager(user_id=user_id)

    if st.button("← Back to Dashboard", key="pick_back"):
        # Clear selection when going back
        st.session_state.pop("selected_anchor_items", None)
        _nav_to("dashboard")
```

**Why**: Go back to dashboard (not mark_challenges which we're removing), clear selection state.

#### B. Load All Items (Not Just Challenges)

**Current** (lines 937-962):
```python
# Load from session state first, fallback to database for returning users
challenge_ids = st.session_state.get("challenging_items", [])
if not challenge_ids:
    # Load persisted challenges from database
    existing_challenges = {
        item.get("id")
        for item in wm.get_wardrobe_items("styling_challenges")
        if item.get("id")
    }
    challenge_ids = list(existing_challenges)
    if challenge_ids:
        st.session_state["challenging_items"] = challenge_ids

if not challenge_ids:
    st.info("Mark at least one styling challenge to continue.")
    if st.button("Back to Mark Challenges", key="pick_back_mark"):
        _nav_to("mark_challenges")
    return

all_items = wm.get_wardrobe_items("all")
challenge_lookup = {item.get("id"): item for item in all_items if item.get("id") in challenge_ids}
if not challenge_lookup:
    st.warning("We couldn't find those challenge items. Try marking them again.")
    if st.button("Back to Closet", key="pick_back_upload"):
        _nav_to("mark_challenges")
    return
```

**New**:
```python
# Load ALL wardrobe items (no challenge filtering)
all_items = wm.get_wardrobe_items("all")

if not all_items:
    st.info("Upload some photos of your wardrobe to get started.")
    if st.button("Go to Upload", key="pick_go_upload"):
        _nav_to("upload")
    return

# Create lookup by item ID
items_lookup = {item.get("id"): item for item in all_items if item.get("id")}
```

**Why**: No more "challenge items" concept - user can select from their entire wardrobe.

#### C. Update Header Copy

**Current** (lines 969-982):
```python
_render_html_block(
    """
    <div class="onboarding-container">
        <div class="onboarding-grain"></div>
        <div class="onboarding-line-top"></div>
        <div class="onboarding-content-medium" style="margin-bottom: 1.5rem;">
            <h2 class="onboarding-title" style="margin-bottom: 0.75rem;">Which piece do you want to wear?</h2>
            <p class="onboarding-subtitle" style="max-width: 36rem;">
                We'll create outfits that make this piece feel authentically you.
            </p>
        </div>
    </div>
    """
)
```

**New**:
```python
_render_html_block(
    """
    <div class="onboarding-container">
        <div class="onboarding-grain"></div>
        <div class="onboarding-line-top"></div>
        <div class="onboarding-content-medium" style="margin-bottom: 1.5rem;">
            <h2 class="onboarding-title" style="margin-bottom: 0.75rem;">What do you want to wear?</h2>
            <p class="onboarding-subtitle" style="max-width: 36rem;">
                Pick 1 or more pieces, and I'll complete the outfit to make you feel put-together.
            </p>
        </div>
    </div>
    """
)
```

**Why**: Remove "challenge" framing, emphasize "put-together" emotional benefit, signal multi-select.

#### D. Multi-Select Item Grid

**Current** (lines 1012-1041):
```python
num_columns = 2 if len(challenge_lookup) > 1 else 1
columns = st.columns(num_columns)

for idx, (item_id, item) in enumerate(challenge_lookup.items()):
    # ... render card ...

    if st.button("Style This Piece", key=f"pick_select_{item_id}", use_container_width=True):
        _confirm_style_dialog(item_id, name, item, user_id)
```

**New**:
```python
# Initialize selected items in session state
if "selected_anchor_items" not in st.session_state:
    st.session_state["selected_anchor_items"] = []

selected_item_ids = st.session_state["selected_anchor_items"]

# Display items in grid (3 columns for better density)
num_columns = min(3, len(items_lookup))
columns = st.columns(num_columns) if num_columns > 0 else [st.container()]

for idx, (item_id, item) in enumerate(items_lookup.items()):
    details = item.get("styling_details") or {}
    name = details.get("name") or item.get("name") or "Unnamed Piece"
    category = details.get("category", "")
    image_path = _resolve_item_image_path(item)

    col = columns[idx % num_columns]
    with col:
        # Card styling
        is_selected = item_id in selected_item_ids
        card_class = "pick-one-card selected" if is_selected else "pick-one-card"
        st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)

        # Image
        if image_path:
            st.image(image_path, use_container_width=True)
        else:
            st.markdown(
                "<div style='height:220px;border-radius:16px;background:#FAF7F2;display:flex;align-items:center;justify-content:center;color:#6B625A;'>📷 Add a photo</div>",
                unsafe_allow_html=True,
            )

        # Item details
        st.markdown(f"<h3>{html.escape(str(name))}</h3>", unsafe_allow_html=True)
        if category:
            st.markdown(f"<p>{html.escape(str(category)).title()}</p>", unsafe_allow_html=True)

        # Multi-select checkbox
        if st.checkbox(
            "Include in outfit",
            value=is_selected,
            key=f"select_item_{item_id}"
        ):
            if item_id not in selected_item_ids:
                selected_item_ids.append(item_id)
                st.session_state["selected_anchor_items"] = selected_item_ids
        else:
            if item_id in selected_item_ids:
                selected_item_ids.remove(item_id)
                st.session_state["selected_anchor_items"] = selected_item_ids

        st.markdown("</div>", unsafe_allow_html=True)
```

**Why**:
- Show all items (not just challenges)
- Checkboxes for multi-select
- Selected state shown with CSS class
- 3 columns for better density (more items visible)

#### E. Add Weather Section

**Insert after item grid**:
```python
st.divider()

# Weather Selection (shared component)
weather_context = _render_weather_section()
```

#### F. Add Bottom CTA

**Insert after weather section**:
```python
st.divider()

# Show selection summary
selected_item_ids = st.session_state.get("selected_anchor_items", [])
num_selected = len(selected_item_ids)

if num_selected > 0:
    if num_selected == 1:
        st.info(f"**You've selected:** {num_selected} piece")
    else:
        st.info(f"**You've selected:** {num_selected} pieces")

# Generate button
if st.button(
    "✨ Complete My Look",
    type="primary",
    use_container_width=True,
    disabled=(num_selected == 0)
):
    # Get selected item objects
    selected_item_objects = [
        item for item in all_items
        if item.get("id") in selected_item_ids
    ]

    # Store in session state for reveal page
    st.session_state["selected_anchor_items_objects"] = selected_item_objects

    # Clear any previous occasion context (this is item-based, not occasion-based)
    st.session_state.pop("occasion_context", None)

    # Clear cached outfits
    for key in list(st.session_state.keys()):
        if key.startswith("_reveal_how_item_") or key == "_merch_reveal_outfits":
            st.session_state.pop(key)

    # Navigate to reveal
    _nav_to("reveal")
```

---

### PART 4: Update Dashboard Card

**File**: `new_onboarding.py`
**Function**: `_page_dashboard()`
**Location**: Lines 1104-1108

**Current** (after P0 lands):
```python
with col1:
    st.markdown("### Plan My Outfit")
    st.caption("Tell me the occasion, I'll style you")
    if st.button("Plan Outfit", type="primary", use_container_width=True):
        _nav_to("plan_outfit")
```

**New**:
```python
with col1:
    st.markdown("### Complete My Look")
    st.caption("Feel put-together, effortlessly")
    if st.button("Complete My Look", type="primary", use_container_width=True):
        _nav_to("complete_my_look")
```

**Alternative** (if you want both paths visible on dashboard):
```python
# Add a 5th column or use tabs/expander
with col1:
    st.markdown("### Create Outfit")

    tab1, tab2 = st.tabs(["By Occasion", "By Items"])

    with tab1:
        st.caption("Tell me what you're doing today")
        if st.button("Plan My Outfit", key="dash_occasion", use_container_width=True):
            _nav_to("plan_outfit")

    with tab2:
        st.caption("Pick pieces to wear")
        if st.button("Complete My Look", key="dash_complete", use_container_width=True):
            _nav_to("complete_my_look")
```

**Recommendation**: Start with single entry point "Complete My Look", see if users ask for occasion-based option.

---

### PART 5: Update Routing

**File**: `new_onboarding.py`
**Function**: `main()` routing section
**Location**: Around line 411

**Find**:
```python
elif step == "pick_one":
    _page_pick_one(user_id)
```

**Replace with**:
```python
elif step == "pick_one" or step == "complete_my_look":
    _page_complete_my_look(user_id)
```

**Why**: Support both old route (`pick_one` for backwards compatibility) and new route (`complete_my_look`).

---

### PART 6: Simplify Onboarding (Remove Mark Challenges)

**File**: `new_onboarding.py`

#### A. Remove Mark Challenges Page Reference

**Find and comment out or delete**:
```python
elif step == "mark_challenges":
    _page_mark_challenges(user_id)
```

#### B. Update Upload Page to Skip to Dashboard

**Find**: `_page_upload()` function (around line 600-700)

**Current**: After upload, navigates to `mark_challenges`
**New**: After upload (when reaching minimum), navigate to dashboard or path choice

**Find the navigation logic** (likely near end of upload function):
```python
# After successful upload
if len(uploaded_items) >= minimum_required:
    _nav_to("mark_challenges")
```

**Replace with**:
```python
# After successful upload
if len(uploaded_items) >= minimum_required:
    _nav_to("path_choice")  # New page to choose between occasion vs complete
```

#### C. Create Path Choice Page (NEW)

**Insert after `_page_upload()`**:

```python
def _page_path_choice(user_id: str) -> None:
    """Let user choose between occasion-based or item-based outfit creation"""

    st.markdown("""
    <div class="onboarding-container">
        <div class="onboarding-grain"></div>
        <div class="onboarding-line-top"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="onboarding-title">How would you like to get started?</h1>', unsafe_allow_html=True)
    st.markdown('<p class="onboarding-subtitle">Choose whichever feels right for today - you can always try the other way later</p>', unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="padding: 2rem; background: linear-gradient(135deg, #FAF7F2 0%, #F5EFE6 100%); border-radius: 16px; min-height: 280px;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">📅</div>
        <h3 style="margin-bottom: 0.5rem;">Plan My Outfit</h3>
        <p style="color: #6B625A; margin-bottom: 1.5rem;">Tell me the occasion and weather, I'll create the full outfit</p>
        <p style="color: #8B7E74; font-size: 0.9rem;">Perfect for: "What should I wear for school drop-off + business meeting?"</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Start with Occasion", key="path_occasion", use_container_width=True, type="primary"):
            _nav_to("plan_outfit")

    with col2:
        st.markdown("""
        <div style="padding: 2rem; background: linear-gradient(135deg, #FFF5F0 0%, #FFE8DC 100%); border-radius: 16px; min-height: 280px;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">✨</div>
        <h3 style="margin-bottom: 0.5rem;">Complete My Look</h3>
        <p style="color: #6B625A; margin-bottom: 1.5rem;">Pick pieces you want to wear, I'll finish the outfit</p>
        <p style="color: #8B7E74; font-size: 0.9rem;">Perfect for: "I want to wear this cute sweater in a fresh way"</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Start with Items", key="path_complete", use_container_width=True, type="primary"):
            _nav_to("complete_my_look")

    st.divider()

    # Skip option (go straight to dashboard)
    if st.button("Skip for now, go to Dashboard", use_container_width=True):
        _nav_to("dashboard")
```

#### D. Add Routing for Path Choice

**In routing section**:
```python
elif step == "path_choice":
    _page_path_choice(user_id)
```

---

### PART 7: Update Reveal Page

**File**: `new_onboarding.py`
**Function**: `_page_reveal()`
**Location**: Around line 1160-1200

**Find the outfit generation code**:
```python
# Get challenge item if available
challenge_item = st.session_state.get("selected_challenge_item")

# Get occasion context if available (from plan_outfit flow)
occasion_context = st.session_state.get("occasion_context", {})

# Generate outfits using style engine
engine = StyleGenerationEngine()
combinations = engine.generate_outfit_combinations(
    user_profile=profile,
    available_items=all_items,
    styling_challenges=[challenge_item] if challenge_item else [],
    occasion=occasion_context.get("occasion"),
    weather_condition=occasion_context.get("weather_condition"),
    temperature_range=occasion_context.get("temperature_range")
)
```

**Replace with**:
```python
# Get anchor items if available (from complete_my_look flow)
anchor_items = st.session_state.get("selected_anchor_items_objects", [])

# Fallback: check for single challenge item (old flow - backwards compatibility)
if not anchor_items:
    challenge_item = st.session_state.get("selected_challenge_item")
    if challenge_item:
        anchor_items = [challenge_item]

# Get occasion context if available (from plan_outfit flow)
occasion_context = st.session_state.get("occasion_context", {})

# Get weather context (from shared weather component)
weather_context = st.session_state.get("weather_context", {})

# Generate outfits using style engine
engine = StyleGenerationEngine()
combinations = engine.generate_outfit_combinations(
    user_profile=profile,
    available_items=all_items,
    styling_challenges=anchor_items,  # Can be empty list, single item, or multiple items
    occasion=occasion_context.get("occasion"),
    weather_condition=weather_context.get("condition") or occasion_context.get("weather_condition"),
    temperature_range=weather_context.get("temperature") or occasion_context.get("temperature_range")
)
```

**Why**:
- Supports both flows: occasion-based (empty `anchor_items`) and complete-my-look (1+ `anchor_items`)
- Weather pulled from shared component first (session state), falls back to occasion context
- Backwards compatible with old single-item flow

---

### PART 8: Update Style Engine Prompt Language

**File**: `style_engine.py`
**Function**: `create_style_prompt()`
**Location**: Task instructions section (lines 113-150)

**Find** (after P0 lands, this will be dynamic):
```python
# Add challenge item requirement (only if challenge items provided)
if styling_challenges and challenge_item_names:
    challenge_requirement = f"2. **REQUIRED: Include THE challenge item(s)**: Every outfit MUST include {challenge_items_text} in the items array. These specific pieces (marked \"(CHALLENGE ITEM - REQUIRED)\" in the wardrobe list above) are what the user specifically wants to style - make {'them' if len(challenge_item_names) > 1 else 'it'} feel wearable and authentic in every outfit."
    task_steps.append(challenge_requirement)
```

**Replace with**:
```python
# Add anchor item requirement (only if anchor items provided)
if styling_challenges and challenge_item_names:
    anchor_requirement = f"2. **REQUIRED: Use these anchor pieces**: Every outfit MUST include {challenge_items_text} in the items array. These are the pieces the user wants to wear today - style them in a fresh, wearable way that makes the user feel put-together. Complete the outfit with complementary items from their wardrobe."
    task_steps.append(anchor_requirement)
```

**Why**: Change from "challenge items the user struggles with" to "anchor pieces the user wants to wear" - removes negative framing, adds "put-together" emotional benefit.

---

## Data Flow Summary

### Flow 1: Occasion-Based (P0)
```
Dashboard → Plan My Outfit
    ↓
Occasion Input Page
    - Select occasions (chips + text)
    - Select weather (_render_weather_section → session state)
    ↓
Reveal Page
    - styling_challenges = []  (no anchor items)
    - occasion = "School drop-off + Business meeting"
    - weather from session state
    ↓
AI generates outfits using full wardrobe
```

### Flow 2: Complete My Look (P1)
```
Dashboard → Complete My Look
    ↓
Complete My Look Page
    - Select 1+ items (checkboxes from ALL wardrobe)
    - Select weather (_render_weather_section → session state)
    ↓
Reveal Page
    - styling_challenges = [selected items]  (anchor items)
    - occasion = None
    - weather from session state
    ↓
AI generates outfits using anchor items + fills gaps
```

### Onboarding (New Users)
```
Upload Photos (10+ items)
    ↓
Path Choice Page
    - Plan My Outfit (occasion-based) → Occasion page
    - Complete My Look (item-based) → Complete page
    - Skip → Dashboard
    ↓
Either flow → Generate first outfit → Dashboard
```

---

## Session State Keys

### New Keys (Primary):
- `selected_anchor_items` - List of selected item IDs (for complete my look flow)
- `selected_anchor_items_objects` - List of selected item objects (passed to reveal)
- `weather_context` - Dict with `condition` and `temperature` (shared across flows)
- `occasion_context` - Dict with `occasion`, `weather_condition`, `temperature_range` (occasion flow only)

### Old Keys (Keep for Backwards Compatibility):
- `selected_challenge_item_id` - Single item ID (old flow)
- `selected_challenge_item` - Single item object (old flow)
- `challenging_items` - List of challenge IDs (no longer used, but don't break if exists)

---

## UX Copy Changes

### All Instances of "Challenge" Language → Remove

**Old → New:**
- "Styling challenges" → "Items in your closet" or just remove
- "Challenge items" → "Selected pieces" or "Anchor pieces"
- "Which piece do you want to wear?" → "What do you want to wear?"
- "Mark styling challenges" → Remove step entirely
- "Style This Piece" (button) → "Include in outfit" (checkbox)
- "CHALLENGE ITEM - REQUIRED" (in wardrobe list) → "ANCHOR PIECE" (in prompt only, not shown to user)

### New Emotional Framing:
- "Feel put-together, effortlessly" (dashboard)
- "I'll complete the outfit to make you feel put-together" (page subtitle)
- "Fresh, wearable way" (prompt language)

---

## Testing Checklist

### Phase 1: Shared Weather Component
- [ ] Weather component displays on occasion page
- [ ] Weather component displays on complete my look page
- [ ] Weather persists across both pages (same session state)
- [ ] Changing weather in one flow reflects in the other

### Phase 2: Complete My Look UI
- [ ] Page loads with ALL wardrobe items (not just challenges)
- [ ] Items display in 3-column grid
- [ ] Can select 1 item (checkbox works)
- [ ] Can select multiple items (2, 3, 4+)
- [ ] Selected state shows visually (CSS class)
- [ ] Selection summary shows correct count
- [ ] "Complete My Look" button disabled when nothing selected
- [ ] "Complete My Look" button enabled when 1+ items selected
- [ ] Weather section displays
- [ ] Back button clears selection and goes to dashboard

### Phase 3: Onboarding Flow
- [ ] After upload, see path choice page
- [ ] Both paths explained clearly
- [ ] "Plan My Outfit" button goes to occasion page
- [ ] "Complete My Look" button goes to complete page
- [ ] Skip button goes to dashboard
- [ ] No reference to "mark challenges" anywhere

### Phase 4: Generation & Integration
- [ ] Single anchor item generates appropriate outfits
- [ ] Multiple anchor items generate appropriate outfits
- [ ] Generated outfits include all selected anchor items
- [ ] Weather affects outfit suggestions
- [ ] Save outfit works
- [ ] Dislike outfit works
- [ ] Back to dashboard clears selection

### Phase 5: Copy Audit
- [ ] No "challenge" language in any user-facing copy
- [ ] Dashboard says "Complete My Look"
- [ ] Page title says "What do you want to wear?"
- [ ] Subtitle mentions "put-together"
- [ ] Button says "Complete My Look"
- [ ] Prompt uses "anchor pieces" not "challenge items"

### Phase 6: Flow Coexistence
- [ ] Occasion flow still works (no regression)
- [ ] Complete flow works independently
- [ ] Weather set in one flow carries to the other
- [ ] Switching flows clears the right context

---

## Migration & Backwards Compatibility

### Keep Working:
- Old route `pick_one` still works (routes to `_page_complete_my_look`)
- Old session keys `selected_challenge_item` still work (reveal page checks both)
- Existing users who have "marked challenges" can still access them

### Gradual Migration:
- Week 1: Deploy new code, both routes work
- Week 2-3: Monitor usage, see if anyone uses old route
- Week 4+: Deprecate old route if no usage

### Don't Break:
- Users mid-flow when you deploy (session state keys compatible)
- Saved outfits (no schema changes)
- Wardrobe metadata (keep internal structure, just don't surface "challenge_reason" in UX)

---

## Definition of Done

- [ ] Code committed to main branch
- [ ] All testing checklist items pass
- [ ] Shared weather component works in both flows
- [ ] Complete my look flow works E2E
- [ ] Onboarding simplified (no mark challenges step)
- [ ] All "challenge" language removed from UX
- [ ] Dashboard shows "Complete My Look"
- [ ] Occasion flow still works (no regression)
- [ ] Builder has used both flows for 2 days
- [ ] Ready for Mia to test

---

## Notes for Cursor

### Key Principles:
1. **Remove "challenge" from UX, not from code** - Internal variables can stay (`styling_challenges` parameter is fine), but all user-facing copy must change
2. **Show ALL items, not just challenges** - Load full wardrobe, user picks what they want
3. **Multi-select is key** - Checkboxes, not buttons. Allow 1, 2, 3+ items.
4. **Weather is shared** - One component, two pages, same session state
5. **Backwards compatible** - Old routes and session keys still work

### Implementation Order:
1. Create `_render_weather_section()` helper
2. Update occasion flow to use it
3. Morph `_page_pick_one()` → `_page_complete_my_look()`
4. Update dashboard card
5. Create path choice page
6. Update routing
7. Update reveal page
8. Audit and remove all "challenge" copy

### Testing Focus:
- Multi-select works smoothly
- Weather persists across flows
- No "challenge" language visible anywhere
- Both flows work independently and together

---

**End of Spec**

This spec is ready for Cursor to implement after P0 (Occasion-Based) lands. Estimated time: 4-5 hours including testing.
