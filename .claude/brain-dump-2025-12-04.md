
## 2025-12-04 - Reflection on Diagnostic Journey

I'm glad we're starting the journey of evaling and identifying what great looks like, what's missing. but i feel we're in a bit of wild goose chase, or having fancy analysis to validate what I already know:

a) across independent occasions the same item gets selected (over representation)
b) the styling is good not great - sometimes the layering is off, the wrong item (like sneaker for a wedding when the rest is not formal) 
c) I still don't know why they recommend certain things and therefore I don't know how to fix

I feel a bit lost on what I'm actually trying to do, but I think pushing through this and having independent thinking on my own and not overly relying on AI's input is critical.


## 2025-12-04 - Core Insights on LLM Behavior and 5-Star Outputs

### 1. The Training Data Distribution Problem

**LLMs naturally create the most likely output (center of mass)**
- 4-star results = the statistical center of billions of training examples
- 5-star results = the creative tail, statistical outliers
- The model KNOWS these exceptional outputs exist (they're in training data), but they're not the highest-probability path

**My job is to:**
- Push the model toward the creative tail (prompting, reasoning)
- Filter out the bad creative outputs (validation, constraints)  
- Keep the good creative outputs (the 5-stars)

The exceptional, surprising, creative stuff exists in the long tail of the distribution. The model knows it's possible - it's seen examples - but it's not the default path.

### 2. RLHF Makes This Worse

Reinforcement learning with human feedback creates risk aversion:
- The penalty of a bad result outweighs the reward of a 5-star result
- Models become even more conservative, defaulting to safe 4-star outputs
- This explains why models generate "good enough" outfits that lack surprise

### 3. The Solution: Explicit Reasoning/Process (Chain-of-Thought)

**Current approach (declarative):**
```
Principle 1: Style DNA Alignment
Every outfit MUST reflect ALL three aspects...
```
→ This tells the model WHAT to do, but not HOW to think through it

**Better approach (procedural):**
```
STEP 1: FUNCTION ANALYSIS
Before selecting any items, answer:
- What's the primary function of this outfit?
- What constraints exist?
- What ONE thing must this outfit accomplish?

STEP 2: ANCHOR SELECTION
Choose the HERO piece that fulfills the primary function
- This piece should be most visually prominent
- Sets the tone for everything else
- Ask: "If someone saw me for 3 seconds, what would they remember?"

STEP 3: SUPPORTING CAST
Choose 2-3 pieces that SUPPORT the anchor without competing
- At least one piece should create intentional contrast
- No piece should fight for attention with anchor
- Ask: "Does this piece make the anchor look better or worse?"

STEP 4: THE UNEXPECTED ELEMENT
What ONE element elevates this from "safe" to "memorable"?
- Wrong Shoe Theory: unexpected footwear that creates tension
- Era mixing: one piece from a different decade
- Texture surprise: unexpected material combination
- Ask: "What would make someone say 'I wouldn't have thought of that'?"

STEP 5: INTENTIONAL DETAILS
How will these pieces be worn?
- Sleeves rolled or down? Tucked or untucked?
- Buttoned or unbuttoned?
- These micro-decisions are what stylists charge for
```

### 4. Key Insight

**4-star prompts describe desired outputs.**
**5-star prompts guide the reasoning process that produces them.**

### 5. What This Means for the Sneaker Problem

The model already "knows" 5-star outfits. They exist in training data. The challenge is:

1. **Shift probability mass toward creative outputs** (prompting techniques)
2. **Make "unexpected" explicitly required** rather than optional (constraints)
3. **Reduce the "safe path" advantage** (forbid recent/common combinations)

When you add explicit reasoning steps like "What's the unexpected element?", you're forcing the model to explore the long tail of the distribution rather than defaulting to the mode.

**The white sneakers are the mode. We need to shift to the tail.**

