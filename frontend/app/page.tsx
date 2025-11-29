'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense } from 'react'
import { useEffect } from 'react'
import Link from 'next/link'
import { isOnboardingComplete, getOnboardingStep } from '@/lib/onboarding'
import { useWardrobe, useProfile, useSavedOutfits, useDislikedOutfits } from '@/lib/queries'

function DashboardContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const userParam = searchParams.get('user')
  const user = userParam || 'default'

  // Capitalize first letter of username for greeting
  const capitalizeFirst = (str: string) => {
    if (!str) return str
    return str.charAt(0).toUpperCase() + str.slice(1)
  }

  // React Query hooks - automatic caching and deduplication
  const { data: wardrobe, isLoading: wardrobeLoading, error: wardrobeError } = useWardrobe(user)
  const { data: profile, isLoading: profileLoading, error: profileError } = useProfile(user)
  const { data: savedData, isLoading: savedLoading } = useSavedOutfits(user)
  const { data: dislikedData, isLoading: dislikedLoading } = useDislikedOutfits(user)

  const savedCount = savedData?.count || 0
  const dislikedCount = dislikedData?.count || 0
  const loading = wardrobeLoading || profileLoading || savedLoading || dislikedLoading

  // Log errors for debugging
  if (wardrobeError) console.error('Wardrobe error:', wardrobeError)
  if (profileError) console.error('Profile error:', profileError)

  // Check onboarding and redirect if needed
  useEffect(() => {
    async function checkOnboarding() {
      // If no user parameter in URL, redirect to welcome page
      if (!userParam) {
        router.push('/welcome')
        return
      }

      // Wait for wardrobe data to load before checking onboarding
      if (wardrobeLoading) return

      try {
        const onboardingComplete = await isOnboardingComplete(user)
        if (!onboardingComplete) {
          const step = await getOnboardingStep(user)
          const stepMap: Record<string, string> = {
            welcome: '/welcome',
            words: '/words',
            upload: '/upload',
            complete: '/' // Already complete, shouldn't happen
          }
          const redirectPath = stepMap[step] || '/welcome'
          router.push(`${redirectPath}?user=${user}`)
        }
      } catch (error) {
        console.error('Error checking onboarding:', error)
        // On error, default to showing dashboard (safer than blocking)
      }
    }
    checkOnboarding()
  }, [user, userParam, wardrobeLoading, router])

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

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <h1 className="text-2xl md:text-3xl font-bold mb-2">Style Inspo</h1>
        <p className="text-muted mb-5 md:mb-8 text-base leading-relaxed">Welcome back {capitalizeFirst(user)}! Ready to discover new outfits?</p>

        {/* Primary CTAs */}
        <div className="space-y-3 md:space-y-4 mb-6 md:mb-8">
          <Link
            href={`/occasion?user=${user}`}
            className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
          >
            Plan my outfit
          </Link>

          <Link
            href={`/complete?user=${user}`}
            className="block w-full bg-white border-2 border-ink text-ink text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:bg-sand transition active:bg-sand/80 min-h-[48px] flex items-center justify-center"
          >
            Complete my look
          </Link>
        </div>

        {/* Buy Smarter Card */}
        {/* Buy Smarter Card */}
        {/* Buy Smarter Card */}
        <Link
          href={`/consider-buying?user=${user}`}
          className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-5 md:mb-8 hover:bg-sand/30 active:bg-sand/50 transition shadow-sm group"
        >
          <div className="flex justify-between items-center mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-lg md:text-xl font-semibold">Buy Smarter</h2>
              <span className="text-xl">✨</span>
            </div>
            <span className="text-terracotta text-sm md:text-base flex items-center font-medium group-hover:opacity-80 transition-opacity">
              Try it now
              <svg className="w-4 h-4 ml-1 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </span>
          </div>
          <p className="text-muted text-base leading-relaxed">
            See how new items work with your closet before you buy.
          </p>
        </Link>

        {/* Wardrobe summary */}
        <Link
          href={`/closet?user=${user}`}
          className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-5 md:mb-8 hover:bg-sand/30 active:bg-sand/50 transition shadow-sm"
        >
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg md:text-xl font-semibold">Your Wardrobe</h2>
            <span className="text-terracotta text-sm md:text-base">
              Manage Closet
            </span>
          </div>
          <p className="text-muted text-base">
            {wardrobe?.count || 0} pieces uploaded
          </p>
        </Link>

        {/* Saved outfits link */}
        <div className="mb-4 md:mb-6">
          <Link
            href={`/saved?user=${user}`}
            className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 hover:bg-sand/30 active:bg-sand/50 transition shadow-sm"
          >
            <h2 className="text-lg md:text-xl font-semibold mb-1.5">Saved Outfits</h2>
            <p className="text-muted text-base">
              {savedCount} saved outfit{savedCount !== 1 ? 's' : ''}
            </p>
          </Link>
        </div>

        {/* Disliked outfits link */}
        <div className="mb-4 md:mb-6 button-container">
          <Link
            href={`/disliked?user=${user}`}
            className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 hover:bg-sand/30 active:bg-sand/50 transition shadow-sm"
          >
            <h2 className="text-lg md:text-xl font-semibold mb-1.5">Disliked Outfits</h2>
            <p className="text-muted text-base">
              {dislikedCount} disliked outfit{dislikedCount !== 1 ? 's' : ''}
            </p>
          </Link>
        </div>
      </div>
    </div >
  )
}

export default function Dashboard() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading...</p>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  )
}

