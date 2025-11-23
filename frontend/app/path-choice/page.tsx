'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import Link from 'next/link'

function PathChoicePageContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <h1 className="text-2xl md:text-3xl font-bold mb-2 text-center">How would you like to get started?</h1>
        <p className="text-muted mb-6 md:mb-8 text-base leading-relaxed text-center">
          Choose whichever feels right for today - you can always try the other way later
        </p>

        <div className="h-px bg-[rgba(26,22,20,0.12)] mb-6 md:mb-8"></div>

        {/* Two column layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-6 md:mb-8">
          {/* Plan My Outfit Card */}
          <div className="bg-gradient-to-br from-[#FAF7F2] to-[#F5EFE6] rounded-2xl p-6 md:p-8 min-h-[280px] flex flex-col">
            <div className="text-5xl mb-4">📅</div>
            <h3 className="text-xl font-semibold mb-2">Plan My Outfit</h3>
            <p className="text-[#6B625A] mb-4 text-base leading-relaxed flex-grow">
              Share your occasion and today's weather, and we'll create outfits for you
            </p>
            <p className="text-[#8B7E74] text-sm mb-4">
              Like: "What should I wear for drop-off + coffee meeting?"
            </p>
            <Link
              href={`/occasion?user=${user}`}
              className="block w-full bg-terracotta text-white text-center py-3 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
            >
              Start with Occasion
            </Link>
          </div>

          {/* Complete My Look Card */}
          <div className="bg-gradient-to-br from-[#FFF5F0] to-[#FFE8DC] rounded-2xl p-6 md:p-8 min-h-[280px] flex flex-col">
            <div className="text-5xl mb-4">✨</div>
            <h3 className="text-xl font-semibold mb-2">Complete My Look</h3>
            <p className="text-[#6B625A] mb-4 text-base leading-relaxed flex-grow">
              Pick pieces you want to wear, we'll complete the outfit
            </p>
            <p className="text-[#8B7E74] text-sm mb-4">
              Like: "I want to wear this sweater in a fresh way"
            </p>
            <Link
              href={`/complete?user=${user}`}
              className="block w-full bg-terracotta text-white text-center py-3 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
            >
              Start with Items
            </Link>
          </div>
        </div>

        <div className="h-px bg-[rgba(26,22,20,0.12)] mb-6 md:mb-8"></div>

        {/* Skip option */}
        <Link
          href={`/?user=${user}`}
          className="block w-full bg-white border-2 border-ink text-ink text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:bg-sand transition active:bg-sand/80 min-h-[48px] flex items-center justify-center button-container"
        >
          Skip for now, go to Dashboard
        </Link>
      </div>
    </div>
  )
}

export default function PathChoicePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <PathChoicePageContent />
    </Suspense>
  )
}


