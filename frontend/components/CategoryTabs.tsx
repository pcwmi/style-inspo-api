'use client'

import { SubCategory } from '@/lib/categoryUtils'

interface CategoryTabsProps {
  categories: string[]
  activeCategory: string
  onCategoryChange: (category: string) => void
  getCategoryCount?: (category: string) => number
  // Sub-category filtering (optional - only shown when provided)
  subCategories?: SubCategory[]
  activeSubCategory?: string | null
  onSubCategoryChange?: (subCategory: string | null) => void
}

export default function CategoryTabs({
  categories,
  activeCategory,
  onCategoryChange,
  getCategoryCount,
  subCategories,
  activeSubCategory,
  onSubCategoryChange
}: CategoryTabsProps) {
  const showSubFilters = subCategories && subCategories.length > 0 && onSubCategoryChange

  return (
    <div className="space-y-2">
      {/* Main category tabs */}
      <div className="flex overflow-x-auto hide-scrollbar px-4 pb-2 gap-2">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => onCategoryChange(cat)}
            className={`flex-shrink-0 flex items-center whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeCategory === cat
                ? 'bg-black text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat}
            {getCategoryCount && (
              <span className="opacity-60 text-xs ml-2">{getCategoryCount(cat)}</span>
            )}
          </button>
        ))}
      </div>

      {/* Sub-category filter chips (only shown when category has >12 items) */}
      {showSubFilters && (
        <div className="flex overflow-x-auto hide-scrollbar px-4 pb-2 gap-2">
          {/* "All" option */}
          <button
            onClick={() => onSubCategoryChange(null)}
            className={`flex-shrink-0 whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              !activeSubCategory
                ? 'bg-gray-800 text-white'
                : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            All
          </button>
          {/* Sub-category chips */}
          {subCategories.map(subCat => (
            <button
              key={subCat.name}
              onClick={() => onSubCategoryChange(subCat.name)}
              className={`flex-shrink-0 flex items-center whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                activeSubCategory === subCat.name
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {subCat.name}
              <span className="opacity-60 ml-1.5">{subCat.count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
