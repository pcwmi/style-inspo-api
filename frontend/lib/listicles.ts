import fs from 'fs'
import path from 'path'
import { getVerdict, type Verdict } from './verdicts'

export interface ListicleEntry {
  verdict_brand: string
  verdict_slug: string
  best_for: string
  summary: string
}

export interface ListiclePick {
  if_you_lean: string
  pick: string
}

export interface Listicle {
  slug: string
  title: string
  headline: string
  lede: string
  category: string
  entries: ListicleEntry[]
  how_to_pick: ListiclePick[]
  honest_caveats: string[]
  last_updated: string
}

export interface ResolvedEntry extends ListicleEntry {
  verdict: Verdict
}

const CONTENT_ROOT = path.join(process.cwd(), 'content', 'listicles')

export function getListicle(slug: string): Listicle | null {
  const filePath = path.join(CONTENT_ROOT, `${slug}.json`)
  if (!fs.existsSync(filePath)) return null
  return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as Listicle
}

export function getAllListiclePaths(): { slug: string }[] {
  if (!fs.existsSync(CONTENT_ROOT)) return []
  return fs
    .readdirSync(CONTENT_ROOT)
    .filter(f => f.endsWith('.json'))
    .map(f => ({ slug: f.replace(/\.json$/, '') }))
}

export function getAllListicles(): Listicle[] {
  return getAllListiclePaths()
    .map(({ slug }) => getListicle(slug))
    .filter((l): l is Listicle => l !== null)
    .sort((a, b) => b.last_updated.localeCompare(a.last_updated))
}

export function resolveEntries(listicle: Listicle): ResolvedEntry[] {
  return listicle.entries
    .map(e => {
      const verdict = getVerdict(e.verdict_brand, e.verdict_slug)
      return verdict ? { ...e, verdict } : null
    })
    .filter((e): e is ResolvedEntry => e !== null)
}
