'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import Link from 'next/link'

function WelcomePageContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'

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
          <h3 className="text-xl md:text-2xl font-semibold mb-4">How It Works</h3>
          <p className="text-muted mb-6 text-base leading-relaxed">
            Three simple steps to unlock your wardrobe:
          </p>
          
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-sm">
                1
              </div>
              <p className="text-base leading-relaxed pt-1">
                Describe your style in three words
              </p>
            </div>
            
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-sm">
                2
              </div>
              <p className="text-base leading-relaxed pt-1">
                Upload 10-15 pieces, a mix of top, bottom, shoes, and accessories works the best.
              </p>
            </div>

            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-terracotta text-white flex items-center justify-center font-semibold text-sm">
                3
              </div>
              <p className="text-base leading-relaxed pt-1">
                Get fresh outfit ideas that stay true to your style
              </p>
            </div>
          </div>
        </div>

        {/* Get Started Button */}
        <Link
          href={`/words?user=${user}`}
          className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center button-container"
        >
          Get Started
        </Link>
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



