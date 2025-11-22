# Cursor Prompt: Improve Feedback UX with Radio/Checkbox Options

Replace text-based feedback with structured options for both Save and Dislike outfit flows.

## Context
Current UX requires users to type feedback on mobile, which is laborious. Replace with:
- **Dislike (👎)**: Radio buttons (pick ONE main reason) + optional Other text
- **Save (❤️)**: Checkboxes (pick multiple) + optional Other text

## Location
File: `new_onboarding.py`
Function: `_page_reveal()` (around lines 1635-1677)

---

## Change 1: Update Save Outfit feedback (line 1635-1652)

**Find this section (around line 1635):**
```python
if is_saving:
    # Show save feedback UI
    st.markdown("❤️ **Great choice!**")
    reason = st.text_area("Why do you like it? (optional)", key=f"save_reason_{idx}", placeholder="e.g., Love how this combines my style!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Done", key=f"save_done_{idx}", type="primary", use_container_width=True):
            from saved_outfits_manager import SavedOutfitsManager
            success = SavedOutfitsManager(user_id=user_id).save_outfit(combo, reason.strip())
```

**Replace with:**
```python
if is_saving:
    # Show save feedback UI
    st.markdown("❤️ **Great choice!**")
    st.markdown("What do you love about it?")

    # Quick feedback options (checkboxes - can select multiple)
    feedback_options = st.multiselect(
        "Select all that apply:",
        options=[
            "Perfect for my occasions",
            "Feels authentic to my style",
            "Never thought to combine these pieces",
            "Love the vibe",
        ],
        key=f"save_feedback_{idx}",
        label_visibility="collapsed"
    )

    # Optional custom feedback
    other_reason = st.text_input(
        "Other (optional):",
        key=f"save_other_{idx}",
        placeholder="e.g., Love how this layers!",
    )

    # Combine feedback
    reason_parts = feedback_options.copy()
    if other_reason.strip():
        reason_parts.append(f"Other: {other_reason.strip()}")
    reason = " | ".join(reason_parts) if reason_parts else ""

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Done", key=f"save_done_{idx}", type="primary", use_container_width=True):
            from saved_outfits_manager import SavedOutfitsManager
            success = SavedOutfitsManager(user_id=user_id).save_outfit(combo, reason)
```

---

## Change 2: Update Dislike Outfit feedback (line 1660-1677)

**Find this section (around line 1660):**
```python
elif is_disliking:
    # Show dislike feedback UI
    st.markdown("💭 **Sorry we missed the mark.**")
    reason = st.text_area("Tell us where it felt off? (optional)", key=f"dislike_reason_{idx}", placeholder="e.g., Too formal for my style")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Done", key=f"dislike_done_{idx}", type="primary", use_container_width=True):
            from disliked_outfits_manager import DislikedOutfitsManager
            success = DislikedOutfitsManager(user_id=user_id).dislike_outfit(combo, reason.strip())
```

**Replace with:**
```python
elif is_disliking:
    # Show dislike feedback UI
    st.markdown("💭 **Sorry we missed the mark.**")
    st.markdown("What's the main issue?")

    # Quick feedback options (radio buttons - pick ONE main reason)
    feedback_option = st.radio(
        "Select one:",
        options=[
            "Won't look good on me",
            "Doesn't match my occasions",
            "Not my style",
            "The outfit doesn't make sense",
            "Other",
        ],
        key=f"dislike_feedback_{idx}",
        label_visibility="collapsed"
    )

    # Show text input if "Other" is selected
    other_reason = ""
    if feedback_option == "Other":
        other_reason = st.text_input(
            "Please specify:",
            key=f"dislike_other_{idx}",
            placeholder="e.g., Two pairs of jeans in one outfit",
        )

    # Combine feedback
    if feedback_option == "Other" and other_reason.strip():
        reason = f"Other: {other_reason.strip()}"
    elif feedback_option == "Other":
        reason = "Other (no details provided)"
    else:
        reason = feedback_option

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Done", key=f"dislike_done_{idx}", type="primary", use_container_width=True):
            from disliked_outfits_manager import DislikedOutfitsManager
            success = DislikedOutfitsManager(user_id=user_id).dislike_outfit(combo, reason)
```

---

## Expected Behavior After Changes

### Save Outfit Flow:
**Before:**
- User sees empty text area
- Must type entire reason on mobile keyboard

**After:**
- User sees 4 checkboxes (can select multiple)
- Can select: ✓ "Feels authentic to my style" + ✓ "Love the vibe"
- Optional "Other" text field for custom feedback
- Saved as: `"Feels authentic to my style | Love the vibe"`
- Or with custom: `"Perfect for my occasions | Other: Love how this layers!"`

### Dislike Outfit Flow:
**Before:**
- User sees empty text area
- Must type entire reason on mobile keyboard

**After:**
- User sees 5 radio buttons (must pick ONE)
- If selects "Other", text input appears
- Saved as: `"Not my style"` or `"Other: Two pairs of jeans in one outfit"`

---

## Testing

1. Navigate to outfit reveal page
2. **Test Save flow:**
   - Click "Save Outfit" button
   - Verify you see 4 checkboxes
   - Select 2+ options (e.g., "Perfect for my occasions" + "Love the vibe")
   - Add text to "Other" field
   - Click Done
   - Verify feedback saved as: `"Perfect for my occasions | Love the vibe | Other: [your text]"`

3. **Test Dislike flow:**
   - Click "👎" button
   - Verify you see 5 radio buttons
   - Select "Not my style" → Click Done → Verify saved as `"Not my style"`
   - Click "👎" again on different outfit
   - Select "Other" → Verify text input appears
   - Type custom reason → Click Done → Verify saved as `"Other: [your text]"`

---

## Copy Guidelines
Feedback options follow `.claude/COPY_GUIDELINES.md`:
- Supportive tone: "Perfect for my occasions" (not "You nailed it")
- User-centric: "Not my style" (not "You got my style wrong")
- Collaborative: "Love the vibe" (casual, friendly)

---

## Files to Modify
- `new_onboarding.py` (lines ~1635-1677 in `_page_reveal()` function)

---

## Notes
- Radio buttons enforce MECE (mutually exclusive) for dislike reasons
- Checkboxes allow multiple positives for save reasons
- "Other" text input only appears if needed (conditional in dislike flow)
- Feedback stored as pipe-separated string: `"Reason 1 | Reason 2 | Other: custom text"`
