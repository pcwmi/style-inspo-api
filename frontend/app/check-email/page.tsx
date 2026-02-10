'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/auth'

function CheckEmailPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const email = searchParams.get('email') || ''
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleResend = async () => {
    if (!email) return

    setResending(true)
    setError(null)

    try {
      await authApi.sendMagicLink(email)
      setResent(true)
      setTimeout(() => setResent(false), 5000) // Reset after 5 seconds
    } catch (err: any) {
      setError(err.message || 'Failed to resend. Please try again.')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-md mx-auto px-4 py-8 md:py-16">
        <div className="text-center">
          {/* Email icon */}
          <div className="w-16 h-16 bg-sand rounded-full flex items-center justify-center mx-auto mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-terracotta" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>

          <h1 className="text-2xl md:text-3xl font-bold mb-4">Check your inbox</h1>

          <p className="text-muted text-base leading-relaxed mb-2">
            We sent a magic link to
          </p>
          <p className="font-medium text-ink mb-6">
            {email || 'your email'}
          </p>

          <p className="text-muted text-base leading-relaxed mb-8">
            Click the link in the email to sign in. The link expires in 15 minutes.
          </p>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          {resent && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 text-sm">Magic link sent! Check your inbox.</p>
            </div>
          )}

          <div className="space-y-4">
            <button
              onClick={handleResend}
              disabled={resending || !email}
              className="w-full bg-white text-ink py-3.5 px-6 rounded-lg font-medium border border-[rgba(26,22,20,0.12)] hover:border-terracotta transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px]"
            >
              {resending ? 'Sending...' : 'Resend magic link'}
            </button>

            <Link
              href="/signup"
              className="block w-full text-center py-3.5 px-6 text-terracotta hover:underline min-h-[48px] flex items-center justify-center"
            >
              Use a different email
            </Link>
          </div>

          <div className="mt-8 pt-6 border-t border-[rgba(26,22,20,0.12)]">
            <p className="text-sm text-muted">
              Didn't get the email? Check your spam folder or{' '}
              <button
                onClick={handleResend}
                disabled={resending}
                className="text-terracotta hover:underline"
              >
                try again
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function CheckEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <CheckEmailPageContent />
    </Suspense>
  )
}
