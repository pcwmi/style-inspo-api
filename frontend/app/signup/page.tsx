'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/auth'
import { posthog } from '@/lib/posthog'

function SignupPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  // Get style words from URL params (passed from /words page)
  const word1 = searchParams.get('word1') || ''
  const word2 = searchParams.get('word2') || ''
  const word3 = searchParams.get('word3') || ''

  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email.trim()) {
      setError('Please enter your email')
      return
    }

    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await authApi.sendMagicLink(email.trim())
      posthog.capture('signup_started', { email: email.trim() })

      // Redirect to check-email page with words preserved
      const params = new URLSearchParams()
      params.set('email', email.trim())
      if (word1) params.set('word1', word1)
      if (word2) params.set('word2', word2)
      if (word3) params.set('word3', word3)

      router.push(`/check-email?${params.toString()}`)
    } catch (err: any) {
      console.error('Error sending magic link:', err)
      setError(err.message || 'Failed to send magic link. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-md mx-auto px-4 py-8 md:py-16">
        <Link href="/words" className="text-terracotta mb-6 inline-block min-h-[44px] flex items-center">
          ← Back
        </Link>

        <div className="text-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold mb-4">Save Your Style Profile</h1>
          <p className="text-muted text-base leading-relaxed">
            Enter your email to save your style words and start building your wardrobe.
          </p>
        </div>

        {/* Show saved words preview */}
        {(word1 || word2 || word3) && (
          <div className="bg-white rounded-lg p-4 mb-6 border border-[rgba(26,22,20,0.12)]">
            <p className="text-sm text-muted mb-2">Your style words:</p>
            <div className="flex flex-wrap gap-2">
              {word1 && (
                <span className="px-3 py-1 bg-sand rounded-full text-sm text-ink">{word1}</span>
              )}
              {word2 && (
                <span className="px-3 py-1 bg-sand rounded-full text-sm text-ink">{word2}</span>
              )}
              {word3 && (
                <span className="px-3 py-1 bg-sand rounded-full text-sm text-ink">{word3}</span>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="email" className="block text-sm font-medium text-ink mb-2">
              Email address
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-4 py-3 text-base border border-[rgba(26,22,20,0.12)] rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta bg-white"
              autoComplete="email"
              autoFocus
            />
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email.trim()}
            className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center button-container"
          >
            {loading ? 'Sending...' : 'Continue with Email'}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          We'll send you a magic link to sign in. No password needed.
        </p>

        <div className="mt-8 pt-6 border-t border-[rgba(26,22,20,0.12)] text-center">
          <p className="text-sm text-muted">
            Already have an account?{' '}
            <Link href="/login" className="text-terracotta hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function SignupPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <SignupPageContent />
    </Suspense>
  )
}
