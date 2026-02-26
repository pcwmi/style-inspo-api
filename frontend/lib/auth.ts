/**
 * Authentication utilities for Style Inspo
 *
 * Handles:
 * - Session management via HTTP-only cookies
 * - Magic link verification
 * - Auth state in React
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface AuthUser {
  user_id: string
  email: string
  legacy_user_id: string | null
}

export interface SendMagicLinkResponse {
  success: boolean
  message: string
}

export interface VerifyTokenResponse {
  success: boolean
  user_id: string
  email: string
  legacy_user_id: string | null
  is_new_user: boolean
}

export const authApi = {
  /**
   * Send magic link email to user
   */
  async sendMagicLink(email: string): Promise<SendMagicLinkResponse> {
    const res = await fetch(`${API_URL}/api/auth/send-magic-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
      credentials: 'include' // Include cookies for session
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Failed to send magic link' }))
      throw new Error(error.detail || 'Failed to send magic link')
    }

    return res.json()
  },

  /**
   * Verify magic link token and establish session
   */
  async verifyToken(token: string): Promise<VerifyTokenResponse> {
    const res = await fetch(`${API_URL}/api/auth/verify?token=${encodeURIComponent(token)}`, {
      method: 'GET',
      credentials: 'include' // Include cookies for session
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Invalid or expired token' }))
      throw new Error(error.detail || 'Invalid or expired token')
    }

    return res.json()
  },

  /**
   * Get current authenticated user from session
   * Returns null if not authenticated
   */
  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const res = await fetch(`${API_URL}/api/auth/me`, {
        method: 'GET',
        credentials: 'include' // Include cookies for session
      })

      if (res.status === 401) {
        return null
      }

      if (!res.ok) {
        return null
      }

      return res.json()
    } catch (error) {
      console.error('Error checking auth status:', error)
      return null
    }
  },

  /**
   * Log out current user
   */
  async logout(): Promise<void> {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include'
    })
  },

  /**
   * Link legacy user ID to current authenticated account
   */
  async linkLegacyUser(legacyUserId: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/auth/link-legacy?legacy_user_id=${encodeURIComponent(legacyUserId)}`, {
      method: 'POST',
      credentials: 'include'
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: 'Failed to link account' }))
      throw new Error(error.detail || 'Failed to link account')
    }
  }
}

/**
 * Get the effective user ID for API calls
 * Prefers session-based auth, falls back to URL param
 */
export function getEffectiveUserId(authUser: AuthUser | null, urlUser: string | null): string {
  // If authenticated, use legacy_user_id (for S3 data) or user_id
  if (authUser) {
    return authUser.legacy_user_id || authUser.user_id
  }

  // Fall back to URL param for transition period
  return urlUser || 'default'
}

/**
 * Build URL with user param for legacy mode, or without for auth mode
 * Used during transition period to support both auth methods
 */
export function buildUserUrl(path: string, authUser: AuthUser | null, effectiveUserId: string): string {
  // If authenticated, no need for URL param
  if (authUser) {
    return path
  }

  // Legacy mode: include user param
  return `${path}?user=${effectiveUserId}`
}
