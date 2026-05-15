import Link from 'next/link'
import type { Metadata } from 'next'
import { getAllVerdicts, type Verdict } from '@/lib/verdicts'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export const metadata: Metadata = {
  title: 'Launch Kit — Internal',
  robots: { index: false, follow: false },
}

function pinDescription(v: Verdict): string {
  // Pinterest favors 200-500 char descriptions with keywords up front.
  const tags = v.tags.map(t => '#' + t.replace(/-/g, '')).join(' ')
  const verdictCounts = `${v.verdicts.filter(x => x.verdict === 'BUY').length} BUY · ${v.verdicts.filter(x => x.verdict === 'MAYBE').length} MAYBE · ${v.verdicts.filter(x => x.verdict === 'PASS').length} PASS`
  return `Should you buy the ${v.brand} ${v.item}? An honest verdict for $${v.price_usd}. We judge it across 4 style archetypes (${verdictCounts}) so you find out if it's actually for you — not just for everyone. Plus 3 alternatives in your style. ${tags}`.slice(0, 480)
}

function pinTitle(v: Verdict): string {
  // Pinterest title: <= 100 chars, leads with the searched query.
  return `Should you buy the ${v.brand} ${v.item}? Honest verdict ($${v.price_usd})`.slice(0, 100)
}

function tweetThread(v: Verdict): string[] {
  const buy = v.verdicts.find(x => x.verdict === 'BUY')
  const pass = v.verdicts.find(x => x.verdict === 'PASS')
  const url = `${SITE_URL}/verdict/${v.brand_slug}/${v.item_slug}`
  return [
    `Should you buy the ${v.brand} ${v.item}?\n\nHonest verdict — not paid placement, not generic praise. Reasoning below 👇`,
    `The pull quote:\n"${v.pull_quote}"`,
    buy ? `BUY if you lean ${buy.archetype}:\n${buy.reasoning}` : '',
    pass ? `PASS if you lean ${pass.archetype}:\n${pass.reasoning}` : '',
    `Full verdict + 3 alternatives in your style: ${url}`,
  ].filter(Boolean)
}

const SKIMLINKS_BIO = `Style Inspo publishes honest, identity-tuned product verdicts for fashion buyers. Each page judges a specific item (e.g. AGOLDE 90s Pinch Waist Jean, Loewe Puzzle Bag, Frankie Shop Bea Cardigan) across four style archetypes — buy / pass / maybe — with three alternatives per piece. The site is editorial, no paid placements, monetized through affiliate links on alternatives. Audience: women 25-45 considering specific purchases. Currently 18 verdicts, growing weekly. URL: ${SITE_URL}`

const AWIN_BIO = `Style Inspo is an editorial site publishing honest "Should you buy this?" verdicts on specific fashion items. Each verdict judges one piece across four reader archetypes (e.g. easy/polished/petite/oversized), gives a BUY/PASS/MAYBE verdict per archetype, and recommends three alternatives. Categories: denim, dresses, knitwear, sneakers, bags, trousers, activewear, outerwear. Target audience: 25-45-year-old women in the US, UK, Australia making purchase decisions in the $100-$500 range. Traffic is from Pinterest and organic Google search. Currently 18 verdicts, publishing 5-10 new pieces weekly. We would feature your brand's pieces in alternative-recommendation slots when they fit the reader profile being addressed. URL: ${SITE_URL}/verdict`

const AMAZON_BIO = `Editorial site publishing fashion product verdicts. We compare specific items across reader style archetypes and recommend alternatives — including Amazon Fashion alternatives where they fit (e.g. CRZ Yoga as a Lululemon Align dupe, Universal Thread as a Birkenstock Boston dupe). 18 verdict pages live, growing weekly. Pinterest + organic search traffic. Affiliate links would be placed in clearly-disclosed alternative-recommendation contexts.`

const SUBSTACK_OUTREACH = `Subject: A free tool you might want to recommend to your readers

Hi [name],

I read [their newsletter] — really enjoyed the recent piece on [specific topic].

I run Style Inspo, a small editorial site that publishes "Should you buy this?" verdicts on specific fashion items (Frankie Shop Bea Cardigan, AGOLDE 90s, Loewe Puzzle, etc.). Each verdict judges the piece across four style archetypes — so a reader who reads it learns whether it's for *them*, not just whether it's "good."

Two reasons I'm reaching out:

1. If a piece in any upcoming newsletter is on something we've already verdicted, you're welcome to quote / link us — most newsletters paywall this kind of opinion and ours is free.

2. If there's a specific item your readers have been asking you about, send it over and I'll write a verdict for it. Free. No strings.

The site: ${SITE_URL}/verdict

[your name]`

export default function LaunchKitPage() {
  const verdicts = getAllVerdicts()

  return (
    <div className="min-h-screen bg-bone">
      <div className="max-w-3xl mx-auto px-5 py-10">
        <Link href="/" className="text-terracotta text-sm mb-6 inline-block">
          &larr; Style Inspo
        </Link>

        <h1 className="text-3xl md:text-4xl font-bold mb-2">Launch Kit</h1>
        <p className="text-muted mb-2 text-sm">Internal — not indexed.</p>
        <p className="text-ink/80 mb-10 leading-relaxed">
          Everything you need to copy-paste to activate. {verdicts.length} verdicts live. Each
          section is grouped by the destination (Pinterest, affiliate apps, outreach).
        </p>

        {/* --- ACTIVATION CHECKLIST --- */}
        <section className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 mb-10">
          <h2 className="text-xl font-semibold mb-4">Activation checklist</h2>
          <ol className="space-y-3 text-sm leading-relaxed list-decimal list-inside text-ink/85">
            <li>
              Stripe Payment Link, $10 — name it "Personal Style Verdict — Style Inspo" at{' '}
              <a href="https://dashboard.stripe.com/payment-links" target="_blank" rel="noopener" className="text-terracotta underline">
                dashboard.stripe.com/payment-links
              </a>
            </li>
            <li>
              Vercel env vars: <code className="bg-sand/40 px-1 rounded">NEXT_PUBLIC_OFFER_URL</code>{' '}
              (your Stripe link), <code className="bg-sand/40 px-1 rounded">NEXT_PUBLIC_SITE_URL</code>{' '}
              (your domain), <code className="bg-sand/40 px-1 rounded">NEXT_PUBLIC_SMS_NUMBER</code>{' '}
              (your Twilio number)
            </li>
            <li>Redeploy frontend</li>
            <li>
              Pinterest business account → claim domain → install conversion tag (optional but
              useful for analytics)
            </li>
            <li>
              Apply to affiliate networks: Skimlinks (
              <a href="https://skimlinks.com" target="_blank" rel="noopener" className="text-terracotta underline">skimlinks.com</a>
              ), Awin (
              <a href="https://www.awin.com/us/publishers" target="_blank" rel="noopener" className="text-terracotta underline">awin.com</a>
              ), Amazon Associates (
              <a href="https://affiliate-program.amazon.com" target="_blank" rel="noopener" className="text-terracotta underline">affiliate-program.amazon.com</a>
              ). Bios below.
            </li>
            <li>
              Use the per-verdict blocks below — pin all {verdicts.length} verdicts across 3 days
              (5-7/day, not all at once)
            </li>
          </ol>
        </section>

        {/* --- AFFILIATE APP BIOS --- */}
        <section className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 mb-10">
          <h2 className="text-xl font-semibold mb-4">Affiliate-network application bios</h2>

          <div className="space-y-6">
            <div>
              <h3 className="font-semibold mb-2 text-base">Skimlinks "About your site"</h3>
              <pre className="bg-sand/30 text-xs leading-relaxed p-4 rounded whitespace-pre-wrap font-sans">{SKIMLINKS_BIO}</pre>
            </div>

            <div>
              <h3 className="font-semibold mb-2 text-base">Awin "Site description"</h3>
              <pre className="bg-sand/30 text-xs leading-relaxed p-4 rounded whitespace-pre-wrap font-sans">{AWIN_BIO}</pre>
            </div>

            <div>
              <h3 className="font-semibold mb-2 text-base">Amazon Associates "Website description"</h3>
              <pre className="bg-sand/30 text-xs leading-relaxed p-4 rounded whitespace-pre-wrap font-sans">{AMAZON_BIO}</pre>
            </div>
          </div>
        </section>

        {/* --- OUTREACH EMAIL --- */}
        <section className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 mb-10">
          <h2 className="text-xl font-semibold mb-4">Substack/newsletter outreach template</h2>
          <p className="text-muted text-sm mb-3">
            Free distribution leverage. Find 10 fashion Substacks under 5k subs. Send this. Aim for
            1-2 mentions; each is worth ~50-200 verdict-page visits.
          </p>
          <pre className="bg-sand/30 text-xs leading-relaxed p-4 rounded whitespace-pre-wrap font-sans">{SUBSTACK_OUTREACH}</pre>
        </section>

        {/* --- PER-VERDICT PIN KIT --- */}
        <section className="mb-10">
          <h2 className="text-xl font-semibold mb-4">Per-verdict pin kit</h2>
          <p className="text-muted text-sm mb-6">
            For each verdict: pin title (paste into Pinterest title), pin description (paste into
            description), and the one-click pin builder URL. The image is auto-fetched by Pinterest
            from the page.
          </p>

          <div className="space-y-6">
            {verdicts.map(v => {
              const url = `${SITE_URL}/verdict/${v.brand_slug}/${v.item_slug}`
              const media = `${url}/opengraph-image`
              const pinUrl = `https://www.pinterest.com/pin-builder/?${new URLSearchParams({
                url,
                media,
                description: pinDescription(v),
              })}`

              return (
                <div
                  key={`${v.brand_slug}-${v.item_slug}`}
                  className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-5"
                >
                  <div className="flex items-baseline justify-between mb-3">
                    <p className="font-semibold text-base">
                      {v.brand} {v.item} <span className="text-muted font-normal">— ${v.price_usd}</span>
                    </p>
                    <a
                      href={pinUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs bg-terracotta text-white px-3 py-1 rounded font-medium"
                    >
                      Open Pinterest pin builder &rarr;
                    </a>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 text-xs">
                    <div>
                      <p className="text-muted uppercase tracking-wide mb-1">Pin title</p>
                      <pre className="bg-sand/30 p-3 rounded whitespace-pre-wrap font-sans leading-relaxed">{pinTitle(v)}</pre>
                    </div>
                    <div>
                      <p className="text-muted uppercase tracking-wide mb-1">Page URL</p>
                      <pre className="bg-sand/30 p-3 rounded whitespace-pre-wrap font-sans leading-relaxed break-all">{url}</pre>
                    </div>
                  </div>

                  <div className="mt-3 text-xs">
                    <p className="text-muted uppercase tracking-wide mb-1">Pin description</p>
                    <pre className="bg-sand/30 p-3 rounded whitespace-pre-wrap font-sans leading-relaxed">{pinDescription(v)}</pre>
                  </div>

                  <details className="mt-3 text-xs">
                    <summary className="cursor-pointer text-muted uppercase tracking-wide hover:text-ink">
                      Twitter/X thread (5 tweets)
                    </summary>
                    <div className="mt-2 space-y-2">
                      {tweetThread(v).map((tweet, i) => (
                        <pre
                          key={i}
                          className="bg-sand/30 p-3 rounded whitespace-pre-wrap font-sans leading-relaxed"
                        >
                          {i + 1}/{tweetThread(v).length} — {tweet}
                        </pre>
                      ))}
                    </div>
                  </details>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}
