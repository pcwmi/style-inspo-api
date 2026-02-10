'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/auth'
import { posthog } from '@/lib/posthog'

function AuthPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const token = searchParams.get('token')
  const isClaim = searchParams.get('claim') === 'true'

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<{ email: string; is_new_user: boolean } | null>(null)

  // Ref to prevent double-execution in React Strict Mode
  const verifiedRef = useRef(false)

  useEffect(() => {
    async function verifyToken() {
      if (verifiedRef.current) return
      verifiedRef.current = true

      if (!token) {
        setStatus('error')
        setError('No token provided')
        return
      }

      try {
        const result = await authApi.verifyToken(token)

        setUser({ email: result.email, is_new_user: result.is_new_user })
        setStatus('success')

        // Track successful auth
        posthog.capture('auth_verified', {
          is_new_user: result.is_new_user,
          is_claim: isClaim
        })

        // Redirect after short delay to show success
        setTimeout(() => {
          if (result.is_new_user) {
            // New users go to upload their wardrobe
            router.push('/upload')
          } else {
            // Returning users go to dashboard
            router.push('/')
          }
        }, 1500)
      } catch (err: any) {
        console.error('Token verification failed:', err)
        setStatus('error')
        setError(err.message || 'Failed to verify token')

        posthog.capture('auth_failed', {
          error: err.message
        })
      }
    }

    verifyToken()
  }, [token, isClaim, router])

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-md mx-auto px-4 py-8 md:py-16">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-6"></div>
              <h1 className="text-2xl md:text-3xl font-bold mb-4">Signing you in...</h1>
              <p className="text-muted text-base">Just a moment</p>
            </>
          )}

          {status === 'success' && user && (
            <>
              {/* Checkmark icon */}
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>

              <h1 className="text-2xl md:text-3xl font-bold mb-4">
                {user.is_new_user ? 'Welcome!' : 'Welcome back!'}
              </h1>
              <p className="text-muted text-base mb-4">
                Signed in as <span className="font-medium text-ink">{user.email}</span>
              </p>
              <p className="text-muted text-sm">
                Redirecting you {user.is_new_user ? 'to upload your wardrobe' : 'to your dashboard'}...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              {/* Error icon */}
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>

              <h1 className="text-2xl md:text-3xl font-bold mb-4">Link expired or invalid</h1>
              <p className="text-muted text-base mb-6">
                {error || 'This magic link is no longer valid. Please request a new one.'}
              </p>

              <div className="space-y-4">
                <Link
                  href="/login"
                  className="block w-full bg-terracotta text-white py-3.5 px-6 rounded-lg font-medium hover:opacity-90 transition text-center min-h-[48px] flex items-center justify-center"
                >
                  Request new link
                </Link>

                <Link
                  href="/"
                  className="block w-full text-center py-3.5 px-6 text-terracotta hover:underline min-h-[48px] flex items-center justify-center"
                >
                  Go to homepage
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-muted">Loading...</p>
        </div>
      </div>
    }>
      <AuthPageContent />
    </Suspense>
  )
}
