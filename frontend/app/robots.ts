import type { MetadataRoute } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://styleinspo.vercel.app'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/verdict', '/verdict/', '/offer'],
        disallow: ['/api/', '/auth/', '/login', '/signup', '/check-email', '/profile', '/saved', '/closet', '/upload', '/wardrobe', '/disliked', '/debug-considering'],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  }
}
