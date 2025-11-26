'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function ConsiderBuyingPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const user = searchParams.get('user') || 'default'
    const [url, setUrl] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [showScreenshotUpload, setShowScreenshotUpload] = useState(false)

    const [extractedData, setExtractedData] = useState<any>(null)
    const [analyzedItem, setAnalyzedItem] = useState<any>(null)
    const [selectedCategory, setSelectedCategory] = useState<string>('')

    const handlePasteLink = async () => {
        if (!url) return

        setLoading(true)
        setError('')
        setExtractedData(null)
        setAnalyzedItem(null)
        setSelectedCategory('')

        try {
            // Step 1: Extract from URL
            const extractRes = await fetch(`http://localhost:8000/api/consider-buying/extract-url?user_id=${user}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            })

            const extractData = await extractRes.json()

            if (!extractData.success) {
                // Extraction failed - show screenshot upload
                setError(extractData.error || "Couldn't extract image from link")
                setShowScreenshotUpload(true)
                setLoading(false)
                return
            }

            // Show extracted data for confirmation
            setExtractedData(extractData.data)
            setLoading(false)

        } catch (err: any) {
            console.error("Error in handlePasteLink:", err)
            setError(err.message || 'An error occurred. Please try again.')
            setShowScreenshotUpload(true)
            setLoading(false)
        }
    }

    const handleAddItem = async () => {
        if (!extractedData) return

        setLoading(true)
        setError('')

        try {
            // Step 2: Add item using image_url
            const formData = new FormData()
            formData.append('image_url', extractedData.image_url)

            if (extractedData.price) {
                formData.append('price', extractedData.price.toString())
            }

            // Pass the extracted title as the name
            if (extractedData.title) {
                formData.append('name', extractedData.title)
            }

            // Pass selected category override if set
            if (selectedCategory) {
                formData.append('category', selectedCategory)
            }

            formData.append('source_url', url)
            formData.append('user_id', user)

            // Step 3: Add item (Analyze)
            const addRes = await fetch('http://localhost:8000/api/consider-buying/add-item', {
                method: 'POST',
                body: formData
            })

            if (!addRes.ok) {
                const errorData = await addRes.json().catch(() => ({}))
                console.error("Add item failed:", errorData)
                throw new Error(errorData.detail || 'Failed to add item')
            }

            const addData = await addRes.json()
            setAnalyzedItem(addData)

        } catch (err: any) {
            console.error("Error in handleAddItem:", err)
            setError(err.message || 'An error occurred. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleContinue = () => {
        if (!analyzedItem) return

        // Store item data in sessionStorage for the next page
        sessionStorage.setItem('consider_buying_item', JSON.stringify(analyzedItem))

        // Navigate to similar items view
        router.push(`/consider-buying/similar?item_id=${analyzedItem.item.id}&user=${user}`)
    }

    const handleScreenshotUpload = async (file: File) => {
        setLoading(true)
        setError('')

        try {
            const formData = new FormData()
            formData.append('image_file', file)
            formData.append('source_url', url || '')
            formData.append('user_id', user)

            const res = await fetch('http://localhost:8000/api/consider-buying/add-item', {
                method: 'POST',
                body: formData
            })

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}))
                console.error("Screenshot upload failed:", errorData)
                throw new Error(errorData.detail || 'Failed to upload screenshot')
            }

            const data = await res.json()

            // Show analysis result instead of redirecting immediately
            setAnalyzedItem(data)
            setShowScreenshotUpload(false) // Switch back to main view to show result

        } catch (err: any) {
            console.error("Error in handleScreenshotUpload:", err)
            setError(err.message || 'An error occurred. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mb-2">Buy Smarter</h1>
            <p className="text-gray-600 mb-8">
                See how it works with your closet before you buy
            </p>

            {!showScreenshotUpload ? (
                <div className="max-w-2xl">
                    <label className="block mb-2 font-medium">
                        Paste product link
                    </label>
                    <div className="flex gap-2 mb-6">
                        <input
                            type="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://zara.com/product/..."
                            className="flex-1 px-4 py-3 border rounded-lg"
                        />
                        <button
                            onClick={handlePasteLink}
                            disabled={loading || !url}
                            className="px-6 py-3 bg-black text-white rounded-lg disabled:opacity-50"
                        >
                            {loading && !extractedData ? 'Extracting...' : 'Extract'}
                        </button>
                    </div>

                    {extractedData && !analyzedItem && (
                        <div className="mb-8 border rounded-lg p-4 bg-gray-50">
                            <h3 className="font-bold mb-4">Extracted Item</h3>
                            <div className="flex gap-4">
                                <img
                                    src={extractedData.image_url}
                                    alt={extractedData.title}
                                    className="w-32 h-40 object-cover rounded"
                                />
                                <div className="flex-1">
                                    <p className="font-medium text-lg">{extractedData.title}</p>
                                    {extractedData.price && (
                                        <p className="text-gray-600 mt-1">${extractedData.price}</p>
                                    )}

                                    <button
                                        onClick={handleAddItem}
                                        disabled={loading}
                                        className="mt-4 px-6 py-2 bg-black text-white rounded-lg w-full md:w-auto"
                                    >
                                        {loading ? 'Analyzing...' : 'Confirm & Analyze'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {analyzedItem && (
                        <div className="mb-8 border rounded-lg p-4 bg-green-50 border-green-200">
                            <h3 className="font-bold mb-4 text-green-800">Analysis Complete!</h3>
                            <div className="flex gap-4">
                                <img
                                    src={analyzedItem.item.system_metadata?.image_path || analyzedItem.item.image_path}
                                    alt={analyzedItem.item.styling_details.name}
                                    className="w-32 h-40 object-cover rounded"
                                />
                                <div className="flex-1">
                                    <p className="font-medium text-lg">{analyzedItem.item.styling_details.name}</p>
                                    <div className="mt-2 space-y-1 text-sm text-gray-700 bg-white p-3 rounded border border-green-100 max-h-60 overflow-y-auto">
                                        {Object.entries(analyzedItem.item.styling_details).map(([key, value]) => {
                                            if (key === 'name' || key === 'image_path' || value === null || value === undefined) return null;

                                            let displayValue = value;
                                            if (Array.isArray(value)) {
                                                displayValue = value.join(', ');
                                            } else if (typeof value === 'object') {
                                                displayValue = JSON.stringify(value);
                                            }

                                            return (
                                                <p key={key} className="break-words">
                                                    <strong className="capitalize">{key.replace(/_/g, ' ')}:</strong> {String(displayValue)}
                                                </p>
                                            );
                                        })}
                                    </div>

                                    <button
                                        onClick={handleContinue}
                                        className="mt-4 px-6 py-2 bg-green-700 text-white rounded-lg w-full md:w-auto hover:bg-green-800"
                                    >
                                        Continue to Outfits →
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                            <p className="text-orange-800">{error}</p>
                            <button
                                onClick={() => setShowScreenshotUpload(true)}
                                className="mt-2 text-orange-600 underline"
                            >
                                Upload screenshot instead
                            </button>
                        </div>
                    )}
                </div>
            ) : (
                <div className="max-w-2xl">
                    <div className="mb-6">
                        <h2 className="text-xl font-bold mb-2">Upload Screenshot</h2>
                        <p className="text-gray-600">
                            {error ? (
                                <span className="text-orange-700 bg-orange-50 px-2 py-1 rounded">
                                    {error.includes("403") || error.includes("CloudFront")
                                        ? "This site blocks automated access. Please upload a screenshot instead."
                                        : error}
                                </span>
                            ) : (
                                "Upload a screenshot of the item you want to add."
                            )}
                        </p>
                    </div>

                    <label className="block mb-2 font-medium">
                        Choose Image
                    </label>
                    <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                            const file = e.target.files?.[0]
                            if (file) handleScreenshotUpload(file)
                        }}
                        className="block w-full text-sm text-gray-500
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-full file:border-0
                            file:text-sm file:font-semibold
                            file:bg-black file:text-white
                            hover:file:bg-gray-800
                            disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={loading}
                    />
                    {loading && <p className="mt-2 text-sm text-gray-600">Analyzing screenshot... this may take a moment.</p>}

                    <button
                        onClick={() => setShowScreenshotUpload(false)}
                        className="mt-6 text-sm text-gray-500 underline"
                    >
                        ← Back to URL paste
                    </button>
                </div>
            )}
        </div>
    )
}
