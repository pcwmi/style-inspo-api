'use client'

import { useRouter } from 'next/navigation'
import { Suspense, useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'
import { STYLE_WORD_CHIPS, STYLE_FEELING_CHIPS, getRandomChips } from '@/lib/styleWords'
import { posthog } from '@/lib/posthog'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function GetStartedContent() {
  const router = useRouter()

  // Section 1: Username state
  const [username, setUsername] = useState('')
  const [usernameStatus, setUsernameStatus] = useState<'idle' | 'checking' | 'available' | 'taken' | 'invalid'>('idle')
  const [usernameError, setUsernameError] = useState<string | null>(null)
  const [suggestion, setSuggestion] = useState<string | null>(null)

  // Section 2: Words state (revealed after username)
  const [showWordsSection, setShowWordsSection] = useState(false)
  const [word1, setWord1] = useState('')
  const [word2, setWord2] = useState('')
  const [word3, setWord3] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Refs for smooth scrolling
  const wordsSectionRef = useRef<HTMLDivElement>(null)

  // Generate random chips
  const [word1Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word2Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word3Chips] = useState(() => getRandomChips(STYLE_FEELING_CHIPS, 6))

  // Debounced username check
  useEffect(() => {
    if (!username.trim()) {
      setUsernameStatus('idle')
      setUsernameError(null)
      setSuggestion(null)
      return
    }

    // Validate format locally first
    const trimmed = username.toLowerCase().trim()
    if (trimmed.length < 3) {
      setUsernameStatus('invalid')
      setUsernameError('At least 3 characters')
      return
    }
    if (trimmed.length > 20) {
      setUsernameStatus('invalid')
      setUsernameError('20 characters max')
      return
    }
    if (!/^[a-z0-9_]+$/.test(trimmed)) {
      setUsernameStatus('invalid')
      setUsernameError('Only lowercase letters, numbers, underscores')
      return
    }

    setUsernameStatus('checking')
    setUsernameError(null)

    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_URL}/api/users/check-username/${trimmed}`)
        const data = await res.json()

        if (data.available) {
          setUsernameStatus('available')
          setUsernameError(null)
          setSuggestion(null)
        } else {
          setUsernameStatus('taken')
          setUsernameError(data.reason || 'Username not available')
          setSuggestion(data.suggestion || null)
        }
      } catch (err) {
        // On error, assume available (will fail at creation if taken)
        setUsernameStatus('available')
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [username])

  const handleContinueToWords = () => {
    setShowWordsSection(true)
    // Smooth scroll to words section
    setTimeout(() => {
      wordsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 100)
  }

  const handleChipClick = (word: string, position: 1 | 2 | 3) => {
    if (position === 1) setWord1(word)
    else if (position === 2) setWord2(word)
    else setWord3(word)
  }

  const handleSubmit = async () => {
    if (!word1.trim() || !word2.trim() || !word3.trim()) {
      setError('Please fill in all three words')
      return
    }

    setSaving(true)
    setError(null)

    const trimmedUsername = username.toLowerCase().trim()

    try {
      // Save profile with the username and display name
      await api.updateProfile(trimmedUsername, {
        three_words: {
          current: word1.trim(),
          aspirational: word2.trim(),
          feeling: word3.trim()
        },
        display_name: username.trim()  // Preserve their preferred capitalization
      })

      posthog.capture('signup_completed', {
        username: trimmedUsername,
        word1: word1.trim(),
        word2: word2.trim(),
        word3: word3.trim()
      })

      // Redirect to upload with username
      router.push(`/upload?user=${trimmedUsername}`)
    } catch (error: any) {
      console.error('Error saving profile:', error)
      setError(error?.message || 'Failed to save. Please try again.')
      setSaving(false)
    }
  }

  const canContinueToWords = usernameStatus === 'available'
  const canSubmit = word1.trim() && word2.trim() && word3.trim()

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-8 md:py-12">

        {/* Section 1: Username */}
        <div className="text-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold mb-3">Welcome to Mira</h1>
          <p className="text-muted text-base">Let's create your style profile</p>
        </div>

        <div className="bg-white rounded-xl border border-[rgba(26,22,20,0.12)] p-6 mb-6">
          <label className="block text-base font-medium text-ink mb-2">
            What should we call you?
          </label>
          <div className="relative">
            <input
              type="text"
              placeholder="Pick a username"
              value={username}
              onChange={(e) => setUsername(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
              className={`w-full px-4 py-3 text-base border rounded-lg focus:outline-none focus:ring-2 bg-white ${
                usernameStatus === 'available' ? 'border-terracotta focus:ring-terracotta' :
                usernameStatus === 'taken' || usernameStatus === 'invalid' ? 'border-red-400 focus:ring-red-400' :
                'border-[rgba(26,22,20,0.12)] focus:ring-terracotta'
              }`}
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
            />
            {/* Status indicator */}
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {usernameStatus === 'checking' && (
                <div className="animate-spin h-5 w-5 border-2 border-sand border-t-terracotta rounded-full" />
              )}
              {usernameStatus === 'available' && (
                <svg className="h-5 w-5 text-terracotta" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {(usernameStatus === 'taken' || usernameStatus === 'invalid') && (
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </div>
          </div>
          <p className="text-xs text-muted mt-2">Letters, numbers, and underscores only</p>

          {/* Error/suggestion message */}
          {usernameError && (
            <p className="text-sm text-red-600 mt-2">{usernameError}</p>
          )}
          {suggestion && (
            <p className="text-sm text-muted mt-1">
              Try: <button
                onClick={() => setUsername(suggestion)}
                className="text-terracotta underline hover:no-underline"
              >
                {suggestion}
              </button>
            </p>
          )}
        </div>

        {/* Continue button (to reveal words section) */}
        {!showWordsSection && (
          <button
            onClick={handleContinueToWords}
            disabled={!canContinueToWords}
            className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center"
          >
            Continue
          </button>
        )}

        {/* Section 2: Style Words (progressive reveal) */}
        {showWordsSection && (
          <div ref={wordsSectionRef} className="mt-8 pt-8 border-t border-[rgba(26,22,20,0.08)]">
            <div className="text-center mb-6">
              <h2 className="text-xl md:text-2xl font-bold mb-2">
                Great! Now let's learn your style, {username}
              </h2>
              <p className="text-muted text-sm max-w-md mx-auto">
                Three words to describe your style. We'll use these to create outfits that honor who you are.
              </p>
            </div>

            {/* Word 1 - Usual Style */}
            <div className="mb-6">
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-xl font-bold text-ink">1</span>
                <label className="text-base font-medium text-terracotta">Your Usual Style</label>
              </div>
              <input
                type="text"
                placeholder="Think of your go-to outfit"
                value={word1}
                onChange={(e) => setWord1(e.target.value)}
                className="w-full px-4 py-3 text-base border border-[rgba(26,22,20,0.12)] rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta bg-white mb-3"
              />
              <div className="flex flex-wrap gap-2">
                {word1Chips.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleChipClick(chip, 1)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      word1.toLowerCase() === chip.toLowerCase()
                        ? 'bg-terracotta text-white border-terracotta'
                        : 'bg-white text-ink border-[rgba(26,22,20,0.12)] hover:border-terracotta/50'
                    }`}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Word 2 - Aspirational Style */}
            <div className="mb-6">
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-xl font-bold text-ink">2</span>
                <label className="text-base font-medium text-terracotta">Your Aspirational Style</label>
              </div>
              <input
                type="text"
                placeholder="What style do you admire but haven't tried?"
                value={word2}
                onChange={(e) => setWord2(e.target.value)}
                className="w-full px-4 py-3 text-base border border-[rgba(26,22,20,0.12)] rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta bg-white mb-3"
              />
              <div className="flex flex-wrap gap-2">
                {word2Chips.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleChipClick(chip, 2)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      word2.toLowerCase() === chip.toLowerCase()
                        ? 'bg-terracotta text-white border-terracotta'
                        : 'bg-white text-ink border-[rgba(26,22,20,0.12)] hover:border-terracotta/50'
                    }`}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Word 3 - How You Want to Feel */}
            <div className="mb-6">
              <div className="flex items-baseline gap-3 mb-2">
                <span className="text-xl font-bold text-ink">3</span>
                <label className="text-base font-medium text-terracotta">How You Want to Feel</label>
              </div>
              <input
                type="text"
                placeholder="What energy do you want to bring?"
                value={word3}
                onChange={(e) => setWord3(e.target.value)}
                className="w-full px-4 py-3 text-base border border-[rgba(26,22,20,0.12)] rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta bg-white mb-3"
              />
              <div className="flex flex-wrap gap-2">
                {word3Chips.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleChipClick(chip, 3)}
                    className={`px-3 py-1.5 text-sm rounded-full border transition ${
                      word3.toLowerCase() === chip.toLowerCase()
                        ? 'bg-terracotta text-white border-terracotta'
                        : 'bg-white text-ink border-[rgba(26,22,20,0.12)] hover:border-terracotta/50'
                    }`}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            {/* Reassurance */}
            <p className="text-muted text-sm text-center mb-6">
              Not sure? Pick what feels right now - you can always change later
            </p>

            {/* Error message */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || saving}
              className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center"
            >
              {saving ? 'Saving...' : 'Save & Start Uploading'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function GetStartedPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <GetStartedContent />
    </Suspense>
  )
}
