'use client'

import Link from 'next/link'
import { useState } from 'react'

function ShowcaseImage({ src, alt, priority }: { src: string; alt: string; priority?: boolean }) {
  const [hasError, setHasError] = useState(false)

  if (hasError) {
    return (
      <div className="w-full h-full bg-sand/30 flex items-center justify-center">
        <p className="text-muted/40 text-sm text-center px-4">{alt}</p>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      className="w-full h-full object-cover object-top"
      onError={() => setHasError(true)}
      loading={priority ? 'eager' : 'lazy'}
    />
  )
}

export function ShowcaseLanding() {
  return (
    <div className="min-h-screen bg-bone">
      {/* Hero Section */}
      <div className="max-w-3xl mx-auto px-4 pt-12 md:pt-20 pb-8 md:pb-12">
        <div className="text-center mb-8 md:mb-10">
          <h1 className="text-3xl md:text-5xl mb-4 tracking-tight">Style Inspo</h1>
          <p className="text-muted text-lg md:text-xl leading-relaxed max-w-2xl mx-auto">
            AI that knows your wardrobe, learns your taste, and helps you get dressed with confidence
          </p>
        </div>

        {/* Hero Carousel */}
        <div className="relative w-full mb-6 md:mb-8 -mx-4 px-4 md:mx-0 md:px-0 overflow-x-auto md:overflow-visible hide-scrollbar">
          <div className="flex gap-3 w-max md:grid md:grid-cols-3 md:gap-4 md:w-full">
            {[
              { src: '/showcase/hero-outfit-1.png', alt: 'Blazer and bow tee outfit with Runway visualization' },
              { src: '/showcase/hero-outfit-2.png', alt: 'Grey sweater and denim skirt outfit with Runway visualization' },
              { src: '/showcase/hero-outfit-3.png', alt: 'Teal jumpsuit and floral heels outfit with Runway visualization' },
            ].map((item, i) => (
              <div key={i} className="shrink-0 w-[260px] md:w-auto">
                <div className="bg-white rounded-xl shadow-lg border border-[rgba(26,22,20,0.08)] overflow-hidden">
                  <div className="aspect-[4/5]">
                    <ShowcaseImage
                      src={item.src}
                      alt={item.alt}
                      priority={i === 0}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Primary CTA */}
        <div className="max-w-md mx-auto mb-16 md:mb-20">
          <Link
            href="/get-started"
            className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
          >
            Get Started
          </Link>
        </div>
      </div>

      {/* Capability Cards */}
      <div className="bg-white border-y border-[rgba(26,22,20,0.06)]">
        <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
          <h2 className="text-center text-2xl md:text-3xl mb-10 md:mb-14">How it works</h2>

          <div className="space-y-12 md:space-y-16">
            {/* Card 1: Text your closet */}
            <div className="md:flex md:items-center md:gap-10">
              <div className="md:w-1/2 mb-6 md:mb-0">
                <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                  <div className="aspect-[4/5]">
                    <ShowcaseImage
                      src="/showcase/sms-flow.png"
                      alt="SMS conversation showing outfit request and response"
                    />
                  </div>
                </div>
              </div>
              <div className="md:w-1/2">
                <h3 className="text-xl md:text-2xl mb-3">Text your closet</h3>
                <p className="text-muted text-base leading-relaxed mb-0">
                  Text a request, get a styled outfit back in 21 seconds. AI matches items from your actual wardrobe and sends a photo collage via SMS.
                </p>
              </div>
            </div>

            {/* Card 2: See it styled */}
            <div className="md:flex md:items-center md:gap-10 md:flex-row-reverse">
              <div className="md:w-1/2 mb-6 md:mb-0">
                <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                  <div className="aspect-[4/5]">
                    <ShowcaseImage
                      src="/showcase/visualization.png"
                      alt="AI visualization showing outfit on a model"
                    />
                  </div>
                </div>
              </div>
              <div className="md:w-1/2">
                <h3 className="text-xl md:text-2xl mb-3">See it styled</h3>
                <p className="text-muted text-base leading-relaxed mb-0">
                  AI generates how the outfit looks on a relatable model using Runway Gen-4. See the full look before you open your closet.
                </p>
              </div>
            </div>

            {/* Card 3: Your closet, organized */}
            <div className="md:flex md:items-center md:gap-10">
              <div className="md:w-1/2 mb-6 md:mb-0">
                <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                  <div className="aspect-[4/5]">
                    <ShowcaseImage
                      src="/showcase/wardrobe.png"
                      alt="Wardrobe grid showing uploaded clothing items"
                    />
                  </div>
                </div>
              </div>
              <div className="md:w-1/2">
                <h3 className="text-xl md:text-2xl mb-3">Your closet, organized</h3>
                <p className="text-muted text-base leading-relaxed mb-0">
                  Upload your clothes. AI analyzes each piece — colors, style, category — and learns your taste over time through feedback.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Social Proof */}
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <div className="max-w-xl mx-auto space-y-8">
          <blockquote className="text-center">
            <p className="text-lg md:text-xl font-serif italic text-ink leading-relaxed">
              &ldquo;It reminded me of clothes I forgot I had&rdquo;
            </p>
          </blockquote>
          <blockquote className="text-center">
            <p className="text-lg md:text-xl font-serif italic text-ink leading-relaxed">
              &ldquo;I dreamt about it after my first session&rdquo;
            </p>
          </blockquote>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="bg-white border-t border-[rgba(26,22,20,0.06)]">
        <div className="max-w-md mx-auto px-4 py-12 md:py-16 text-center">
          <h2 className="text-2xl md:text-3xl mb-4">Ready to get styled?</h2>
          <p className="text-muted text-base mb-8 leading-relaxed">
            Upload a few pieces from your closet. AI does the rest.
          </p>
          <Link
            href="/get-started"
            className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
          >
            Get Started
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-[rgba(26,22,20,0.06)] py-8">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <p className="text-sm text-muted">
            Built by{' '}
            <a
              href="https://www.linkedin.com/in/peichin/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-terracotta hover:underline"
            >
              Pei-Chin
            </a>
          </p>
          <p className="text-xs text-muted/60 mt-2">
            FastAPI &middot; Next.js &middot; GPT-5.2 &middot; Runway Gen-4
          </p>
        </div>
      </footer>
    </div>
  )
}
