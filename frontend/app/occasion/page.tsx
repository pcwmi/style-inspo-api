'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useState } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import { posthog } from '@/lib/posthog'

const OCCASIONS = [
  'School drop-off',
  'Weekend errands',
  'Business meeting',
  'Date night',
  'Coffee meeting',
  'Formal event',
  'Working from home',
  'Brunch'
]

function OccasionPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const debugMode = searchParams.get('debug') === 'true'

  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([])
  const [customOccasion, setCustomOccasion] = useState('')
  const [generating, setGenerating] = useState(false)

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const { job_id } = await api.generateOutfits({
        user_id: user,
        occasions: [...selectedOccasions, customOccasion].filter(Boolean),
        temperature_range: undefined,
        mode: 'occasion',
        mock: user === 'test',
        include_reasoning: debugMode
      })

      posthog.capture('outfit_generated', {
        occasions: [...selectedOccasions, customOccasion].filter(Boolean),
        mode: 'occasion'
      })

      // Redirect with debug param if enabled
      const debugParam = debugMode ? '&debug=true' : ''
      router.push(`/reveal?user=${user}&job=${job_id}${debugParam}`)
    } catch (error) {
      console.error('Error generating outfits:', error)
      alert('Failed to generate outfits. Please try again.')
      setGenerating(false)
    }
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
          What does this ONE outfit need to do today?
        </h1>
        <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
          Pick everything you're doing—we'll find pieces that transition across all of it
        </p>

        {/* Occasion chips */}
        <div className="flex flex-wrap gap-2 mb-5 md:mb-6">
          {OCCASIONS.map(occ => (
            <button
              key={occ}
              onClick={() => {
                if (selectedOccasions.includes(occ)) {
                  setSelectedOccasions(selectedOccasions.filter(o => o !== occ))
                } else {
                  setSelectedOccasions([...selectedOccasions, occ])
                }
              }}
              className={`px-3 py-1.5 text-sm rounded-full border transition ${
                selectedOccasions.includes(occ)
                  ? 'bg-terracotta text-white border-terracotta'
                  : 'bg-white text-ink border-[rgba(26,22,20,0.12)] hover:border-terracotta/50'
              }`}
            >
              {occ}
            </button>
          ))}
        </div>

        {/* Custom occasion */}
        <div className="mb-5 md:mb-6">
          <input
            type="text"
            placeholder="Or describe your day..."
            value={customOccasion}
            onChange={(e) => setCustomOccasion(e.target.value)}
            className="w-full px-4 py-3 text-base border border-[rgba(26,22,20,0.12)] rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta bg-white"
          />
        </div>

        {/* Confirmation message */}
        {selectedOccasions.length > 1 && (
          <div className="bg-sand/30 border border-terracotta/30 rounded-lg p-3 md:p-4 mb-5 md:mb-6">
            <p className="text-terracotta text-sm leading-relaxed">
              💡 You'll get ONE versatile outfit that works for: {selectedOccasions.join(', ')}
            </p>
          </div>
        )}

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={selectedOccasions.length === 0 && !customOccasion || generating}
          className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center button-container"
        >
          {generating ? 'Creating Outfits...' : 'Create Outfits'}
        </button>
      </div>
    </div>
  )
}

export default function OccasionPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <OccasionPageContent />
    </Suspense>
  )
}

