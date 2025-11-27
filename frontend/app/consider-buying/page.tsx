'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { api } from '@/lib/api'

import { Suspense } from 'react'

function ConsiderBuyingContent() {
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

            if (!extractRes.ok) {
                // If extraction fails (e.g. Sezane), show screenshot upload
                console.log("Extraction failed, showing screenshot upload")
                setError(extractData.detail || 'Could not extract product details automatically.')
                setShowScreenshotUpload(true)
                setLoading(false)
                return
            }

            setExtractedData(extractData)

            // Step 2: Analyze Item
            // If we have a category override, pass it
            const analyzeBody: any = {
                ...extractData,
                user_id: user
            }
            if (selectedCategory) {
                analyzeBody.category = selectedCategory
            }

            const analyzeRes = await fetch('http://localhost:8000/api/consider-buying/add-item', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(analyzeBody)
            })

            if (!analyzeRes.ok) {
                throw new Error('Failed to analyze item')
            }

            const analyzeData = await analyzeRes.json()
            setAnalyzedItem(analyzeData)

        } catch (err: any) {
            console.error("Error in handlePasteLink:", err)
            setError(err.message || 'An error occurred. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleAddItem = async () => {
        if (!analyzedItem) return
        // Navigate to similar items view
        sessionStorage.setItem('consider_buying_item', JSON.stringify(analyzedItem))
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
        <div className="min-h-screen bg-bone page-container">
            <div className="max-w-md mx-auto px-4 py-8">
                <h1 className="text-2xl font-serif mb-6 text-center">Buy Smarter</h1>

                {/* Initial View: URL Input or Screenshot Upload */}
                {!analyzedItem && (
                    <div className="bg-white p-6 rounded-lg shadow-sm border border-[rgba(26,22,20,0.12)]">
                        <p className="text-gray-600 mb-4 text-center">
                            Paste a product link or upload a screenshot to see how it fits with your closet.
                        </p>

                        {!showScreenshotUpload ? (
                            <>
                                <div className="flex gap-2 mb-4">
                                    <input
                                        type="url"
                                        placeholder="Paste product URL..."
                                        className="flex-1 p-3 border rounded-lg bg-gray-50 focus:bg-white focus:ring-2 focus:ring-black outline-none transition-all"
                                        value={url}
                                        onChange={(e) => setUrl(e.target.value)}
                                        disabled={loading}
                                    />
                                    <button
                                        onClick={handlePasteLink}
                                        disabled={loading || !url}
                                        className="bg-black text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-gray-800 transition-colors"
                                    >
                                        {loading ? '...' : 'Analyze'}
                                    </button>
                                </div>

                                {error && (
                                    <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                                        {error}
                                        {/* If it's a specific extraction error, suggest screenshot */}
                                        <div className="mt-2">
                                            <button
                                                onClick={() => setShowScreenshotUpload(true)}
                                                className="text-black underline font-medium hover:text-gray-700"
                                            >
                                                Try uploading a screenshot instead
                                            </button>
                                        </div>
                                    </div>
                                )}

                                <div className="relative my-6">
                                    <div className="absolute inset-0 flex items-center">
                                        <div className="w-full border-t border-gray-200"></div>
                                    </div>
                                    <div className="relative flex justify-center text-sm">
                                        <span className="px-2 bg-white text-gray-500">or</span>
                                    </div>
                                </div>

                                <button
                                    onClick={() => setShowScreenshotUpload(true)}
                                    className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-black hover:text-black transition-colors font-medium"
                                >
                                    Upload Screenshot
                                </button>
                            </>
                        ) : (
                            <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
                                <h3 className="font-medium mb-3 text-center">Upload Screenshot</h3>
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
                                    className="mt-4 text-sm text-gray-500 hover:text-black underline w-full text-center"
                                >
                                    Cancel
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Analysis Result View */}
                {analyzedItem && (
                    <div className="animate-in fade-in slide-in-from-bottom-8 duration-500">
                        <div className="mb-8 border rounded-lg p-4 bg-green-50 border-green-200">
                            <h3 className="font-bold mb-4 text-green-800">Analysis Complete!</h3>
                            <div className="flex gap-4">
                                <div className="relative w-32 h-40 rounded overflow-hidden">
                                    <Image
                                        src={analyzedItem.item.image_path.startsWith('http')
                                            ? analyzedItem.item.image_path
                                            : `/api/images/${analyzedItem.item.image_path.split('/').pop()}`}
                                        alt="Analyzed Item"
                                        fill
                                        className="object-cover"
                                    />
                                    {/* Cleanup Button */}
                                    <button
                                        onClick={async (e) => {
                                            e.preventDefault()
                                            e.stopPropagation()
                                            if (!analyzedItem?.item?.id) return

                                            try {
                                                setLoading(true)
                                                // 1. Get current image as blob/file
                                                const imgPath = analyzedItem.item.image_path.startsWith('http')
                                                    ? analyzedItem.item.image_path
                                                    : `/api/images/${analyzedItem.item.image_path.split('/').pop()}`

                                                const imgRes = await fetch(imgPath)
                                                const imgBlob = await imgRes.blob()
                                                const imgFile = new File([imgBlob], "image.png", { type: "image/png" })

                                                // 2. Remove background (assuming 'api' is imported or defined elsewhere)
                                                const cleanedBlob = await api.removeBackground(imgFile, user)

                                                // 3. Update item with new image
                                                const cleanedFile = new File([cleanedBlob], "cleaned.png", { type: "image/png" })
                                                const updateRes = await api.updateConsiderBuyingImage(analyzedItem.item.id, cleanedFile, user)

                                                // 4. Update state
                                                setAnalyzedItem((prev: any) => ({
                                                    ...prev,
                                                    item: {
                                                        ...prev.item,
                                                        image_path: updateRes.image_path,
                                                        system_metadata: {
                                                            ...prev.item.system_metadata,
                                                            image_path: updateRes.image_path
                                                        }
                                                    }
                                                }))

                                            } catch (err) {
                                                console.error("Cleanup failed:", err)
                                                setError("Failed to clean up image")
                                            } finally {
                                                setLoading(false)
                                            }
                                        }}
                                        className="absolute top-2 right-2 bg-white/90 hover:bg-white text-ink p-2 rounded-full shadow-sm transition-all z-10"
                                        title="Remove background"
                                        disabled={loading}
                                    >
                                        {loading ? (
                                            <div className="w-5 h-5 border-2 border-ink border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <span className="text-lg">✨</span>
                                        )}
                                    </button>
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-lg">{analyzedItem.item.styling_details.name}</p>
                                    <div className="mt-2 space-y-1 text-sm text-gray-700 bg-white p-3 rounded border border-green-100 max-h-60 overflow-y-auto">
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
