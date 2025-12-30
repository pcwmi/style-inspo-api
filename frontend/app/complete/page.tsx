'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { posthog } from '@/lib/posthog'
import Link from 'next/link'
import Image from 'next/image'

function CompletePageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const debugMode = searchParams.get('debug') === 'true'
  
  const [wardrobe, setWardrobe] = useState<any>(null)
  const [consideringItems, setConsideringItems] = useState<any>(null)
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [generating, setGenerating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchItems() {
      try {
        const [wardrobeData, consideringData] = await Promise.all([
          api.getWardrobe(user),
          api.getConsiderBuyingItems(user, 'considering')
        ])
        setWardrobe(wardrobeData)
        setConsideringItems(consideringData)
      } catch (error) {
        console.error('Error fetching items:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchItems()
  }, [user])

  const handleGenerate = async () => {
    if (selectedItems.length === 0) {
      alert('Please select at least one item to start with')
      return
    }
    
    setGenerating(true)
    try {
      // Track outfit generation with anchor items
      const selectedItemNames = allItems
        .filter((item: any) => selectedItems.includes(item.id))
        .map((item: any) => item.styling_details?.name || item.id)

      posthog.capture('outfit_generated', {
        mode: 'complete',
        anchor_item_ids: selectedItems,
        anchor_item_names: selectedItemNames,
        anchor_count: selectedItems.length
      })

      // Redirect with streaming params
      const params = new URLSearchParams({
        user: user,
        mode: 'complete',
        anchor_items: selectedItems.join(','),
        stream: 'true'
      })
      if (debugMode) params.append('debug', 'true')
      router.push(`/reveal?${params.toString()}`)
    } catch (error) {
      console.error('Error generating outfits:', error)
      alert('Failed to generate outfits. Please try again.')
      setGenerating(false)
    }
  }

  const toggleItem = (itemId: string) => {
    if (selectedItems.includes(itemId)) {
      setSelectedItems(selectedItems.filter(id => id !== itemId))
    } else {
      setSelectedItems([...selectedItems, itemId])
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading your wardrobe...</p>
        </div>
      </div>
    )
  }

  // Merge wardrobe and considering items for display
  const allItems = [
    ...(wardrobe?.items || []),
    ...(consideringItems?.items || [])
  ]

  if (allItems.length === 0) {
    return (
      <div className="min-h-screen bg-bone page-container">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
            ← Back
          </Link>
          <p className="text-muted">No wardrobe items found. Please upload some items first.</p>
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

        {/* Debug mode indicator */}
        {debugMode && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              🐛 Debug Mode Active - Showing AI reasoning
            </p>
          </div>
        )}
        
        <h1 className="text-2xl md:text-3xl font-bold mb-2">
          Start with a piece you want to wear
        </h1>
        <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
          Select 1-2 items you want to wear today, and we'll complete the outfit
        </p>

        {/* Item selection grid */}
        <div className="grid grid-cols-2 gap-3 md:gap-4 mb-5 md:mb-6">
          {allItems.map((item: any) => {
            const isSelected = selectedItems.includes(item.id)
            const imagePath = item.system_metadata?.image_path || item.image_path
            const isConsidering = item.id.startsWith('consider_')

            return (
              <button
                key={item.id}
                onClick={() => toggleItem(item.id)}
                className={`border-2 rounded-lg p-2.5 md:p-3 text-left transition min-h-[44px] ${
                  isSelected
                    ? 'border-terracotta bg-terracotta text-white'
                    : 'border-[rgba(26,22,20,0.12)] bg-white hover:border-terracotta/50'
                }`}
              >
            {imagePath && (
              <div className="relative w-full aspect-square mb-2 rounded overflow-hidden bg-sand">
                {/* Considering badge */}
                {isConsidering && (
                  <div className="absolute top-2 right-2 bg-terracotta backdrop-blur-sm px-2 py-0.5 rounded-full z-10">
                    <span className="text-xs font-medium text-white">Considering</span>
                  </div>
                )}
                {imagePath.startsWith('http') ? (
                  <img
                    src={imagePath}
                    alt={item.styling_details?.name || 'Item'}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Image
                    src={`/${imagePath}`}
                    alt={item.styling_details?.name || 'Item'}
                    fill
                    className="object-cover"
                  />
                )}
              </div>
            )}
                <p className="text-sm font-medium truncate leading-tight">
                  {item.styling_details?.name || 'Unnamed Item'}
                </p>
              </button>
            )
          })}
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={selectedItems.length === 0 || generating}
          className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center button-container"
        >
          {generating ? 'Creating Outfits...' : `Complete My Look (${selectedItems.length} selected)`}
        </button>
      </div>
    </div>
  )
}

export default function CompletePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <CompletePageContent />
    </Suspense>
  )
}

