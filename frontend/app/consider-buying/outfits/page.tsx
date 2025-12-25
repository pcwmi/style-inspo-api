'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { Suspense } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function OutfitsContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const itemId = searchParams.get('item_id')
    const user = searchParams.get('user') || 'default'
    const useExisting = searchParams.get('use_existing') === 'true'
    const debugMode = searchParams.get('debug') === 'true'

    const [generating, setGenerating] = useState(false)
    const [error, setError] = useState('')
    const [decisionMade, setDecisionMade] = useState(false)
    const [feedbackMessage, setFeedbackMessage] = useState('')
    const [decisionType, setDecisionType] = useState<string>('')

    const handleGenerate = async () => {
        if (!itemId) {
            setError('No item selected')
            return
        }

        setGenerating(true)
        setError('')

        try {
            const formData = new FormData()
            formData.append('item_id', itemId)
            formData.append('use_existing_similar', useExisting.toString())
            formData.append('user_id', user)
            formData.append('include_reasoning', debugMode.toString())

            const res = await fetch(`${API_URL}/api/consider-buying/generate-outfits`, {
                method: 'POST',
                body: formData
            })

            if (!res.ok) {
                throw new Error('Failed to generate outfits')
            }

            const data = await res.json()
            const jobId = data.job_id

            if (!jobId) {
                throw new Error('No job_id returned from API')
            }

            // Redirect to reveal page with job_id and debug param
            const debugParam = debugMode ? '&debug=true' : ''
            router.push(`/reveal?user=${user}&job=${jobId}${debugParam}`)

        } catch (err: any) {
            console.error('Error generating outfits:', err)
            setError(err.message || 'Failed to generate outfits. Please try again.')
            setGenerating(false)
        }
    }

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

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-800">{error}</p>
                </div>
            )}

            {generating && (
                <div className="text-center py-4">
                    <p className="text-muted">Starting outfit generation...</p>
                </div>
            )}

            {!generating && !error && (
                <button
                    onClick={handleGenerate}
                    disabled={!itemId}
                    className="w-full bg-terracotta text-white py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 active:opacity-80 transition disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] flex items-center justify-center"
                >
                    Generate Outfits
                </button>
            )}
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
