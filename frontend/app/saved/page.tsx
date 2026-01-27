'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense, useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { VisualizedOutfitCard } from '@/components/VisualizedOutfitCard'
import { ModelDescriptorModal } from '@/components/ModelDescriptorModal'
import { WornTrackingModal } from '@/components/WornTrackingModal'
import { PhotoUploadModal } from '@/components/PhotoUploadModal'
import { api } from '@/lib/api'

type Tab = 'not_worn' | 'worn'

function SavedPageContent() {
  const searchParams = useSearchParams()
  const user = searchParams.get('user') || 'default'

  const [outfits, setOutfits] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [hasDescriptor, setHasDescriptor] = useState<boolean | null>(null)
  const [showDescriptorModal, setShowDescriptorModal] = useState(false)
  const [pendingVisualizationOutfitId, setPendingVisualizationOutfitId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('not_worn')
  const [showWornModal, setShowWornModal] = useState(false)
  const [pendingWornOutfitId, setPendingWornOutfitId] = useState<string | null>(null)
  const [showPhotoModal, setShowPhotoModal] = useState(false)
  const [pendingPhotoOutfitId, setPendingPhotoOutfitId] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        // Fetch saved outfits and user profile in parallel
        const [outfitsResult, profileResult] = await Promise.all([
          api.getSavedOutfits(user),
          api.getProfile(user)
        ])
        setOutfits(outfitsResult.outfits || [])
        setHasDescriptor(!!profileResult.model_descriptor)
      } catch (err: any) {
        setError(err.message || 'Failed to load saved outfits')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [user])

  // Split outfits into not worn and worn
  const { notWornOutfits, wornOutfits } = useMemo(() => {
    const notWorn = outfits.filter(o => !o.worn_at)
    const worn = outfits
      .filter(o => o.worn_at)
      .sort((a, b) => new Date(b.worn_at).getTime() - new Date(a.worn_at).getTime())
    return { notWornOutfits: notWorn, wornOutfits: worn }
  }, [outfits])

  const displayedOutfits = activeTab === 'not_worn' ? notWornOutfits : wornOutfits

  // Handle visualize button click - check for descriptor first
  const handleVisualize = (outfitId: string) => {
    if (!hasDescriptor) {
      setPendingVisualizationOutfitId(outfitId)
      setShowDescriptorModal(true)
    }
    // If hasDescriptor, the VisualizedOutfitCard will handle it directly
  }

  // Handle descriptor saved - start the pending visualization
  const handleDescriptorSaved = (descriptor: string) => {
    setHasDescriptor(true)
    setShowDescriptorModal(false)
    // The card will pick up that hasDescriptor is now true and can proceed
  }

  // Update outfit in state when visualization completes
  const handleVisualizationComplete = (outfitId: string, url: string) => {
    setOutfits(prev => prev.map(outfit =>
      (outfit.id === outfitId || outfit.outfit_id === outfitId)
        ? { ...outfit, visualization_url: url }
        : outfit
    ))
  }

  // Handle mark as worn button click
  const handleMarkAsWorn = (outfitId: string) => {
    setPendingWornOutfitId(outfitId)
    setShowWornModal(true)
  }

  // Handle worn tracking complete
  const handleWornComplete = (outfitId: string, wornAt: string, photoUrl?: string) => {
    setOutfits(prev => prev.map(outfit =>
      (outfit.id === outfitId || outfit.outfit_id === outfitId)
        ? { ...outfit, worn_at: wornAt, worn_photo_url: photoUrl }
        : outfit
    ))
    setShowWornModal(false)
    setPendingWornOutfitId(null)
    // Switch to worn tab to show the outfit there
    setActiveTab('worn')
  }

  // Handle upload photo button click
  const handleUploadPhoto = (outfitId: string) => {
    setPendingPhotoOutfitId(outfitId)
    setShowPhotoModal(true)
  }

  // Handle photo upload complete
  const handlePhotoComplete = (outfitId: string, photoUrl: string) => {
    setOutfits(prev => prev.map(outfit =>
      (outfit.id === outfitId || outfit.outfit_id === outfitId)
        ? { ...outfit, worn_photo_url: photoUrl }
        : outfit
    ))
    setShowPhotoModal(false)
    setPendingPhotoOutfitId(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center page-container">
        <div className="text-center px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta mx-auto mb-4"></div>
          <p className="text-ink text-base font-medium">Loading saved outfits...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bone page-container">
        <div className="max-w-2xl mx-auto px-4 py-6 md:py-8">
          <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
            &larr; Back
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 md:p-6">
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bone page-container">
      <div className="max-w-2xl mx-auto px-4 py-4 md:py-8">
        <Link href={`/?user=${user}`} className="text-terracotta mb-4 inline-block min-h-[44px] flex items-center">
          &larr; Back
        </Link>

        <h1 className="text-2xl md:text-3xl font-bold mb-2">Saved Outfits</h1>
        <p className="text-muted mb-4 text-base leading-relaxed">
          {outfits.length === 0
            ? "You haven't saved any outfits yet. Save outfits you love from the reveal page!"
            : `${outfits.length} saved outfit${outfits.length === 1 ? '' : 's'}`}
        </p>

        {outfits.length > 0 && (
          <>
            {/* Tabs */}
            <div className="flex border-b border-[rgba(26,22,20,0.12)] mb-5 md:mb-8">
              <button
                onClick={() => setActiveTab('not_worn')}
                className={`flex-1 py-3 text-center font-medium text-base min-h-[48px] transition-colors ${
                  activeTab === 'not_worn'
                    ? 'text-ink border-b-2 border-terracotta'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Not Yet Worn ({notWornOutfits.length})
              </button>
              <button
                onClick={() => setActiveTab('worn')}
                className={`flex-1 py-3 text-center font-medium text-base min-h-[48px] transition-colors ${
                  activeTab === 'worn'
                    ? 'text-ink border-b-2 border-terracotta'
                    : 'text-muted hover:text-ink'
                }`}
              >
                Worn ({wornOutfits.length})
              </button>
            </div>

            {/* Outfit List */}
            {displayedOutfits.length === 0 ? (
              <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 md:p-8 text-center shadow-sm">
                <p className="text-muted text-sm md:text-base leading-relaxed">
                  {activeTab === 'not_worn'
                    ? "All your saved outfits have been worn! Nice work."
                    : "No outfits worn yet. Mark an outfit as worn when you try it!"}
                </p>
              </div>
            ) : (
              <div className="space-y-4 md:space-y-6">
                {displayedOutfits.map((saved: any) => {
                  const outfit = saved.outfit_data || saved
                  const outfitId = saved.id || saved.outfit_id
                  return (
                    <VisualizedOutfitCard
                      key={outfitId}
                      outfit={outfit}
                      outfitId={outfitId}
                      outfitName={outfit.vibe_keywords?.[0] || 'Saved Outfit'}
                      visualizationUrl={saved.visualization_url}
                      wornAt={saved.worn_at}
                      wornPhotoUrl={saved.worn_photo_url}
                      user={user}
                      showVisualizeButton={true}
                      showMarkAsWornButton={true}
                      hasDescriptor={hasDescriptor === true}
                      onVisualize={() => handleVisualize(outfitId)}
                      onVisualizationComplete={(url) => handleVisualizationComplete(outfitId, url)}
                      onMarkAsWorn={() => handleMarkAsWorn(outfitId)}
                      onUploadPhoto={() => handleUploadPhoto(outfitId)}
                    />
                  )
                })}
              </div>
            )}
          </>
        )}

        {outfits.length === 0 && (
          <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-6 md:p-8 text-center shadow-sm">
            <p className="text-muted text-sm md:text-base leading-relaxed">No saved outfits yet</p>
          </div>
        )}
      </div>

      {/* Model Descriptor Modal */}
      <ModelDescriptorModal
        isOpen={showDescriptorModal}
        userId={user}
        onClose={() => {
          setShowDescriptorModal(false)
          setPendingVisualizationOutfitId(null)
        }}
        onSaved={handleDescriptorSaved}
      />

      {/* Worn Tracking Modal */}
      {pendingWornOutfitId && (
        <WornTrackingModal
          isOpen={showWornModal}
          outfitId={pendingWornOutfitId}
          userId={user}
          onClose={() => {
            setShowWornModal(false)
            setPendingWornOutfitId(null)
          }}
          onComplete={(wornAt, photoUrl) => handleWornComplete(pendingWornOutfitId, wornAt, photoUrl)}
        />
      )}

      {/* Photo Upload Modal */}
      {pendingPhotoOutfitId && (
        <PhotoUploadModal
          isOpen={showPhotoModal}
          outfitId={pendingPhotoOutfitId}
          userId={user}
          onClose={() => {
            setShowPhotoModal(false)
            setPendingPhotoOutfitId(null)
          }}
          onComplete={(photoUrl) => handlePhotoComplete(pendingPhotoOutfitId, photoUrl)}
        />
      )}
    </div>
  )
}

export default function SavedPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-bone flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-sand border-t-terracotta"></div>
      </div>
    }>
      <SavedPageContent />
    </Suspense>
  )
}
