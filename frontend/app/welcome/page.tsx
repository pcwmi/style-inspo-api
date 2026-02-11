'use client'

import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { ShowcaseLanding } from '@/components/ShowcaseLanding'

// Welcome page now redirects to root which renders the showcase.
// Keeping this route so old links still work.
export default function WelcomePage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/')
  }, [router])

  // Show showcase while redirect happens (instant, no flash)
  return <ShowcaseLanding />
}
