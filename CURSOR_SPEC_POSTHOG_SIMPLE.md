# PostHog Analytics - Simple Implementation

## Goal
Add basic PostHog analytics so we know: who visited, where they are in onboarding, and what key actions they took.

## Scope
- Initialize PostHog
- Track page views automatically
- Track 5 key events manually
- Identify users by their `?user=` param

## NOT in scope (do later)
- Session recording
- Feature flags
- A/B testing
- Backend events

---

## Step 1: Create PostHog Provider

Create `frontend/lib/posthog.tsx`:

```tsx
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
```

---

## Step 2: Add to Providers

Update `frontend/app/providers.tsx`:

```tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState, Suspense } from 'react'
import { PostHogProvider } from '@/lib/posthog'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000,
            gcTime: 10 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={null}>
        <PostHogProvider>{children}</PostHogProvider>
      </Suspense>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

---

## Step 3: Add Environment Variables

Add to `frontend/.env.local`:

```
NEXT_PUBLIC_POSTHOG_KEY=phc_YOUR_KEY_HERE
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

---

## Step 4: Track 5 Key Events

### 4a. Words Completed (onboarding step 1)

In `frontend/app/words/page.tsx`, find the `handleSubmit` function. After the successful API call, add:

```tsx
import { posthog } from '@/lib/posthog'

// Inside handleSubmit, after api.updateProfile succeeds:
posthog.capture('words_completed', {
  word1: word1.trim(),
  word2: word2.trim(),
  word3: word3.trim()
})
```

### 4b. Upload Completed (onboarding step 2)

In `frontend/app/upload/page.tsx`, find where uploads complete. Add:

```tsx
import { posthog } from '@/lib/posthog'

// When user clicks continue after uploading items:
posthog.capture('upload_completed', {
  item_count: uploadedItems.length
})
```

### 4c. Outfit Generated

In `frontend/app/occasion/page.tsx`, in `handleGenerate` after the API call:

```tsx
import { posthog } from '@/lib/posthog'

// After api.generateOutfits succeeds:
posthog.capture('outfit_generated', {
  occasions: [...selectedOccasions, customOccasion].filter(Boolean),
  mode: 'occasion'
})
```

### 4d. Outfit Saved

Find where outfit is saved (likely in reveal page or outfit card). Add:

```tsx
posthog.capture('outfit_saved', {
  outfit_id: outfit.id
})
```

### 4e. Outfit Disliked

Find where outfit is disliked. Add:

```tsx
posthog.capture('outfit_disliked', {
  outfit_id: outfit.id
})
```

---

## Step 5: Verify

1. Run `npm run dev` in frontend
2. Open the app with `?user=test`
3. Go through the flow
4. Check PostHog dashboard for events

---

## What You'll See in PostHog

**Funnels tab:** Set up funnel:
1. $pageview where path = /welcome
2. words_completed
3. upload_completed
4. outfit_generated

**Activity tab:** See who visited yesterday, what they did

**Persons tab:** See each user's journey by their user param

---

## Files Changed
- `frontend/lib/posthog.tsx` (new)
- `frontend/app/providers.tsx` (modified)
- `frontend/.env.local` (add keys)
- `frontend/app/words/page.tsx` (add 1 event)
- `frontend/app/upload/page.tsx` (add 1 event)
- `frontend/app/occasion/page.tsx` (add 1 event)
- Wherever save/dislike happens (add 2 events)

Total: ~50 lines of new code across 6-7 files.
