# SPEC: Occasion-Based Outfit Generation (P0)

**Version**: 1.1
**Date**: 2025-11-14
**Status**: Ready for Implementation
**Estimated Time**: 3-5 hours

---

## Overview

Add a new "Plan My Outfit" flow that generates complete outfits based on:
1. **Occasion** (chips + free text, can combine both)
2. **Weather** (manual dropdowns for condition + temperature)

This is a new dashboard entry point that runs end-to-end from input → generation → reveal, separate from the existing "challenge item" flow.

**Key Difference from Challenge Item Flow**: Occasion-based has NO required items - the AI chooses the best pieces from the entire wardrobe based on occasion and weather.

---

## User Story

**As a user**, I want to tell the app what I'm doing today (e.g., "school drop-off + business meeting + afternoon tea with girlfriend") and what the weather is like, so it can generate complete outfits that are appropriate for my day without me having to think about which specific pieces to start with.

**UX Insight**: Users want to **tap common activities (chips) AND add special context (text)** in the same flow. Example: Tap "School drop-off" + "Business meeting" chips, then add "afternoon tea with girlfriend" in text box.

---

## Success Criteria

- [ ] New "Plan My Outfit" card appears on dashboard (col1, replaces "Generate New Outfit")
- [ ] Clicking card navigates to occasion input page
- [ ] User can select occasion(s) via chips (multi-select)
- [ ] User can add custom text input for additional context
- [ ] **BOTH chips AND text can be used together** (not either/or)
- [ ] User can select weather condition + temperature range via dropdowns
- [ ] "Generate Outfits" button triggers outfit generation with occasion/weather context
- [ ] Generated outfits appear on reveal page (reuse existing reveal page)
- [ ] Outfits are contextually appropriate for the occasion and weather
- [ ] NO challenge items required (AI picks best items from full wardrobe)
- [ ] Works E2E: Dashboard → Occasion Input → Reveal → Save/Dislike → Dashboard

---

## Architecture

### New Components

1. **Dashboard Card** (modify `_page_dashboard` in `new_onboarding.py`)
   - Replace col1 "Generate New Outfit" → "Plan My Outfit"

2. **Occasion Input Page** (new function `_page_plan_outfit` in `new_onboarding.py`)
   - Occasion selection (chips + text, combinable)
   - Weather selection (dropdowns)
   - Generate button

3. **Style Engine Enhancement** (modify `style_engine.py`)
   - Add occasion/weather parameters to `create_style_prompt()`
   - Make challenge items optional in prompt logic
   - Inject occasion/weather context into prompt

4. **Navigation** (modify routing in `new_onboarding.py`)
   - Add route: `step == "plan_outfit"` → `_page_plan_outfit()`

### Reused Components

- **Reveal Page**: Reuse existing `_page_reveal()` - minor changes to pass occasion context
- **Saved/Disliked Outfits**: Existing infrastructure works as-is
- **Wardrobe Manager**: Pull all items (no filtering)
- **User Profile**: Pull existing three-word style profile

---

## Detailed Implementation

### 1. Dashboard Card Update

**File**: `new_onboarding.py`
**Function**: `_page_dashboard()`
**Location**: Lines 1104-1108

**Current Code**:
```python
with col1:
    st.markdown("### Generate New Outfit")
    st.caption("How do you want to wear your pieces today?")
    if st.button("Create Outfit", type="primary", use_container_width=True):
        _nav_to("pick_one")
```

**New Code**:
```python
with col1:
    st.markdown("### Plan My Outfit")
    st.caption("Tell me the occasion, I'll style you")
    if st.button("Plan Outfit", type="primary", use_container_width=True):
        _nav_to("plan_outfit")
```

**Why**: Change language from generic "Generate" to specific "Plan My Outfit" to match the occasion-based mental model. Keep existing "pick_one" flow intact (will be accessed differently later).

---

### 2. Occasion Input Page (New)

**File**: `new_onboarding.py`
**Function**: `_page_plan_outfit(user_id: str)` (NEW)
**Insert After**: `_page_pick_one()` function (around line 1073)

**Full Implementation**:

```python
def _page_plan_outfit(user_id: str) -> None:
    """Occasion-based outfit planning: user specifies occasion + weather"""

    st.markdown("""
    <div class="onboarding-container">
        <div class="onboarding-grain"></div>
        <div class="onboarding-line-top"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="onboarding-title">What are you doing today?</h1>', unsafe_allow_html=True)
    st.markdown('<p class="onboarding-subtitle">Tell me the occasion and weather, I\'ll create the perfect outfit</p>', unsafe_allow_html=True)

    st.divider()

    # Occasion Selection Section
    st.markdown("### 📅 Occasion")
    st.caption("Tap the usual stuff, add anything special in the box below")

    # Default occasion chips (multi-select)
    occasion_chips = [
        "School drop-off",
        "Business meeting",
        "Coffee meeting",
        "Working from home",
        "Weekend errands",
        "Date night",
        "Formal event",
        "Brunch"
    ]

    # Multi-select chips via checkboxes in a grid
    selected_occasions = []
    cols = st.columns(4)
    for idx, occasion in enumerate(occasion_chips):
        col = cols[idx % 4]
        with col:
            if st.checkbox(occasion, key=f"occasion_chip_{idx}"):
                selected_occasions.append(occasion)

    # Free text input for custom occasions (can be used WITH chips)
    st.markdown("##### Add any special plans:")
    custom_occasion = st.text_input(
        "E.g., 'afternoon tea with girlfriend'",
        placeholder="Add anything special...",
        label_visibility="collapsed"
    )

    st.divider()

    # Weather Selection Section
    st.markdown("### 🌤️ Weather")
    st.caption("Help me choose weather-appropriate pieces")

    col1, col2 = st.columns(2)

    with col1:
        weather_condition = st.selectbox(
            "Weather Condition",
            ["Sunny", "Cloudy", "Rainy", "Snowy", "Windy"],
            index=0
        )

    with col2:
        temperature_range = st.selectbox(
            "Temperature",
            ["Cold (<50°F)", "Cool (50-65°F)", "Mild (65-75°F)", "Warm (75-85°F)", "Hot (85°F+)"],
            index=1  # Default to "Cool"
        )

    st.divider()

    # Generate Button
    # Combine chips AND text (not either/or)
    occasion_parts = []

    if selected_occasions:
        occasion_parts.extend(selected_occasions)

    if custom_occasion.strip():
        occasion_parts.append(custom_occasion.strip())

    # Join all parts
    if occasion_parts:
        final_occasion = " + ".join(occasion_parts)
    else:
        final_occasion = None

    # Show what will be generated
    if final_occasion:
        st.info(f"**Generating outfits for:** {final_occasion} | {weather_condition}, {temperature_range}")

    # Generate button (disabled if no occasion selected)
    if st.button(
        "✨ Generate Outfits",
        type="primary",
        use_container_width=True,
        disabled=(final_occasion is None)
    ):
        # Store context in session state
        st.session_state["occasion_context"] = {
            "occasion": final_occasion,
            "weather_condition": weather_condition,
            "temperature_range": temperature_range
        }

        # Clear any previous challenge item selection (this is occasion-based, not item-based)
        st.session_state.pop("selected_challenge_item_id", None)
        st.session_state.pop("selected_challenge_item", None)

        # Navigate to reveal page
        _nav_to("reveal")

    # Back button
    st.divider()
    if st.button("← Back to Dashboard", use_container_width=True):
        _nav_to("dashboard")
```

**Key Design Decisions**:

1. **Chips AND Text (Combined)**: User can select chips AND add custom text. Both are concatenated with " + " separator.
   - Example: "School drop-off + Business meeting + afternoon tea with girlfriend"
   - This matches real usage: common activities (chips) + special context (text)

2. **Multi-select chips via checkboxes**: Streamlit doesn't have native multi-select buttons, so use checkboxes styled in a grid (4 columns)

3. **Join with " + "**: Clear separator between occasion parts
   - Alternative (more natural): Could use ", " and "and" for last item
   - Current approach is simpler and AI handles either format

4. **Disabled state**: Button disabled until at least one occasion (chip or text) is provided

5. **Session state storage**: Store `occasion_context` dict for reveal page to access

6. **Clear challenge item state**: Ensure occasion-based flow doesn't accidentally pull in challenge item logic

7. **UI Copy**: "Tap the usual stuff, add anything special in the box below" clearly signals both can be used

---

### 3. Routing Update

**File**: `new_onboarding.py`
**Function**: `main()` routing section
**Location**: Around line 411

**Add this route**:
```python
elif step == "plan_outfit":
    _page_plan_outfit(user_id)
```

**Insert after**: The `elif step == "pick_one":` block

---

### 4. Style Engine Prompt Enhancement

**File**: `style_engine.py`

#### A. Add Parameters to Function Signature (Line 38)

**Current**:
```python
def create_style_prompt(self,
                      user_profile: Dict,
                      available_items: List[Dict],
                      styling_challenges: List[Dict]) -> str:
```

**New**:
```python
def create_style_prompt(self,
                      user_profile: Dict,
                      available_items: List[Dict],
                      styling_challenges: List[Dict],
                      occasion: Optional[str] = None,
                      weather_condition: Optional[str] = None,
                      temperature_range: Optional[str] = None) -> str:
```

#### B. Add Context Section to Prompt (After Line 58)

**Insert this section** after the "## USER STYLE PROFILE" section and before "## AVAILABLE WARDROBE":

```python
# Add occasion/weather context if provided
if occasion or weather_condition:
    prompt += "\n## TODAY'S CONTEXT\n"
    if occasion:
        prompt += f"- **Occasion**: {occasion}\n"
    if weather_condition and temperature_range:
        prompt += f"- **Weather**: {weather_condition}, {temperature_range}\n"
    elif weather_condition:
        prompt += f"- **Weather**: {weather_condition}\n"
```

#### C. Make Challenge Items Optional in Task Instructions

**Location**: Around lines 113-150

**Implementation Approach**: Build task instructions dynamically based on whether challenge items, occasion, and weather are provided.

**Add this code** (replace the static task section):

```python
# Build task instructions dynamically
task_intro = "Create"
task_steps = []

# Add occasion/weather context if provided
if occasion or weather_condition:
    context_parts = []
    if occasion:
        context_parts.append(occasion)
    if weather_condition and temperature_range:
        context_parts.append(f"{weather_condition}, {temperature_range}")
    elif weather_condition:
        context_parts.append(weather_condition)
    task_intro = f"Given today's context ({', '.join(context_parts)}), create"

    # Add appropriateness requirement
    occasion_text = occasion if occasion else "the activities"
    weather_text = temperature_range if temperature_range else "the climate"
    task_steps.append(f"0. **Are appropriate for the occasion and weather**: Ensure items work for {occasion_text} and {weather_text}")

# Add style DNA requirement (always present)
task_steps.append("1. **Honor their style DNA** (Principle 1): Ensure all three style words appear in the outfit")

# Add challenge item requirement (only if challenge items provided)
if styling_challenges and challenge_item_names:
    challenge_requirement = f"2. **REQUIRED: Include THE challenge item(s)**: Every outfit MUST include {challenge_items_text} in the items array. These specific pieces (marked \"(CHALLENGE ITEM - REQUIRED)\" in the wardrobe list above) are what the user specifically wants to style - make {'them' if len(challenge_item_names) > 1 else 'it'} feel wearable and authentic in every outfit."
    task_steps.append(challenge_requirement)

# Add remaining standard requirements (adjust numbering)
next_num = len(task_steps) + 1
task_steps.append(f"{next_num}. **Apply Intentional Contrast** (Principle 2): Use at least 2 types of contrast per outfit")
task_steps.append(f"{next_num + 1}. **Add Intentional Details** (Principle 3): Specify concrete styling gestures")
task_steps.append(f"{next_num + 2}. **No two pants in the same outfit**: A person can only wear one pair of pants at a time.")
task_steps.append(f"{next_num + 3}. **Neck space**: Consider visual balance when styling neck area (scarves, necklaces, tops with details)")

# Assemble final task section
prompt += f"\n## YOUR TASK\n{task_intro} 3 outfit combinations that:\n\n"
prompt += "\n".join(task_steps)
```

#### D. Update Final Reminder (Only if Challenge Items Present)

**Location**: Around line 149

**Replace the static CRITICAL reminder with**:

```python
# Add critical reminder only if challenge items required
if styling_challenges and challenge_item_names:
    prompt += f"\n\nCRITICAL: Each outfit MUST include {challenge_items_text} (marked \"(CHALLENGE ITEM - REQUIRED)\") in the items array. Use these specific pieces in every outfit combination - {'they are' if len(challenge_item_names) > 1 else 'it is'} what the user specifically wants to style."
```

---

### 5. Update `generate_outfit_combinations()` Method

**File**: `style_engine.py`
**Function**: `generate_outfit_combinations()`
**Location**: Around line 250

**Current Signature**:
```python
def generate_outfit_combinations(self,
                                user_profile: Dict,
                                available_items: List[Dict],
                                styling_challenges: List[Dict],
                                num_combinations: int = 3) -> List[OutfitCombination]:
```

**New Signature**:
```python
def generate_outfit_combinations(self,
                                user_profile: Dict,
                                available_items: List[Dict],
                                styling_challenges: List[Dict],
                                num_combinations: int = 3,
                                occasion: Optional[str] = None,
                                weather_condition: Optional[str] = None,
                                temperature_range: Optional[str] = None) -> List[OutfitCombination]:
```

**Update the `create_style_prompt()` call** (around line 265):

**Current**:
```python
prompt = self.create_style_prompt(
    user_profile=user_profile,
    available_items=available_items,
    styling_challenges=styling_challenges
)
```

**New**:
```python
prompt = self.create_style_prompt(
    user_profile=user_profile,
    available_items=available_items,
    styling_challenges=styling_challenges,
    occasion=occasion,
    weather_condition=weather_condition,
    temperature_range=temperature_range
)
```

---

### 6. Reveal Page Integration

**File**: `new_onboarding.py`
**Function**: `_page_reveal()`
**Location**: Around line 1160

**Find the outfit generation call** (approximate lines 1180-1200):

**Current**:
```python
# Generate outfits using style engine
engine = StyleGenerationEngine()
combinations = engine.generate_outfit_combinations(
    user_profile=profile,
    available_items=all_items,
    styling_challenges=[challenge_item] if challenge_item else []
)
```

**New**:
```python
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

---

## Data Flow

```
Dashboard
    ↓ (click "Plan Outfit")
Occasion Input Page (_page_plan_outfit)
    - User selects occasion chips (e.g., "School drop-off", "Business meeting")
    - User adds custom text (e.g., "afternoon tea with girlfriend")
    - Combined: "School drop-off + Business meeting + afternoon tea with girlfriend"
    - User selects weather dropdowns
    - Stores in session_state["occasion_context"]
    ↓ (click "Generate Outfits")
Reveal Page (_page_reveal)
    - Retrieves occasion_context from session state
    - Passes to style_engine.generate_outfit_combinations()
    - Passes EMPTY LIST for styling_challenges (no required items)
    - Style engine injects context into prompt
    - Prompt does NOT require specific challenge items
    - OpenAI generates appropriate outfits from full wardrobe
    ↓ (user sees outfits)
Save/Dislike/Generate More
    ↓ (click "Back to Dashboard")
Dashboard
```

---

## Example User Flows

### Flow 1: Chips Only
- User taps: "School drop-off" + "Business meeting"
- Result: `"School drop-off + Business meeting"`
- AI generates: Professional but comfortable outfit for morning transitions

### Flow 2: Text Only
- User types: "afternoon tea with my mother-in-law"
- Result: `"afternoon tea with my mother-in-law"`
- AI generates: Polished, appropriate outfit for formal tea

### Flow 3: Chips + Text (Most Common)
- User taps: "School drop-off" + "Business meeting"
- User adds: "afternoon tea with girlfriend"
- Result: `"School drop-off + Business meeting + afternoon tea with girlfriend"`
- AI generates: All-day versatile outfit that transitions from casual → professional → social

### Flow 4: Weather Impact
- Same as Flow 3, but weather is "Cold (<50°F)"
- AI generates: Layered outfit with coat, scarf, warm pieces

---

## Edge Cases & Error Handling

### 1. No Occasion Selected
- **Behavior**: Disable "Generate Outfits" button
- **Implementation**: `disabled=(final_occasion is None)` on button

### 2. User Navigates Directly to Reveal Without Occasion Context
- **Behavior**: Treat as normal generation (no occasion/weather context)
- **Implementation**: `occasion_context.get()` with defaults returns `None`, which is handled by optional parameters

### 3. User Has No Wardrobe Items
- **Behavior**: Existing error handling in reveal page will catch this
- **Implementation**: No changes needed

### 4. OpenAI API Fails
- **Behavior**: Existing error handling in `style_engine.py` will catch this
- **Implementation**: No changes needed

### 5. Very Long Occasion String
- **Example**: "School drop-off + Business meeting + Coffee meeting + Lunch + Afternoon tea with girlfriend + Dinner"
- **Behavior**: AI will handle it gracefully, prioritizing versatile all-day pieces
- **Implementation**: No validation needed, trust AI to parse

### 6. Occasion-Based Flow vs Challenge Item Flow
- **Behavior**: Occasion-based passes empty `[]` for `styling_challenges`, so AI can pick any items
- **Implementation**: Prompt conditionally requires challenge items only if `styling_challenges` is non-empty

---

## Testing Checklist

### Manual Testing (Builder-User)

**Phase 1: UI Flow**
- [ ] Dashboard displays "Plan My Outfit" card
- [ ] Clicking card navigates to occasion input page
- [ ] All 8 occasion chips display correctly
- [ ] Can select multiple chips (checkboxes work)
- [ ] Custom text input accepts free text
- [ ] Can use chips only (e.g., "School drop-off + Business meeting")
- [ ] Can use text only (e.g., "afternoon tea with girlfriend")
- [ ] Can use chips + text together (e.g., "School drop-off + Business meeting + afternoon tea")
- [ ] Weather dropdowns populate correctly
- [ ] "Generate Outfits" button is disabled when no occasion selected
- [ ] "Generate Outfits" button enables when occasion selected (chips or text)
- [ ] Info banner shows correct combined summary
- [ ] Back button returns to dashboard

**Phase 2: Generation**
- [ ] Chips only generates appropriate outfits
- [ ] Text only generates appropriate outfits
- [ ] Chips + text (combined) generates appropriate outfits
- [ ] Multiple chips generate versatile all-day outfits
- [ ] Different weather conditions affect outfit choices (e.g., cold = layers, hot = breathable)
- [ ] Generated outfits include weather-appropriate items
- [ ] **CRITICAL**: No specific items are required - AI chooses freely from full wardrobe

**Phase 3: Integration**
- [ ] Generated outfits appear on reveal page correctly
- [ ] Save outfit works (saves to saved_outfits.json)
- [ ] Dislike outfit works (saves to disliked_outfits.json)
- [ ] "Generate More" on reveal page maintains occasion context
- [ ] Back to dashboard clears occasion context (fresh state)
- [ ] Existing challenge item flow still works (unchanged)

**Phase 4: Real-World Usage (7-Day Test)**
- [ ] Day 1: Generate outfit for actual day's schedule (mix of chips + text)
- [ ] Day 2-7: Continue daily usage, note friction points
- [ ] Validate: Do you naturally use chips, text, or both?
- [ ] Validate: Are suggestions actually wearable?
- [ ] Validate: Does weather context improve recommendations?
- [ ] Validate: Do multi-occasion days generate appropriate outfits?

---

## Future Enhancements (Not in P0)

### Phase 2 (Week 2-3)
- **Smart chip learning**: Auto-populate chips from frequently typed custom occasions
  - Example: User types "afternoon tea" 3 times → becomes a chip
- **Weather API integration**: Auto-detect location and populate weather
- **Recent outfit exclusion**: Pass last 7 days of saved/disliked outfits to avoid repeats
- **Smarter joining**: Use ", " and "and" for more natural language
  - "School drop-off, Business meeting, and afternoon tea"

### Phase 3 (Month 2)
- **Occasion history**: "You wore [outfit] last time for this occasion"
- **Calendar integration**: Pull today's events from Google Calendar
- **Voice input**: Speak occasion instead of typing
- **Personalized chips**: Top 4 chips = user's most common occasions

---

## Definition of Done

- [ ] Code committed to main branch
- [ ] All manual testing checklist items pass
- [ ] Feature works E2E: Dashboard → Occasion → Reveal → Save → Dashboard
- [ ] Challenge item flow still works (unchanged behavior)
- [ ] Builder (you) has used feature for 1 full day and confirmed chips+text works well
- [ ] Ready for Mia to test

---

## Notes for Cursor Implementation

### Style Conventions
- Follow existing Streamlit patterns in `new_onboarding.py`
- Reuse CSS classes: `onboarding-container`, `onboarding-title`, `onboarding-subtitle`
- Use `_nav_to()` helper for navigation (don't modify URL params directly)
- Session state keys use lowercase with underscores (e.g., `occasion_context`)

### Code Organization
- New page function goes after `_page_pick_one()` (around line 1073)
- New routing goes with other `elif step ==` blocks (around line 411)
- Style engine changes are isolated to `style_engine.py` (don't modify other files)

### Prompt Engineering
- Keep occasion/weather context concise (1-2 lines in prompt)
- Don't over-constrain the AI (trust it to handle "business meeting + coffee + afternoon tea")
- Weather should influence but not dominate (style DNA still primary)
- Make challenge items conditional - only require them if `styling_challenges` is non-empty

### Session State Management
- Store occasion context in session state (persist across reruns)
- Clear context when navigating away from reveal → dashboard
- Don't store in query params (too verbose for URLs)

### Critical: Two Different Flows

**Occasion-Based Flow** (NEW):
```python
# From plan_outfit page → reveal
styling_challenges=[]  # Empty - no required items
occasion="School drop-off + Business meeting + afternoon tea with girlfriend"
weather_condition="Cloudy"
temperature_range="Cool (50-65°F)"
```

**Challenge Item Flow** (EXISTING):
```python
# From pick_one page → reveal
styling_challenges=[selected_item]  # One required item
occasion=None
weather_condition=None
temperature_range=None
```

Both flows converge at `_page_reveal()` but with different parameters.

### Key Implementation Detail: Chips + Text Concatenation

```python
# Combine chips AND text (not either/or)
occasion_parts = []

if selected_occasions:
    occasion_parts.extend(selected_occasions)  # Add all selected chips

if custom_occasion.strip():
    occasion_parts.append(custom_occasion.strip())  # Add custom text

# Join all parts
if occasion_parts:
    final_occasion = " + ".join(occasion_parts)
else:
    final_occasion = None
```

This allows:
- Chips only: `["School drop-off", "Business meeting"]` → `"School drop-off + Business meeting"`
- Text only: `["afternoon tea with girlfriend"]` → `"afternoon tea with girlfriend"`
- Both: `["School drop-off", "Business meeting", "afternoon tea with girlfriend"]` → `"School drop-off + Business meeting + afternoon tea with girlfriend"`

---

## Questions for Builder (Pei-Chin)

Before implementing, confirm:

1. **Chip layout**: 4 columns OK? Or prefer different layout?
2. **Default chips**: Are these 8 occasions right for your life? Any changes?
   - Current: School drop-off, Business meeting, Coffee meeting, Working from home, Weekend errands, Date night, Formal event, Brunch
3. **Temperature ranges**: Are the 5 ranges clear enough? Or need more granularity?
4. **Separator**: Use " + " or prefer ", " and "and" for last item?
   - " + ": Simpler, clear structure
   - ", and ": More natural language, slightly more complex

---

**End of Spec**

This spec is ready for Cursor to implement. Estimated time: 3-5 hours including testing.
