import { ImageResponse } from 'next/og'
import { getVerdict, getAllVerdictPaths } from '@/lib/verdicts'

export const runtime = 'nodejs'
export const contentType = 'image/png'
// Pinterest-optimal aspect ratio: 2:3 (1000x1500). We render at 1200x1800 for sharpness.
export const size = { width: 1200, height: 1800 }
export const alt = 'Should you buy this? A verdict from Style Inspo.'

export async function generateStaticParams() {
  return getAllVerdictPaths()
}

export default async function OG({ params }: { params: Promise<{ brand: string; slug: string }> }) {
  const { brand, slug } = await params
  const v = getVerdict(brand, slug)
  if (!v) return new ImageResponse(<div>Not found</div>, size)

  const buyCount = v.verdicts.filter(x => x.verdict === 'BUY').length
  const passCount = v.verdicts.filter(x => x.verdict === 'PASS').length
  const maybeCount = v.verdicts.filter(x => x.verdict === 'MAYBE').length

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: '#F5F1EA',
          padding: '90px 80px',
          fontFamily: 'sans-serif',
        }}
      >
        <div
          style={{
            fontSize: 36,
            color: '#A6694A',
            letterSpacing: 4,
            textTransform: 'uppercase',
            marginBottom: 40,
          }}
        >
          Style Inspo · Verdict
        </div>

        <div
          style={{
            fontSize: 100,
            fontWeight: 700,
            color: '#1A1614',
            lineHeight: 1.05,
            marginBottom: 40,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <span>Should you buy</span>
          <span>the {v.brand}</span>
          <span style={{ fontStyle: 'italic' }}>{v.item}?</span>
        </div>

        <div
          style={{
            fontSize: 44,
            color: '#3a3330',
            lineHeight: 1.35,
            marginBottom: 60,
            fontWeight: 400,
            display: 'flex',
          }}
        >
          {v.pull_quote}
        </div>

        <div style={{ display: 'flex', gap: 24, marginBottom: 'auto' }}>
          {buyCount > 0 && (
            <div
              style={{
                background: '#D1FAE5',
                color: '#065F46',
                padding: '20px 36px',
                borderRadius: 16,
                fontSize: 38,
                fontWeight: 600,
                display: 'flex',
              }}
            >
              {buyCount} BUY
            </div>
          )}
          {maybeCount > 0 && (
            <div
              style={{
                background: '#FEF3C7',
                color: '#92400E',
                padding: '20px 36px',
                borderRadius: 16,
                fontSize: 38,
                fontWeight: 600,
                display: 'flex',
              }}
            >
              {maybeCount} MAYBE
            </div>
          )}
          {passCount > 0 && (
            <div
              style={{
                background: '#FFE4E6',
                color: '#9F1239',
                padding: '20px 36px',
                borderRadius: 16,
                fontSize: 38,
                fontWeight: 600,
                display: 'flex',
              }}
            >
              {passCount} PASS
            </div>
          )}
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            borderTop: '2px solid #1A1614',
            paddingTop: 36,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontSize: 32, color: '#6b6360' }}>${v.price_usd}</span>
            <span style={{ fontSize: 32, color: '#1A1614', fontWeight: 600 }}>
              styleinspo.vercel.app
            </span>
          </div>
          <div
            style={{
              fontSize: 30,
              color: '#A6694A',
              fontStyle: 'italic',
              maxWidth: 420,
              textAlign: 'right',
              display: 'flex',
            }}
          >
            text us for a verdict on yours
          </div>
        </div>
      </div>
    ),
    { ...size }
  )
}
