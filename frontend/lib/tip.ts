import { posthog } from './posthog'

export const TIP_URL = process.env.NEXT_PUBLIC_TIP_URL || ''
export const TIP_AMOUNT_LABEL = process.env.NEXT_PUBLIC_TIP_AMOUNT_LABEL || '$10'

const COOLDOWN_KEY = 'styleinspo_tip_last_shown_at'
const COOLDOWN_MS = 1000 * 60 * 60 * 24 * 7 // 7 days

export function tipEnabled(): boolean {
  return Boolean(TIP_URL)
}

export function canShowTipPrompt(): boolean {
  if (!tipEnabled()) return false
  if (typeof window === 'undefined') return false
  try {
    const last = window.localStorage.getItem(COOLDOWN_KEY)
    if (!last) return true
    const lastMs = Number(last)
    if (Number.isNaN(lastMs)) return true
    return Date.now() - lastMs > COOLDOWN_MS
  } catch {
    return true
  }
}

export function markTipPromptShown(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(COOLDOWN_KEY, String(Date.now()))
  } catch {
    // ignore
  }
}

// Atomic claim: returns true once per cooldown window, then locks out other surfaces.
export function tryClaimTipPrompt(): boolean {
  if (!canShowTipPrompt()) return false
  markTipPromptShown()
  return true
}

export function trackTipShown(reason: string, extra: Record<string, any> = {}): void {
  posthog.capture('tip_shown', { reason, ...extra })
}

export function trackTipClicked(reason: string, extra: Record<string, any> = {}): void {
  posthog.capture('tip_clicked', { reason, tip_url: TIP_URL, ...extra })
}

export function trackTipDismissed(reason: string, extra: Record<string, any> = {}): void {
  posthog.capture('tip_dismissed', { reason, ...extra })
}
