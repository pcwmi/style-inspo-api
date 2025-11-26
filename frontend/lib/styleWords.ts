/**
 * Style word chips for onboarding three words selection
 * Matches Streamlit new_onboarding.py chip lists
 */

export const STYLE_WORD_CHIPS: string[] = [
  // Classics
  "classic", "minimal", "elegant", "polished",
  // Mood & Energy
  "romantic", "edgy", "bold", "soft", "relaxed",
  // Aesthetic
  "vintage", "modern", "feminine", "androgynous", "casual",
  // Vibe
  "effortless", "structured", "playful", "sophisticated", "artistic",
  // Aspirational
  "daring", "refined", "eclectic", "chic",
  // Additions
  "sporty", "preppy", "outdoorsy", "comfortable",
]

export const STYLE_FEELING_CHIPS: string[] = [
  "confident", "playful", "comfortable", "sleek", "bold", "chic", "sharp"
]

/**
 * Get a random subset of chips
 */
export function getRandomChips(chips: string[], count: number): string[] {
  const shuffled = [...chips].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}



