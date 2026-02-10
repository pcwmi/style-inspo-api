'use client'

/**
 * Auth hook and context for managing authentication state
 *
 * Provides:
 * - Current user from session cookie
 * - Effective user ID (session-based or URL param fallback)
 * - Loading state during auth check
 * - Logout function
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useSearchParams } from 'next/navigation'
import { authApi, AuthUser, getEffectiveUserId } from './auth'

interface AuthContextType {
  // Current authenticated user (null if not logged in)
  authUser: AuthUser | null
  // Whether auth check is in progress
  loading: boolean
  // Effective user ID for API calls (session or URL fallback)
  effectiveUserId: string
  // Whether user is using legacy URL param (for claim banner)
  isUsingLegacyUrl: boolean
  // Logout function
  logout: () => Promise<void>
  // Refresh auth state
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams()
  const urlUser = searchParams.get('user')

  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = async () => {
    try {
      const user = await authApi.getCurrentUser()
      setAuthUser(user)
    } catch (error) {
      console.error('Error checking auth:', error)
      setAuthUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkAuth()
  }, [])

  const logout = async () => {
    try {
      await authApi.logout()
      setAuthUser(null)
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  const effectiveUserId = getEffectiveUserId(authUser, urlUser)
  const isUsingLegacyUrl = !authUser && !!urlUser

  return (
    <AuthContext.Provider
      value={{
        authUser,
        loading,
        effectiveUserId,
        isUsingLegacyUrl,
        logout,
        refresh: checkAuth
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/**
 * Hook that provides effective user ID for API calls
 * Works in both auth and legacy URL modes
 */
export function useEffectiveUser() {
  const searchParams = useSearchParams()
  const urlUser = searchParams.get('user')
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function check() {
      try {
        const user = await authApi.getCurrentUser()
        setAuthUser(user)
      } catch {
        setAuthUser(null)
      } finally {
        setLoading(false)
      }
    }
    check()
  }, [])

  const effectiveUserId = getEffectiveUserId(authUser, urlUser)
  const isAuthenticated = !!authUser
  const isUsingLegacyUrl = !authUser && !!urlUser

  return {
    effectiveUserId,
    isAuthenticated,
    isUsingLegacyUrl,
    authUser,
    urlUser,
    loading
  }
}
