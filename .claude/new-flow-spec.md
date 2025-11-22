# New Onboarding Flow Specification
**Focus: "How Item" as the killer feature**

## Flow Overview
1. Welcome
2. Three Words
3. **Upload (UPDATED COPY)**
4. **Mark Your Challenges (NEW STEP)**
5. **Pick One to Style (NEW STEP - replaces vibe picker)**
6. Reveal (wire to How Item logic)

---

## STEP 3: Upload Page - COPY UPDATES ONLY

### Current Issues
- Generic prompt doesn't guide users to upload challenging items
- No context for WHY we need certain types of items

### New Copy (Update existing page, don't rebuild)

**Title:** "Your Digital Closet" (keep existing)

**New Subtitle/Instructional Copy:**
```
Upload 10-15 pieces, including things you love but don't wear often.

Think: The dress that might feel too dressy, or the skirt that doesn't 
quite go with other things you have. We'll help you style them.
```

**Progress milestone messages (update):**
- At 0 items: "Begin by uploading pieces from your closet"
- At 5 items: "Great start! Don't forget items you struggle to wear."
- At 10 items: "You can continue or proceed to styling!"
- At 15+ items: "Amazing variety! Ready to style your challenges?"

**Reassurance message (keep but maybe tweak):**
"Just hang or lay flat — don't worry about photo quality; the app figures it out."

### Technical Changes
- NO structural changes to upload UI
- ONLY update copy/text strings
- Keep existing upload interface, progress bar, etc.

---

## STEP 4: Mark Your Challenges (NEW PAGE)

### Purpose
Explicitly identify which uploaded items are "challenging pieces" that user wants help styling.

### Page Layout

**Back button:** ← Back (to upload)

**Title:** "Mark Your Challenges"

**Subtitle:**
```
Which pieces do you love but rarely wear?

These are items that feel too dressy, too bold, or just hard to style. 
We'll focus on making these work for you.
```

**Content:**
- Display all uploaded items in a grid (similar to current wardrobe display)
- Each item shows thumbnail + name
- Add visual indicator for selection state (checkbox, border, or overlay)
- Allow multi-select (can mark multiple items as challenges)

**Selection Interaction:**
- Tap/click item to toggle "marked as challenge"
- Visual feedback: Maybe orange/coral border or checkmark icon
- Must select at least 1 item to continue

**Reassurance Note (at bottom):**
```
💡 You can mark 1-3 pieces for now — we'll help you style them one at a time.
```

**Continue Button:**
- Text: "Continue → Pick One to Style"
- Disabled until at least 1 item marked
- When clicked: Store marked items in session state, navigate to step 5

### Technical Implementation

**New route:** `?step=mark_challenges`

**Session state:**
- Read: `wardrobe_items` (all uploaded)
- Write: `challenging_items` (list of item IDs marked as challenges)

**Data structure:**
```python
# Store just the item IDs or references
st.session_state["challenging_items"] = [item_id1, item_id2, ...]
```

**Also update wardrobe metadata:**
When items are marked, update their category in wardrobe_metadata.json to "styling_challenges" (or add a flag). This way the marking persists.

**Grid layout:**
- Reuse existing `WardrobeManager.display_wardrobe_item()` pattern
- Add selection toggle functionality
- 3 columns on mobile, 4-5 on desktop

---

## STEP 5: Pick One to Style (NEW PAGE - Replaces Vibe Picker)

### Purpose
User selects ONE challenging item to style right now. This becomes the focus of outfit generation.

### Page Layout

**Back button:** ← Back (to mark challenges)

**Title:** "Which piece do you want to wear?"

**Subtitle:**
```
We'll create outfits that make this piece feel authentically you.
```

**Content:**
- Display ONLY items marked as challenges in previous step
- Larger thumbnails than previous step (more prominent)
- Show item name + category
- Show why it's challenging (if user provided reason during upload - optional for now)

**Selection Interaction:**
- Tap/click to select ONE item
- Highlight selected item (visual feedback)
- Can change selection before continuing

**Additional Context (Optional - Simple Implementation):**

**Occasion selector (simple dropdown):**
```
Where might you wear this?
- Casual daily life (default)
- Work/professional
- Social event
- Weekend activities
```

**Confidence goal (simple dropdown):**
```
How bold do you want to feel?
- Comfort zone (default)
- Gentle push
- Bold move
```

**Generate Button:**
- Text: "✨ Style This Piece"
- Primary/prominent button
- Disabled until item selected
- When clicked: Navigate to reveal with selected item context

### Technical Implementation

**New route:** `?step=pick_one`

**Session state:**
- Read: `challenging_items` (from previous step)
- Write: `selected_challenge_item` (single item reference)
- Write: `occasion` (optional context)
- Write: `confidence_level` (optional context)

**Navigation:**
```python
# On button click:
st.session_state["selected_challenge_item"] = item
st.session_state["occasion"] = occasion  # from dropdown
st.session_state["confidence_level"] = confidence_level  # from dropdown
_nav_to("reveal")
```

---

## STEP 6: Reveal Page - LOGIC CHANGES

### Current Problem
Currently generates generic mood-based outfits. Needs to generate "How Item" outfits instead.

### Changes Needed

**Title change:**
```
OLD: "Your Outfit"
NEW: "How to Wear: [Item Name]"
```

**Subtitle:**
```
3 ways to style your [item name] that feel like you
```

**Generation Logic:**
Replace current generic generation with "How Item" approach (this logic already exists in legacy app.py, lines 218-348).

**Key parameters for outfit generation:**
```python
selected_item = st.session_state.get("selected_challenge_item")
occasion = st.session_state.get("occasion", "casual daily life")
confidence_level = st.session_state.get("confidence_level", "comfort zone")
style_profile = # from three words

# Get ALL other wardrobe items except the selected one
all_items = wm.get_wardrobe_items("all")
available_items = [item for item in all_items if item['id'] != selected_item['id']]

# Generate outfits featuring the selected challenge item
combinations = style_engine.generate_outfit_combinations(
    style_profile, 
    available_items,  # items to pair with
    [selected_item],  # the challenge item to feature
    confidence_goal=confidence_level,
    occasion=occasion
)
```

**Display:**
- Use existing magazine layout (outfit_visualizer)
- Each outfit MUST include the selected challenge item
- Show styling notes specific to that item
- Highlight the challenge item in each outfit (visual emphasis)

**Bottom Actions:**
```
[Generate Another] [Save Outfit] [Try Different Item]
                                  ↓
                        (goes back to step 5 - pick different challenge)
```

**Additional Context Display:**
```
Style: classic, minimal, bold  |  For: [occasion]  |  Confidence: [level]
```

---

## Implementation Order

### Phase 1: Update Copy (Quick - 15 min)
1. Update upload page subtitle and milestone messages
2. Test that copy feels clearer

### Phase 2: Add New Steps (2-3 hours)
3. Create `_page_mark_challenges()` in new_onboarding.py
4. Create `_page_pick_one()` in new_onboarding.py
5. Update router in `render_flow()` to include new steps
6. Test navigation: upload → mark → pick → reveal

### Phase 3: Wire Reveal Logic (1-2 hours)
7. Update `_page_reveal()` to use "How Item" logic
8. Test outfit generation focuses on selected item
9. Verify magazine layout displays properly

### Phase 4: Polish & Test (1 hour)
10. Test full flow on mobile
11. Verify items persist in session state correctly
12. Test with real wardrobe (10-15 items)

---

## Success Criteria

✅ User uploads items and copy guides them to include challenging pieces
✅ User can mark 1+ items as challenges
✅ User picks one item to style
✅ Generated outfits ALL feature that item and look styled (not random)
✅ Full flow works on mobile without breaking
✅ Magazine layout looks editorial/professional

---

## Notes for Cursor

- Reuse existing patterns from legacy "How Item" tab (app.py lines 218-348)
- Don't rebuild upload UI, just update copy/text
- Session state keys must be unique and persist across navigation
- Use existing `WardrobeManager` and `StyleGenerationEngine` methods
- Magazine layout code already exists in `outfit_visualizer.py`
- Focus on flow logic first, visual polish second

