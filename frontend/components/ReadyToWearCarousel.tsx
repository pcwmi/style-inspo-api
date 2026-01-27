'use client'

import Link from 'next/link'
import Image from 'next/image'

interface OutfitItem {
  id?: string
  name: string
  category: string
  image_path?: string
  system_metadata?: { image_path?: string }
}

interface SavedOutfit {
  id: string
  outfit_data: {
    items: OutfitItem[]
    vibe_keywords?: string[]
    styling_notes?: string
  }
  visualization_url?: string
  saved_at: string
}

interface ReadyToWearCarouselProps {
  outfits: SavedOutfit[]
  userId: string
}

export function ReadyToWearCarousel({ outfits, userId }: ReadyToWearCarouselProps) {
  if (outfits.length === 0) return null

  // Get image path for an item
  const getImagePath = (item: OutfitItem) => {
    return item.system_metadata?.image_path || item.image_path
  }

  // Get visualization URL only - ensemble grid will be shown as fallback
  const getVisualizationUrl = (outfit: SavedOutfit) => {
    return outfit.visualization_url || null
  }

  return (
    <div className="mb-5 md:mb-8">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg md:text-xl font-semibold">Ready to Wear</h2>
        <Link
          href={`/saved?user=${userId}`}
          className="text-terracotta text-sm md:text-base flex items-center font-medium hover:opacity-80 transition-opacity"
        >
          See all
          <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>
      <p className="text-muted text-sm mb-3">Outfits waiting for you to try</p>

      {/* Horizontal Scroll Carousel */}
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {outfits.slice(0, 5).map((outfit) => {
          const visualizationUrl = getVisualizationUrl(outfit)

          return (
            <Link
              key={outfit.id}
              href={`/saved?user=${userId}`}
              className="flex-shrink-0 w-36 md:w-44 bg-white border border-[rgba(26,22,20,0.12)] rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Image area */}
              <div className="aspect-square bg-gray-100 relative">
                {visualizationUrl ? (
                  <img
                    src={visualizationUrl}
                    alt="Outfit visualization"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  // Grid of item thumbnails (ensemble view)
                  <div className="w-full h-full grid grid-cols-2 gap-0.5 p-0.5">
                    {outfit.outfit_data.items.slice(0, 4).map((item, idx) => {
                      const itemImage = getImagePath(item)
                      return (
                        <div key={idx} className="bg-sand flex items-center justify-center overflow-hidden">
                          {itemImage ? (
                            itemImage.startsWith('http') ? (
                              <img
                                src={itemImage}
                                alt={item.name}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="relative w-full h-full">
                                <Image
                                  src={itemImage.startsWith('/') ? itemImage : `/${itemImage}`}
                                  alt={item.name}
                                  fill
                                  className="object-cover"
                                />
                              </div>
                            )
                          ) : (
                            <span className="text-[8px] text-muted text-center p-1 line-clamp-2">
                              {item.name}
                            </span>
                          )}
                        </div>
                      )
                    })}
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
