'use client'

import { useRouter } from 'next/navigation'
import { Suspense, useState } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/auth'
import { posthog } from '@/lib/posthog'

function LoginPageContent() {
  const router = useRouter()

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
      posthog.capture('login_started', { email: email.trim() })

      router.push(`/check-email?email=${encodeURIComponent(email.trim())}`)
    } catch (err: any) {
      console.error('Error sending magic link:', err)
      setError(err.message || 'Failed to send magic link. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-md mx-auto px-4 py-8 md:py-16">
        <Link href="/" className="text-terracotta mb-6 inline-block min-h-[44px] flex items-center">
          ← Back
        </Link>

        <div className="text-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold mb-4">Welcome back</h1>
          <p className="text-muted text-base leading-relaxed">
            Enter your email and we'll send you a magic link to sign in.
          </p>
        </div>

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
            {loading ? 'Sending...' : 'Send magic link'}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          No password required. We'll email you a secure link.
        </p>

        <div className="mt-8 pt-6 border-t border-[rgba(26,22,20,0.12)] text-center">
          <p className="text-sm text-muted">
            New to Mira?{' '}
            <Link href="/welcome" className="text-terracotta hover:underline">
              Get started
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <LoginPageContent />
    </Suspense>
  )
}
