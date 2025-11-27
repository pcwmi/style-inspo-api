'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { OutfitCard } from '@/components/OutfitCard'

import { Suspense } from 'react'

function OutfitsContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const itemId = searchParams.get('item_id')
    const user = searchParams.get('user') || 'default'
    const useExisting = searchParams.get('use_existing') === 'true'

    const [outfits, setOutfits] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [decisionMade, setDecisionMade] = useState(false)

    useEffect(() => {
        const generateOutfits = async () => {
            try {
                const formData = new FormData()
                formData.append('item_id', itemId || '')
                formData.append('use_existing_similar', useExisting.toString())
                formData.append('user_id', user)

                const res = await fetch('http://localhost:8000/api/consider-buying/generate-outfits', {
                    method: 'POST',
                    body: formData
                })

                const data = await res.json()
                setOutfits(data.outfits)
            } catch (err) {
                console.error(err)
                setError('Failed to generate outfits')
            } finally {
                setLoading(false)
            }
        }

        if (itemId) {
            generateOutfits()
        }
    }, [itemId, useExisting])

    const handleDecision = async (decision: string) => {
        try {
            await fetch(`http://localhost:8000/api/consider-buying/decide?user_id=${user}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_id: itemId,
                    decision: decision,
                    reason: decision === 'passed' ? 'User decided not to buy' : undefined
                })
            })

            setDecisionMade(true)

            // Redirect to dashboard (root) or closet after a delay
            setTimeout(() => {
                router.push(`/?user=${user}`)
            }, 2000)

        } catch (err) {
            console.error(err)
            alert('Failed to record decision')
        }
    }

    if (loading) return <div>Generating outfits...</div>
    if (error) return <div>{error}</div>

    if (decisionMade) {
        return (
            <div className="container mx-auto px-4 py-8 text-center">
                <h2 className="text-2xl font-bold mb-4">Decision Recorded!</h2>
                <p>Redirecting to dashboard...</p>
            </div>
        )
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold mb-6">Here's how it works with your closet</h2>

            <div className="space-y-8 mb-12">
                {outfits.map((outfit, idx) => (
                    <OutfitCard
                        key={idx}
                        outfit={outfit}
                        user={user}
                        index={idx + 1}
                        allowSave={false}
                        allowDislike={false}
                    />
                ))}
            </div>

            <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 shadow-lg">
                <div className="container mx-auto flex gap-4 max-w-lg">
                    <button
                        onClick={() => handleDecision('bought')}
                        className="flex-1 px-4 py-3 bg-black text-white rounded-lg font-medium"
                    >
                        I bought it!
                    </button>
                    <button
                        onClick={() => handleDecision('passed')}
                        className="flex-1 px-4 py-3 border border-black rounded-lg font-medium"
                    >
                        Not buying
                    </button>
                    <button
                        onClick={() => handleDecision('later')}
                        className="flex-1 px-4 py-3 text-gray-600 font-medium"
                    >
                        Decide later
                    </button>
                </div>
            </div>

            {/* Spacer for fixed bottom bar */}
            <div className="h-24"></div>
        </div>
    )
}

export default function OutfitsPage() {
    return (
        <Suspense fallback={<div>Loading outfits...</div>}>
            <OutfitsContent />
        </Suspense>
    )
}
