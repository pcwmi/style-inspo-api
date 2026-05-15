import fs from 'fs'
import path from 'path'

export interface VerdictArchetype {
  archetype: string
  label: string
  verdict: 'BUY' | 'PASS' | 'MAYBE'
  reasoning: string
}

export interface VerdictAlternative {
  if_you_lean: string
  name: string
  price_usd: number
  url: string
  reasoning: string
}

export interface Verdict {
  brand: string
  brand_slug: string
  item: string
  item_slug: string
  price_usd: number
  category: string
  image_url: string
  affiliate_url: string
  one_line_summary: string
  energy: string
  pull_quote: string
  verdicts: VerdictArchetype[]
  why_people_love_it: string[]
  where_it_falls_flat: string[]
  alternatives: VerdictAlternative[]
  tags: string[]
  last_updated: string
}

const CONTENT_ROOT = path.join(process.cwd(), 'content', 'verdicts')

export function getVerdict(brand: string, slug: string): Verdict | null {
  const filePath = path.join(CONTENT_ROOT, brand, `${slug}.json`)
  if (!fs.existsSync(filePath)) return null
  const raw = fs.readFileSync(filePath, 'utf-8')
  return JSON.parse(raw) as Verdict
}

export function getAllVerdictPaths(): { brand: string; slug: string }[] {
  if (!fs.existsSync(CONTENT_ROOT)) return []
  const brands = fs.readdirSync(CONTENT_ROOT).filter(b => {
    const p = path.join(CONTENT_ROOT, b)
    return fs.statSync(p).isDirectory()
  })
  const out: { brand: string; slug: string }[] = []
  for (const brand of brands) {
    const items = fs.readdirSync(path.join(CONTENT_ROOT, brand))
      .filter(f => f.endsWith('.json'))
      .map(f => f.replace(/\.json$/, ''))
    for (const slug of items) {
      out.push({ brand, slug })
    }
  }
  return out
}

export function getAllVerdicts(): Verdict[] {
  return getAllVerdictPaths()
    .map(({ brand, slug }) => getVerdict(brand, slug))
    .filter((v): v is Verdict => v !== null)
    .sort((a, b) => b.last_updated.localeCompare(a.last_updated))
}

export function getRelatedVerdicts(current: Verdict, max = 3): Verdict[] {
  const all = getAllVerdicts().filter(
    v => !(v.brand_slug === current.brand_slug && v.item_slug === current.item_slug)
  )

  const score = (v: Verdict) => {
    let s = 0
    if (v.category === current.category) s += 5
    const tagOverlap = v.tags.filter(t => current.tags.includes(t)).length
    s += tagOverlap * 2
    const priceDelta = Math.abs(v.price_usd - current.price_usd)
    if (priceDelta < 50) s += 2
    else if (priceDelta < 150) s += 1
    return s
  }

  return all
    .map(v => ({ v, s: score(v) }))
    .sort((a, b) => b.s - a.s)
    .slice(0, max)
    .map(x => x.v)
}
