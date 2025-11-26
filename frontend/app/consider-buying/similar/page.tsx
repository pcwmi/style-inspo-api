'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function SimilarItemsPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const itemId = searchParams.get('item_id')
    const user = searchParams.get('user') || 'default'

    const [item, setItem] = useState<any>(null)
    const [similarItems, setSimilarItems] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Fetch item data (stored in sessionStorage from previous page)
        const itemData = sessionStorage.getItem('consider_buying_item')
        if (itemData) {
            const parsed = JSON.parse(itemData)
            setItem(parsed.item)
            setSimilarItems(parsed.similar_items || [])
            setLoading(false)
        }
    }, [itemId])

    const handleShowExisting = () => {
        // Generate outfits with existing similar items
        router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=true&user=${user}`)
    }

    const handleContinueWithNew = () => {
        // Generate outfits with new item
        router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=false&user=${user}`)
    }

    if (loading) return <div>Loading...</div>

    if (similarItems.length === 0) {
        // No similar items - auto-proceed to outfit generation
        router.push(`/consider-buying/outfits?item_id=${itemId}&use_existing=false&user=${user}`)
        return null
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h2 className="text-2xl font-bold mb-2">You already own similar items</h2>
            <p className="text-gray-600 mb-6">
                These might work for what you're looking for
            </p>

            <div className="grid grid-cols-3 gap-4 mb-8">
                {similarItems.map((similar, idx) => (
                    <div key={idx} className="border rounded-lg p-4">
                        <img
                            src={similar.item.system_metadata.image_path}
                            alt={similar.item.styling_details.name}
                            className="w-full h-48 object-cover rounded mb-2"
                        />
                        <h3 className="font-medium">{similar.item.styling_details.name}</h3>
                        <p className="text-sm text-gray-500">
                            {Math.round(similar.similarity_score * 100)}% similar
                        </p>
                        <p className="text-xs text-gray-400">{similar.reason}</p>
                    </div>
                ))}
            </div>

            <div className="flex gap-4">
                <button
                    onClick={handleShowExisting}
                    className="flex-1 px-6 py-3 border border-black rounded-lg hover:bg-gray-50"
                >
                    Show outfits with my existing items
                </button>
                <button
                    onClick={handleContinueWithNew}
                    className="flex-1 px-6 py-3 bg-black text-white rounded-lg"
                >
                    Continue with new item
                </button>
            </div>
        </div>
    )
}
