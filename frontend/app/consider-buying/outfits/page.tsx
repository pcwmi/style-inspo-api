'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { OutfitCard } from '@/components/OutfitCard'

import { Suspense } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function OutfitsContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const itemId = searchParams.get('item_id')
    const user = searchParams.get('user') || 'default'
    const useExisting = searchParams.get('use_existing') === 'true'
    const debugMode = searchParams.get('debug') === 'true'

    const [outfits, setOutfits] = useState<any[]>([])
    const [reasoning, setReasoning] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [decisionMade, setDecisionMade] = useState(false)
    const [feedbackMessage, setFeedbackMessage] = useState('')
    const [decisionType, setDecisionType] = useState<string>('')

    useEffect(() => {
        const generateOutfits = async () => {
            try {
                const formData = new FormData()
                formData.append('item_id', itemId || '')
                formData.append('use_existing_similar', useExisting.toString())
                formData.append('user_id', user)
                formData.append('include_reasoning', debugMode.toString())

                const res = await fetch(`${API_URL}/api/consider-buying/generate-outfits`, {
                    method: 'POST',
                    body: formData
                })

                if (!res.ok) throw new Error('Failed to generate outfits')

                const data = await res.json()
                setOutfits(data.outfits)
                
                // Store reasoning if present
                if (debugMode && data.reasoning) {
                    setReasoning(data.reasoning)
                }
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
    }, [itemId, useExisting, debugMode])

    const handleDecision = async (decision: string) => {
        try {
            const res = await fetch(`${API_URL}/api/consider-buying/decide?user_id=${user}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_id: itemId,
                    decision: decision,
                    reason: decision === 'passed' ? 'User decided not to buy' : undefined
                })
            })

            const data = await res.json()
            const itemName = data.item?.name || 'Item'
            const itemPrice = data.item?.price || 0

            // Set feedback message based on decision
            let message = ''
            if (decision === 'bought') {
                message = `${itemName} is added to your closet`
            } else if (decision === 'passed') {
                message = `Great, $${itemPrice.toFixed(2)} saved`
            } else if (decision === 'later') {
                message = `${itemName} is added to your Considering section of closet`
            }

            setFeedbackMessage(message)
            setDecisionType(decision)
            setDecisionMade(true)

            // Redirect to dashboard after showing feedback
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
                <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-4">
                    <h2 className="text-2xl font-bold mb-2 text-green-800">✓ {feedbackMessage}</h2>
                </div>
                <p className="text-gray-600">Returning to dashboard...</p>
            </div>
        )
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Debug mode indicator */}
            {debugMode && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800">
                        🐛 Debug Mode Active - Showing AI reasoning
                    </p>
                </div>
            )}

            <h2 className="text-2xl font-bold mb-6">Here's how it works with your closet</h2>

            {/* Show reasoning if debug mode is on */}
            {debugMode && reasoning ? (
                <div className="space-y-6 mb-8">
                    <div className="bg-white rounded-lg shadow-sm border border-sand p-6">
                        <h2 className="text-lg font-semibold text-ink mb-4">
                            Chain-of-Thought Reasoning
                        </h2>
                        <pre className="whitespace-pre-wrap text-sm text-muted font-mono bg-bone p-4 rounded border border-sand overflow-x-auto max-h-96 overflow-y-auto">
                            {reasoning}
                        </pre>
                    </div>

                    {/* Still show outfits below reasoning */}
                    <div className="border-t border-sand pt-6">
                        <h2 className="text-lg font-semibold text-ink mb-4">
                            Final Outfits
                        </h2>
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
                    </div>
                </div>
            ) : (
                /* Normal mode: just show outfit cards */
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
            )}

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
