'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense, useState, useEffect } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Tooltip } from '../../components/ui/Tooltip';

import { api } from '@/lib/api'

function SavedPageContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'

  const [outfits, setOutfits] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    async function fetchSavedOutfits() {
      try {
        setLoading(true)
        const result = await api.getSavedOutfits(user)
        setOutfits(result.outfits || [])
      } catch (err: any) {
        setError(err.message || 'Failed to load saved outfits')
      } finally {
        setLoading(false)
      }
    }
    fetchSavedOutfits()
  }, [user])

  if (loading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading saved outfits...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bone page-container">
        <div className="max-w-2xl mx-auto px-4 py-6 md:py-8">
          <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
            ← Back
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 md:p-6">
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
          ← Back
        </Link>

        <h1 className="text-2xl md:text-3xl font-bold mb-2">Saved Outfits</h1>
        <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
          {outfits.length === 0
            ? "You haven't saved any outfits yet. Save outfits you love from the reveal page!"
            : `${outfits.length} saved outfit${outfits.length === 1 ? '' : 's'}`}
        </p>

        {outfits.length === 0 ? (
          <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 md:p-8 text-center shadow-sm">
            <p className="text-muted text-sm md:text-base leading-relaxed">No saved outfits yet</p>
          </div>
        ) : (
          <div className="space-y-4 md:space-y-6">
            {outfits.map((saved: any) => {
              const outfit = saved.outfit_data || saved
              return (
                <div key={saved.id} className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 shadow-sm">
                  {/* Outfit images */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    {outfit.items?.map((item: any, idx: number) => {
                      const imagePath = item.image_path || item.system_metadata?.image_path
                      const itemName = item.name || `Item ${idx + 1}`
                      const isConsidering = item.id?.startsWith('consider_')
                      return (
                        <div key={idx} className="relative aspect-square rounded overflow-hidden bg-gray-100">
                          {/* Considering badge */}
                          {isConsidering && (
                            <div className="absolute top-2 right-2 bg-terracotta backdrop-blur-sm px-2 py-0.5 rounded-full z-10">
                              <span className="text-xs font-medium text-white">Considering</span>
                            </div>
                          )}
                          {imagePath ? (
                            imagePath.startsWith('http') ? (
                              <img
                                src={imagePath}
                                alt={itemName}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  // If image fails to load, show placeholder with item name
                                  const target = e.currentTarget
                                  target.style.display = 'none'
                                  const parent = target.parentElement
                                  if (parent) {
                                    const placeholder = document.createElement('div')
                                    placeholder.className = 'w-full h-full flex flex-col items-center justify-center text-muted text-xs bg-sand p-2'
                                    placeholder.innerHTML = `<div class="text-center">${itemName}</div>`
                                    parent.appendChild(placeholder)
                                  }
                                }}
                              />
                            ) : (
                              <Image
                                src={`/${imagePath}`}
                                alt={itemName}
                                fill
                                className="object-cover"
                                onError={() => {
                                  // Next.js Image component handles errors internally
                                  // But we can add a fallback if needed
                                }}
                              />
                            )
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-muted text-xs bg-sand p-2">
                              <div className="text-center">{itemName}</div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  {/* Styling notes */}
                  {outfit.styling_notes && (
                    <div className="mb-3 md:mb-4">
                      <h3 className="font-semibold mb-2 text-base">How to Style</h3>
                      <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.styling_notes}</p>
                    </div>
                  )}

                  {/* Why it works */}
                  {outfit.why_it_works && (
                    <div className="mb-3 md:mb-4">
                      <h3 className="font-semibold mb-2 text-base">Why This Works</h3>
                      <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.why_it_works}</p>
                    </div>
                  )}

                  {/* User reason if provided */}
                  {saved.user_reason && (
                    <div className="mb-3 md:mb-4">
                      <h3 className="font-semibold mb-2 text-base">Your Note</h3>
                      <p className="text-muted text-sm md:text-base italic">"{saved.user_reason}"</p>
                    </div>
                  )}

                  {/* Context (Occasion, Weather) */}
                  {saved.context && (
                    <div className="mb-3 md:mb-4 flex flex-wrap gap-2">
                      {saved.context.occasions && saved.context.occasions.length > 0 && (
                        <Tooltip content={saved.context.occasions.join(", ")}>
                          <span
                            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sand text-ink max-w-[200px] truncate cursor-help"
                          >
                            {saved.context.occasions.join(", ")}
                          </span>
                        </Tooltip>
                      )}
                      {saved.context.weather_condition && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
                          {saved.context.weather_condition}
                        </span>
                      )}
                      {saved.context.temperature_range && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-100">
                          {saved.context.temperature_range}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Saved date */}
                  {saved.saved_at && (
                    <p className="text-xs text-muted">
                      Saved {new Date(saved.saved_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function SavedPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-bone flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta"></div>
      </div>
    }>
      <SavedPageContent />
    </Suspense>
  )
}
