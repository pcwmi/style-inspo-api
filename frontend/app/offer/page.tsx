'use client'

import { Suspense } from 'react'
import Link from 'next/link'
import { posthog } from '@/lib/posthog'

const OFFER_URL = process.env.NEXT_PUBLIC_OFFER_URL || ''
const OFFER_PRICE = process.env.NEXT_PUBLIC_OFFER_PRICE || '$10'
const SMS_NUMBER = process.env.NEXT_PUBLIC_SMS_NUMBER || ''
const FREE_VERDICT_EMAIL = process.env.NEXT_PUBLIC_FREE_VERDICT_EMAIL || ''
const FREE_VERDICT_LIMIT = process.env.NEXT_PUBLIC_FREE_VERDICT_LIMIT || '10'

function OfferContent() {
  const paidReady = Boolean(OFFER_URL)
  const freeReady = Boolean(FREE_VERDICT_EMAIL)

  const handlePaidClick = () => {
    posthog.capture('offer_clicked', { offer_url: OFFER_URL, price: OFFER_PRICE })
  }

  const handleFreeClick = () => {
    posthog.capture('free_verdict_requested', { email: FREE_VERDICT_EMAIL })
  }

  const handleTextClick = () => {
    posthog.capture('offer_text_clicked', { sms_number: SMS_NUMBER })
  }

  const smsHref = SMS_NUMBER
    ? `sms:${SMS_NUMBER}?body=${encodeURIComponent('Should I buy this? ')}`
    : ''

  const freeEmailBody = `Hi —

I'd like a free style verdict. Here's the item I'm considering:

Item link or brand/name:
[paste here]

Optional: a screenshot or photo
[attach to this email]

To give me a useful verdict, here are a few signals about my style:

Three outfits I love (Instagram screenshots, Pinterest links, descriptions — whatever):
1.
2.
3.

One thing I tried recently that didn't feel like me, and why:


My usual price range for this category:


Thanks!`

  const freeHref = FREE_VERDICT_EMAIL
    ? `mailto:${FREE_VERDICT_EMAIL}?subject=${encodeURIComponent('Free verdict request — Style Inspo')}&body=${encodeURIComponent(freeEmailBody)}`
    : ''

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-xl mx-auto px-5 py-10 md:py-16">
        <Link href="/verdict" className="text-terracotta text-sm mb-6 inline-block min-h-[44px] flex items-center">
          &larr; All verdicts
        </Link>

        <p className="text-muted text-sm uppercase tracking-wide mb-3">
          Personal verdict · turnaround under 24 hours
        </p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-4">
          Should you buy <span className="italic">that</span> specific thing?
        </h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-8">
          Send a screenshot or link of the item you're considering, plus a few signals about
          your style. You get back a personal buy / pass / wait verdict — grounded in your
          taste, not generic praise — within 24 hours.
        </p>

        {/* --- FREE TRIAL CTA (primary) --- */}
        {freeReady && (
          <div className="bg-ink text-white rounded-xl p-6 md:p-8 mb-6">
            <p className="text-white/70 text-xs uppercase tracking-wide mb-3">
              Free this week · {FREE_VERDICT_LIMIT} slots
            </p>
            <h2 className="text-xl md:text-2xl font-semibold mb-3 leading-tight">
              Your first verdict is free. Reply within 24 hours.
            </h2>
            <p className="text-white/85 text-sm md:text-base leading-relaxed mb-5">
              Send one email with the item you're considering and a few notes about your taste.
              I write you back with a personal verdict. If it saves you from one bad purchase,
              you've already broken even. If it doesn't, you've lost nothing.
            </p>
            <a
              href={freeHref}
              onClick={handleFreeClick}
              className="inline-block bg-white text-ink px-6 py-3 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px]"
            >
              Get my free verdict &rarr;
            </a>
            <p className="text-white/60 text-xs mt-4">
              Opens your email client with everything pre-filled. Just hit send.
            </p>
          </div>
        )}

        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 mb-8 shadow-sm">
          <p className="font-medium text-ink mb-3">How it works</p>
          <ol className="space-y-3 text-ink/80 text-sm md:text-base leading-relaxed list-decimal list-inside">
            <li>You email the item link / screenshot + style signals.</li>
            <li>Within 24 hours: personal buy / pass / wait verdict.</li>
            <li>
              If you want more verdicts on other items, they're {OFFER_PRICE} each — sent via
              the link below.
            </li>
          </ol>
        </div>

        <div className="bg-sand/30 border border-[rgba(26,22,20,0.08)] rounded-lg p-5 md:p-6 mb-8">
          <p className="font-medium text-ink mb-3">Why this works</p>
          <ul className="space-y-2 text-ink/80 text-sm md:text-base leading-relaxed">
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              The piece you're considering is usually $50-$500. One mistake avoided pays this
              back many times over.
            </li>
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              Most "style advice" online is paid placement. This isn't.
            </li>
            <li className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              Built on the AI styling tool you can see in action across our{' '}
              <Link href="/verdict" className="text-terracotta underline">public verdicts</Link>.
              You're getting that, tuned to you.
            </li>
          </ul>
        </div>

        {/* --- PAID CTA (secondary, surfaced after free slots are exhausted or for return users) --- */}
        {paidReady ? (
          <a
            href={OFFER_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handlePaidClick}
            className="block w-full bg-terracotta text-white text-center py-4 px-6 rounded-lg font-medium text-base hover:opacity-90 transition active:opacity-80 min-h-[52px] flex items-center justify-center"
          >
            Or skip the queue — {OFFER_PRICE} for a guaranteed 24-hour verdict
          </a>
        ) : !freeReady ? (
          <div className="bg-sand/40 border border-[rgba(26,22,20,0.12)] rounded-lg p-5 text-sm text-ink/70 leading-relaxed">
            <p className="font-medium mb-1">Not yet configured.</p>
            <p>
              Set <code className="px-1 py-0.5 bg-white rounded">NEXT_PUBLIC_FREE_VERDICT_EMAIL</code>{' '}
              (your email) for the free-trial path, and/or{' '}
              <code className="px-1 py-0.5 bg-white rounded">NEXT_PUBLIC_OFFER_URL</code> (a Stripe
              Payment Link) for the paid path. Either alone is enough to activate this page.
            </p>
          </div>
        ) : null}

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
          Personal verdicts are human-in-the-loop — me + the AI styling tool.
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
