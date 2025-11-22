'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'

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
  const [loadingProfile, setLoadingProfile] = useState(true)

  // Capitalize first letter of username for greeting
  const capitalizeFirst = (str: string) => {
    if (!str) return str
    return str.charAt(0).toUpperCase() + str.slice(1)
  }

  // Check if user has profile (partial user)
  useEffect(() => {
    async function checkProfile() {
      try {
        const [profileData, wardrobeData] = await Promise.all([
          api.getProfile(user).catch(() => null),
          api.getWardrobe(user).catch(() => null)
        ])
        setProfile(profileData)
        setWardrobe(wardrobeData)
      } catch (error) {
        console.error('Error loading profile:', error)
      } finally {
        setLoadingProfile(false)
      }
    }
    checkProfile()
  }, [user])

  const hasProfile = profile?.three_words && 
    profile.three_words.current &&
    profile.three_words.aspirational &&
    profile.three_words.feeling
  
  const wardrobeCount = wardrobe?.count || 0
  const isPartialUser = hasProfile && wardrobeCount < 10

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    setUploadStatus('Compressing image...')

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
            setUploadStatus(`Uploaded! Analyzing ${file.name}... (Job: ${result.job_id})`)
          } else {
            setUploadStatus(`Uploaded ${file.name} successfully`)
          }
        } catch (uploadError: any) {
          // Re-throw to be caught by outer catch
          throw uploadError
        }
      }
      
      setUploadStatus('Upload complete!')
      
      // Check wardrobe count and profile to determine redirect
      try {
        const [wardrobeData, profileData] = await Promise.all([
          api.getWardrobe(user).catch(() => ({ count: 0 })),
          api.getProfile(user).catch(() => null)
        ])
        
        const wardrobeCount = wardrobeData?.count || 0
        const hasProfile = profileData?.three_words && 
          profileData.three_words.current &&
          profileData.three_words.aspirational &&
          profileData.three_words.feeling

        // Redirect based on onboarding status
        if (wardrobeCount >= 10 && hasProfile) {
          // Complete onboarding - go to path choice
          setTimeout(() => {
            router.push(`/path-choice?user=${user}`)
          }, 2000)
        } else if (wardrobeCount >= 10 && !hasProfile) {
          // Has wardrobe but no profile - go to words
          setTimeout(() => {
            router.push(`/words?user=${user}`)
          }, 2000)
        } else {
          // Not enough items yet - stay on upload page
          // Clear status after showing success
          setTimeout(() => {
            setUploadStatus('')
          }, 3000)
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error)
        // Fallback: redirect to dashboard
        setTimeout(() => {
          router.push(`/?user=${user}`)
        }, 2000)
      }
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
        <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
          ← Back
        </Link>
        
        {isPartialUser ? (
          <>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">Welcome back {capitalizeFirst(user)}!</h1>
            <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
              Let's add more pieces to your closet. Upload photos of your clothing items and we'll analyze them to help you discover new outfit combinations.
            </p>
          </>
        ) : (
          <>
            <h1 className="text-2xl md:text-3xl font-bold mb-2">Upload Wardrobe Items</h1>
            <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">
              Upload photos of your clothing items. We'll analyze them and add them to your wardrobe.
            </p>
          </>
        )}

        {/* AI Analysis toggle */}
        <div className="mb-5 md:mb-6">
          <label className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
            <input
              type="checkbox"
              checked={useRealAi}
              onChange={(e) => setUseRealAi(e.target.checked)}
              className="w-5 h-5 rounded border-[rgba(26,22,20,0.12)] flex-shrink-0"
            />
            <span className="text-base leading-relaxed">✨ Use AI Fashion Analysis (GPT-4V)</span>
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
            className={`block w-full border-2 border-dashed rounded-lg p-6 md:p-12 text-center cursor-pointer transition min-h-[140px] md:min-h-[180px] flex items-center justify-center ${
              uploading
                ? 'border-[rgba(26,22,20,0.12)] bg-sand cursor-not-allowed'
                : 'border-[rgba(26,22,20,0.3)] hover:border-terracotta hover:bg-sand/30 active:border-terracotta/70 bg-white'
            }`}
          >
            <div>
              <p className="text-base md:text-lg font-medium mb-2 leading-relaxed">
                {uploading ? 'Uploading...' : 'Tap to upload photos'}
              </p>
              <p className="text-sm text-muted leading-relaxed">
                PNG, JPG, WEBP up to 10MB each
              </p>
            </div>
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
        <div className="bg-sand/30 rounded-lg p-4 border border-[rgba(26,22,20,0.12)]">
          <p className="text-sm text-ink leading-relaxed">
            💡 Tip: You can select multiple photos at once from your camera roll or gallery.
            Images will be automatically compressed before uploading.
          </p>
        </div>
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

