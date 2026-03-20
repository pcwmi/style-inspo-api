/**
 * Onboarding check utilities
 */

import { api } from './api'

export type OnboardingStep = 'welcome' | 'words' | 'upload' | 'complete'

/**
 * Check if user has completed onboarding from pre-fetched data.
 * Returns true if both profile and wardrobe meet requirements.
 * Returns true on null data (defensive: show dashboard rather than redirect on API failure).
 */
export function checkOnboardingComplete(profile: any, wardrobe: any): boolean {
  // If data failed to load, assume complete (show dashboard, don't redirect)
  if (!profile && !wardrobe) return true

  const hasProfile = profile?.three_words &&
    profile.three_words.current &&
    profile.three_words.aspirational &&
    profile.three_words.feeling

  const hasWardrobe = wardrobe && wardrobe.count >= 10

  return !!(hasProfile && hasWardrobe)
}

/**
 * Determine which onboarding step user should be on from pre-fetched data.
 */
export function getOnboardingStepFromData(profile: any, wardrobe: any): OnboardingStep {
  const hasProfile = profile?.three_words &&
    profile.three_words.current &&
    profile.three_words.aspirational &&
    profile.three_words.feeling

  const wardrobeCount = wardrobe?.count || 0

  if (!hasProfile && wardrobeCount < 10) {
    return 'welcome'
  } else if (!hasProfile) {
    return 'words'
  } else if (wardrobeCount < 10) {
    return 'upload'
  } else {
    return 'complete'
  }
}

/**
 * Check if user has completed onboarding via API calls.
 * Used by pages other than the dashboard (which should use checkOnboardingComplete instead).
 */
export async function isOnboardingComplete(userId: string): Promise<boolean> {
  try {
    const [profile, wardrobe] = await Promise.all([
      api.getProfile(userId).catch(() => null),
      api.getWardrobe(userId).catch(() => null)
    ])

    return checkOnboardingComplete(profile, wardrobe)
  } catch (error) {
    console.error('Error checking onboarding status:', error)
    // Default to true (show dashboard) on error
    return true
  }
}

/**
 * Determine which onboarding step user should be on via API calls.
 * Used by pages other than the dashboard (which should use getOnboardingStepFromData instead).
 */
export async function getOnboardingStep(userId: string): Promise<OnboardingStep> {
  try {
    const [profile, wardrobe] = await Promise.all([
      api.getProfile(userId).catch(() => null),
      api.getWardrobe(userId).catch(() => null)
    ])

    return getOnboardingStepFromData(profile, wardrobe)
  } catch (error) {
    console.error('Error determining onboarding step:', error)
    return 'welcome'
  }
}



