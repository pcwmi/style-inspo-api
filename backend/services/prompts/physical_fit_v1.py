"""Baseline + Physical Fit Check skill.

Extends baseline_v1 with a tactical layering feasibility check that forces
the model to reason about whether each layer physically fits over the one
beneath it, using the item's fit/cut/fabric metadata.
"""

from typing import List, Optional
from .baseline_v1 import BaselinePromptV1
from .base import PromptContext


PHYSICAL_FIT_SKILL = """
## PHYSICAL FIT CHECK (Apply BEFORE finalizing each outfit)

Imagine putting this outfit on, piece by piece, starting from the innermost layer.
For each layer transition, check: does the OUTER piece physically fit over the INNER piece?

**Use the fit/cut metadata to decide.** The rules:

1. **Fitted over fitted = usually fails.** A fitted cardigan cannot go over a fitted button-up
   without pulling or bunching. But a fitted cardigan CAN go over a slim tank or baby tee.

2. **Oversized under anything = fails.** You cannot put a blazer over an oversized chunky knit
   unless the blazer is explicitly oversized/relaxed itself. An oversized sweater under a
   structured jacket will bunch at the shoulders and sleeves.

3. **Fabric bulk matters.** A heavy knit sweater under a leather jacket only works if the jacket
   is cut generously. A thin merino sweater under the same jacket works fine.
   Check fabric weight: heavy fabrics need more room in the outer layer.

4. **Tucking changes the math.** A relaxed blouse tucked into high-waisted pants works.
   The same blouse left untucked under a fitted blazer creates bulk at the waist.
   If you suggest tucking, verify the top's fabric isn't too thick/stiff to tuck cleanly.

5. **Cut compatibility:**
   - Cropped top + high-waisted bottom = works (no overlap zone)
   - Boxy top + slim bottom = works (proportional contrast)
   - Boxy top + wide-leg bottom = risky (can look shapeless unless intentional)
   - Fitted top + fitted bottom = works only if lengths don't fight (e.g., top hits at waist, not mid-hip)

**Examples of physical failures to AVOID:**
- Tight cardigan styled as a layer over a loose/flowy blouse (cardigan can't contain the volume)
- Structured blazer over a chunky cable-knit sweater (shoulders won't fit)
- Tucking a heavy denim shirt into slim pants (too much bulk at waistband)
- Slim-cut bomber over a thick hoodie (arms won't move)

**Examples that DO work despite seeming tricky:**
- Oversized blazer over a fitted turtleneck (outer > inner volume)
- Cropped cardigan over a longer fitted tee (different coverage zones, no competition)
- Lightweight button-up under a snug leather jacket (thin fabric compresses fine)
- Relaxed linen shirt half-tucked into wide-leg pants (the half-tuck manages bulk)

For each outfit, mentally dress the person layer by layer. If any transition fails
the physical check, swap the problematic piece for one that works — or adjust
the styling (e.g., leave unbuttoned instead of closed, roll sleeves to reduce bulk).
"""


class PhysicalFitPromptV1(BaselinePromptV1):
    """Baseline prompt + physical fit check skill."""

    @property
    def version(self) -> str:
        return "physical_fit_v1"

    def build(self, context: PromptContext) -> str:
        """Build baseline prompt with physical fit skill injected before the task section."""
        # Get the full baseline prompt
        base_prompt = super().build(context)

        # Inject the physical fit skill right before "## YOUR TASK"
        return base_prompt.replace(
            "## YOUR TASK",
            PHYSICAL_FIT_SKILL + "\n## YOUR TASK",
        )
