'use client'

import Link from 'next/link'

interface WardrobeItem {
  id: string
  name: string
  category: string
  image_path?: string
  system_metadata?: { image_path?: string }
}

interface WardrobePreviewCarouselProps {
  items: WardrobeItem[]
  totalCount: number
  userId: string
}

export function WardrobePreviewCarousel({ items, totalCount, userId }: WardrobePreviewCarouselProps) {
  // Get image path for an item
  const getImagePath = (item: WardrobeItem) => {
    return item.system_metadata?.image_path || item.image_path
  }

  return (
    <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-5 md:mb-8 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg md:text-xl font-semibold">Your Wardrobe ({totalCount})</h2>
        <Link
          href={`/closet?user=${userId}`}
          className="text-terracotta text-sm md:text-base flex items-center font-medium hover:opacity-80 transition-opacity"
        >
          See all
          <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>

      {/* Horizontal Scroll Carousel */}
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 md:-mx-6 md:px-6 scrollbar-hide">
        {items.slice(0, 8).map((item) => {
          const imagePath = getImagePath(item)

          return (
            <Link
              key={item.id}
              href={`/closet?user=${userId}`}
              className="flex-shrink-0 w-20 md:w-24 bg-white border border-[rgba(26,22,20,0.08)] rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Image area - square for items */}
              <div className="aspect-square bg-sand relative">
                {imagePath ? (
                  <img
                    src={imagePath}
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-[10px] text-muted text-center p-1 line-clamp-2">
                      {item.name}
                    </span>
                  </div>
                )}
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
