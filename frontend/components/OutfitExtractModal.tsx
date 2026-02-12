'use client'

import { useState, useRef } from 'react'
import { api } from '@/lib/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Try to import image compression (optional)
let imageCompression: any = null
if (typeof window !== 'undefined') {
  try {
    imageCompression = require('browser-image-compression').default || require('browser-image-compression')
  } catch (e) {
    // Library not installed, will upload without compression
  }
}

interface ExtractedItem {
  item_id: string
  name: string
  category: string
  image_path: string | null
  colors: string | string[]
}

interface OutfitExtractModalProps {
  isOpen: boolean
  userId: string
  onClose: () => void
  onComplete: () => void
}

type ModalPhase = 'idle' | 'uploading' | 'extracting' | 'reviewing' | 'done'

export function OutfitExtractModal({
  isOpen,
  userId,
  onClose,
  onComplete
}: OutfitExtractModalProps) {
  const [phase, setPhase] = useState<ModalPhase>('idle')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [extractedItems, setExtractedItems] = useState<ExtractedItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [removingItems, setRemovingItems] = useState<Set<string>>(new Set())
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!isOpen) return null

  const reset = () => {
    setPhase('idle')
    setPreviewUrl(null)
    setProgress(0)
    setProgressMessage('')
    setExtractedItems([])
    setError(null)
    setRemovingItems(new Set())
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)

    // Show preview
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)

    // Compress
    setPhase('uploading')
    let fileToUpload = file
    if (imageCompression) {
      try {
        fileToUpload = await imageCompression(file, {
          maxSizeMB: 1,
          maxWidthOrHeight: 1920,
          useWebWorker: true,
          preserveExif: true
        })
      } catch {
        fileToUpload = file
      }
    }

    try {
      // Upload
      const result = await api.uploadOutfitPhoto(userId, fileToUpload)

      if (!result.job_id) {
        throw new Error('No job ID returned')
      }

      // Track extraction via SSE
      setPhase('extracting')
      setProgress(20)
      setProgressMessage('Identifying items in outfit photo...')

      const eventSource = new EventSource(`${API_URL}/api/jobs/${result.job_id}/stream`)

      eventSource.addEventListener('progress', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          if (data.progress) setProgress(data.progress)
          if (data.message) setProgressMessage(data.message)
        } catch {}
      })

      eventSource.addEventListener('complete', (event: MessageEvent) => {
        eventSource.close()
        try {
          const data = JSON.parse(event.data)
          // SSE sends job result directly (not wrapped), polling wraps in {result: ...}
          const items = data.items || data.result?.items || []
          setExtractedItems(items)
          setProgress(100)
          setPhase(items.length > 0 ? 'reviewing' : 'done')
          if (items.length === 0) {
            setProgressMessage('No items detected in photo')
          }
        } catch {
          setExtractedItems([])
          setPhase('done')
        }
      })

      eventSource.addEventListener('error', () => {
        eventSource.close()
        // Try polling as fallback
        pollJobStatus(result.job_id)
      })

    } catch (err: any) {
      setError(err.message || 'Failed to upload outfit photo')
      setPhase('idle')
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 60 // 5 min at 5s intervals
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 5000))
      try {
        const status = await api.getJobStatus(jobId)
        if (status.progress) setProgress(status.progress)
        if (status.message) setProgressMessage(status.message)

        if (status.status === 'complete' || status.status === 'finished') {
          const items = status.result?.items || []
          setExtractedItems(items)
          setPhase(items.length > 0 ? 'reviewing' : 'done')
          return
        }
        if (status.status === 'failed') {
          setError(status.error || 'Extraction failed')
          setPhase('idle')
          return
        }
      } catch {
        // Keep polling
      }
    }
    setError('Extraction timed out')
    setPhase('idle')
  }

  const handleRemoveItem = async (itemId: string) => {
    setRemovingItems(prev => new Set(prev).add(itemId))
    try {
      await api.deleteItem(userId, itemId)
      setExtractedItems(prev => prev.filter(i => i.item_id !== itemId))
    } catch (err: any) {
      console.error('Failed to remove item:', err)
    } finally {
      setRemovingItems(prev => {
        const next = new Set(prev)
        next.delete(itemId)
        return next
      })
    }
  }

  const handleDone = () => {
    onComplete()
    handleClose()
  }

  const activeItemCount = extractedItems.length

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-lg sm:rounded-lg rounded-t-2xl shadow-xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-sand/30">
          <h2 className="text-lg font-semibold text-ink">
            {phase === 'idle' && 'Extract from Outfit Photo'}
            {phase === 'uploading' && 'Uploading...'}
            {phase === 'extracting' && 'Extracting Items...'}
            {phase === 'reviewing' && `${activeItemCount} Item${activeItemCount !== 1 ? 's' : ''} Found`}
            {phase === 'done' && 'Done'}
          </h2>
          <button
            onClick={handleClose}
            className="text-muted hover:text-ink text-xl leading-none p-1"
          >
            x
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1">
          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          {/* Phase: Idle - Select photo */}
          {phase === 'idle' && (
            <div>
              <p className="text-muted text-sm mb-4">
                Upload a photo of a full outfit and we'll extract each item into your wardrobe automatically.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                id="outfit-extract-upload"
              />
              <label
                htmlFor="outfit-extract-upload"
                className="block w-full text-center py-3.5 px-6 rounded-lg font-medium bg-terracotta text-white hover:opacity-90 active:opacity-80 cursor-pointer transition min-h-[48px] flex items-center justify-center"
              >
                Choose Outfit Photo
              </label>
            </div>
          )}

          {/* Phase: Uploading */}
          {phase === 'uploading' && (
            <div className="text-center">
              {previewUrl && (
                <img src={previewUrl} alt="Outfit" className="w-full max-h-48 object-contain rounded-lg mb-4" />
              )}
              <div className="animate-spin h-8 w-8 border-3 border-terracotta border-t-transparent rounded-full mx-auto mb-3" />
              <p className="text-muted text-sm">Uploading outfit photo...</p>
            </div>
          )}

          {/* Phase: Extracting */}
          {phase === 'extracting' && (
            <div>
              {previewUrl && (
                <img src={previewUrl} alt="Outfit" className="w-full max-h-48 object-contain rounded-lg mb-4" />
              )}
              <div className="mb-3">
                <div className="flex items-center gap-3 mb-2">
                  <div className="animate-spin h-5 w-5 border-2 border-terracotta border-t-transparent rounded-full" />
                  <span className="text-sm font-medium text-ink">{progressMessage || 'Processing...'}</span>
                </div>
                <div className="w-full bg-sand/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-terracotta h-full rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Phase: Reviewing */}
          {phase === 'reviewing' && (
            <div>
              <p className="text-muted text-sm mb-4">
                These items have been added to your closet. Remove any that don't look right.
              </p>
              <div className="grid grid-cols-3 gap-3">
                {extractedItems.map(item => (
                  <div key={item.item_id} className="relative group">
                    <div className="aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden">
                      {item.image_path ? (
                        <img
                          src={item.image_path.startsWith('http')
                            ? item.image_path
                            : `${API_URL}/api/images/${item.image_path.split('/').pop()}`}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">
                          No preview
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-ink mt-1 truncate">{item.name}</p>
                    <span className="text-[10px] text-muted capitalize">{item.category}</span>
                    <button
                      onClick={() => handleRemoveItem(item.item_id)}
                      disabled={removingItems.has(item.item_id)}
                      className="absolute top-1 right-1 bg-white/90 rounded-full w-6 h-6 flex items-center justify-center text-xs text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                    >
                      {removingItems.has(item.item_id) ? '...' : 'x'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase: Done (no items) */}
          {phase === 'done' && extractedItems.length === 0 && (
            <div className="text-center py-6">
              <p className="text-muted mb-4">No items were detected in this photo. Try a clearer outfit photo.</p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-sand/30">
          {phase === 'reviewing' && (
            <button
              onClick={handleDone}
              className="w-full py-3 rounded-lg font-medium bg-terracotta text-white hover:opacity-90 active:opacity-80 transition"
            >
              Done - View in Closet
            </button>
          )}

          {phase === 'done' && (
            <div className="flex gap-3">
              <button
                onClick={reset}
                className="flex-1 py-3 rounded-lg font-medium border border-terracotta text-terracotta hover:bg-terracotta/5 transition"
              >
                Upload Another
              </button>
              <button
                onClick={handleClose}
                className="flex-1 py-3 rounded-lg font-medium bg-terracotta text-white hover:opacity-90 transition"
              >
                Close
              </button>
            </div>
          )}

          {(phase === 'uploading' || phase === 'extracting') && (
            <button
              onClick={handleClose}
              className="w-full py-3 rounded-lg font-medium text-muted hover:text-ink transition"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
