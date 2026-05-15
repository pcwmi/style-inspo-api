import Link from 'next/link'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import {
  getListicle,
  getAllListiclePaths,
  resolveEntries,
} from '@/lib/listicles'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

interface Params {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  return getAllListiclePaths()
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params
  const l = getListicle(slug)
  if (!l) return { title: 'List not found' }

  const ogUrl = `${SITE_URL}/best/${slug}/opengraph-image`
  return {
    title: l.title,
    description: l.headline,
    alternates: { canonical: `${SITE_URL}/best/${slug}` },
    openGraph: {
      title: l.title,
      description: l.headline,
      url: `${SITE_URL}/best/${slug}`,
      images: [{ url: ogUrl, width: 1200, height: 1800 }],
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title: l.title,
      description: l.headline,
      images: [ogUrl],
    },
  }
}

export default async function BestPage({ params }: Params) {
  const { slug } = await params
  const l = getListicle(slug)
  if (!l) notFound()
  const entries = resolveEntries(l)

  const itemListJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: l.title,
    description: l.headline,
    numberOfItems: entries.length,
    itemListElement: entries.map((e, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: `${e.verdict.brand} ${e.verdict.item}`,
      url: `${SITE_URL}/verdict/${e.verdict.brand_slug}/${e.verdict.item_slug}`,
    })),
  }

  return (
    <div className="min-h-screen bg-bone">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListJsonLd) }}
      />
      <article className="max-w-2xl mx-auto px-5 py-8 md:py-14">
        <Link href="/best" className="text-terracotta text-sm mb-6 inline-block">
          &larr; All buying guides
        </Link>

        <p className="text-muted text-xs uppercase tracking-wide mb-2">Buying guide · {l.category}</p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-3">{l.title}</h1>
        <p className="text-ink/85 text-base md:text-lg leading-relaxed mb-3">{l.headline}</p>
        <p className="text-ink/70 text-sm md:text-base leading-relaxed mb-10">{l.lede}</p>

        <h2 className="text-xl md:text-2xl font-semibold mb-4">The picks</h2>
        <div className="space-y-5 mb-12">
          {entries.map((e, i) => (
            <Link
              key={i}
              href={`/verdict/${e.verdict.brand_slug}/${e.verdict.item_slug}`}
              className="block bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5 md:p-6 hover:border-terracotta transition"
            >
              <p className="text-muted text-xs uppercase tracking-wide mb-1">
                {e.verdict.brand} · ${e.verdict.price_usd} · #{i + 1}
              </p>
              <p className="font-semibold text-lg md:text-xl mb-2">{e.verdict.item}</p>
              <p className="text-terracotta text-sm md:text-base mb-2 font-medium">
                {e.best_for}
              </p>
              <p className="text-ink/80 text-sm md:text-base leading-relaxed">{e.summary}</p>
              <p className="text-terracotta text-sm mt-3 font-medium">
                Full verdict + 3 alternatives &rarr;
              </p>
            </Link>
          ))}
        </div>

        <h2 className="text-xl md:text-2xl font-semibold mb-4">How to pick the right one</h2>
        <div className="space-y-3 mb-12">
          {l.how_to_pick.map((p, i) => (
            <div
              key={i}
              className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-5"
            >
              <p className="text-muted text-xs uppercase tracking-wide mb-1">If you lean</p>
              <p className="font-medium text-base mb-1">{p.if_you_lean}</p>
              <p className="text-ink/80 text-sm md:text-base leading-relaxed">{p.pick}</p>
            </div>
          ))}
        </div>

        <h2 className="text-xl md:text-2xl font-semibold mb-4">Honest caveats</h2>
        <ul className="space-y-2 text-sm md:text-base text-ink/80 leading-relaxed mb-12">
          {l.honest_caveats.map((c, i) => (
            <li key={i} className="pl-4 relative">
              <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-terracotta rounded-full" />
              {c}
            </li>
          ))}
        </ul>

        <p className="text-muted text-xs leading-relaxed">
          Last updated {l.last_updated}. Some links earn affiliate commissions — we'd make the same
          picks without them, and the full reasoning (including what each piece does badly) is on
          the individual verdict pages.
        </p>
      </article>
    </div>
  )
}
