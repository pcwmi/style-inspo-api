'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { posthog } from '@/lib/posthog'

const OFFER_URL = process.env.NEXT_PUBLIC_OFFER_URL || ''
const OFFER_PRICE = process.env.NEXT_PUBLIC_OFFER_PRICE || '$10'
const SMS_NUMBER = process.env.NEXT_PUBLIC_SMS_NUMBER || ''

function OfferContent() {
  const ready = Boolean(OFFER_URL)

  const handleClick = () => {
    posthog.capture('offer_clicked', { offer_url: OFFER_URL, price: OFFER_PRICE })
  }

  const handleTextClick = () => {
    posthog.capture('offer_text_clicked', { sms_number: SMS_NUMBER })
  }

  const smsHref = SMS_NUMBER
    ? `sms:${SMS_NUMBER}?body=${encodeURIComponent('Should I buy this? ')}`
    : ''

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-xl mx-auto px-5 py-10 md:py-16">
        <Link href="/verdict" className="text-terracotta text-sm mb-6 inline-block min-h-[44px] flex items-center">
          &larr; All verdicts
        </Link>

        <p className="text-muted text-sm uppercase tracking-wide mb-3">
          Personal verdict · {OFFER_PRICE} · turnaround under 24 hours
        </p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-4">
          Should you buy <span className="italic">that</span> specific thing?
        </h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-8">
          Send a screenshot or link of the item you're considering, plus a few signals about
          your style. You get back a personal buy / pass / wait verdict — grounded in your
          taste, not generic praise — within 24 hours.
        </p>

        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 mb-8 shadow-sm">
          <p className="font-medium text-ink mb-3">How it works</p>
          <ol className="space-y-3 text-ink/80 text-sm md:text-base leading-relaxed list-decimal list-inside">
            <li>Pay {OFFER_PRICE} and leave your email at checkout.</li>
            <li>
              Within an hour, I email you for three things: the item link / screenshot, 2-3
              outfits you've saved that feel like &quot;you,&quot; and what doesn't work for you.
            </li>
            <li>
              Within 24 hours: a personal verdict + (if it's a pass) one alternative in your
              taste that won't end up in the donate pile.
            </li>
          </ol>
        </div>

        <div className="bg-sand/30 border border-[rgba(26,22,20,0.08)] rounded-lg p-5 md:p-6 mb-8">
          <p className="font-medium text-ink mb-3">Why this is worth {OFFER_PRICE}</p>
          <ul className="space-y-2 text-ink/80 text-sm md:text-base leading-relaxed">
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              The piece you're considering is usually $50-$500. One returned mistake pays this back many times over.
            </li>
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              Most &quot;style advice&quot; you can find for free is paid placement. This isn't.
            </li>
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              Built on the AI styling tool you can see in action across our <Link href="/verdict" className="text-terracotta underline">public verdicts</Link>. You're getting that, tuned to you.
            </li>
          </ul>
        </div>

        {ready ? (
          <a
            href={OFFER_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleClick}
            className="block w-full bg-terracotta text-white text-center py-4 px-6 rounded-lg font-medium text-base hover:opacity-90 transition active:opacity-80 min-h-[52px] flex items-center justify-center"
          >
            Get my verdict — {OFFER_PRICE}
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

        {smsHref && (
          <a
            href={smsHref}
            onClick={handleTextClick}
            className="block text-center text-terracotta hover:text-terracotta/80 text-sm md:text-base mt-4 py-2 min-h-[44px] flex items-center justify-center"
          >
            Or text us a quick question first &rarr;
          </a>
        )}

        <p className="text-muted text-xs mt-6 leading-relaxed">
          Personal verdicts are human-in-the-loop — me + the AI styling tool. Refund if I can't
          deliver within 48 hours.
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
