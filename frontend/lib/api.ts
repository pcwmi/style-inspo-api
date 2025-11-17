/**
 * API client for Style Inspo backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = {
  // Wardrobe
  async getWardrobe(userId: string) {
    const res = await fetch(`${API_URL}/api/wardrobe/${userId}`)
    if (!res.ok) throw new Error('Failed to fetch wardrobe')
    return res.json()
  },

  async uploadItem(userId: string, file: File, useRealAi: boolean = true) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('use_real_ai', String(useRealAi))

    const res = await fetch(`${API_URL}/api/wardrobe/${userId}/upload`, {
      method: 'POST',
      body: formData
    })
    
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(errorData.detail || errorData.message || `Upload failed: ${res.status} ${res.statusText}`)
    }
    
    return res.json()
  },

  async deleteItem(userId: string, itemId: string) {
    const res = await fetch(`${API_URL}/api/wardrobe/${userId}/items/${itemId}`, {
      method: 'DELETE'
    })
    if (!res.ok) throw new Error('Failed to delete item')
    return res.json()
  },

  // Outfits
  async generateOutfits(request: {
    user_id: string
    occasions?: string[]
    weather_condition?: string
    temperature_range?: string
    mode: 'occasion' | 'complete'
    anchor_items?: string[]
  }) {
    const res = await fetch(`${API_URL}/api/outfits/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!res.ok) throw new Error('Failed to generate outfits')
    return res.json()
  },

  async getJobStatus(jobId: string) {
    const res = await fetch(`${API_URL}/api/jobs/${jobId}`)
    if (!res.ok) throw new Error('Failed to get job status')
    return res.json()
  },

  async saveOutfit(request: {
    user_id: string
    outfit: any
    feedback?: string[]
  }) {
    const res = await fetch(`${API_URL}/api/outfits/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!res.ok) throw new Error('Failed to save outfit')
    return res.json()
  },

  async dislikeOutfit(request: {
    user_id: string
    outfit: any
    reason: string
  }) {
    const res = await fetch(`${API_URL}/api/outfits/dislike`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    })
    if (!res.ok) throw new Error('Failed to dislike outfit')
    return res.json()
  },

  // Profile
  async getProfile(userId: string) {
    const res = await fetch(`${API_URL}/api/users/${userId}/profile`)
    if (!res.ok) throw new Error('Failed to fetch profile')
    return res.json()
  },

  async updateProfile(userId: string, profile: {
    three_words?: Record<string, string>
    daily_emotion?: Record<string, string>
  }) {
    const res = await fetch(`${API_URL}/api/users/${userId}/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    })
    if (!res.ok) throw new Error('Failed to update profile')
    return res.json()
  },

  // Saved/Disliked Outfits
  async getSavedOutfits(userId: string) {
    const res = await fetch(`${API_URL}/api/outfits/${userId}/saved`)
    if (!res.ok) throw new Error('Failed to fetch saved outfits')
    return res.json()
  },

  async getDislikedOutfits(userId: string) {
    const res = await fetch(`${API_URL}/api/outfits/${userId}/disliked`)
    if (!res.ok) throw new Error('Failed to fetch disliked outfits')
    return res.json()
  }
}

