'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect } from 'react'
import { ShowcaseLanding } from '@/components/ShowcaseLanding'

// Welcome page now redirects to root which renders the showcase.
// Keeping this route so old links still work.
export default function WelcomePage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const user = searchParams.get('user')
    const target = user ? `/?user=${encodeURIComponent(user)}` : '/'
    router.replace(target)
  }, [router, searchParams])

  // Show showcase while redirect happens (instant, no flash)
  return <ShowcaseLanding />
}
