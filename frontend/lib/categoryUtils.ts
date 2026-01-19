// Sub-category navigation utilities
// Always show sub-filters when they exist (no threshold)

// Inference keywords for sub-categories (case-insensitive matching)
// Order matters: more specific patterns should come before general ones
const SUB_CATEGORY_KEYWORDS: Record<string, Record<string, string[]>> = {
  Tops: {
    'Sweaters': ['sweater', 'cardigan', 'pullover', 'knit top', 'fleece'],
    'T-Shirts': ['tee', 't-shirt', 'graphic tee', 'basic tee'],
    'Blouses': ['blouse', 'silk top', 'satin top'],
    'Button-Ups': ['button-up', 'button down', 'oxford', 'dress shirt', 'chambray'],
    'Tanks & Camis': ['tank', 'cami', 'camisole', 'sleeveless'],
    'Hoodies & Sweatshirts': ['hoodie', 'sweatshirt', 'zip-up'],
    'Crop Tops': ['crop', 'cropped'],
    'Polos': ['polo', 'henley'],
  },
  Bottoms: {
    'Jeans': ['jeans', 'denim'],
    'Trousers': ['trouser', 'dress pants', 'slacks', 'chinos'],
    'Shorts': ['shorts', 'short'],
    'Skirts': ['skirt', 'mini skirt', 'midi skirt', 'maxi skirt'],
    'Leggings': ['leggings', 'joggers', 'sweatpants', 'track pants'],
  },
  Outerwear: {
    // Blazers must come BEFORE Jackets to avoid "blazer jacket" matching Jackets
    'Blazers': ['blazer'],
    'Jackets': ['jacket', 'bomber', 'denim jacket', 'leather jacket', 'biker jacket'],
    'Coats': ['coat', 'trench', 'overcoat', 'peacoat', 'parka'],
    'Cardigans': ['cardigan', 'shrug'],
    'Vests': ['vest', 'gilet'],
  },
  Dresses: {
    'Mini': ['mini dress', 'mini'],
    'Midi': ['midi dress', 'midi'],
    'Maxi': ['maxi dress', 'maxi', 'long dress'],
    'Casual': ['casual dress', 'day dress', 'sundress', 'shift dress'],
    'Formal': ['formal dress', 'cocktail', 'evening', 'gown'],
  },
  Shoes: {
    'Sneakers': ['sneaker', 'trainer', 'athletic'],
    'Boots': ['boot', 'ankle boot', 'chelsea', 'combat boot'],
    'Heels': ['heel', 'pump', 'stiletto', 'wedge'],
    'Flats': ['flat', 'ballet', 'loafer', 'oxford'],
    'Sandals': ['sandal', 'slide', 'flip flop', 'espadrille'],
  },
  Accessories: {
    'Bags': ['bag', 'purse', 'tote', 'clutch', 'crossbody', 'backpack'],
    'Jewelry': ['necklace', 'bracelet', 'earring', 'ring', 'jewelry'],
    'Scarves': ['scarf', 'wrap', 'shawl'],
    'Hats': ['hat', 'cap', 'beanie', 'beret'],
    'Belts': ['belt'],
    'Sunglasses': ['sunglasses', 'glasses'],
  },
}

// Exclusion patterns: if a pattern matches but text also contains an exclusion, skip it
// This prevents "sweatshirt cardigan" from being categorized as Hoodies & Sweatshirts
const EXCLUSION_PATTERNS: Record<string, string[]> = {
  'sweatshirt': ['cardigan', 'blazer', 'jacket', 'structured'],
}

export interface WardrobeItem {
  id: string
  styling_details?: {
    name?: string
    category?: string
    sub_category?: string
  }
}

export interface SubCategory {
  name: string
  count: number
}

/**
 * Check if a pattern should be excluded based on the full text
 */
function shouldExcludePattern(pattern: string, fullText: string): boolean {
  const exclusions = EXCLUSION_PATTERNS[pattern.toLowerCase()]
  if (!exclusions) return false

  const lowerText = fullText.toLowerCase()
  return exclusions.some(exclusion => lowerText.includes(exclusion))
}

/**
 * Try to match a string against our keywords to find the normalized sub-category name
 */
function normalizeToSubCategory(text: string, mainCategory: string): string | null {
  const keywords = SUB_CATEGORY_KEYWORDS[mainCategory]
  if (!keywords) return null

  const lowerText = text.toLowerCase()

  for (const [subCat, patterns] of Object.entries(keywords)) {
    for (const pattern of patterns) {
      if (lowerText.includes(pattern.toLowerCase())) {
        // Check if this pattern should be excluded based on the full text
        if (shouldExcludePattern(pattern, text)) {
          continue // Skip this pattern, try next one
        }
        return subCat
      }
    }
  }

  return null
}

/**
 * Get sub-category for an item (hybrid: normalize explicit field or infer from name)
 * Always returns normalized sub-category names for consistent display
 */
export function getItemSubCategory(item: WardrobeItem, mainCategory: string): string | null {
  const itemName = item.styling_details?.name || ''

  // First, try to normalize the explicit sub_category field if present
  if (item.styling_details?.sub_category) {
    const normalized = normalizeToSubCategory(item.styling_details.sub_category, mainCategory)
    if (normalized) return normalized
  }

  // Fall back to inference from item name
  return normalizeToSubCategory(itemName, mainCategory)
}

/**
 * Get sub-categories for a list of items in a category
 * Returns alphabetically sorted list with counts, excluding zero-count entries
 */
export function getSubCategories(items: WardrobeItem[], mainCategory: string): SubCategory[] {
  const subCatCounts = new Map<string, number>()

  for (const item of items) {
    const subCat = getItemSubCategory(item, mainCategory)
    if (subCat) {
      subCatCounts.set(subCat, (subCatCounts.get(subCat) || 0) + 1)
    }
  }

  // Convert to array and sort alphabetically for stable ordering
  return Array.from(subCatCounts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

/**
 * Filter items by sub-category
 */
export function filterBySubCategory(
  items: WardrobeItem[],
  mainCategory: string,
  subCategory: string | null
): WardrobeItem[] {
  // If no sub-category selected (null or 'All'), return all items
  if (!subCategory || subCategory === 'All') {
    return items
  }

  return items.filter(item => {
    const itemSubCat = getItemSubCategory(item, mainCategory)
    return itemSubCat === subCategory
  })
}
