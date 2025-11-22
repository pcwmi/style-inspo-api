'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import Image from 'next/image'

function RevealPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const jobId = searchParams.get('job')

  const [outfits, setOutfits] = useState<any[]>([])
  const [status, setStatus] = useState<'loading' | 'complete' | 'error'>('loading')
  const [error, setError] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [pollCount, setPollCount] = useState<number>(0)

  useEffect(() => {
    if (!jobId) {
      setStatus('error')
      setError('No job ID provided')
      return
    }

    // TypeScript now knows jobId is string after the check above
    const validJobId = jobId

    let pollInterval: NodeJS.Timeout
    const MAX_POLLS = 90 // 3 minutes max (90 polls * 2 seconds)
    let pollCounter = 0

    async function pollJob() {
      pollCounter++
      setPollCount(pollCounter)

      // Timeout after max polls
      if (pollCounter > MAX_POLLS) {
        setStatus('error')
        setError('Outfit generation is taking longer than expected. The job may have failed or the worker may be unavailable. Please try again.')
        clearInterval(pollInterval)
        return
      }

      try {
        const result = await api.getJobStatus(validJobId)

        // Update progress if available
        if (result.progress !== undefined) {
          setProgress(result.progress)
        }

        if (result.status === 'complete') {
          const outfitsArray = result.result?.outfits || []
          console.log('Job completed, outfits:', outfitsArray, 'Full result:', result.result)
          setOutfits(outfitsArray)
          setStatus('complete')
          clearInterval(pollInterval)
        } else if (result.status === 'failed') {
          setStatus('error')
          // Extract error message from job.exc_info if it's a string
          const errorMsg = result.error || 'Generation failed'
          setError(errorMsg.length > 500 ? errorMsg.substring(0, 500) + '...' : errorMsg)
          clearInterval(pollInterval)
        }
        // else keep polling (status === 'processing' or 'queued')
      } catch (err: any) {
        // Handle 404 (job not found) specially
        if (err.message?.includes('404') || err.message?.includes('not found')) {
          setStatus('error')
          setError('Job not found. The job may have expired or the worker may not be running. Please try generating outfits again.')
        } else {
          setStatus('error')
          setError(err.message || 'Failed to check job status. Please check your connection and try again.')
        }
        clearInterval(pollInterval)
      }
    }

    // Initial call
    pollJob()

    // Poll every 2 seconds
    pollInterval = setInterval(pollJob, 2000)

    return () => clearInterval(pollInterval)
  }, [jobId])

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4 max-w-sm">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium mb-2">Creating your outfits...</p>
          <p className="text-muted text-sm leading-relaxed mb-2">This usually takes 20-30 seconds</p>
          {progress > 0 && (
            <div className="mt-4">
              <div className="w-full bg-sand rounded-full h-2 mb-2">
                <div
                  className="bg-terracotta h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="text-xs text-muted">{progress}% complete</p>
            </div>
          )}
          {pollCount > 30 && (
            <p className="text-xs text-muted mt-2">Still processing... ({Math.floor(pollCount * 2)}s elapsed)</p>
          )}
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-bone page-container">
        <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 md:p-6">
            <h2 className="text-lg md:text-xl font-semibold mb-2 text-red-900">Oops! Something went wrong</h2>
            <p className="text-red-800 mb-4 text-sm md:text-base leading-relaxed">{error}</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => router.back()}
                className="bg-terracotta text-white px-6 py-3 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
              >
                Try Again
              </button>
              <Link
                href={`/?user=${user}`}
                className="bg-white border-2 border-ink text-ink px-6 py-3 rounded-lg hover:bg-sand/30 active:bg-sand/50 text-center min-h-[48px] flex items-center justify-center"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <h1 className="text-2xl md:text-3xl font-bold mb-5 md:mb-8">
          Here's what could work for your day
        </h1>

        {outfits.length === 0 ? (
          <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 md:p-8 mb-6 shadow-sm">
            <p className="text-muted text-base leading-relaxed mb-4">
              No outfits were generated. This might happen if:
            </p>
            <ul className="text-muted text-sm md:text-base leading-relaxed mb-4 list-disc list-inside space-y-2">
              <li>Your wardrobe doesn't have enough items for the selected occasions</li>
              <li>The style engine couldn't find suitable combinations</li>
              <li>There was an issue during generation</li>
            </ul>
            <p className="text-muted text-sm md:text-base leading-relaxed">
              Try adding more items to your wardrobe or selecting different occasions.
            </p>
          </div>
        ) : (
          outfits.map((outfit, idx) => (
            <OutfitCard
              key={idx}
              outfit={outfit}
              user={user}
              index={idx + 1}
            />
          ))
        )}

        <div className="mt-6 md:mt-8">
          <Link
            href={`/?user=${user}`}
            className="block w-full bg-white border-2 border-ink text-ink text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:bg-sand/30 active:bg-sand/50 transition min-h-[48px] flex items-center justify-center button-container"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function RevealPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <RevealPageContent />
    </Suspense>
  )
}

function OutfitCard({ outfit, user, index }: { outfit: any; user: string; index: number }) {
  const [saving, setSaving] = useState(false)
  const [disliking, setDisliking] = useState(false)
  const [selectedFeedback, setSelectedFeedback] = useState<string[]>([])
  const [dislikeReason, setDislikeReason] = useState('')
  const [otherReasonText, setOtherReasonText] = useState('')

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.saveOutfit({
        user_id: user,
        outfit,
        feedback: selectedFeedback
      })
      alert('Outfit saved!')
      setSaving(false)
    } catch (error) {
      console.error('Error saving outfit:', error)
      alert('Failed to save outfit')
      setSaving(false)
    }
  }

  const handleDislike = async () => {
    setDisliking(true)
    try {
      await api.dislikeOutfit({
        user_id: user,
        outfit,
        reason: dislikeReason === 'Other' ? `Other: ${otherReasonText}` : dislikeReason
      })
      alert('Feedback recorded')
      setDisliking(false)
    } catch (error) {
      console.error('Error disliking outfit:', error)
      alert('Failed to record feedback')
      setDisliking(false)
    }
  }





  return (
    <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-4 md:mb-6 shadow-sm">
      <h2 className="text-lg md:text-xl font-semibold mb-3 md:mb-4">Outfit {index}</h2>

      {/* Outfit images */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {outfit.items.map((item: any, idx: number) => (
          <div key={idx} className="relative aspect-square rounded overflow-hidden bg-sand">
            {item.image_path ? (
              item.image_path.startsWith('http') ? (
                <img
                  src={item.image_path}
                  alt={item.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Image
                  src={`/${item.image_path}`}
                  alt={item.name}
                  fill
                  className="object-cover"
                />
              )
            ) : null}
          </div>
        ))}
      </div>

      {/* Styling notes */}
      <div className="mb-3 md:mb-4">
        <h3 className="font-semibold mb-2 text-base">How to Style</h3>
        <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.styling_notes}</p>
      </div>

      {/* Why it works */}
      <div className="mb-3 md:mb-4">
        <h3 className="font-semibold mb-2 text-base">Why This Works</h3>
        <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.why_it_works}</p>
      </div>

      {/* Actions */}
      {!saving && !disliking ? (
        <div className="flex gap-3">
          <button
            onClick={() => setSaving(true)}
            className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
          >
            Save Outfit
          </button>
          <button
            onClick={() => setDisliking(true)}
            className="px-6 py-3 border border-[rgba(26,22,20,0.12)] rounded-lg hover:bg-sand/30 active:bg-sand/50 min-h-[48px] min-w-[48px] flex items-center justify-center"
          >
            👎
          </button>
        </div>
      ) : saving ? (
        <div className="mt-4 border-t border-[rgba(26,22,20,0.12)] pt-4">
          <h3 className="text-lg font-semibold mb-4">What do you love about it?</h3>
          <div className="space-y-2.5 mb-4">
            {['Perfect for my occasions', 'Feels authentic to my style', 'Never thought to combine these pieces', 'Love the vibe'].map(option => (
              <label key={option} className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
                <input
                  type="checkbox"
                  checked={selectedFeedback.includes(option)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedFeedback([...selectedFeedback, option])
                    } else {
                      setSelectedFeedback(selectedFeedback.filter(f => f !== option))
                    }
                  }}
                  className="w-5 h-5 rounded border-[rgba(26,22,20,0.12)] flex-shrink-0"
                />
                <span className="text-base leading-relaxed flex-1">{option}</span>
              </label>
            ))}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleSave}
              className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
            >
              Save
            </button>
            <button
              onClick={() => setSaving(false)}
              className="flex-1 bg-sand text-ink py-3 px-6 rounded-lg hover:bg-sand/80 active:bg-sand/70 min-h-[48px] flex items-center justify-center"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-4 border-t border-[rgba(26,22,20,0.12)] pt-4">
          <h3 className="text-lg font-semibold mb-4">What's the main issue?</h3>
          <div className="space-y-2.5 mb-4">
            {["Won't look good on me", "Doesn't match my occasions", "Not my style", "The outfit doesn't make sense", "Other"].map(option => (
              <label key={option} className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
                <input
                  type="radio"
                  name="dislike-reason"
                  value={option}
                  checked={dislikeReason === option}
                  onChange={(e) => setDislikeReason(e.target.value)}
                  className="w-5 h-5 flex-shrink-0"
                />
                <span className="text-base leading-relaxed flex-1">{option}</span>
              </label>
            ))}
          </div>
          {dislikeReason === 'Other' && (
            <input
              type="text"
              placeholder="Please specify..."
              value={otherReasonText}
              onChange={(e) => setOtherReasonText(e.target.value)}
              className="w-full px-4 py-3 border border-[rgba(26,22,20,0.12)] rounded-lg mb-4 text-base bg-white"
            />
          )}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleDislike}
              className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
            >
              Submit
            </button>
            <button
              onClick={() => setDisliking(false)}
              className="flex-1 bg-sand text-ink py-3 px-6 rounded-lg hover:bg-sand/80 active:bg-sand/70 min-h-[48px] flex items-center justify-center"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

