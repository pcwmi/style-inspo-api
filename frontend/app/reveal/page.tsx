'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import Image from 'next/image'
import { OutfitCard } from '@/components/OutfitCard'

function RevealPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const jobId = searchParams.get('job')
  const debugMode = searchParams.get('debug') === 'true'

  const [outfits, setOutfits] = useState<any[]>([])
  const [reasoning, setReasoning] = useState<string | null>(null)
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
          
          // Extract reasoning if present
          if (debugMode && result.result?.reasoning) {
            setReasoning(result.result.reasoning)
          }
          
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
        {/* Debug mode indicator */}
        {debugMode && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              🐛 Debug Mode Active - Showing AI reasoning
            </p>
          </div>
        )}

        <h1 className="text-2xl md:text-3xl font-bold mb-5 md:mb-8">
          Here's what could work for your day
        </h1>

        {/* Show reasoning if debug mode is on */}
        {debugMode && reasoning && (
          <div className="space-y-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm border border-sand p-6">
              <h2 className="text-lg font-semibold text-ink mb-4">
                Chain-of-Thought Reasoning
              </h2>
              <pre className="whitespace-pre-wrap text-sm text-muted font-mono bg-bone p-4 rounded border border-sand overflow-x-auto max-h-96 overflow-y-auto">
                {reasoning}
              </pre>
            </div>

            <div className="border-t border-sand pt-6">
              <h2 className="text-lg font-semibold text-ink mb-4">
                Final Outfits
              </h2>
            </div>
          </div>
        )}

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

// Removed inline OutfitCard component as it is now imported from @/components/OutfitCard

