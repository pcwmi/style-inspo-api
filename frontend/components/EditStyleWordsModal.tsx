'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { STYLE_WORD_CHIPS, STYLE_FEELING_CHIPS, getRandomChips } from '@/lib/styleWords'

interface EditStyleWordsModalProps {
  isOpen: boolean
  userId: string
  initialValues?: {
    current?: string
    aspirational?: string
    feeling?: string
  }
  onClose: () => void
  onSaved: (threeWords: { current: string; aspirational: string; feeling: string }) => void
}

export function EditStyleWordsModal({
  isOpen,
  userId,
  initialValues,
  onClose,
  onSaved
}: EditStyleWordsModalProps) {
  const [word1, setWord1] = useState(initialValues?.current || '')
  const [word2, setWord2] = useState(initialValues?.aspirational || '')
  const [word3, setWord3] = useState(initialValues?.feeling || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Generate random chips (persist during modal session)
  const [word1Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word2Chips] = useState(() => getRandomChips(STYLE_WORD_CHIPS, 6))
  const [word3Chips] = useState(() => getRandomChips(STYLE_FEELING_CHIPS, 6))

  if (!isOpen) return null

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
      await api.updateProfile(userId, {
        three_words: {
          current: word1.trim(),
          aspirational: word2.trim(),
          feeling: word3.trim()
        }
      })

      onSaved({
        current: word1.trim(),
        aspirational: word2.trim(),
        feeling: word3.trim()
      })
    } catch (e: any) {
      setError(e.message || 'Failed to save style words')
      setSaving(false)
    }
  }

  const canSave = word1.trim() && word2.trim() && word3.trim()

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-ink">Edit Style Words</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p className="text-sm text-gray-600 mb-6">
            Your three words guide our outfit recommendations.
          </p>

          {/* Word 1 - Usual Style */}
          <div className="mb-5">
            <label className="text-xs font-semibold text-ink block mb-2">
              1. Your Usual Style
            </label>
            <input
              type="text"
              placeholder="e.g., classic, minimal, relaxed"
              value={word1}
              onChange={(e) => setWord1(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta/50 mb-2"
            />
            <div className="flex flex-wrap gap-1.5">
              {word1Chips.map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleChipClick(chip, 1)}
                  className={`px-2.5 py-1 text-xs rounded-full border transition ${
                    word1.toLowerCase() === chip.toLowerCase()
                      ? 'bg-terracotta text-white border-terracotta'
                      : 'bg-white text-ink border-gray-200 hover:border-terracotta/50'
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* Word 2 - Aspirational Style */}
          <div className="mb-5">
            <label className="text-xs font-semibold text-ink block mb-2">
              2. Your Aspirational Style
            </label>
            <input
              type="text"
              placeholder="e.g., bold, sophisticated, edgy"
              value={word2}
              onChange={(e) => setWord2(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta/50 mb-2"
            />
            <div className="flex flex-wrap gap-1.5">
              {word2Chips.map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleChipClick(chip, 2)}
                  className={`px-2.5 py-1 text-xs rounded-full border transition ${
                    word2.toLowerCase() === chip.toLowerCase()
                      ? 'bg-terracotta text-white border-terracotta'
                      : 'bg-white text-ink border-gray-200 hover:border-terracotta/50'
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* Word 3 - How You Want to Feel */}
          <div className="mb-6">
            <label className="text-xs font-semibold text-ink block mb-2">
              3. How You Want to Feel
            </label>
            <input
              type="text"
              placeholder="e.g., confident, playful, comfortable"
              value={word3}
              onChange={(e) => setWord3(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-terracotta/50 mb-2"
            />
            <div className="flex flex-wrap gap-1.5">
              {word3Chips.map((chip) => (
                <button
                  key={chip}
                  onClick={() => handleChipClick(chip, 3)}
                  className={`px-2.5 py-1 text-xs rounded-full border transition ${
                    word3.toLowerCase() === chip.toLowerCase()
                      ? 'bg-terracotta text-white border-terracotta'
                      : 'bg-white text-ink border-gray-200 hover:border-terracotta/50'
                  }`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-500 text-center mb-4">{error}</p>
          )}

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl text-sm font-medium hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canSave || saving}
              className="flex-1 py-3 bg-terracotta text-white rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
