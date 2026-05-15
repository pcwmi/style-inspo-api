import Link from 'next/link'
import type { Metadata } from 'next'
import { getAllVerdicts } from '@/lib/verdicts'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export const metadata: Metadata = {
  title: 'Should You Buy This? — Honest Verdicts for Real Wardrobes',
  description:
    'Identity-tuned buy/pass verdicts on the items you are considering. No paid placements, no generic praise — just an opinion you can act on.',
  alternates: { canonical: `${SITE_URL}/verdict` },
}

export default function VerdictIndex() {
  const verdicts = getAllVerdicts()

  return (
    <div className="min-h-screen bg-bone">
      <div className="max-w-3xl mx-auto px-5 py-10 md:py-16">
        <Link href="/" className="text-terracotta text-sm mb-6 inline-block">
          &larr; Style Inspo
        </Link>

        <h1 className="text-3xl md:text-5xl font-bold leading-tight mb-3">
          Should you buy this?
        </h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-10 max-w-xl">
          Honest, identity-tuned verdicts on the things you are considering. Every piece judged
          across 4 style archetypes — so you find out if it is actually for you, not just for
          everyone.
        </p>

        {verdicts.length === 0 ? (
          <p className="text-muted">No verdicts yet.</p>
        ) : (
          <div className="space-y-3">
            {verdicts.map(v => (
              <Link
                key={`${v.brand_slug}-${v.item_slug}`}
                href={`/verdict/${v.brand_slug}/${v.item_slug}`}
                className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 hover:border-terracotta transition"
              >
                <p className="text-muted text-xs uppercase tracking-wide mb-1">
                  {v.brand} · {v.category} · ${v.price_usd}
                </p>
                <p className="font-semibold text-lg md:text-xl mb-1">
                  Should you buy the {v.item}?
                </p>
                <p className="text-ink/70 text-sm md:text-base leading-relaxed">
                  {v.one_line_summary}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
