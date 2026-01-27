'use client'

import { useState, useRef } from 'react'
import { api } from '@/lib/api'

interface WornTrackingModalProps {
  isOpen: boolean
  outfitId: string
  userId: string
  onClose: () => void
  onComplete: (wornAt: string, photoUrl?: string) => void
}

export function WornTrackingModal({
  isOpen,
  outfitId,
  userId,
  onClose,
  onComplete
}: WornTrackingModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!isOpen) return null

  const handleSkip = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.markOutfitWorn(userId, outfitId)
      onComplete(result.worn_at)
    } catch (e: any) {
      setError(e.message || 'Failed to mark as worn')
    } finally {
      setLoading(false)
    }
  }

  const handlePhotoSelect = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setLoading(true)
    setError(null)
    try {
      const result = await api.uploadWornPhoto(userId, outfitId, file)
      onComplete(result.worn_at, result.worn_photo_url)
    } catch (e: any) {
      setError(e.message || 'Failed to upload photo')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-md sm:rounded-lg rounded-t-2xl p-6 shadow-xl">
        <h2 className="text-xl font-semibold mb-2">How did this outfit work?</h2>
        <p className="text-muted mb-6">
          Add a photo to see how it looked in real life!
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <div className="space-y-3">
          {/* Photo upload button */}
          <button
            onClick={handlePhotoSelect}
            disabled={loading}
            className="w-full bg-terracotta text-white py-3.5 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <span className="animate-spin">...</span>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Add a photo
              </>
            )}
          </button>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Skip button */}
          <button
            onClick={handleSkip}
            disabled={loading}
            className="w-full bg-sand text-ink py-3.5 px-6 rounded-lg font-medium hover:bg-sand/80 transition active:bg-sand/60 min-h-[48px] flex items-center justify-center disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Skip, just mark as worn'}
          </button>

          {/* Cancel button */}
          <button
            onClick={onClose}
            disabled={loading}
            className="w-full text-muted py-2 text-sm hover:text-ink transition min-h-[44px]"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
