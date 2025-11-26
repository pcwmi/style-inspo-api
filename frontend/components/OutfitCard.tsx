'use client'

import { useState } from 'react'
import Image from 'next/image'
import { api } from '@/lib/api'

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

    const handleSave = async () => {
        setSaving(true)
        try {
            await api.saveOutfit({
                user_id: user,
                outfit,
                feedback: selectedFeedback
            })
            alert('Outfit saved!')
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

                    return (
                        <div key={idx} className="relative aspect-square rounded overflow-hidden bg-sand">
                            {imagePath ? (
                                imagePath.startsWith('http') ? (
                                    <img
                                        src={imagePath}
                                        alt={item.name}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <Image
                                        src={imagePath.startsWith('/') ? imagePath : `/${imagePath}`}
                                        alt={item.name}
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
                    {!saving && !disliking ? (
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
