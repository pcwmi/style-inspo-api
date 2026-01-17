'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { api } from '@/lib/api'
import { posthog } from '@/lib/posthog'

interface OutfitCardProps {
    outfit: any
    user: string
    index: number
    allowSave?: boolean
    allowDislike?: boolean
}

export function OutfitCard({ outfit, user, index, allowSave = true, allowDislike = true }: OutfitCardProps) {
    const [saving, setSaving] = useState(false)
    const [disliking, setDisliking] = useState(false)
    const [selectedFeedback, setSelectedFeedback] = useState<string[]>([])
    const [dislikeReason, setDislikeReason] = useState('')
    const [otherReasonText, setOtherReasonText] = useState('')
    const [savedOutfitId, setSavedOutfitId] = useState<string | null>(null)

    const handleSave = async () => {
        try {
            const response = await api.saveOutfit({
                user_id: user,
                outfit,
                feedback: selectedFeedback
            })
            posthog.capture('outfit_saved', {
                outfit_id: response.outfit_id,
                feedback: selectedFeedback
            })
            // Store the saved outfit ID to show visualization CTA
            setSavedOutfitId(response.outfit_id)
            setSaving(false)
        } catch (error) {
            console.error('Error saving outfit:', error)
            alert('Failed to save outfit')
            setSaving(false)
        }
    }

    const handleDislike = async () => {
        setDisliking(true)
        try {
            await api.dislikeOutfit({
                user_id: user,
                outfit,
                reason: dislikeReason === 'Other' ? `Other: ${otherReasonText}` : dislikeReason
            })
            posthog.capture('outfit_disliked', {
                outfit_id: outfit.id,
                reason: dislikeReason === 'Other' ? `Other: ${otherReasonText}` : dislikeReason
            })
            alert('Feedback recorded')
            setDisliking(false)
        } catch (error) {
            console.error('Error disliking outfit:', error)
            alert('Failed to record feedback')
            setDisliking(false)
        }
    }

    return (
        <div className="bg-white border border-[rgba(26,22,20,0.12)] rounded-lg p-4 md:p-6 mb-4 md:mb-6 shadow-sm">
            <h2 className="text-lg md:text-xl font-semibold mb-3 md:mb-4">Outfit {index}</h2>

            {/* Outfit images */}
            <div className="grid grid-cols-3 gap-2 mb-4">
                {outfit.items.map((item: any, idx: number) => {
                    const imagePath = item.system_metadata?.image_path || item.image_path
                    const isConsidering = item.id?.startsWith('consider_')
                    const isSynthetic = !imagePath && item.category === "unknown"
                    const itemName = item.name || `Item ${idx + 1}`

                    return (
                        <div key={idx} className={`relative aspect-square rounded overflow-hidden ${
                            isSynthetic
                                ? 'bg-gradient-to-br from-sand to-bone border-2 border-dashed border-terracotta/30'
                                : 'bg-sand'
                        }`}>
                            {/* Considering badge */}
                            {isConsidering && (
                                <div className="absolute top-2 right-2 bg-terracotta backdrop-blur-sm px-2 py-0.5 rounded-full z-10">
                                    <span className="text-xs font-medium text-white">Considering</span>
                                </div>
                            )}
                            {isSynthetic ? (
                                <>
                                    {/* "Suggested" badge */}
                                    <div className="absolute top-2 left-2 right-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-md shadow-sm">
                                        <div className="flex items-center gap-1.5 justify-center">
                                            <svg className="w-3 h-3 text-terracotta" viewBox="0 0 24 24" fill="currentColor">
                                                <path d="M12 0L14.59 8.41L23 11L14.59 13.59L12 22L9.41 13.59L1 11L9.41 8.41L12 0Z"/>
                                            </svg>
                                            <span className="text-[10px] font-medium text-terracotta uppercase tracking-wide">
                                                Suggested
                                            </span>
                                        </div>
                                    </div>
                                    {/* Item name */}
                                    <div className="absolute inset-0 flex items-center justify-center p-3 pt-10">
                                        <p className="text-center text-sm font-medium text-ink leading-tight">
                                            {itemName}
                                        </p>
                                    </div>
                                </>
                            ) : imagePath ? (
                                imagePath.startsWith('http') ? (
                                    <img
                                        src={imagePath}
                                        alt={itemName}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <Image
                                        src={imagePath.startsWith('/') ? imagePath : `/${imagePath}`}
                                        alt={itemName}
                                        fill
                                        className="object-cover"
                                    />
                                )
                            ) : null}
                        </div>
                    )
                })}
            </div>

            {/* Styling notes */}
            <div className="mb-3 md:mb-4">
                <h3 className="font-semibold mb-2 text-base">How to Style</h3>
                <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.styling_notes}</p>
            </div>

            {/* Why it works */}
            <div className="mb-3 md:mb-4">
                <h3 className="font-semibold mb-2 text-base">Why This Works</h3>
                <p className="text-ink text-sm md:text-base leading-relaxed">{outfit.why_it_works}</p>
            </div>

            {/* Actions */}
            {(allowSave || allowDislike) && (
                <>
                    {savedOutfitId ? (
                        // Saved state - show success and visualization CTA
                        <div className="mt-4 border-t border-[rgba(26,22,20,0.12)] pt-4">
                            <div className="flex items-center gap-2 mb-4 text-green-700">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span className="font-medium">Outfit saved!</span>
                            </div>
                            <Link
                                href={`/saved?user=${user}`}
                                className="w-full bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center gap-2"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                See it on a model
                            </Link>
                        </div>
                    ) : !saving && !disliking ? (
                        <div className="flex gap-3">
                            {allowSave && (
                                <button
                                    onClick={() => setSaving(true)}
                                    className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
                                >
                                    Save Outfit
                                </button>
                            )}
                            {allowDislike && (
                                <button
                                    onClick={() => setDisliking(true)}
                                    className="px-6 py-3 border border-[rgba(26,22,20,0.12)] rounded-lg hover:bg-sand/30 active:bg-sand/50 min-h-[48px] min-w-[48px] flex items-center justify-center"
                                >
                                    👎
                                </button>
                            )}
                        </div>
                    ) : saving ? (
                        <div className="mt-4 border-t border-[rgba(26,22,20,0.12)] pt-4">
                            <h3 className="text-lg font-semibold mb-4">What do you love about it?</h3>
                            <div className="space-y-2.5 mb-4">
                                {['Perfect for my occasions', 'Feels authentic to my style', 'Never thought to combine these pieces', 'Love the vibe'].map(option => (
                                    <label key={option} className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
                                        <input
                                            type="checkbox"
                                            checked={selectedFeedback.includes(option)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedFeedback([...selectedFeedback, option])
                                                } else {
                                                    setSelectedFeedback(selectedFeedback.filter(f => f !== option))
                                                }
                                            }}
                                            className="w-5 h-5 rounded border-[rgba(26,22,20,0.12)] flex-shrink-0"
                                        />
                                        <span className="text-base leading-relaxed flex-1">{option}</span>
                                    </label>
                                ))}
                            </div>
                            <div className="flex flex-col sm:flex-row gap-3">
                                <button
                                    onClick={handleSave}
                                    className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
                                >
                                    Save
                                </button>
                                <button
                                    onClick={() => setSaving(false)}
                                    className="flex-1 bg-sand text-ink py-3 px-6 rounded-lg hover:bg-sand/80 active:bg-sand/70 min-h-[48px] flex items-center justify-center"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="mt-4 border-t border-[rgba(26,22,20,0.12)] pt-4">
                            <h3 className="text-lg font-semibold mb-4">What's the main issue?</h3>
                            <div className="space-y-2.5 mb-4">
                                {["Won't look good on me", "Doesn't match my occasions", "Not my style", "The outfit doesn't make sense", "Other"].map(option => (
                                    <label key={option} className="flex items-center space-x-3 cursor-pointer min-h-[44px] py-1">
                                        <input
                                            type="radio"
                                            name="dislike-reason"
                                            value={option}
                                            checked={dislikeReason === option}
                                            onChange={(e) => setDislikeReason(e.target.value)}
                                            className="w-5 h-5 flex-shrink-0"
                                        />
                                        <span className="text-base leading-relaxed flex-1">{option}</span>
                                    </label>
                                ))}
                            </div>
                            {dislikeReason === 'Other' && (
                                <input
                                    type="text"
                                    placeholder="Please specify..."
                                    value={otherReasonText}
                                    onChange={(e) => setOtherReasonText(e.target.value)}
                                    className="w-full px-4 py-3 border border-[rgba(26,22,20,0.12)] rounded-lg mb-4 text-base bg-white"
                                />
                            )}
                            <div className="flex flex-col sm:flex-row gap-3">
                                <button
                                    onClick={handleDislike}
                                    className="flex-1 bg-terracotta text-white py-3 px-6 rounded-lg hover:opacity-90 active:opacity-80 min-h-[48px] flex items-center justify-center"
                                >
                                    Submit
                                </button>
                                <button
                                    onClick={() => setDisliking(false)}
                                    className="flex-1 bg-sand text-ink py-3 px-6 rounded-lg hover:bg-sand/80 active:bg-sand/70 min-h-[48px] flex items-center justify-center"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
