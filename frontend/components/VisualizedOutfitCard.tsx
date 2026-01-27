'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { api } from '@/lib/api'
import { posthog } from '@/lib/posthog'
import { ShareImageGenerator } from './ShareImageGenerator'

interface OutfitItem {
  id?: string
  name: string
  category: string
  image_path?: string
  system_metadata?: { image_path?: string }
}

interface OutfitData {
  items: OutfitItem[]
  styling_notes: string
  why_it_works: string
  confidence_level?: string
  vibe_keywords?: string[]
  context?: any
}

interface VisualizedOutfitCardProps {
  outfit: OutfitData
  outfitId?: string
  outfitName?: string
  visualizationUrl?: string
  wornAt?: string | null  // When the outfit was worn
  wornPhotoUrl?: string | null  // User's photo wearing the outfit
  user: string
  showVisualizeButton?: boolean
  showMarkAsWornButton?: boolean  // Show the mark as worn button
  hasDescriptor?: boolean  // If false, onVisualize() is called but API call is skipped (parent shows modal)
  onVisualize?: () => void
  onVisualizationComplete?: (url: string) => void
  onMarkAsWorn?: () => void  // Called when user clicks mark as worn
  onUploadPhoto?: () => void  // Called when user wants to upload a photo for worn outfit
  onWornComplete?: (wornAt: string, photoUrl?: string) => void  // Called after marking worn
}

type VisualizationState = 'not_visualized' | 'generating' | 'visualized'

export function VisualizedOutfitCard({
  outfit,
  outfitId,
  outfitName,
  visualizationUrl: initialVisualizationUrl,
  wornAt: initialWornAt,
  wornPhotoUrl: initialWornPhotoUrl,
  user,
  showVisualizeButton = true,
  showMarkAsWornButton = false,
  hasDescriptor = true,  // Default true so standalone usage works
  onVisualize,
  onVisualizationComplete,
  onMarkAsWorn,
  onUploadPhoto,
  onWornComplete
}: VisualizedOutfitCardProps) {
  const [visualizationUrl, setVisualizationUrl] = useState(initialVisualizationUrl)
  const [wornAt, setWornAt] = useState(initialWornAt)
  const [wornPhotoUrl, setWornPhotoUrl] = useState(initialWornPhotoUrl)
  const [vizState, setVizState] = useState<VisualizationState>(
    initialVisualizationUrl ? 'visualized' : 'not_visualized'
  )
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [imageExpanded, setImageExpanded] = useState(false)

  // Handle mark as worn
  const handleMarkAsWorn = () => {
    if (onMarkAsWorn) onMarkAsWorn()
  }

  // Called from parent when worn tracking is complete
  const handleWornComplete = (newWornAt: string, photoUrl?: string) => {
    setWornAt(newWornAt)
    if (photoUrl) setWornPhotoUrl(photoUrl)
    if (onWornComplete) onWornComplete(newWornAt, photoUrl)
  }

  // Format worn date
  const formatWornDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  // Handle visualization generation
  const handleVisualize = async () => {
    if (!outfitId) {
      setError('Cannot visualize: outfit not saved yet')
      return
    }

    // If no descriptor, notify parent to show modal and don't proceed with API call
    if (!hasDescriptor) {
      if (onVisualize) onVisualize()
      return
    }

    setVizState('generating')
    setProgress(0)
    setStatusMessage('Starting visualization...')
    setError(null)

    if (onVisualize) onVisualize()

    try {
      // Start visualization job
      const response = await api.generateVisualization({
        user_id: user,
        outfit_id: outfitId
      })

      // If cached, we get immediate result
      if (response.status === 'complete' && response.visualization_url) {
        setVisualizationUrl(response.visualization_url)
        setVizState('visualized')
        if (onVisualizationComplete) onVisualizationComplete(response.visualization_url)
        posthog.capture('visualization_complete', { outfit_id: outfitId, cached: true })
        return
      }

      // Poll for completion
      const jobId = response.job_id
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.getJobStatus(jobId)

          setProgress(status.progress || 0)
          if (status.result?.status_message) {
            setStatusMessage(status.result.status_message)
          }

          if (status.status === 'complete' && status.result?.image_url) {
            clearInterval(pollInterval)
            setVisualizationUrl(status.result.image_url)
            setVizState('visualized')
            if (onVisualizationComplete) onVisualizationComplete(status.result.image_url)
            posthog.capture('visualization_complete', { outfit_id: outfitId, cached: false })
          } else if (status.status === 'failed') {
            clearInterval(pollInterval)
            setError(status.error || 'Visualization failed')
            setVizState('not_visualized')
            posthog.capture('visualization_failed', { outfit_id: outfitId, error: status.error })
          }
        } catch (e) {
          console.error('Error polling job:', e)
        }
      }, 2000)

      // Cleanup on unmount
      return () => clearInterval(pollInterval)
    } catch (e: any) {
      setError(e.message || 'Failed to start visualization')
      setVizState('not_visualized')
      posthog.capture('visualization_error', { outfit_id: outfitId, error: e.message })
    }
  }

  // Get image path for an item
  const getImagePath = (item: OutfitItem) => {
    return item.system_metadata?.image_path || item.image_path
  }

  return (
    <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-4 md:mb-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <h2 className="text-lg md:text-xl font-semibold">{outfitName || 'Outfit'}</h2>
        <div className="flex items-center gap-2">
          {wornAt && (
            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Worn
            </span>
          )}
          {visualizationUrl && !wornAt && (
            <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
              Visualized
            </span>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {vizState === 'visualized' && visualizationUrl ? (
        // Visualized state: Show visualization (or side-by-side if worn photo exists)
        <div className="mb-4">
          {wornPhotoUrl ? (
            // Side-by-side view: AI viz + worn photo
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <p className="text-xs text-muted text-center">The Plan</p>
                <div
                  className="aspect-[4/5] rounded-lg overflow-hidden cursor-pointer relative bg-gradient-to-b from-purple-50 to-pink-50"
                  onClick={() => setImageExpanded(true)}
                >
                  <img
                    src={visualizationUrl}
                    alt="AI visualization"
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted text-center">The Reality</p>
                <div className="aspect-[4/5] rounded-lg overflow-hidden relative bg-gray-100">
                  <img
                    src={wornPhotoUrl}
                    alt="How it looked"
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
            </div>
          ) : (
            // Just the visualization
            <div
              className="aspect-[4/5] rounded-lg overflow-hidden cursor-pointer relative bg-gradient-to-b from-purple-50 to-pink-50"
              onClick={() => setImageExpanded(true)}
            >
              <img
                src={visualizationUrl}
                alt="Outfit visualization"
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-2 right-2 bg-white/80 px-2 py-1 rounded-full text-xs">
                Tap to expand
              </div>
            </div>
          )}
          {wornAt && (
            <p className="text-xs text-muted mt-2 text-center">
              Worn on {formatWornDate(wornAt)}
            </p>
          )}
          {/* Upload Photo button for worn outfits without a photo */}
          {wornAt && !wornPhotoUrl && onUploadPhoto && (
            <button
              onClick={onUploadPhoto}
              className="w-full mt-3 bg-white border-2 border-ink text-ink py-2 px-4 rounded-lg hover:bg-sand transition active:bg-sand/80 min-h-[44px] flex items-center justify-center gap-2 text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Add a photo
            </button>
          )}
        </div>
      ) : wornAt && wornPhotoUrl && !visualizationUrl ? (
        // Worn with photo but no visualization: Show ensemble + worn photo side-by-side
        <div className="mb-4">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <p className="text-xs text-muted text-center">The Outfit</p>
              <div className="aspect-[4/5] rounded-lg overflow-hidden bg-gray-50 p-1">
                <div className="w-full h-full grid grid-cols-2 gap-1">
                  {outfit.items.slice(0, 4).map((item, idx) => {
                    const itemImage = getImagePath(item)
                    return (
                      <div key={idx} className="bg-sand rounded overflow-hidden flex items-center justify-center">
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
                          <span className="text-[8px] text-muted text-center p-1">
                            {item.name}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted text-center">The Reality</p>
              <div className="aspect-[4/5] rounded-lg overflow-hidden relative bg-gray-100">
                <img
                  src={wornPhotoUrl}
                  alt="How it looked"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
          <p className="text-xs text-muted mt-2 text-center">
            Worn on {formatWornDate(wornAt)}
          </p>
        </div>
      ) : vizState === 'generating' ? (
        // Generating state: Show progress
        <div className="mb-4">
          <p className="font-bold text-ink text-center mb-4">Generating visualization...</p>
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div
              className="bg-terracotta h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="space-y-2 text-sm mb-6">
            <div className="flex items-center gap-2">
              {progress >= 20 ? (
                <span className="text-green-500">&#10003;</span>
              ) : (
                <span className="text-terracotta animate-spin">&#8635;</span>
              )}
              <span className={progress >= 20 ? 'text-gray-400' : 'text-ink font-medium'}>
                Loading outfit data
              </span>
            </div>
            <div className="flex items-center gap-2">
              {progress >= 90 ? (
                <span className="text-green-500">&#10003;</span>
              ) : progress >= 30 ? (
                <span className="text-terracotta animate-spin">&#8635;</span>
              ) : (
                <span className="text-gray-300">&#9675;</span>
              )}
              <span className={progress >= 30 && progress < 90 ? 'text-ink font-medium' : 'text-gray-400'}>
                Creating visualization with AI
              </span>
            </div>
            <div className="flex items-center gap-2">
              {progress >= 100 ? (
                <span className="text-green-500">&#10003;</span>
              ) : (
                <span className="text-gray-300">&#9675;</span>
              )}
              <span className={progress >= 90 && progress < 100 ? 'text-ink font-medium' : 'text-gray-400'}>
                Finalizing image
              </span>
            </div>
          </div>
          <p className="text-xs text-center text-gray-400">
            This takes about 30-40 seconds. You can browse other outfits while waiting.
          </p>
        </div>
      ) : (
        // Not visualized state: Show collage + visualize button
        <div>
          <div className="grid grid-cols-3 gap-2 mb-4">
            {outfit.items.slice(0, 6).map((item, idx) => {
              const imagePath = getImagePath(item)
              const isSynthetic = !imagePath && item.category === "unknown"
              return (
                <div key={idx} className={`aspect-square rounded-lg overflow-hidden ${
                  isSynthetic
                    ? 'bg-gradient-to-br from-sand to-bone border-2 border-dashed border-terracotta/30'
                    : 'bg-gray-100'
                }`}>
                  {isSynthetic ? (
                    <div className="relative w-full h-full">
                      {/* "Suggested" badge */}
                      <div className="absolute top-1.5 left-1.5 right-1.5 bg-white/90 backdrop-blur-sm px-1.5 py-0.5 rounded-md shadow-sm">
                        <div className="flex items-center gap-1 justify-center">
                          <svg className="w-2.5 h-2.5 text-terracotta" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 0L14.59 8.41L23 11L14.59 13.59L12 22L9.41 13.59L1 11L9.41 8.41L12 0Z"/>
                          </svg>
                          <span className="text-[8px] font-medium text-terracotta uppercase tracking-wide">
                            Suggested
                          </span>
                        </div>
                      </div>
                      {/* Item name */}
                      <div className="absolute inset-0 flex items-center justify-center p-2 pt-8">
                        <p className="text-center text-xs font-medium text-ink leading-tight">
                          {item.name}
                        </p>
                      </div>
                    </div>
                  ) : imagePath ? (
                    imagePath.startsWith('http') ? (
                      <img
                        src={imagePath}
                        alt={item.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Image
                        src={imagePath.startsWith('/') ? imagePath : `/${imagePath}`}
                        alt={item.name}
                        fill
                        className="object-cover"
                      />
                    )
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-gray-400 p-2 text-center">
                      {item.name}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Worn date display */}
          {wornAt && (
            <p className="text-xs text-muted mb-3 text-center">
              Worn on {formatWornDate(wornAt)}
            </p>
          )}

          {/* Action buttons */}
          <div className="space-y-2 mb-4">
            {/* Visualize button */}
            {showVisualizeButton && outfitId && (
              <button
                onClick={handleVisualize}
                className="w-full bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
              >
                See it on a model
              </button>
            )}

            {/* Mark as Worn button */}
            {showMarkAsWornButton && outfitId && !wornAt && (
              <button
                onClick={handleMarkAsWorn}
                className="w-full bg-white border-2 border-ink text-ink py-3 px-6 rounded-lg hover:bg-sand transition active:bg-sand/80 min-h-[48px] flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Mark as Worn
              </button>
            )}

            {/* Upload Photo button for worn outfits without a photo */}
            {wornAt && !wornPhotoUrl && onUploadPhoto && (
              <button
                onClick={onUploadPhoto}
                className="w-full bg-white border-2 border-ink text-ink py-2 px-4 rounded-lg hover:bg-sand transition active:bg-sand/80 min-h-[44px] flex items-center justify-center gap-2 text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Add a photo
              </button>
            )}
          </div>

          {/* Error message */}
          {error && (
            <p className="mt-2 text-sm text-red-500 text-center">{error}</p>
          )}
        </div>
      )}

      {/* Items Row (horizontal scroll) - shown when visualized */}
      {vizState === 'visualized' && (
        <div className="mb-3 md:mb-4">
          <p className="text-xs text-muted mb-1">Items in this outfit:</p>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {outfit.items.map((item, idx) => {
              const imagePath = getImagePath(item)
              const isSynthetic = !imagePath && item.category === "unknown"
              return (
                <div
                  key={idx}
                  className={`w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden ${
                    isSynthetic
                      ? 'bg-gradient-to-br from-sand to-bone border-2 border-dashed border-terracotta/30'
                      : 'bg-gray-100'
                  }`}
                >
                  {isSynthetic ? (
                    <div className="relative w-full h-full">
                      {/* Sparkle icon at top */}
                      <div className="absolute top-1 left-0 right-0 flex justify-center">
                        <svg className="w-2.5 h-2.5 text-terracotta" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0L14.59 8.41L23 11L14.59 13.59L12 22L9.41 13.59L1 11L9.41 8.41L12 0Z"/>
                        </svg>
                      </div>
                      {/* Item name */}
                      <div className="absolute inset-0 flex items-center justify-center p-1 pt-4">
                        <p className="text-center text-[7px] font-medium text-ink leading-tight line-clamp-2">
                          {item.name}
                        </p>
                      </div>
                    </div>
                  ) : imagePath ? (
                    imagePath.startsWith('http') ? (
                      <img
                        src={imagePath}
                        alt={item.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="relative w-full h-full">
                        <Image
                          src={imagePath.startsWith('/') ? imagePath : `/${imagePath}`}
                          alt={item.name}
                          fill
                          className="object-cover"
                        />
                      </div>
                    )
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[8px] text-gray-400 p-1 text-center">
                      {item.name}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Mark as Worn button - shown when visualized but not worn */}
      {vizState === 'visualized' && showMarkAsWornButton && outfitId && !wornAt && (
        <button
          onClick={handleMarkAsWorn}
          className="w-full bg-white border-2 border-ink text-ink py-3 px-6 rounded-lg hover:bg-sand transition active:bg-sand/80 min-h-[48px] flex items-center justify-center gap-2 mb-4"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Mark as Worn
        </button>
      )}

      {/* Styling Notes - matches original OutfitCard */}
      <div className="mb-3 md:mb-4">
        <h3 className="font-semibold mb-2 text-base">How to Style</h3>
        <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.styling_notes}</p>
      </div>
      <div className="mb-3 md:mb-4">
        <h3 className="font-semibold mb-2 text-base">Why This Works</h3>
        <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.why_it_works}</p>
      </div>

      {/* Share button - only shown when both visualization and worn photo exist */}
      {visualizationUrl && wornPhotoUrl && (
        <div className="mb-3 md:mb-4">
          <ShareImageGenerator
            visualizationUrl={visualizationUrl}
            wornPhotoUrl={wornPhotoUrl}
            outfitName={outfitName}
          />
        </div>
      )}

      {/* Fullscreen Modal */}
      {imageExpanded && visualizationUrl && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setImageExpanded(false)}
        >
          <img
            src={visualizationUrl}
            alt="Outfit visualization"
            className="max-w-full max-h-full object-contain"
          />
          <button
            className="absolute top-4 right-4 text-white text-2xl"
            onClick={() => setImageExpanded(false)}
          >
            &times;
          </button>
        </div>
      )}
    </div>
  )
}
