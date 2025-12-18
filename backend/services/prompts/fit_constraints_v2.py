"""Fit Constraints Prompt V2: Baseline + Garment Fit Rules"""

from .baseline_v1 import BaselinePromptV1
from .base import PromptContext


class FitConstraintsPromptV2(BaselinePromptV1):
    """Baseline Style Constitution + Garment Fit Constraints

    Addresses 30% of eval failures (8 out of 16 low ratings) caused by
    impossible layering suggestions like "layer cardigan over oversized top"
    """

    @property
    def version(self) -> str:
        return "fit_constraints_v2"

    def build(self, context: PromptContext) -> str:
        """Build baseline prompt + add fit constraints section"""

        # Get baseline prompt
        baseline_prompt = super().build(context)

        # Add fit constraints section BEFORE "YOUR TASK" section
        fit_constraints = self._get_fit_constraints_section()

        # Insert fit constraints after "STYLE CONSTITUTION" section
        parts = baseline_prompt.split("## YOUR TASK")
        if len(parts) == 2:
            return parts[0] + fit_constraints + "\n\n## YOUR TASK" + parts[1]
        else:
            # Fallback: append at end
            return baseline_prompt + "\n\n" + fit_constraints

    def _get_fit_constraints_section(self) -> str:
        """Return garment fit constraints from eval analysis"""
        return """
## GARMENT FIT CONSTRAINTS (CRITICAL)

Before suggesting layering, verify physical fit compatibility. **Impossible layering is a common error** - avoid it by checking these rules:

### 1. LAYERING RULES (Physical Fit)

**Rule: Each layer must be looser than the previous layer**
- Order: tight → medium → loose (each layer progressively looser)
- ✅ VALID: Fitted tee → regular cardigan → oversized coat
- ❌ INVALID: Oversized top → fitted cardigan (sleeves won't fit)
- ❌ INVALID: Loose blouse → tight blazer (bunches up awkwardly)

**Rule: Fitted garments CANNOT go over loose/oversized garments**
- Sleeves won't fit through sleeves
- Fabric bunches up and looks messy
- ❌ INVALID: "Layer fitted cardigan over oversized top"
- ❌ INVALID: "Tuck oversized shirt into fitted blazer"

**Rule: Oversized garments CAN go over fitted garments**
- ✅ VALID: Fitted turtleneck under oversized blazer
- ✅ VALID: Tank top under loose cardigan

### 2. ITEM-SPECIFIC CONSTRAINTS

**Pants/Jeans:**
- Flare jeans: CANNOT be cuffed (only skinny/straight cut can cuff)
- Wide-leg pants: CANNOT be tucked into boots
- ❌ INVALID: "Cuff your flare jeans"
- ✅ VALID: "Cuff your straight-leg jeans"

**Belts:**
- Wide belts with belt loops: Check belt loop compatibility
- ❌ INVALID: "2-inch belt through 1-inch belt loops"
- ✅ VALID: Dresses are flexible - can layer belts at waistline even without loops

**Tucking:**
- Both fitted and oversized garments can be tucked
- ✅ VALID: "Partial front tuck of fitted tee"
- ✅ VALID: "Half tuck of oversized sweater" (around belly button, not full tuck)

**Layered Visibility:**
- Don't suggest items that won't be visible
- ❌ INVALID: "Wear tank under sweater" (if tank has no visible collar/hem)
- ✅ VALID: "Wear collared shirt under sweater with collar peeking out"

### 3. VALIDATION CHECKLIST

Before including any layered combination, verify:
1. **Can person physically put this on?** (Will sleeves fit through sleeves?)
2. **Is each layer looser than the previous?** (Fitted → loose progression?)
3. **Will all items be visible or purposefully hidden?** (Why include if hidden?)
4. **Do garment types support the styling?** (Can these jeans be cuffed? Does this top have belt loops?)

**If uncertain about fit, choose simpler unlayered option.**

### 4. COMMON FAILURE PATTERNS TO AVOID

Based on analysis of styling errors:
- ❌ "Layer cardigan over oversized top" → Sleeves won't fit
- ❌ "Layer fitted blazer over loose blouse" → Blouse bunches up
- ❌ "Cuff the flare jeans" → Only straight/skinny can cuff
- ❌ "Tank under sweater" → Won't be visible, why include?

**Remember:** Physical fit constraints are non-negotiable. Style DNA and Constitution principles come AFTER ensuring the outfit can physically be worn.
"""
