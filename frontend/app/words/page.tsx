'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import { STYLE_WORD_CHIPS, STYLE_FEELING_CHIPS, getRandomChips } from '@/lib/styleWords'

function WordsPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'

  const [word1, setWord1] = useState('')
  const [word2, setWord2] = useState('')
  const [word3, setWord3] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Generate random chips for each word (persist across rerenders)
  const [word1Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word2Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word3Chips] = useState(() => getRandomChips(STYLE_FEELING_CHIPS, 6))

  useEffect(() => {
    async function loadProfile() {
      try {
        const profile = await api.getProfile(user)
        if (profile?.three_words) {
          setWord1(profile.three_words.current || '')
          setWord2(profile.three_words.aspirational || '')
          setWord3(profile.three_words.feeling || '')
        }
      } catch (error) {
        console.error('Error loading profile:', error)
        // Continue without pre-filling
      } finally {
        setLoading(false)
      }
    }
    loadProfile()
  }, [user])

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

    try {
      await api.updateProfile(user, {
        three_words: {
          current: word1.trim(),
          aspirational: word2.trim(),
          feeling: word3.trim()
        }
      })
      router.push(`/upload?user=${user}`)
    } catch (error: any) {
      console.error('Error saving profile:', error)
      setError(error?.message || 'Failed to save your style words. Please try again.')
      setSaving(false)
    }
  }

  const canContinue = word1.trim() && word2.trim() && word3.trim()

  if (loading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <Link href={`/welcome?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
          ← Back
        </Link>

        <div className="text-center mb-6 md:mb-8">
          <div className="inline-block px-3 py-1 bg-white border border-[rgba(26,22,20,0.12)] rounded-full text-sm text-ink mb-4">
            Style Profile
          </div>
          <h2 className="text-2xl md:text-3xl font-bold mb-3">Three Words</h2>
          <p className="text-muted text-base leading-relaxed max-w-xl mx-auto">
            Your first word describes your usual style, the second is your aspirational style, and the third is how you want to feel.
            <br /><br />
            We'll use these to create outfits that honor your style.
          </p>
        </div>

        {/* Word 1 - Usual Style */}
        <div className="mb-6 md:mb-8">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-2xl font-bold text-ink">1</span>
            <label className="text-base font-medium text-terracotta">Your Usual Style</label>
          </div>
          <input
            type="text"
            placeholder="e.g., classic"
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
        <div className="mb-6 md:mb-8">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-2xl font-bold text-ink">2</span>
            <label className="text-base font-medium text-terracotta">Your Aspirational Style</label>
          </div>
          <input
            type="text"
            placeholder="e.g., bold"
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
        <div className="mb-6 md:mb-8">
          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-2xl font-bold text-ink">3</span>
            <label className="text-base font-medium text-terracotta">How You Want to Feel</label>
          </div>
          <input
            type="text"
            placeholder="e.g., confident"
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

        {/* Reassurance text */}
        <div className="mb-6 md:mb-8">
          <p className="text-muted text-sm text-center">
            Not sure? Pick what feels right now - you can always change later
          </p>
          <p className="text-muted text-xs text-center mt-3">
            Inspired by{' '}
            <a
              href="https://www.allisonbornstein.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-terracotta transition"
            >
              Allison Bornstein's
            </a>
            {' '}three-word method
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        {/* Continue button */}
        <button
          onClick={handleSubmit}
          disabled={!canContinue || saving}
          className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center button-container"
        >
          {saving ? 'Saving...' : 'Continue to Upload'}
        </button>
      </div>
    </div>
  )
}

export default function WordsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <WordsPageContent />
    </Suspense>
  )
}



