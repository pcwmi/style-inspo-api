'use client'

import posthog from 'posthog-js'
import { PostHogProvider as PHProvider } from 'posthog-js/react'
import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

// Initialize PostHog once
if (typeof window !== 'undefined' && !posthog.__loaded) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: false, // We'll do this manually for SPA
    capture_pageleave: true,
  })
}

// Component to track page views and identify user
function PostHogPageView() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (pathname) {
      // Identify user from URL param
      const user = searchParams.get('user')
      if (user && user !== 'default') {
        posthog.identify(user)
      }

      // Track page view
      posthog.capture('$pageview', {
        $current_url: window.location.href,
        path: pathname,
        user: user || 'default'
      })
    }
  }, [pathname, searchParams])

  return null
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  return (
    <PHProvider client={posthog}>
      <PostHogPageView />
      {children}
    </PHProvider>
  )
}

// Export for manual event tracking
export { posthog }


