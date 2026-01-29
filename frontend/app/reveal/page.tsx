'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import Image from 'next/image'
import { OutfitCard } from '@/components/OutfitCard'
import { posthog } from '@/lib/posthog'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function RevealPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const jobId = searchParams.get('job')
  const debugMode = searchParams.get('debug') === 'true'
  const streamMode = searchParams.get('stream') === 'true'
  const mode = searchParams.get('mode') || 'occasion'
  const occasions = searchParams.get('occasions') || ''
  const anchorItems = searchParams.get('anchor_items') || ''
  const weatherCondition = searchParams.get('weather_condition') || ''
  const temperatureRange = searchParams.get('temperature_range') || ''

  const [outfits, setOutfits] = useState<any[]>([])
  const [reasoning, setReasoning] = useState<string | null>(null)
  const [status, setStatus] = useState<'loading' | 'complete' | 'error'>('loading')
  const [error, setError] = useState<string>('')
  const [progress, setProgress] = useState<number>(0)
  const [pollCount, setPollCount] = useState<number>(0)
  const [streamedContent, setStreamedContent] = useState<string>('')
  const [currentOutfit, setCurrentOutfit] = useState<number>(0)

  useEffect(() => {
    let eventSource: EventSource | null = null
    let pollInterval: NodeJS.Timeout | null = null

    if (streamMode) {
      // NEW: Direct streaming mode
      const params = new URLSearchParams({
        user_id: user,
        mode: mode,
      })
      if (occasions) params.append('occasions', occasions)
      if (anchorItems) params.append('anchor_items', anchorItems)
      if (weatherCondition) params.append('weather_condition', weatherCondition)
      if (temperatureRange) params.append('temperature_range', temperatureRange)
      if (debugMode) params.append('include_reasoning', 'true')

      // Pass device_id for analytics filtering (separates real users from admin testing)
      // Use $device_id property which is the anonymous ID that persists after identify()
      // This ensures we capture Pei-Chin's device even when visiting other users' URLs
      const deviceId = posthog?.get_property?.('$device_id') || posthog?.get_distinct_id?.()
      if (deviceId) params.append('device_id', deviceId)

      try {
        eventSource = new EventSource(`${API_URL}/api/outfits/generate/stream?${params.toString()}`)

        eventSource.addEventListener('outfit', (e) => {
          const data = JSON.parse(e.data)
          console.log(`Outfit ${data.outfit_number} received`)
          // APPEND outfit to array (not replace)
          setOutfits(prev => [...prev, data.outfit])
          setCurrentOutfit(data.outfit_number)
          setStreamedContent(`Outfit ${data.outfit_number} ready!`)
        })

        eventSource.addEventListener('complete', (e) => {
          const data = JSON.parse(e.data)
          console.log('Streaming complete, total outfits:', data.total)
          
          // Extract reasoning if debug mode and available
          if (debugMode && data.reasoning) {
            setReasoning(data.reasoning)
          }
          
          setStatus('complete')
          eventSource?.close()
        })

        eventSource.addEventListener('error', (e: Event) => {
          console.error('Streaming error', e)
          eventSource?.close()
          setStatus('error')
          setError('Streaming failed. Please try again.')
        })

      } catch (err) {
        console.error('SSE not supported', err)
        setStatus('error')
        setError('Streaming not supported in this browser.')
      }
    } else if (jobId) {
      // EXISTING: Job-based polling mode (keep existing code)
      const validJobId = jobId

      const startSSEStreaming = () => {
        try {
          eventSource = new EventSource(`${API_URL}/api/jobs/${validJobId}/stream`)

          eventSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data)
            setProgress(data.progress)
            setCurrentOutfit(data.current_outfit || 0)

            // Update status message
            if (data.message) {
              setStreamedContent(data.message)
            }
          })

          eventSource.addEventListener('outfit', (e) => {
            const data = JSON.parse(e.data)
            console.log(`Outfit ${data.outfit_number} being generated...`)
            setCurrentOutfit(data.outfit_number)
          })

          eventSource.addEventListener('complete', (e) => {
            const result = JSON.parse(e.data)
            const outfitsArray = result.outfits || []
            console.log('SSE complete, outfits:', outfitsArray.length)
            setOutfits(outfitsArray)

            // Extract reasoning if debug mode
            if (debugMode && result.reasoning) {
              console.log('Setting reasoning from SSE, length:', result.reasoning.length)
              setReasoning(result.reasoning)
            }

            setStatus('complete')
            eventSource?.close()
          })

          eventSource.addEventListener('error', (e: Event) => {
            console.warn('SSE error, falling back to polling', e)
            eventSource?.close()

            // Fall back to polling
            startPolling()
          })

        } catch (err) {
          console.warn('SSE not supported, using polling', err)
          startPolling()
        }
      }

      const startPolling = () => {
        // Existing polling logic as fallback
        let pollCounter = 0
        const MAX_POLLS = 90

        const pollJob = async () => {
          pollCounter++
          setPollCount(pollCounter)

          if (pollCounter > MAX_POLLS) {
            setStatus('error')
            setError('Generation taking longer than expected...')
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
              console.log('Polling complete, outfits:', outfitsArray.length)
              setOutfits(outfitsArray)

              if (debugMode && result.result?.reasoning) {
                console.log('Setting reasoning from polling, length:', result.result.reasoning.length)
                setReasoning(result.result.reasoning)
              }

              setStatus('complete')
              if (pollInterval) clearInterval(pollInterval)
            } else if (result.status === 'failed') {
              setStatus('error')
              const errorMsg = result.error || 'Generation failed'
              setError(errorMsg.length > 500 ? errorMsg.substring(0, 500) + '...' : errorMsg)
              if (pollInterval) clearInterval(pollInterval)
            }
          } catch (err: any) {
            // Handle 404 (job not found) specially
            if (err.message?.includes('404') || err.message?.includes('not found')) {
              setStatus('error')
              setError('Job not found. The job may have expired or the worker may not be running. Please try generating outfits again.')
            } else {
              setStatus('error')
              setError(err.message || 'Failed to check job status. Please check your connection and try again.')
            }
            if (pollInterval) clearInterval(pollInterval)
          }
        }

        pollJob()
        pollInterval = setInterval(pollJob, 2000)
      }

      // Try SSE first
      startSSEStreaming()
    } else {
      setStatus('error')
      setError('No job ID or streaming params provided')
    }

    return () => {
      eventSource?.close()
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [streamMode, jobId, mode, occasions, anchorItems, weatherCondition, temperatureRange, user, debugMode])

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-bone page-container">
        <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
          {/* Show any outfits we've received so far */}
          {outfits.length > 0 && (
            <>
              <h1 className="text-2xl md:text-3xl font-bold mb-5 md:mb-8">
                Here's what could work for your day
              </h1>
              {outfits.map((outfit, idx) => (
                <OutfitCard
                  key={idx}
                  outfit={outfit}
                  user={user}
                  index={idx + 1}
                />
              ))}
            </>
          )}

          {/* Show loading indicator for remaining outfits */}
          <div className="text-center px-4 py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
            <p className="text-ink text-base font-medium">
              {outfits.length === 0
                ? 'Creating your first outfit...'
                : `Creating outfit ${outfits.length + 1} of 3...`}
            </p>
            {!streamMode && progress > 0 && (
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
            {!streamMode && pollCount > 30 && (
              <p className="text-xs text-muted mt-2">
                Still processing... ({Math.floor(pollCount * 2)}s elapsed)
              </p>
            )}
          </div>
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

