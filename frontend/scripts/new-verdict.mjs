#!/usr/bin/env node
/**
 * Generate a new verdict JSON file via OpenAI in the exact schema the
 * /verdict/[brand]/[slug] route expects.
 *
 * Usage:
 *   OPENAI_API_KEY=sk-... node scripts/new-verdict.mjs \
 *     --brand "Frankie Shop" --item "Bea Cardigan" \
 *     --slug bea-cardigan --price 185 --category knitwear
 *
 * Optional flags:
 *   --notes "anything you want the AI to know — past reviews, hot takes, etc."
 *   --model gpt-4o            (default: gpt-4o)
 *   --force                   (overwrite if file exists)
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

function slugify(s) {
  return s
    .toLowerCase()
    .trim()
    .replace(/['']/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function parseArgs() {
  const argv = process.argv.slice(2)
  const args = {}
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i]
    if (k.startsWith('--')) {
      const key = k.slice(2)
      const next = argv[i + 1]
      if (!next || next.startsWith('--')) {
        args[key] = true
      } else {
        args[key] = next
        i++
      }
    }
  }
  return args
}

const args = parseArgs()

if (!args.brand || !args.item) {
  console.error('Required: --brand "<name>" --item "<name>"')
  process.exit(1)
}

const brand = args.brand
const item = args.item
const brandSlug = slugify(args['brand-slug'] || brand)
const itemSlug = slugify(args.slug || item)
const price = Number(args.price || 0)
const category = args.category || 'apparel'
const notes = args.notes || ''
const model = args.model || 'gpt-4o'
const force = Boolean(args.force)

const apiKey = process.env.OPENAI_API_KEY
if (!apiKey) {
  console.error('OPENAI_API_KEY env var required')
  process.exit(1)
}

const outDir = path.join(ROOT, 'content', 'verdicts', brandSlug)
const outPath = path.join(outDir, `${itemSlug}.json`)

if (fs.existsSync(outPath) && !force) {
  console.error(`File already exists: ${outPath}\nPass --force to overwrite.`)
  process.exit(1)
}

const today = new Date().toISOString().slice(0, 10)

const systemPrompt = `You are the editorial voice behind Style Inspo's "Should you buy this?" verdict pages.

You write opinionated, identity-tuned product verdicts for shoppers considering specific fashion items. The voice is:
- Confident and specific, never hedging or generically positive
- Honest about flaws — including when a famous brand falls short
- Concrete: cite materials, construction, fit, real flaws people report
- Plain-spoken; no marketing-speak; no exclamation points; no hype words ("game-changer," "obsessed")
- Respectful of the reader's intelligence and budget

Every verdict must include four archetype-specific verdicts (BUY / PASS / MAYBE) that read as if four different stylish friends weighed in. The four archetypes should span style identity (e.g. easy/structured/polished/maximalist/bold/minimal) OR practical body/budget concerns (e.g. petite, narrow foot, minimal budget). At least one verdict should be BUY and at least one PASS — never four BUYs.

Output ONLY valid JSON that exactly matches the schema. No prose around it. No markdown fences.`

const schema = {
  brand: 'string',
  brand_slug: 'string',
  item: 'string',
  item_slug: 'string',
  price_usd: 'number',
  category: 'string',
  image_url: 'string (empty string is fine)',
  affiliate_url: 'string (empty string is fine)',
  one_line_summary: 'one sentence physical/conceptual description',
  energy: 'one short evocative phrase, e.g. "downtown effortless"',
  pull_quote: 'one or two sentence headline judgment',
  verdicts: [
    {
      archetype: 'short noun phrase, e.g. "easy / textured / lived-in"',
      label: 'three slash-separated descriptors',
      verdict: 'BUY | PASS | MAYBE',
      reasoning: '3-5 sentence personal-feeling explanation',
    },
  ],
  why_people_love_it: ['3 bullet strings'],
  where_it_falls_flat: ['3 honest critique strings'],
  alternatives: [
    {
      if_you_lean: 'short style descriptor',
      name: 'real product name',
      price_usd: 'number',
      url: 'string (empty string is fine)',
      reasoning: '2-3 sentence why this alt fits this archetype',
    },
  ],
  tags: ['array of 4-6 lowercase tag strings'],
  last_updated: 'ISO date',
}

const userPrompt = `Write a Style Inspo verdict for:

Brand: ${brand}
Item: ${item}
Brand slug: ${brandSlug}
Item slug: ${itemSlug}
Price (USD): ${price}
Category: ${category}
Today: ${today}
${notes ? `\nAdditional context from the editor:\n${notes}\n` : ''}

Requirements:
- 4 archetype verdicts spanning meaningfully different reader types
- Mix of BUY/PASS/MAYBE — at least one of each ideally, never all BUYs
- 3 alternatives that each genuinely fit a different reader type
- Tone matches the system instruction: confident, specific, honest
- All slugs lowercase-hyphenated

JSON schema (for reference, output the actual values, not the type names):
${JSON.stringify(schema, null, 2)}

Output ONLY the JSON object.`

console.log(`Generating verdict: ${brand} — ${item} ($${price}, ${category})`)
console.log(`Model: ${model}`)

const res = await fetch('https://api.openai.com/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${apiKey}`,
  },
  body: JSON.stringify({
    model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
    response_format: { type: 'json_object' },
    temperature: 0.7,
  }),
})

if (!res.ok) {
  const txt = await res.text()
  console.error(`OpenAI ${res.status}: ${txt}`)
  process.exit(1)
}

const data = await res.json()
const raw = data.choices?.[0]?.message?.content
if (!raw) {
  console.error('No content in response')
  process.exit(1)
}

let parsed
try {
  parsed = JSON.parse(raw)
} catch (e) {
  console.error('Model returned non-JSON:', raw.slice(0, 500))
  process.exit(1)
}

// Sanity-check required fields
const required = ['brand', 'item', 'one_line_summary', 'energy', 'pull_quote', 'verdicts', 'why_people_love_it', 'where_it_falls_flat', 'alternatives']
const missing = required.filter(k => !parsed[k])
if (missing.length) {
  console.error('Missing required fields:', missing.join(', '))
  console.error('Got:', Object.keys(parsed).join(', '))
  process.exit(1)
}

// Force-canonicalize slugs and date in case the model drifted
parsed.brand_slug = brandSlug
parsed.item_slug = itemSlug
parsed.price_usd = parsed.price_usd || price
parsed.category = parsed.category || category
parsed.last_updated = today
parsed.image_url = parsed.image_url || ''
parsed.affiliate_url = parsed.affiliate_url || ''
parsed.alternatives = (parsed.alternatives || []).map(a => ({ ...a, url: a.url || '' }))

fs.mkdirSync(outDir, { recursive: true })
fs.writeFileSync(outPath, JSON.stringify(parsed, null, 2) + '\n')

console.log(`✓ Wrote ${path.relative(ROOT, outPath)}`)
console.log(`\nPreview:`)
console.log(`  ${parsed.one_line_summary}`)
console.log(`  → "${parsed.pull_quote}"`)
console.log(`\nReview the file, edit if needed, then:`)
console.log(`  git add ${path.relative(ROOT, outPath)}`)
console.log(`  git commit -m "Add verdict: ${brand} ${item}"`)
console.log(`  git push`)
