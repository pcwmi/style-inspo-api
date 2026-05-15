import type { MetadataRoute } from 'next'
import { getAllVerdictPaths } from '@/lib/verdicts'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date()

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${SITE_URL}/verdict`, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${SITE_URL}/offer`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
  ]

  const verdictRoutes: MetadataRoute.Sitemap = getAllVerdictPaths().map(({ brand, slug }) => ({
    url: `${SITE_URL}/verdict/${brand}/${slug}`,
    lastModified: now,
    changeFrequency: 'monthly',
    priority: 0.9,
  }))

  return [...staticRoutes, ...verdictRoutes]
}
