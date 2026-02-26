'use client'

import { useState, useRef, useEffect } from 'react'

interface ShareImageGeneratorProps {
  visualizationUrl: string
  wornPhotoUrl: string
  outfitName?: string
  onShare?: () => void
}

export function ShareImageGenerator({
  visualizationUrl,
  wornPhotoUrl,
  outfitName,
  onShare
}: ShareImageGeneratorProps) {
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const generateAndShare = async () => {
    if (!canvasRef.current) return

    setGenerating(true)
    setError(null)

    try {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) throw new Error('Could not get canvas context')

      // Canvas dimensions (optimized for Instagram stories - 1080x1920)
      const width = 1080
      const height = 1350  // 4:5 aspect ratio for Instagram feed
      canvas.width = width
      canvas.height = height

      // Load both images
      const [vizImg, wornImg] = await Promise.all([
        loadImage(visualizationUrl),
        loadImage(wornPhotoUrl)
      ])

      // Background gradient
      const gradient = ctx.createLinearGradient(0, 0, 0, height)
      gradient.addColorStop(0, '#FAF9F7')  // bone color
      gradient.addColorStop(1, '#F5F0EB')  // sand color
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, width, height)

      // Header area
      ctx.fillStyle = '#1a1614'  // ink color
      ctx.font = 'bold 48px system-ui, -apple-system, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('StyleInspo', width / 2, 80)

      ctx.font = '32px system-ui, -apple-system, sans-serif'
      ctx.fillStyle = '#666'
      ctx.fillText('"AI planned it \u2192 I wore it"', width / 2, 130)

      // Image area dimensions
      const imageY = 180
      const imageHeight = 900
      const imageWidth = (width - 60) / 2  // 20px padding on each side, 20px gap
      const gap = 20
      const leftX = 20
      const rightX = leftX + imageWidth + gap

      // Labels above images
      ctx.font = '28px system-ui, -apple-system, sans-serif'
      ctx.fillStyle = '#666'
      ctx.textAlign = 'center'
      ctx.fillText('The Plan', leftX + imageWidth / 2, imageY - 15)
      ctx.fillText('The Reality', rightX + imageWidth / 2, imageY - 15)

      // Draw images with rounded corners
      drawRoundedImage(ctx, vizImg, leftX, imageY, imageWidth, imageHeight, 20)
      drawRoundedImage(ctx, wornImg, rightX, imageY, imageWidth, imageHeight, 20)

      // Footer
      ctx.fillStyle = '#666'
      ctx.font = '24px system-ui, -apple-system, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('styleinspo.vercel.app', width / 2, height - 30)

      // Convert to blob and share
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setError('Failed to generate image')
          setGenerating(false)
          return
        }

        // Check if Web Share API is supported
        if (navigator.share && navigator.canShare) {
          const file = new File([blob], 'styleinspo-outfit.png', { type: 'image/png' })
          const shareData = {
            files: [file],
            title: 'My StyleInspo Outfit',
            text: outfitName ? `Check out this outfit: ${outfitName}` : 'Check out this outfit I planned with StyleInspo!'
          }

          if (navigator.canShare(shareData)) {
            try {
              await navigator.share(shareData)
              if (onShare) onShare()
            } catch (e: any) {
              if (e.name !== 'AbortError') {
                // User cancelled, not an error
                console.error('Share failed:', e)
                setError('Share failed. Try downloading instead.')
              }
            }
          } else {
            // Fallback: download the image
            downloadImage(blob)
          }
        } else {
          // Fallback: download the image
          downloadImage(blob)
        }
        setGenerating(false)
      }, 'image/png', 0.95)

    } catch (e: any) {
      console.error('Error generating share image:', e)
      setError(e.message || 'Failed to generate image')
      setGenerating(false)
    }
  }

  const loadImage = (src: string): Promise<HTMLImageElement> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => resolve(img)
      img.onerror = () => reject(new Error(`Failed to load image: ${src}`))
      img.src = src
    })
  }

  const drawRoundedImage = (
    ctx: CanvasRenderingContext2D,
    img: HTMLImageElement,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number
  ) => {
    // Create rounded rect path
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + width - radius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
    ctx.lineTo(x + width, y + height - radius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    ctx.lineTo(x + radius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()

    // Clip to rounded rect and draw image
    ctx.save()
    ctx.clip()

    // Calculate crop to cover the area while maintaining aspect ratio
    const imgAspect = img.width / img.height
    const boxAspect = width / height

    let sx = 0, sy = 0, sw = img.width, sh = img.height

    if (imgAspect > boxAspect) {
      // Image is wider - crop sides
      sw = img.height * boxAspect
      sx = (img.width - sw) / 2
    } else {
      // Image is taller - crop top/bottom
      sh = img.width / boxAspect
      sy = (img.height - sh) / 2
    }

    ctx.drawImage(img, sx, sy, sw, sh, x, y, width, height)
    ctx.restore()

    // Draw border
    ctx.strokeStyle = 'rgba(26, 22, 20, 0.1)'
    ctx.lineWidth = 2
    ctx.stroke()
  }

  const downloadImage = (blob: Blob) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'styleinspo-outfit.png'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <button
        onClick={generateAndShare}
        disabled={generating}
        className="w-full bg-white border-2 border-ink text-ink py-3 px-6 rounded-lg hover:bg-sand transition active:bg-sand/80 min-h-[48px] flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {generating ? (
          <span className="animate-spin">...</span>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            Share
          </>
        )}
      </button>

      {error && (
        <p className="mt-2 text-sm text-red-500 text-center">{error}</p>
      )}

      {/* Hidden canvas for image generation */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </>
  )
}
