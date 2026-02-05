'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/useAuth'
import { buildUserUrl } from '@/lib/auth'

function WelcomePageContent() {
  const searchParams = useSearchParams()
  const { authUser, effectiveUserId } = useAuth()

  // Legacy URL param support
  const userParam = searchParams.get('user')

  // Build URL for words page - include user param only in legacy mode
  const wordsUrl = authUser ? '/words' : (userParam ? `/words?user=${userParam}` : '/words')

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <div className="text-center mb-8 md:mb-12">
          <div className="inline-block px-3 py-1 bg-white border border-[rgba(26,22,20,0.12)] rounded-full text-sm text-ink mb-4">
            Digital Wardrobe
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-4">Style Inspo</h1>
          <p className="text-muted text-base md:text-lg leading-relaxed max-w-xl mx-auto">
            Endless outfit possibilities that feel like you — comfortable, confident, and aspirational
          </p>
        </div>

        {/* How It Works Card */}
        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 md:p-8 mb-6 md:mb-8 shadow-sm">
          <h3 className="text-xl md:text-2xl font-semibold mb-6">How It Works</h3>

          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-xs">
                1
              </div>
              <p className="text-base leading-relaxed">
                Describe your style
              </p>
            </div>

            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-xs">
                2
              </div>
              <p className="text-base leading-relaxed">
                Upload 10-15 pieces, a mix of top, bottom, shoes, and accessories works the best.
              </p>
            </div>

            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-xs">
                3
              </div>
              <p className="text-base leading-relaxed">
                Get fresh outfit ideas that stay true to your style
              </p>
            </div>
          </div>
        </div>

        {/* Get Started Button */}
        <Link
          href={wordsUrl}
          className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center button-container"
        >
          Get Started
        </Link>

        {/* Sign in link for returning users */}
        <div className="mt-6 text-center">
          <p className="text-sm text-muted">
            Already have an account?{' '}
            <Link href="/login" className="text-terracotta hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function WelcomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <WelcomePageContent />
    </Suspense>
  )
}



