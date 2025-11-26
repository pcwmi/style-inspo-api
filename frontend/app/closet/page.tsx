'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import UploadModal from '@/components/UploadModal'
import PhotoGuidelines from '@/components/PhotoGuidelines'

const CATEGORIES = ['All', 'Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Shoes', 'Accessories', 'Considering']

import { Suspense } from 'react'

function ClosetContent() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const user = searchParams.get('user') || 'default'

    const [items, setItems] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [activeCategory, setActiveCategory] = useState('All')
    const [showUploadModal, setShowUploadModal] = useState(false)
    const [showGuidelines, setShowGuidelines] = useState(false)
    const [analyzingCount, setAnalyzingCount] = useState(0)

    // Sync activeCategory with URL param on mount and when param changes
    useEffect(() => {
        const categoryParam = searchParams.get('category')
        if (categoryParam) {
            // Validate category exists in our list (case insensitive check)
            const matchedCategory = CATEGORIES.find(c => c.toLowerCase() === categoryParam.toLowerCase())
            if (matchedCategory) {
                setActiveCategory(matchedCategory)
            }
        } else {
            setActiveCategory('All')
        }
    }, [searchParams])

    const handleCategoryClick = (cat: string) => {
        let newCategory = cat

        // Toggle behavior: if clicking active category, reset to All
        if (activeCategory === cat) {
            newCategory = 'All'
        }

        setActiveCategory(newCategory)

        // Update URL
        const params = new URLSearchParams(searchParams.toString())
        if (newCategory === 'All') {
            params.delete('category')
        } else {
            params.set('category', newCategory)
        }

        // Use push to add to history stack so back button works
        router.push(`?${params.toString()}`, { scroll: false })
    }

    useEffect(() => {
        fetchWardrobe()
    }, [user, activeCategory])

    const fetchWardrobe = async () => {
        try {
            setLoading(true)
            if (activeCategory === 'Considering') {
                const data = await api.getConsiderBuyingItems(user, 'considering')
                setItems(data.items || [])
            } else {
                const data = await api.getWardrobe(user)
                setItems(data.items || [])
            }
        } catch (err) {
            console.error('Failed to fetch wardrobe:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleAddClick = () => {
        const hasSeenGuidelines = localStorage.getItem(`photo_guidelines_seen_${user}`)
        if (!hasSeenGuidelines) {
            setShowGuidelines(true)
        } else {
            setShowUploadModal(true)
        }
    }

    const handleGuidelinesContinue = () => {
        localStorage.setItem(`photo_guidelines_seen_${user}`, 'true')
        setShowGuidelines(false)
        setShowUploadModal(true)
    }

    const handleUploadComplete = (count: number, jobIds: string[]) => {
        setAnalyzingCount(count)

        // Poll for updates using job IDs
        const checkJobs = async () => {
            let allComplete = true
            for (const jobId of jobIds) {
                try {
                    const status = await api.getJobStatus(jobId)
                    if (status.status !== 'complete' && status.status !== 'failed') {
                        allComplete = false
                    }
                } catch (e) {
                    console.error('Error checking job:', e)
                }
            }

            // Refresh wardrobe to see new items
            await fetchWardrobe()

            if (!allComplete) {
                setTimeout(checkJobs, 2000)
            } else {
                setAnalyzingCount(0)
            }
        }

        checkJobs()
    }

    const CATEGORY_ALIASES: Record<string, string[]> = {
        'Shoes': ['footwear'],
    }

    const matchesCategory = (item: any, category: string) => {
        if (category === 'All') return true
        const itemCat = item.styling_details.category.toLowerCase()
        const targetCat = category.toLowerCase()

        if (itemCat === targetCat) return true

        const aliases = CATEGORY_ALIASES[category]
        if (aliases && aliases.includes(itemCat)) return true

        return false
    }

    const filteredItems = items.filter(item => matchesCategory(item, activeCategory))

    const getCategoryCount = (cat: string) => {
        return items.filter(item => matchesCategory(item, cat)).length
    }

    return (
        <div className="min-h-screen bg-white pb-24">
            {/* Header */}
            <div className="sticky top-0 bg-white z-10 border-b border-gray-100">
                <div className="flex items-center p-4">
                    <Link href={`/?user=${user}`} className="text-gray-500 mr-4">
                        ←
                    </Link>
                    <h1 className="text-xl font-serif font-semibold">My Closet</h1>
                </div>

                {/* Category Tabs */}
                <div className="flex overflow-x-auto hide-scrollbar px-4 pb-2 gap-2">
                    {CATEGORIES.map(cat => (
                        <button
                            key={cat}
                            onClick={() => handleCategoryClick(cat)}
                            className={`flex-shrink-0 flex items-center whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-colors ${activeCategory === cat
                                ? 'bg-black text-white'
                                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {cat} <span className="opacity-60 text-xs ml-2">{getCategoryCount(cat)}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Analyzing Banner */}
            {analyzingCount > 0 && (
                <div className="bg-blue-50 px-4 py-3 flex items-center justify-between animate-pulse">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">📸</span>
                        <span className="text-sm text-blue-800 font-medium">
                            Analyzing {analyzingCount} photos...
                        </span>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="p-4">
                {loading ? (
                    <div className="grid grid-cols-3 gap-4">
                        {[1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="aspect-[3/4] bg-gray-100 rounded-lg animate-pulse" />
                        ))}
                    </div>
                ) : items.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="text-6xl mb-4">👗</div>
                        <h3 className="text-xl font-serif font-medium mb-2">Your closet is empty</h3>
                        <p className="text-gray-500 mb-8 max-w-xs mx-auto">
                            Let's start building! Add your favorite pieces so I can help you style them.
                        </p>
                        <button
                            onClick={handleAddClick}
                            className="bg-black text-white px-8 py-3 rounded-full font-medium shadow-lg hover:scale-105 transition-transform"
                        >
                            📷 Add to Closet
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        {filteredItems.map(item => (
                            <Link
                                key={item.id}
                                href={`/closet/${item.id}?user=${user}`}
                                className="group relative block aspect-[3/4] bg-gray-50 rounded-lg overflow-hidden"
                            >
                                {(() => {
                                    const imagePath = item.system_metadata?.image_path || item.image_path
                                    if (!imagePath) {
                                        return (
                                            <div className="w-full h-full flex items-center justify-center text-gray-300">
                                                No Image
                                            </div>
                                        )
                                    }
                                    return (
                                        <img
                                            src={imagePath.startsWith('http')
                                                ? imagePath
                                                : `/api/images/${imagePath.split('/').pop()}`} // Fallback for local dev
                                            alt={item.styling_details?.name || 'Item'}
                                            className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                        />
                                    )
                                })()}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                                    <span className="text-white text-xs font-medium truncate w-full">
                                        {item.styling_details?.name || 'Item'}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>

            {/* Floating Add Button */}
            {items.length > 0 && (
                <button
                    onClick={handleAddClick}
                    className="fixed bottom-6 right-6 w-14 h-14 bg-black text-white rounded-full shadow-xl flex items-center justify-center text-2xl hover:scale-105 transition-transform z-40"
                    style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
                >
                    +
                </button>
            )}

            {/* Modals */}
            <PhotoGuidelines
                isOpen={showGuidelines}
                onClose={() => setShowGuidelines(false)}
                onContinue={handleGuidelinesContinue}
            />

            <UploadModal
                isOpen={showUploadModal}
                onClose={() => setShowUploadModal(false)}
                onUploadComplete={handleUploadComplete}
                user={user}
            />
        </div>
    )
}

export default function ClosetPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading closet...</div>}>
            <ClosetContent />
        </Suspense>
    )
}
