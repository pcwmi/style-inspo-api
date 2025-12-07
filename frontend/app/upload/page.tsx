'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import PhotoGuidelines from '@/components/PhotoGuidelines'

// Try to import image compression (optional)
let imageCompression: any = null
if (typeof window !== 'undefined') {
  try {
    imageCompression = require('browser-image-compression').default || require('browser-image-compression')
  } catch (e) {
    // Library not installed, will upload without compression
  }
}

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
  const [analyzingCount, setAnalyzingCount] = useState(0)

  // Capitalize first letter of username for greeting
  const capitalizeFirst = (str: string) => {
    if (!str) return str
    return str.charAt(0).toUpperCase() + str.slice(1)
  }

  // Fetch wardrobe items
  const fetchWardrobe = async () => {
    try {
      const wardrobeData = await api.getWardrobe(user).catch(() => ({ count: 0, items: [] }))
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

  // Auto-route to dashboard when 10+ photos uploaded
  useEffect(() => {
    if (!loadingProfile && wardrobeCount >= 10 && hasProfile) {
      router.push(`/?user=${user}`)
    }
  }, [wardrobeCount, hasProfile, loadingProfile, user, router])

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

    setUploading(true)
    setUploadStatus('Compressing image...')
    const jobIds: string[] = []

    try {
      for (const file of Array.from(files)) {
        let fileToUpload = file
        
        // Compress image client-side (if library is available)
        if (imageCompression) {
          try {
            const options = {
              maxSizeMB: 1,
              maxWidthOrHeight: 1920,
              useWebWorker: true
            }
            
            setUploadStatus(`Compressing ${file.name}...`)
            fileToUpload = await imageCompression(file, options)
          } catch (compressionError: any) {
            console.warn('Compression failed, uploading original:', compressionError)
            // Continue with original file if compression fails
            fileToUpload = file
          }
        } else {
          setUploadStatus(`Preparing ${file.name}...`)
        }
        
        setUploadStatus(`Uploading ${file.name}...`)
        
        try {
          const result = await api.uploadItem(user, fileToUpload, useRealAi)
          
          if (result.job_id) {
            jobIds.push(result.job_id)
            setUploadStatus(`Uploaded! Analyzing ${file.name}... (Job: ${result.job_id})`)
          } else {
            setUploadStatus(`Uploaded ${file.name} successfully`)
          }
        } catch (uploadError: any) {
          // Re-throw to be caught by outer catch
          throw uploadError
        }
      }
      
      // Refresh wardrobe to show new items and update progress
      await fetchWardrobe()
      
      // If there are job IDs, poll for completion
      if (jobIds.length > 0) {
        setAnalyzingCount(jobIds.length)
        
        const checkJobs = async () => {
          let allComplete = true
          for (const jobId of jobIds) {
            try {
              const status = await api.getJobStatus(jobId)
              if (status.status !== 'complete' && status.status !== 'failed') {
                allComplete = false
              }
            } catch (e) {
              console.error('Error checking job:', e)
            }
          }

          // Refresh wardrobe to see new items
          await fetchWardrobe()

          if (!allComplete) {
            setTimeout(checkJobs, 2000)
          } else {
            setAnalyzingCount(0)
          }
        }

        checkJobs()
      }
      
      // Show success message and clear after 3 seconds
      setUploadStatus('Upload complete!')
      setTimeout(() => {
        setUploadStatus('')
      }, 3000)
    } catch (error: any) {
      console.error('Upload error (full error object):', error)
      console.error('Error type:', typeof error)
      console.error('Error constructor:', error?.constructor?.name)
      console.error('Error keys:', Object.keys(error || {}))
      
      // Extract error message properly
      let errorMessage = 'Unknown error occurred'
      
      if (error instanceof Error) {
        errorMessage = error.message || error.toString()
      } else if (error?.message) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error?.detail) {
        errorMessage = error.detail
      } else if (error?.toString && typeof error.toString === 'function') {
        errorMessage = error.toString()
      } else {
        // Last resort: try to stringify, but handle circular references
        try {
          errorMessage = JSON.stringify(error, null, 2)
        } catch (e) {
          errorMessage = String(error)
        }
      }
      
      setUploadStatus(`Error: ${errorMessage}`)
      
      // Clear error after 8 seconds (longer for debugging)
      setTimeout(() => {
        setUploadStatus('')
      }, 8000)
    } finally {
      setUploading(false)
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

        {/* Progress Bar */}
        {wardrobeCount < 10 && (
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

        {/* Analyzing Banner */}
        {analyzingCount > 0 && (
          <div className="bg-blue-50 px-4 py-3 flex items-center justify-between mb-5 md:mb-6 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2">
              <span className="text-xl">📸</span>
              <span className="text-sm text-blue-800 font-medium">
                Analyzing {analyzingCount} photo{analyzingCount !== 1 ? 's' : ''}...
              </span>
            </div>
          </div>
        )}

        {/* AI Analysis toggle */}
        <div className="mb-5 md:mb-6">
          <label className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
            <input
              type="checkbox"
              checked={useRealAi}
              onChange={(e) => setUseRealAi(e.target.checked)}
              className="w-5 h-5 rounded border-[rgba(26,22,20,0.12)] flex-shrink-0 accent-terracotta"
            />
            <span className="text-base leading-relaxed">Use AI Fashion Analysis</span>
          </label>
        </div>

        {/* File upload */}
        <div className="mb-5 md:mb-6">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileSelect}
            disabled={uploading}
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
              uploading ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {uploading ? 'Uploading...' : 'Upload Photos'}
          </label>
        </div>

        {/* Upload status */}
        {uploadStatus && (
          <div className={`rounded-lg p-4 md:p-6 mb-5 md:mb-6 ${
            uploadStatus.startsWith('Error:')
              ? 'bg-red-50 border border-red-200'
              : uploadStatus.includes('complete') || uploadStatus.includes('Uploaded')
              ? 'bg-green-50 border border-green-200'
              : 'bg-sand/30 border border-terracotta/30'
          }`}>
            <p className={`text-sm md:text-base leading-relaxed ${
              uploadStatus.startsWith('Error:')
                ? 'text-red-800 font-medium'
                : uploadStatus.includes('complete') || uploadStatus.includes('Uploaded')
                ? 'text-green-800'
                : 'text-terracotta'
            }`}>{uploadStatus}</p>
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

