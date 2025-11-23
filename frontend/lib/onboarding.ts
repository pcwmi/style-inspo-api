/**
 * Onboarding check utilities
 */

import { api } from './api'

export type OnboardingStep = 'welcome' | 'words' | 'upload' | 'complete'

/**
 * Check if user has completed onboarding
 * Onboarding is complete if:
 * - Profile exists with three_words (all 3 keys: current, aspirational, feeling)
 * - Wardrobe has 10+ items
 */
export async function isOnboardingComplete(userId: string): Promise<boolean> {
  try {
    const [profile, wardrobe] = await Promise.all([
      api.getProfile(userId).catch(() => null),
      api.getWardrobe(userId).catch(() => null)
    ])

    // Check profile has three_words with all required keys
    const hasProfile = profile?.three_words && 
      profile.three_words.current &&
      profile.three_words.aspirational &&
      profile.three_words.feeling

    // Check wardrobe has 10+ items
    const hasWardrobe = wardrobe && wardrobe.count >= 10

    return !!(hasProfile && hasWardrobe)
  } catch (error) {
    console.error('Error checking onboarding status:', error)
    // Default to false (show onboarding) on error
    return false
  }
}

/**
 * Determine which onboarding step user should be on
 */
export async function getOnboardingStep(userId: string): Promise<OnboardingStep> {
  try {
    const [profile, wardrobe] = await Promise.all([
      api.getProfile(userId).catch(() => null),
      api.getWardrobe(userId).catch(() => null)
    ])

    const hasProfile = profile?.three_words && 
      profile.three_words.current &&
      profile.three_words.aspirational &&
      profile.three_words.feeling

    const wardrobeCount = wardrobe?.count || 0

    // Determine step based on what's missing
    if (!hasProfile && wardrobeCount < 10) {
      return 'welcome'
    } else if (!hasProfile) {
      return 'words'
    } else if (wardrobeCount < 10) {
      return 'upload'
    } else {
      return 'complete'
    }
  } catch (error) {
    console.error('Error determining onboarding step:', error)
    // Default to welcome on error
    return 'welcome'
  }
}


