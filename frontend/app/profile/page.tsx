'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { Suspense, useState, useEffect } from 'react'
import { api } from '@/lib/api'
import Link from 'next/link'
import { EditStyleWordsModal } from '@/components/EditStyleWordsModal'
import { posthog } from '@/lib/posthog'

interface ProfileData {
  three_words?: {
    current?: string
    aspirational?: string
    feeling?: string
  }
  model_descriptor?: string
}

function ProfilePageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const user = searchParams.get('user') || 'default'

  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Style words modal
  const [showStyleWordsModal, setShowStyleWordsModal] = useState(false)

  // Descriptor visibility (hidden by default for privacy)
  const [showDescriptor, setShowDescriptor] = useState(false)
  const [editingDescriptor, setEditingDescriptor] = useState(false)
  const [descriptorValue, setDescriptorValue] = useState('')
  const [savingDescriptor, setSavingDescriptor] = useState(false)

  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await api.getProfile(user)
        setProfile(data)
        setDescriptorValue(data?.model_descriptor || '')
      } catch (err: any) {
        console.error('Error loading profile:', err)
        setError(err?.message || 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    }
    loadProfile()
  }, [user])

  const handleStyleWordsSaved = (threeWords: { current: string; aspirational: string; feeling: string }) => {
    setProfile(prev => ({
      ...prev,
      three_words: threeWords
    }))
    setShowStyleWordsModal(false)
    posthog.capture('profile_style_words_updated')
  }

  const handleSaveDescriptor = async () => {
    if (!descriptorValue.trim()) return

    setSavingDescriptor(true)
    try {
      await api.saveDescriptor({
        user_id: user,
        descriptor: descriptorValue.trim()
      })
      setProfile(prev => ({
        ...prev,
        model_descriptor: descriptorValue.trim()
      }))
      setEditingDescriptor(false)
      posthog.capture('profile_descriptor_updated')
    } catch (err: any) {
      console.error('Error saving descriptor:', err)
      setError(err?.message || 'Failed to save description')
    } finally {
      setSavingDescriptor(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading profile...</p>
        </div>
      </div>
    )
  }

  const threeWords = profile?.three_words
  const hasDescriptor = !!profile?.model_descriptor

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
          ← Back to Dashboard
        </Link>

        <h1 className="text-2xl md:text-3xl font-bold mb-2">Your Profile</h1>
        <p className="text-muted mb-6 md:mb-8 text-base leading-relaxed">
          Manage your style identity and visualization settings.
        </p>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-600 text-sm underline mt-1"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Section 1: Style Identity */}
        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-5 shadow-sm">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg md:text-xl font-semibold mb-1">Style Identity</h2>
              <p className="text-muted text-sm">Your three words guide every outfit we create.</p>
            </div>
            <button
              onClick={() => setShowStyleWordsModal(true)}
              className="text-terracotta text-sm font-medium hover:opacity-80 min-h-[44px] px-2 flex items-center"
            >
              Edit
            </button>
          </div>

          {threeWords ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-muted uppercase tracking-wide w-24">Usual</span>
                <span className="px-3 py-1.5 bg-sand/50 rounded-full text-sm font-medium">{threeWords.current}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-muted uppercase tracking-wide w-24">Aspirational</span>
                <span className="px-3 py-1.5 bg-sand/50 rounded-full text-sm font-medium">{threeWords.aspirational}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-muted uppercase tracking-wide w-24">Feeling</span>
                <span className="px-3 py-1.5 bg-sand/50 rounded-full text-sm font-medium">{threeWords.feeling}</span>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-muted text-sm mb-3">You haven't set your style words yet.</p>
              <button
                onClick={() => setShowStyleWordsModal(true)}
                className="text-terracotta text-sm font-medium underline"
              >
                Add style words
              </button>
            </div>
          )}
        </div>

        {/* Section 2: Visualization Settings */}
        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 shadow-sm">
          <h2 className="text-lg md:text-xl font-semibold mb-1">Visualization Settings</h2>
          <p className="text-muted text-sm mb-4">
            Your description helps us show outfits on someone who shares your look.
          </p>

          {!showDescriptor ? (
            <div className="text-center py-4 border border-dashed border-gray-200 rounded-lg">
              <p className="text-muted text-sm mb-3">
                {hasDescriptor
                  ? 'Your description is saved and hidden for privacy.'
                  : 'No description saved yet.'}
              </p>
              <button
                onClick={() => setShowDescriptor(true)}
                className="inline-flex items-center gap-2 text-terracotta text-sm font-medium hover:opacity-80 min-h-[44px] px-4"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                {hasDescriptor ? 'Show my description' : 'Add description'}
              </button>
              <p className="text-[11px] text-gray-400 mt-3 flex items-center justify-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Only used for visualizations through our AI partner
              </p>
            </div>
          ) : (
            <div>
              <div className="flex justify-between items-center mb-3">
                <label className="text-xs font-medium text-muted uppercase tracking-wide">Your Description</label>
                <button
                  onClick={() => setShowDescriptor(false)}
                  className="text-gray-400 text-sm hover:text-gray-600 min-h-[44px] px-2 flex items-center"
                >
                  Hide
                </button>
              </div>

              {editingDescriptor ? (
                <div>
                  <textarea
                    value={descriptorValue}
                    onChange={(e) => setDescriptorValue(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-terracotta/50 mb-3"
                    rows={3}
                    placeholder="e.g., 5'4&quot;, Asian, shoulder-length hair, average build"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleSaveDescriptor}
                      disabled={savingDescriptor || !descriptorValue.trim()}
                      className="flex-1 bg-terracotta text-white py-2 px-4 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
                    >
                      {savingDescriptor ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        setEditingDescriptor(false)
                        setDescriptorValue(profile?.model_descriptor || '')
                      }}
                      className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  {profile?.model_descriptor ? (
                    <div className="bg-sand/30 rounded-lg p-3 mb-3">
                      <p className="text-sm">{profile.model_descriptor}</p>
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg p-3 mb-3 text-center">
                      <p className="text-sm text-muted">No description yet</p>
                    </div>
                  )}
                  <button
                    onClick={() => setEditingDescriptor(true)}
                    className="text-terracotta text-sm font-medium hover:opacity-80"
                  >
                    {profile?.model_descriptor ? 'Edit description' : 'Add description'}
                  </button>
                </div>
              )}

              <p className="text-[11px] text-gray-400 mt-4 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Only used for visualizations through our AI partner
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Style Words Modal */}
      {showStyleWordsModal && (
        <EditStyleWordsModal
          isOpen={showStyleWordsModal}
          userId={user}
          initialValues={threeWords}
          onClose={() => setShowStyleWordsModal(false)}
          onSaved={handleStyleWordsSaved}
        />
      )}
    </div>
  )
}

export default function ProfilePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-bone">
        <p className="text-muted">Loading...</p>
      </div>
    }>
      <ProfilePageContent />
    </Suspense>
  )
}
