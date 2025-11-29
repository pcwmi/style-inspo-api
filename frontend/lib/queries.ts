/**
 * Centralized React Query hooks for data fetching
 *
 * Benefits:
 * - Automatic caching (5 min staleTime, 10 min gcTime)
 * - Deduplication (multiple components requesting same data = 1 API call)
 * - Background refetching when data becomes stale
 * - Loading/error states managed automatically
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import { api } from './api'

// Query Keys - centralized to ensure cache consistency
export const queryKeys = {
  wardrobe: (userId: string) => ['wardrobe', userId] as const,
  wardrobeItem: (userId: string, itemId: string) => ['wardrobe', userId, 'item', itemId] as const,
  profile: (userId: string) => ['profile', userId] as const,
  savedOutfits: (userId: string) => ['savedOutfits', userId] as const,
  dislikedOutfits: (userId: string) => ['dislikedOutfits', userId] as const,
  jobStatus: (jobId: string) => ['jobStatus', jobId] as const,
  considerBuying: (userId: string, status?: string) =>
    status ? ['considerBuying', userId, status] : ['considerBuying', userId] as const,
}

/**
 * Fetch user's wardrobe
 * @param userId - User ID
 * @param options - Additional React Query options
 */
export function useWardrobe(userId: string, options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: queryKeys.wardrobe(userId),
    queryFn: () => api.getWardrobe(userId),
    enabled: !!userId, // Only fetch if userId exists
    ...options,
  })
}

/**
 * Fetch a single wardrobe item
 * @param userId - User ID
 * @param itemId - Item ID
 * @param options - Additional React Query options
 */
export function useWardrobeItem(
  userId: string,
  itemId: string,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: queryKeys.wardrobeItem(userId, itemId),
    queryFn: () => api.getItem(userId, itemId),
    enabled: !!userId && !!itemId,
    ...options,
  })
}

/**
 * Fetch user's style profile
 * @param userId - User ID
 * @param options - Additional React Query options
 */
export function useProfile(userId: string, options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: queryKeys.profile(userId),
    queryFn: () => api.getProfile(userId),
    enabled: !!userId,
    ...options,
  })
}

/**
 * Fetch user's saved outfits
 * @param userId - User ID
 * @param options - Additional React Query options
 */
export function useSavedOutfits(userId: string, options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: queryKeys.savedOutfits(userId),
    queryFn: () => api.getSavedOutfits(userId),
    enabled: !!userId,
    ...options,
  })
}

/**
 * Fetch user's disliked outfits
 * @param userId - User ID
 * @param options - Additional React Query options
 */
export function useDislikedOutfits(userId: string, options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: queryKeys.dislikedOutfits(userId),
    queryFn: () => api.getDislikedOutfits(userId),
    enabled: !!userId,
    ...options,
  })
}

/**
 * Poll job status (e.g., outfit generation)
 * @param jobId - Job ID
 * @param options - Additional React Query options (use refetchInterval for polling)
 */
export function useJobStatus(jobId: string, options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>) {
  return useQuery({
    queryKey: queryKeys.jobStatus(jobId),
    queryFn: () => api.getJobStatus(jobId),
    enabled: !!jobId,
    ...options,
  })
}

/**
 * Fetch consider buying items
 * @param userId - User ID
 * @param status - Optional status filter
 * @param options - Additional React Query options
 */
export function useConsiderBuying(
  userId: string,
  status?: string,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: queryKeys.considerBuying(userId, status),
    queryFn: () => api.getConsiderBuyingItems(userId, status),
    enabled: !!userId,
    ...options,
  })
}
