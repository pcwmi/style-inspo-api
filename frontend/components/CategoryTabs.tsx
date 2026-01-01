'use client'

interface CategoryTabsProps {
  categories: string[]
  activeCategory: string
  onCategoryChange: (category: string) => void
  getCategoryCount?: (category: string) => number
}

export default function CategoryTabs({
  categories,
  activeCategory,
  onCategoryChange,
  getCategoryCount
}: CategoryTabsProps) {
  return (
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
  )
}
