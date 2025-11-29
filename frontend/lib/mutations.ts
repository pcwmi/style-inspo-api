/**
 * Centralized React Query mutation hooks for data modification
 *
 * Benefits:
 * - Automatic cache invalidation after mutations
 * - Optimistic updates for instant UI feedback
 * - Automatic error handling and retry logic
 * - Loading/success/error states managed automatically
 */

import { useMutation, useQueryClient, UseMutationOptions } from '@tanstack/react-query'
import { api } from './api'
import { queryKeys } from './queries'

/**
 * Upload a wardrobe item
 * Invalidates wardrobe cache after successful upload
 */
export function useUploadItem(userId: string, options?: Omit<UseMutationOptions<any, Error, { file: File; useRealAi: boolean }>, 'mutationFn'>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, useRealAi }: { file: File; useRealAi: boolean }) =>
      api.uploadItem(userId, file, useRealAi),
    onSuccess: () => {
      // Invalidate wardrobe cache to refetch updated data
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobe(userId) })
    },
    ...options,
  })
}

/**
 * Update a wardrobe item
 * Invalidates both item and wardrobe caches
 */
export function useUpdateItem(
  userId: string,
  itemId: string,
  options?: Omit<UseMutationOptions<any, Error, any>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: any) => api.updateItem(userId, itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobeItem(userId, itemId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobe(userId) })
    },
    ...options,
  })
}

/**
 * Delete a wardrobe item
 * Invalidates wardrobe cache and removes item from cache
 */
export function useDeleteItem(
  userId: string,
  itemId: string,
  options?: Omit<UseMutationOptions<any, Error, void>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => api.deleteItem(userId, itemId),
    onSuccess: () => {
      // Remove item from cache
      queryClient.removeQueries({ queryKey: queryKeys.wardrobeItem(userId, itemId) })
      // Invalidate wardrobe list
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobe(userId) })
    },
    ...options,
  })
}

/**
 * Rotate a wardrobe item
 * Invalidates both item and wardrobe caches
 */
export function useRotateItem(
  userId: string,
  itemId: string,
  options?: Omit<UseMutationOptions<any, Error, number>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (degrees: number = 90) => api.rotateItem(userId, itemId, degrees),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobeItem(userId, itemId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.wardrobe(userId) })
    },
    ...options,
  })
}

/**
 * Update user profile
 * Invalidates profile cache
 */
export function useUpdateProfile(
  userId: string,
  options?: Omit<UseMutationOptions<any, Error, { three_words?: Record<string, string>; daily_emotion?: Record<string, string> }>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (profile: { three_words?: Record<string, string>; daily_emotion?: Record<string, string> }) =>
      api.updateProfile(userId, profile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.profile(userId) })
    },
    ...options,
  })
}

/**
 * Save an outfit
 * Invalidates saved outfits cache
 */
export function useSaveOutfit(
  userId: string,
  options?: Omit<UseMutationOptions<any, Error, { outfit: any; feedback?: string[] }>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ outfit, feedback }: { outfit: any; feedback?: string[] }) =>
      api.saveOutfit({ user_id: userId, outfit, feedback }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.savedOutfits(userId) })
    },
    ...options,
  })
}

/**
 * Dislike an outfit
 * Invalidates disliked outfits cache
 */
export function useDislikeOutfit(
  userId: string,
  options?: Omit<UseMutationOptions<any, Error, { outfit: any; reason: string }>, 'mutationFn'>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ outfit, reason }: { outfit: any; reason: string }) =>
      api.dislikeOutfit({ user_id: userId, outfit, reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dislikedOutfits(userId) })
    },
    ...options,
  })
}

/**
 * Generate outfits (async job)
 * Returns job ID for polling with useJobStatus
 */
export function useGenerateOutfits(
  options?: Omit<
    UseMutationOptions<
      any,
      Error,
      {
        user_id: string
        occasions?: string[]
        weather_condition?: string
        temperature_range?: string
        mode: 'occasion' | 'complete'
        anchor_items?: string[]
        mock?: boolean
      }
    >,
    'mutationFn'
  >
) {
  return useMutation({
    mutationFn: (request: {
      user_id: string
      occasions?: string[]
      weather_condition?: string
      temperature_range?: string
      mode: 'occasion' | 'complete'
      anchor_items?: string[]
      mock?: boolean
    }) => api.generateOutfits(request),
    ...options,
  })
}
