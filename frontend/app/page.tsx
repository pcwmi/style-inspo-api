'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'

function DashboardContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'
  
  // Capitalize first letter of username for greeting
  const capitalizeFirst = (str: string) => {
    if (!str) return str
    return str.charAt(0).toUpperCase() + str.slice(1)
  }
  
  const [wardrobe, setWardrobe] = useState<any>(null)
  const [profile, setProfile] = useState<any>(null)
  const [savedCount, setSavedCount] = useState<number>(0)
  const [dislikedCount, setDislikedCount] = useState<number>(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [wardrobeData, profileData, savedData, dislikedData] = await Promise.all([
          api.getWardrobe(user),
          api.getProfile(user),
          api.getSavedOutfits(user).catch(() => ({ count: 0 })),
          api.getDislikedOutfits(user).catch(() => ({ count: 0 }))
        ])
        setWardrobe(wardrobeData)
        setProfile(profileData)
        setSavedCount(savedData.count || 0)
        setDislikedCount(dislikedData.count || 0)
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }
    if (user) fetchData()
  }, [user])

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

        {/* Wardrobe summary */}
        <Link
          href={`/upload?user=${user}`}
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
    </div>
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

