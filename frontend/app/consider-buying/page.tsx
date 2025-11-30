'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { api } from '@/lib/api'

import { Suspense } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
    const [passedItems, setPassedItems] = useState<any[]>([])
    const [stats, setStats] = useState<any>(null)
    const [analyzing, setAnalyzing] = useState(false)

    const handlePasteLink = async () => {
        if (!url) return

        setLoading(true)
        setError('')
        setExtractedData(null)
        setAnalyzedItem(null)
        setSelectedCategory('')

        try {
            // Step 1: Extract from URL
            const extractRes = await fetch(`${API_URL}/api/consider-buying/extract-url?user_id=${user}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            })

            // Check if response is OK before parsing JSON
            if (!extractRes.ok) {
                const errorText = await extractRes.text()
                console.error("Extract URL failed with status:", extractRes.status, errorText)
                throw new Error(`Failed to fetch: ${extractRes.status} ${errorText}`)
            }

            const extractData = await extractRes.json()
            console.log("Extract response:", extractData)

            // Check success field instead of response status
            if (!extractData.success) {
                // If extraction fails (e.g. Sezane, Reformation), show screenshot upload
                console.log("Extraction failed, showing screenshot upload", extractData.error)
                setError(extractData.error || 'Could not extract product details automatically.')
                setShowScreenshotUpload(true)
                setLoading(false)
                return
            }

            // Show extracted data immediately (progressive display)
            setExtractedData(extractData.data)
            setLoading(false) // Stop initial loading, show extracted data
            
            // Step 2: Send image URL to backend (backend will download it to avoid CORS/mixed content issues)
            const imageUrl = extractData.data.image_url
            if (!imageUrl) {
                throw new Error('No image URL found in extraction result')
            }

            console.log('Using image URL (backend will download):', imageUrl)

            // Start analyzing state
            setAnalyzing(true)

            // Create FormData - pass image_url instead of downloading client-side
            // This avoids CORS and mixed content issues (HTTP images on HTTPS pages)
            const formData = new FormData()
            formData.append('image_url', imageUrl)
            if (extractData.data.price) {
                formData.append('price', extractData.data.price.toString())
            }
            if (extractData.data.title) {
                formData.append('name', extractData.data.title)
            }
            if (extractData.data.brand) {
                formData.append('brand', extractData.data.brand)
            }
            if (selectedCategory) {
                formData.append('category', selectedCategory)
            }
            formData.append('source_url', url)
            formData.append('user_id', user)

            // Step 3: Add item (image analysis)
            const analyzeRes = await fetch(`${API_URL}/api/consider-buying/add-item`, {
                method: 'POST',
                body: formData
            })

            if (!analyzeRes.ok) {
                const errorData = await analyzeRes.json().catch(() => ({}))
                throw new Error(errorData.detail || 'Failed to analyze item')
            }

            const analyzeData = await analyzeRes.json()
            setAnalyzedItem(analyzeData)
            setExtractedData(null) // Hide extracted data, show full analysis
            setAnalyzing(false)

        } catch (err: any) {
            console.error("Error in handlePasteLink:", err)
            setError(err.message || 'An error occurred. Please try again.')
            setAnalyzing(false)
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

            const res = await fetch(`${API_URL}/api/consider-buying/add-item`, {
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

    // Load passed items and stats on mount
    useEffect(() => {
        const loadPassedItems = async () => {
            try {
                const data = await api.getConsiderBuyingItems(user, 'passed')
                setPassedItems(data.items || [])
                
                // Also get stats
                const statsRes = await fetch(`${API_URL}/api/consider-buying/stats?user_id=${user}`)
                if (statsRes.ok) {
                    const statsData = await statsRes.json()
                    setStats(statsData)
                }
            } catch (err) {
                console.error('Failed to load passed items:', err)
            }
        }
        loadPassedItems()
    }, [user])

    return (
        <div className="min-h-screen bg-bone page-container">
            <div className="max-w-md mx-auto px-4 py-8">
                <h1 className="text-2xl font-serif mb-6 text-center">Buy Smarter</h1>

                {/* Extracted Data View (Progressive Display) */}
                {extractedData && !analyzedItem && (
                    <div className="mb-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
                        <div className="bg-white p-6 rounded-lg shadow-sm border border-[rgba(26,22,20,0.12)]">
                            <h3 className="font-bold mb-4 text-gray-800">Product Found!</h3>
                            <div className="flex gap-4 mb-4">
                                {extractedData.image_url && (
                                    <div className="relative w-24 h-32 rounded overflow-hidden flex-shrink-0 bg-gray-100">
                                        <img
                                            src={extractedData.image_url}
                                            alt="Product"
                                            className="w-full h-full object-cover"
                                            onError={(e) => {
                                                // Hide image if it fails to load
                                                e.currentTarget.style.display = 'none'
                                            }}
                                        />
                                    </div>
                                )}
                                <div className="flex-1">
                                    <p className="font-medium text-lg mb-2">{extractedData.title || 'Product'}</p>
                                    <div className="space-y-1 text-sm text-gray-700">
                                        {extractedData.brand && (
                                            <p><strong>Brand:</strong> {extractedData.brand}</p>
                                        )}
                                        {extractedData.price && (
                                            <p><strong>Price:</strong> ${extractedData.price}</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                            {analyzing && (
                                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                        <p className="text-sm text-blue-800">Analyzing image and finding similar items...</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Initial View: URL Input or Screenshot Upload */}
                {!analyzedItem && !extractedData && (
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
                                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-black file:text-white hover:file:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
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
                            <div className="flex gap-4 mb-4">
                                <div className="relative w-32 h-40 rounded overflow-hidden flex-shrink-0 bg-gray-100">
                                    {analyzedItem.item.image_path ? (
                                        analyzedItem.item.image_path.startsWith('http') ? (
                                            <img
                                                src={analyzedItem.item.image_path}
                                                alt="Analyzed Item"
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <Image
                                                src={`/api/images/${analyzedItem.item.image_path.split('/').pop()}`}
                                                alt="Analyzed Item"
                                                fill
                                                className="object-cover"
                                            />
                                        )
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                                            No Image
                                        </div>
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-lg mb-2">{analyzedItem.item.styling_details.name}</p>
                                    <div className="mt-2 space-y-1 text-sm text-gray-700 bg-white p-3 rounded border border-green-100 max-h-60 overflow-y-auto">
                                        <p><strong>Category:</strong> {analyzedItem.item.styling_details.category}</p>
                                        <p><strong>Subcategory:</strong> {analyzedItem.item.styling_details.sub_category}</p>
                                        {analyzedItem.item.styling_details.colors && (
                                            <p><strong>Colors:</strong> {Array.isArray(analyzedItem.item.styling_details.colors) 
                                                ? analyzedItem.item.styling_details.colors.join(', ') 
                                                : analyzedItem.item.styling_details.colors}</p>
                                        )}
                                        {analyzedItem.item.price && (
                                            <p><strong>Price:</strong> ${analyzedItem.item.price}</p>
                                        )}
                                        {analyzedItem.item.styling_details.brand && (
                                            <p><strong>Brand:</strong> {analyzedItem.item.styling_details.brand}</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={handleAddItem}
                                className="w-full mt-4 px-6 py-3 bg-black text-white rounded-lg font-medium hover:bg-gray-800 transition-colors"
                            >
                                Continue to Similar Items
                            </button>
                        </div>
                    </div>
                )}

                {/* Save $$ Section - Show passed items */}
                {passedItems.length > 0 && (
                    <div className="mt-8">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold">Save $$</h2>
                            {stats && (
                                <p className="text-sm text-gray-600">
                                    Total saved: ${stats.total_saved?.toFixed(2) || '0.00'}
                                </p>
                            )}
                        </div>
                        <div className="bg-white rounded-lg border border-[rgba(26,22,20,0.12)] p-4">
                            <p className="text-sm text-gray-600 mb-4">
                                Items you decided not to buy ({passedItems.length})
                            </p>
                            <div className="grid grid-cols-3 gap-3">
                                {passedItems.map((item) => (
                                    <div key={item.id} className="relative aspect-square rounded overflow-hidden">
                                        <Image
                                            src={item.image_path.startsWith('http')
                                                ? item.image_path
                                                : `/api/images/${item.image_path.split('/').pop()}`}
                                            alt={item.styling_details.name}
                                            fill
                                            className="object-cover"
                                        />
                                        {item.price && (
                                            <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-1 text-center">
                                                ${item.price}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default function ConsiderBuyingPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <ConsiderBuyingContent />
        </Suspense>
    )
}
