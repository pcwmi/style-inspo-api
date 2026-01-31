'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import PhotoGuidelines from '@/components/PhotoGuidelines'
import { posthog } from '@/lib/posthog'

// Try to import image compression (optional)
let imageCompression: any = null
if (typeof window !== 'undefined') {
  try {
    imageCompression = require('browser-image-compression').default || require('browser-image-compression')
  } catch (e) {
    // Library not installed, will upload without compression
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function UploadPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [useRealAi, setUseRealAi] = useState(true)
  const [profile, setProfile] = useState<any>(null)
  const [wardrobe, setWardrobe] = useState<any>(null)
  const [wardrobeItems, setWardrobeItems] = useState<any[]>([])
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [showGuidelines, setShowGuidelines] = useState(false)

  // Unified progress state: tracks both upload and analysis phases
  const [uploadPhase, setUploadPhase] = useState<'idle' | 'uploading' | 'analyzing' | 'done'>('idle')
  const [uploadedCount, setUploadedCount] = useState(0)  // Files uploaded (phase 1)
  const [analyzedCount, setAnalyzedCount] = useState(0)  // Files analyzed (phase 2)
  const [totalFiles, setTotalFiles] = useState(0)

  // Legacy state for compatibility
  const isProcessing = uploadPhase === 'uploading' || uploadPhase === 'analyzing'

  // Capitalize first letter of username for greeting
  const capitalizeFirst = (str: string) => {
    if (!str) return str
    return str.charAt(0).toUpperCase() + str.slice(1)
  }

  // Fetch wardrobe items (with cache-busting for upload flow)
  const fetchWardrobe = async (bustCache = false) => {
    try {
      // During uploads, bypass browser cache to get fresh data
      const cacheBuster = bustCache ? `?_t=${Date.now()}` : ''
      const res = await fetch(`${API_URL}/api/wardrobe/${user}${cacheBuster}`)
      if (!res.ok) throw new Error('Failed to fetch wardrobe')
      const wardrobeData = await res.json()
      setWardrobe(wardrobeData)
      setWardrobeItems(wardrobeData.items || [])
    } catch (error) {
      console.error('Error fetching wardrobe:', error)
    }
  }

  // Check if user has profile (partial user) and fetch wardrobe
  useEffect(() => {
    async function checkProfile() {
      try {
        const [profileData, wardrobeData] = await Promise.all([
          api.getProfile(user).catch(() => null),
          api.getWardrobe(user).catch(() => ({ count: 0, items: [] }))
        ])
        setProfile(profileData)
        setWardrobe(wardrobeData)
        setWardrobeItems(wardrobeData.items || [])
      } catch (error) {
        console.error('Error loading profile:', error)
      } finally {
        setLoadingProfile(false)
      }
    }
    checkProfile()
  }, [user])

  // Show PhotoGuidelines on first load
  useEffect(() => {
    if (!loadingProfile) {
      const hasSeenGuidelines = localStorage.getItem(`photo_guidelines_seen_${user}`)
      if (!hasSeenGuidelines) {
        setShowGuidelines(true)
      }
    }
  }, [loadingProfile, user])

  const handleGuidelinesContinue = () => {
    localStorage.setItem(`photo_guidelines_seen_${user}`, 'true')
    setShowGuidelines(false)
  }

  const hasProfile = profile?.three_words && 
    profile.three_words.current &&
    profile.three_words.aspirational &&
    profile.three_words.feeling
  
  const wardrobeCount = wardrobe?.count || 0
  const isPartialUser = hasProfile && wardrobeCount < 10

  // Auto-route to dashboard when 10+ photos uploaded
  useEffect(() => {
    if (!loadingProfile && wardrobeCount >= 10 && hasProfile) {
      posthog.capture('upload_completed', {
        item_count: wardrobeCount
      })
      router.push(`/?user=${user}`)
    }
  }, [wardrobeCount, hasProfile, loadingProfile, user, router])

  const handleBack = () => {
    // Check if there's browser history to go back to
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back()
    } else {
      // Fallback to dashboard or welcome if no history
      router.push(hasProfile ? `/?user=${user}` : `/welcome?user=${user}`)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const fileArray = Array.from(files)
    const numFiles = fileArray.length

    // Initialize unified progress state
    setUploading(true)
    setUploadPhase('uploading')
    setTotalFiles(numFiles)
    setUploadedCount(0)
    setAnalyzedCount(0)
    setUploadStatus('')  // Clear any previous status

    // Track active EventSource connections for cleanup
    const eventSources: EventSource[] = []

    try {
      let uploadedCount = 0

      for (const file of fileArray) {
        let fileToUpload = file

        // Compress image client-side (if library is available)
        if (imageCompression) {
          try {
            const options = {
              maxSizeMB: 1,
              maxWidthOrHeight: 1920,
              useWebWorker: true,
              preserveExif: true
            }
            fileToUpload = await imageCompression(file, options)
          } catch (compressionError: any) {
            console.warn('Compression failed, uploading original:', compressionError)
            fileToUpload = file
          }
        }

        try {
          const result = await api.uploadItem(user, fileToUpload, useRealAi)
          uploadedCount++
          setUploadedCount(uploadedCount)  // Update unified progress

          if (result.job_id) {
            // Use SSE to track this job's completion
            const eventSource = new EventSource(`${API_URL}/api/jobs/${result.job_id}/stream`)
            eventSources.push(eventSource)

            eventSource.addEventListener('complete', async () => {
              eventSource.close()
              // Increment analyzed count and refresh wardrobe (bypass cache)
              setAnalyzedCount(prev => {
                const newCompleted = prev + 1
                // Check if all done
                if (newCompleted >= numFiles) {
                  setUploadPhase('done')
                  setUploadStatus('')
                  // Reset after brief delay
                  setTimeout(() => {
                    setUploadPhase('idle')
                    setTotalFiles(0)
                    setUploadedCount(0)
                    setAnalyzedCount(0)
                  }, 100)
                }
                return newCompleted
              })
              await fetchWardrobe(true)  // bust cache to get fresh data
            })

            eventSource.addEventListener('error', (e) => {
              console.error('SSE error for job:', result.job_id, e)
              eventSource.close()
              // Still count as completed (failed) so we don't hang
              setAnalyzedCount(prev => {
                const newCompleted = prev + 1
                if (newCompleted >= numFiles) {
                  setUploadPhase('done')
                  setUploadStatus('')
                  setTimeout(() => {
                    setUploadPhase('idle')
                    setTotalFiles(0)
                    setUploadedCount(0)
                    setAnalyzedCount(0)
                  }, 100)
                }
                return newCompleted
              })
              fetchWardrobe(true)  // bust cache to get fresh data
            })
          } else {
            // No job ID means it completed synchronously
            setAnalyzedCount(prev => prev + 1)
            await fetchWardrobe()
          }
        } catch (uploadError: any) {
          throw uploadError
        }
      }

      // All uploads initiated - switch to analyzing phase
      setUploadPhase('analyzing')
      setUploading(false)

    } catch (error: any) {
      console.error('Upload error:', error)

      let errorMessage = 'Unknown error occurred'
      if (error instanceof Error) {
        errorMessage = error.message || error.toString()
      } else if (error?.message) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error?.detail) {
        errorMessage = error.detail
      }

      setUploadStatus(`Error: ${errorMessage}`)

      // Clean up all event sources on error
      eventSources.forEach(es => es.close())

      // Reset processing state
      setUploadPhase('idle')
      setTotalFiles(0)
      setUploadedCount(0)
      setAnalyzedCount(0)

      setTimeout(() => {
        setUploadStatus('')
      }, 8000)

      setUploading(false)
    } finally {
      // Reset file input so user can select the same files again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  if (loadingProfile) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <button
          onClick={handleBack}
          className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center"
        >
          ← Back
        </button>
        
        {isPartialUser ? (
          <>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">Welcome back {capitalizeFirst(user)}!</h1>
            <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
              Upload at least 10 photos with a mix of top/bottom/shoes/accessories. More pieces lead to more inspiration.
            </p>
          </>
        ) : (
          <>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">Upload Wardrobe Items</h1>
            <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
              Upload at least 10 photos with a mix of top/bottom/shoes/accessories. More pieces lead to more inspiration.
            </p>
          </>
        )}

        {/* Wardrobe Progress - only show when not actively processing */}
        {wardrobeCount < 10 && uploadPhase === 'idle' && (
          <div className="mb-5 md:mb-6">
            <div className="flex justify-end items-center mb-2">
              <span className="text-sm text-muted">
                {wardrobeCount} out of 10 photos uploaded
              </span>
            </div>
            <div className="w-full bg-sand/30 rounded-full h-3 overflow-hidden">
              <div
                className="bg-terracotta h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min((wardrobeCount / 10) * 100, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Unified Progress Component - Two Phase */}
        {(uploadPhase === 'uploading' || uploadPhase === 'analyzing') && (
          <div className="border border-terracotta rounded-lg p-4 mb-5 md:mb-6 bg-bone">
            <div className="flex items-center gap-3 mb-2">
              <div className="animate-spin h-5 w-5 border-2 border-terracotta border-t-transparent rounded-full" />
              <span className="font-medium text-ink">
                Adding {totalFiles} item{totalFiles !== 1 ? 's' : ''} to your wardrobe
              </span>
            </div>
            <p className="text-sm text-muted mb-3">
              {uploadPhase === 'uploading'
                ? 'Uploading photos...'
                : 'Getting texture, cut, color details...'}
            </p>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-sand/50 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-terracotta h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${uploadPhase === 'uploading'
                      ? (uploadedCount / totalFiles) * 100
                      : (analyzedCount / totalFiles) * 100}%`
                  }}
                />
              </div>
              <span className="text-sm text-muted whitespace-nowrap">
                {uploadPhase === 'uploading' ? uploadedCount : analyzedCount} of {totalFiles}
              </span>
            </div>
          </div>
        )}

        {/* File upload */}
        <div className="mb-5 md:mb-6">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileSelect}
            disabled={uploading || isProcessing}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className={`block w-full text-center py-3.5 md:py-4 px-6 rounded-lg font-medium transition min-h-[48px] flex items-center justify-center cursor-pointer ${
              wardrobeCount >= 10
                ? 'bg-white text-terracotta border-2 border-terracotta hover:bg-terracotta/5 active:bg-terracotta/10'
                : 'bg-terracotta text-white hover:opacity-90 active:opacity-80'
            } ${
              (uploading || isProcessing) ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {uploading ? 'Uploading...' : isProcessing ? 'Processing...' : 'Upload Photos'}
          </label>
        </div>

        {/* Error status only */}
        {uploadStatus && uploadStatus.startsWith('Error:') && (
          <div className="rounded-lg p-4 md:p-6 mb-5 md:mb-6 bg-red-50 border border-red-200">
            <p className="text-sm md:text-base leading-relaxed text-red-800 font-medium">{uploadStatus}</p>
          </div>
        )}

        {/* Tips */}
        <div className="bg-sand/30 rounded-lg p-3 border border-[rgba(26,22,20,0.12)] mb-5 md:mb-6">
          <p className="text-sm text-ink leading-tight mb-0">
            Tip: Select multiple photos at once from your camera roll.
          </p>
        </div>

        {/* Continue Button when 10+ items */}
        {wardrobeCount >= 10 && hasProfile && (
          <div className="mb-5 md:mb-6">
            <Link
              href={`/?user=${user}`}
              className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
            >
              Continue to Generate Outfits
            </Link>
          </div>
        )}

        {/* Uploaded Items Display */}
        {wardrobeItems.length > 0 && (
          <div className="mt-8 md:mt-12">
            <h2 className="text-xl md:text-2xl font-bold mb-4">Your Uploaded Items</h2>
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {wardrobeItems.map(item => (
                <Link
                  key={item.id}
                  href={`/closet/${item.id}?user=${user}`}
                  className="group relative block aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden"
                >
                  {item.system_metadata?.image_path ? (
                    <img
                      src={item.system_metadata.image_path.startsWith('http')
                        ? item.system_metadata.image_path
                        : `/api/images/${item.system_metadata.image_path.split('/').pop()}`}
                      alt={item.styling_details?.name || 'Clothing item'}
                      className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300">
                      No Image
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                    <span className="text-white text-xs font-medium truncate w-full">
                      {item.styling_details?.name || 'Item'}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* PhotoGuidelines Modal */}
        <PhotoGuidelines
          isOpen={showGuidelines}
          onClose={() => {
            localStorage.setItem(`photo_guidelines_seen_${user}`, 'true')
            setShowGuidelines(false)
          }}
          onContinue={handleGuidelinesContinue}
        />
      </div>
    </div>
  )
}

export default function UploadPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <UploadPageContent />
    </Suspense>
  )
}

