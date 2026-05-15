import Link from 'next/link'
import type { Metadata } from 'next'
import { getAllListicles } from '@/lib/listicles'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export const metadata: Metadata = {
  title: 'Buying Guides — Style Inspo',
  description:
    'Honest, identity-tuned buying guides for the most-considered fashion categories. Find the right pick for who you are, not for everyone.',
  alternates: { canonical: `${SITE_URL}/best` },
}

export default function BestIndex() {
  const listicles = getAllListicles()
  return (
    <div className="min-h-screen bg-bone">
      <div className="max-w-3xl mx-auto px-5 py-10 md:py-16">
        <Link href="/" className="text-terracotta text-sm mb-6 inline-block">
          &larr; Style Inspo
        </Link>
        <h1 className="text-3xl md:text-5xl font-bold leading-tight mb-3">Buying guides</h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-10 max-w-xl">
          The right pick depends on who's asking. Each guide gives you 3 honest picks across
          archetypes — not a generic best-of, not paid placement.
        </p>
        {listicles.length === 0 ? (
          <p className="text-muted">No guides yet.</p>
        ) : (
          <div className="space-y-3">
            {listicles.map(l => (
              <Link
                key={l.slug}
                href={`/best/${l.slug}`}
                className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 hover:border-terracotta transition"
              >
                <p className="text-muted text-xs uppercase tracking-wide mb-1">{l.category}</p>
                <p className="font-semibold text-lg md:text-xl mb-1">{l.title}</p>
                <p className="text-ink/70 text-sm md:text-base leading-relaxed">{l.headline}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
