'use client'

import { useEffect } from 'react'
import {
  TIP_URL,
  TIP_AMOUNT_LABEL,
  tipEnabled,
  markTipPromptShown,
  trackTipShown,
  trackTipClicked,
  trackTipDismissed,
} from '@/lib/tip'

interface EnergyTipModalProps {
  isOpen: boolean
  reason: string
  onClose: () => void
  headline?: string
  subline?: string
}

export function EnergyTipModal({
  isOpen,
  reason,
  onClose,
  headline = 'Glad that worked.',
  subline = 'If StyleInspo gave you good energy today, you can tip the maker.',
}: EnergyTipModalProps) {
  useEffect(() => {
    if (isOpen && tipEnabled()) {
      trackTipShown(reason)
      markTipPromptShown()
    }
  }, [isOpen, reason])

  if (!isOpen || !tipEnabled()) return null

  const handleTip = () => {
    trackTipClicked(reason)
    if (typeof window !== 'undefined') {
      window.open(TIP_URL, '_blank', 'noopener,noreferrer')
    }
    onClose()
  }

  const handleDismiss = () => {
    trackTipDismissed(reason)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white w-full sm:max-w-md sm:rounded-lg rounded-t-2xl p-6 shadow-xl">
        <h2 className="text-xl font-semibold mb-2">{headline}</h2>
        <p className="text-muted mb-6 leading-relaxed">{subline}</p>

        <div className="space-y-3">
          <button
            onClick={handleTip}
            className="w-full bg-terracotta text-white py-3.5 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center gap-2"
          >
            Tip {TIP_AMOUNT_LABEL}
          </button>
          <button
            onClick={handleDismiss}
            className="w-full text-muted py-2 text-sm hover:text-ink transition min-h-[44px]"
          >
            Not today
          </button>
        </div>
      </div>
    </div>
  )
}

export function SupportLink({ reason = 'footer', className = '' }: { reason?: string; className?: string }) {
  if (!tipEnabled()) return null
  return (
    <a
      href={TIP_URL}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => trackTipClicked(reason)}
      className={
        className ||
        'text-muted hover:text-terracotta transition text-sm flex items-center gap-2'
      }
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 016.364 0L12 7.636l1.318-1.318a4.5 4.5 0 116.364 6.364L12 20.364l-7.682-7.682a4.5 4.5 0 010-6.364z" />
      </svg>
      Support StyleInspo
    </a>
  )
}
