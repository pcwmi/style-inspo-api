import { notFound } from 'next/navigation'
import Link from 'next/link'
import type { Metadata } from 'next'
import { getVerdict, getAllVerdictPaths } from '@/lib/verdicts'

interface Params {
  params: Promise<{ brand: string; slug: string }>
}

const SMS_NUMBER = process.env.NEXT_PUBLIC_SMS_NUMBER || ''
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export async function generateStaticParams() {
  return getAllVerdictPaths()
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { brand, slug } = await params
  const v = getVerdict(brand, slug)
  if (!v) return { title: 'Verdict not found' }

  const title = `Should You Buy the ${v.brand} ${v.item}? An Honest Verdict`
  const description = v.pull_quote
  const ogUrl = `${SITE_URL}/verdict/${brand}/${slug}/opengraph-image`

  return {
    title,
    description,
    alternates: { canonical: `${SITE_URL}/verdict/${brand}/${slug}` },
    openGraph: {
      title,
      description,
      url: `${SITE_URL}/verdict/${brand}/${slug}`,
      images: [{ url: ogUrl, width: 1200, height: 1800 }],
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [ogUrl],
    },
    other: {
      // Pinterest hint — use the tall OG image as the saved pin
      'pinterest-rich-pin': 'true',
    },
  }
}

const verdictColor: Record<string, string> = {
  BUY: 'bg-emerald-50 border-emerald-200 text-emerald-900',
  PASS: 'bg-rose-50 border-rose-200 text-rose-900',
  MAYBE: 'bg-amber-50 border-amber-200 text-amber-900',
}

export default async function VerdictPage({ params }: Params) {
  const { brand, slug } = await params
  const v = getVerdict(brand, slug)
  if (!v) notFound()

  const smsHref = SMS_NUMBER
    ? `sms:${SMS_NUMBER}?body=${encodeURIComponent(`Should I buy the ${v.brand} ${v.item}?`)}`
    : ''

  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Review',
    itemReviewed: {
      '@type': 'Product',
      name: `${v.brand} ${v.item}`,
      brand: { '@type': 'Brand', name: v.brand },
      offers: {
        '@type': 'Offer',
        price: v.price_usd,
        priceCurrency: 'USD',
      },
    },
    author: { '@type': 'Organization', name: 'Style Inspo' },
    description: v.pull_quote,
    datePublished: v.last_updated,
  }

  return (
    <div className="min-h-screen bg-bone">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd) }}
      />

      <article className="max-w-2xl mx-auto px-5 py-8 md:py-14">
        <Link href="/verdict" className="text-terracotta text-sm mb-6 inline-block">
          &larr; All verdicts
        </Link>

        <p className="text-muted text-xs uppercase tracking-wide mb-2">
          {v.category} · ${v.price_usd}
        </p>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight mb-3">
          Should you buy the {v.brand} {v.item}?
        </h1>
        <p className="text-ink/80 text-base md:text-lg leading-relaxed mb-2">
          {v.one_line_summary}
        </p>
        <p className="text-muted text-sm md:text-base italic mb-8">
          Energy: {v.energy}
        </p>

        <blockquote className="border-l-4 border-terracotta pl-4 py-2 mb-10 text-ink/90 text-base md:text-lg leading-relaxed">
          {v.pull_quote}
        </blockquote>

        <h2 className="text-xl md:text-2xl font-semibold mb-4">Verdict by style archetype</h2>
        <div className="space-y-3 mb-12">
          {v.verdicts.map((va, i) => (
            <div
              key={i}
              className={`border rounded-lg p-4 md:p-5 ${verdictColor[va.verdict] || 'bg-white border-gray-200'}`}
            >
              <div className="flex items-baseline justify-between gap-3 mb-1">
                <p className="font-medium text-sm md:text-base">{va.archetype}</p>
                <p className="font-bold text-base md:text-lg">{va.verdict}</p>
              </div>
              <p className="text-xs md:text-sm uppercase tracking-wide opacity-70 mb-2">
                {va.label}
              </p>
              <p className="text-sm md:text-base leading-relaxed">{va.reasoning}</p>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <div>
            <h3 className="font-semibold mb-2 text-base">Why people love it</h3>
            <ul className="space-y-2 text-sm md:text-base text-ink/80 leading-relaxed">
              {v.why_people_love_it.map((p, i) => (
                <li key={i} className="pl-4 relative">
                  <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-2 text-base">Where it falls flat</h3>
            <ul className="space-y-2 text-sm md:text-base text-ink/80 leading-relaxed">
              {v.where_it_falls_flat.map((p, i) => (
                <li key={i} className="pl-4 relative">
                  <span className="absolute left-0 top-1.5 w-1.5 h-1.5 bg-rose-500 rounded-full" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {v.affiliate_url && (
          <a
            href={v.affiliate_url}
            target="_blank"
            rel="sponsored noopener"
            className="block w-full bg-terracotta text-white text-center py-4 px-6 rounded-lg font-medium mb-10 hover:opacity-90"
          >
            Shop {v.brand} {v.item} — ${v.price_usd}
          </a>
        )}

        <h2 className="text-xl md:text-2xl font-semibold mb-4">Better in your style</h2>
        <div className="space-y-4 mb-12">
          {v.alternatives.map((alt, i) => (
            <div key={i} className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-5">
              <p className="text-muted text-xs uppercase tracking-wide mb-1">
                If you lean {alt.if_you_lean}
              </p>
              <p className="font-semibold text-base md:text-lg mb-1">
                {alt.name} <span className="text-muted text-sm font-normal">— ${alt.price_usd}</span>
              </p>
              <p className="text-sm md:text-base text-ink/80 leading-relaxed mb-3">
                {alt.reasoning}
              </p>
              {alt.url && (
                <a
                  href={alt.url}
                  target="_blank"
                  rel="sponsored noopener"
                  className="inline-block text-terracotta text-sm font-medium hover:opacity-80"
                >
                  Shop {alt.name} →
                </a>
              )}
            </div>
          ))}
        </div>

        <div className="bg-ink text-white rounded-xl p-6 md:p-8 text-center">
          <h3 className="text-xl md:text-2xl font-semibold mb-2">
            Want a personal verdict on something you're considering?
          </h3>
          <p className="text-white/80 text-sm md:text-base mb-5 leading-relaxed">
            Send the item plus a few signals about your style. Personal buy / pass within 24
            hours. $10. Refund if we don't deliver.
          </p>
          <Link
            href="/offer"
            className="inline-block bg-white text-ink px-6 py-3 rounded-lg font-medium hover:opacity-90"
          >
            Get my verdict — $10 &rarr;
          </Link>
          {smsHref && (
            <div className="mt-4">
              <a
                href={smsHref}
                className="text-white/70 text-sm underline hover:text-white"
              >
                Or text us a quick free question
              </a>
            </div>
          )}
        </div>

        <p className="text-muted text-xs mt-10 leading-relaxed">
          Last updated {v.last_updated}. Some links are affiliate links — Style Inspo may earn a
          small commission if you buy through them. The verdict is the same either way.
        </p>
      </article>
    </div>
  )
}
