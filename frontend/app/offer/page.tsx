'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { posthog } from '@/lib/posthog'

const OFFER_URL = process.env.NEXT_PUBLIC_OFFER_URL || ''
const OFFER_PRICE = process.env.NEXT_PUBLIC_OFFER_PRICE || '$10'
const OFFER_HEADLINE =
  process.env.NEXT_PUBLIC_OFFER_HEADLINE || 'I will style one outfit from your closet.'
const OFFER_SUBLINE =
  process.env.NEXT_PUBLIC_OFFER_SUBLINE ||
  'Send 5–10 photos of clothes you own. I send back one curated outfit and the reasoning behind it — what works, why it works, the energy it carries.'

function OfferContent() {
  const ready = Boolean(OFFER_URL)

  const handleClick = () => {
    posthog.capture('offer_clicked', { offer_url: OFFER_URL, price: OFFER_PRICE })
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-xl mx-auto px-5 py-10 md:py-16">
        <Link href="/" className="text-terracotta text-sm mb-6 inline-block min-h-[44px] flex items-center">
          &larr; Style Inspo
        </Link>

        <p className="text-muted text-sm uppercase tracking-wide mb-3">
          One-time offer · {OFFER_PRICE}
        </p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-4">
          {OFFER_HEADLINE}
        </h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-8">
          {OFFER_SUBLINE}
        </p>

        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 mb-8 shadow-sm">
          <p className="font-medium text-ink mb-3">How it works</p>
          <ol className="space-y-3 text-ink/80 text-sm md:text-base leading-relaxed list-decimal list-inside">
            <li>You pay {OFFER_PRICE} and leave your email at checkout.</li>
            <li>I email you within an hour asking for 5–10 closet photos.</li>
            <li>Within 24 hours: one outfit, photographed-style, with the reasoning.</li>
          </ol>
        </div>

        {ready ? (
          <a
            href={OFFER_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleClick}
            className="block w-full bg-terracotta text-white text-center py-4 px-6 rounded-lg font-medium text-base hover:opacity-90 transition active:opacity-80 min-h-[52px] flex items-center justify-center"
          >
            Pay {OFFER_PRICE} and start
          </a>
        ) : (
          <div className="bg-sand/40 border border-[rgba(26,22,20,0.12)] rounded-lg p-5 text-sm text-ink/70 leading-relaxed">
            <p className="font-medium mb-1">Checkout not yet live.</p>
            <p>
              Set <code className="px-1 py-0.5 bg-white rounded">NEXT_PUBLIC_OFFER_URL</code> in
              Vercel to your Stripe Payment Link, then redeploy. The page will activate.
            </p>
          </div>
        )}

        <p className="text-muted text-xs mt-6 leading-relaxed">
          Built on top of Style Inspo, an AI personal styling tool that reasons about your existing
          closet. The deliverable is human-in-the-loop — me + the tool.
        </p>
      </div>
    </div>
  )
}

export default function OfferPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bone" />}>
      <OfferContent />
    </Suspense>
  )
}
