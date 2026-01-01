'use client'

import Link from 'next/link'

export interface WardrobeItem {
  id: string
  styling_details?: {
    name?: string
    category?: string
  }
  system_metadata?: {
    image_path?: string
  }
  image_path?: string
}

interface WardrobeGridProps {
  items: WardrobeItem[]
  user: string
  // Selection mode props (for Complete page)
  selectionMode?: boolean
  selectedItems?: string[]
  onItemSelect?: (itemId: string) => void
}

export default function WardrobeGrid({
  items,
  user,
  selectionMode = false,
  selectedItems = [],
  onItemSelect
}: WardrobeGridProps) {
  return (
    <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {items.map((item) => {
        const isConsidering = item.id.startsWith('consider_')
        const imagePath = item.system_metadata?.image_path || item.image_path
        const isSelected = selectedItems.includes(item.id)

        const imageContent = (
          <>
            {/* Considering badge */}
            {isConsidering && (
              <div className="absolute top-2 right-2 bg-terracotta backdrop-blur-sm px-2 py-0.5 rounded-full z-10">
                <span className="text-xs font-medium text-white">Considering</span>
              </div>
            )}
            {/* Selection indicator */}
            {selectionMode && isSelected && (
              <div className="absolute top-2 left-2 w-6 h-6 bg-black rounded-full z-10 flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
            {(() => {
              if (!imagePath) {
                return (
                  <div className="w-full h-full flex items-center justify-center text-gray-300">
                    No Image
                  </div>
                )
              }
              return (
                <img
                  src={imagePath.startsWith('http')
                    ? imagePath
                    : `/api/images/${imagePath.split('/').pop()}`}
                  alt={item.styling_details?.name || 'Item'}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                />
              )
            })()}
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
              <span className="text-white text-xs font-medium truncate w-full">
                {item.styling_details?.name || 'Item'}
              </span>
            </div>
          </>
        )

        if (selectionMode && onItemSelect) {
          return (
            <button
              key={item.id}
              onClick={() => onItemSelect(item.id)}
              className={`group relative block aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden ${
                isSelected ? 'ring-2 ring-black ring-offset-2' : ''
              }`}
            >
              {imageContent}
            </button>
          )
        }

        return (
          <Link
            key={item.id}
            href={`/closet/${item.id}?user=${user}`}
            className="group relative block aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden"
          >
            {imageContent}
          </Link>
        )
      })}
    </div>
  )
}
