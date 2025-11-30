'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

interface BackButtonProps {
  label?: string // Default: "Back"
  fallbackHref?: string // Optional custom fallback (defaults to dashboard)
  className?: string // Optional custom styling
}

function BackButtonContent({ 
  label = "Back",
  fallbackHref,
  className = "text-terracotta mb-4 inline-block min-h-[44px] flex items-center"
}: BackButtonProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'

  const handleBack = () => {
    // Check if there's navigation history
    if (typeof window !== 'undefined' && window.history.length > 1) {
      // Use browser back - respects user's actual navigation path
      router.back()
    } else {
      // Fallback to dashboard (or custom href) when no history exists
      const destination = fallbackHref || `/?user=${user}`
      router.push(destination)
    }
  }

  return (
    <button
      onClick={handleBack}
      className={className}
      type="button"
    >
      ← {label}
    </button>
  )
}

export function BackButton(props: BackButtonProps) {
  return (
    <Suspense fallback={<div className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">← Back</div>}>
      <BackButtonContent {...props} />
    </Suspense>
  )
}

