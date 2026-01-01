'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useMemo } from 'react'
import { useState } from 'react'
import { useWardrobe, useConsiderBuying } from '@/lib/queries'
import { posthog } from '@/lib/posthog'
import Link from 'next/link'
import CategoryTabs from '@/components/CategoryTabs'
import WardrobeGrid from '@/components/WardrobeGrid'

function CompletePageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const debugMode = searchParams.get('debug') === 'true'

  // React Query hooks - automatic caching (shares cache with closet/dashboard)
  const { data: wardrobeData, isLoading: wardrobeLoading } = useWardrobe(user)
  const { data: consideringData, isLoading: consideringLoading } = useConsiderBuying(user, 'considering')

  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [generating, setGenerating] = useState(false)
  const [activeCategory, setActiveCategory] = useState('All')

  // Category tabs (matching closet page)
  const categories = ['All', 'Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Shoes', 'Accessories', 'Bags', 'Considering']

  // Merge wardrobe and considering items
  const allItems = useMemo(() => [
    ...(wardrobeData?.items || []),
    ...(consideringData?.items || [])
  ], [wardrobeData, consideringData])

  // Filter items by category
  const filteredItems = useMemo(() => {
    if (activeCategory === 'All') return allItems
    if (activeCategory === 'Considering') {
      return allItems.filter(item => item.id?.startsWith('consider_'))
    }
    // For regular categories, exclude considering items and filter by category
    return allItems.filter(item =>
      !item.id?.startsWith('consider_') &&
      item.styling_details?.category?.toLowerCase() === activeCategory.toLowerCase()
    )
  }, [allItems, activeCategory])

  // Only show loading on first load (no cached data)
  const loading = (wardrobeLoading && !wardrobeData) || (consideringLoading && !consideringData)

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
        <p className="text-muted mb-4 text-base leading-relaxed">
          Select 1-2 items you want to wear today, and we'll complete the outfit
        </p>

        {/* Category tabs */}
        <CategoryTabs
          categories={categories}
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />

        {/* Item selection grid */}
        <div className="mt-4">
          {filteredItems.length === 0 ? (
            <div className="text-center py-12 text-muted">
              <p>No items in {activeCategory}</p>
            </div>
          ) : (
            <div className="mb-5 md:mb-6">
              <WardrobeGrid
                items={filteredItems}
                user={user}
                selectionMode={true}
                selectedItems={selectedItems}
                onItemSelect={toggleItem}
              />
            </div>
          )}
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

