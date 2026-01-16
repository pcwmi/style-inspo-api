'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { posthog } from '@/lib/posthog'

interface ModelDescriptorModalProps {
  isOpen: boolean
  userId: string
  onClose: () => void
  onSaved: (descriptor: string) => void
}

// Example descriptors that represent diverse body types authentically
const EXAMPLE_DESCRIPTORS = [
  "5'4\", Asian, chest length wavy black hair, not skinny but not fat either",
  "5'8\", white with fair skin, brunette shoulder length hair, athletic build",
  "5'5\", black, medium build, natural curls, wear tortoise glasses"
]

export function ModelDescriptorModal({
  isOpen,
  userId,
  onClose,
  onSaved
}: ModelDescriptorModalProps) {
  const [descriptor, setDescriptor] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleExampleClick = (example: string) => {
    setDescriptor(example)
    setError(null)
  }

  const handleSubmit = async () => {
    if (!descriptor.trim()) {
      setError('Please describe yourself to continue')
      return
    }

    setSaving(true)
    setError(null)

    try {
      await api.saveDescriptor({
        user_id: userId,
        descriptor: descriptor.trim()
      })

      posthog.capture('descriptor_saved', {
        descriptor_length: descriptor.length
      })

      onSaved(descriptor.trim())
    } catch (e: any) {
      setError(e.message || 'Failed to save description')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <h2 className="text-xl font-bold text-ink text-center mb-2">
            See Your Outfits Come to Life
          </h2>
          <p className="text-sm text-center text-gray-600 mb-6">
            We'll show your outfit on someone who shares your look.
          </p>

          {/* Input */}
          <div className="mb-4">
            <label className="text-xs font-semibold text-ink block mb-2">
              Describe yourself however feels right:
            </label>
            <textarea
              value={descriptor}
              onChange={(e) => {
                setDescriptor(e.target.value)
                setError(null)
              }}
              className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-terracotta/50"
              rows={3}
              placeholder="e.g., 5'4&quot;, Asian, shoulder-length hair, average build"
            />
          </div>

          {/* Tappable Examples */}
          <div className="mb-6">
            <p className="text-xs text-gray-500 mb-2">Examples (tap to use):</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_DESCRIPTORS.map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => handleExampleClick(example)}
                  className="text-xs px-3 py-1.5 bg-gray-100 rounded-full hover:bg-gray-200 text-left transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* Privacy Notice */}
          <p className="text-[10px] text-center text-gray-400 mb-4">
            Your description is used only to generate visualizations through our AI partner.
          </p>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-500 text-center mb-4">{error}</p>
          )}

          {/* Continue Button - No Skip Option */}
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="w-full py-3 bg-terracotta text-white rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {saving ? 'Saving...' : 'Continue \u2192'}
          </button>
        </div>
      </div>
    </div>
  )
}
