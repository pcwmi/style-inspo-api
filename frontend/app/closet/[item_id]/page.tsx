'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import DeleteItemModal from '@/components/DeleteItemModal'

const CATEGORIES = ['Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Shoes', 'Accessories', 'Bags']

function ItemDetailContent() {
    const params = useParams()
    const searchParams = useSearchParams()
    const router = useRouter()
    const user = searchParams.get('user') || 'default'
    const itemId = params.item_id as string

    const [item, setItem] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [isEditing, setIsEditing] = useState(false)
    const [showDeleteModal, setShowDeleteModal] = useState(false)
    const [saving, setSaving] = useState(false)
    const [isConsideringItem, setIsConsideringItem] = useState(false)
    const [deleting, setDeleting] = useState(false)

    // Edit form state
    const [formData, setFormData] = useState({
        name: '',
        category: '',
        colors: '',
        style_tags: '',
        texture: '',
        brand: '',
        cut: '',
        fit: '',
        style: '',
        sub_category: '',
        fabric: '',
        styling_notes: ''
    })

    useEffect(() => {
        // Check if this is a considering item (ID starts with "consider_")
        const isConsidering = itemId.startsWith('consider_')
        setIsConsideringItem(isConsidering)
        fetchItem(isConsidering)
    }, [itemId, user])

    const fetchItem = async (isConsidering: boolean = false) => {
        try {
            setLoading(true)
            if (isConsidering) {
                // Fetch from consider-buying list
                const data = await api.getConsiderBuyingItems(user, 'considering')
                const foundItem = data.items.find((i: any) => i.id === itemId)
                if (!foundItem) {
                    throw new Error('Item not found')
                }
                setItem(foundItem)
                initializeForm(foundItem)
            } else {
                // Fetch from wardrobe
                const data = await api.getItem(user, itemId)
                setItem(data)
                initializeForm(data)
            }
        } catch (err) {
            console.error('Failed to fetch item:', err)
            // router.push(`/closet?user=${user}`)
        } finally {
            setLoading(false)
        }
    }

    const initializeForm = (data: any) => {
        setFormData({
            name: data.styling_details.name || '',
            category: data.styling_details.category || '',
            colors: Array.isArray(data.styling_details.colors)
                ? data.styling_details.colors.join(', ')
                : data.styling_details.colors || '',
            style_tags: (data.usage_metadata?.tags || []).join(', '),
            texture: data.styling_details.texture || '',
            brand: data.styling_details.brand || '',
            cut: data.styling_details.cut || '',
            fit: data.styling_details.fit || '',
            style: data.styling_details.style || '',
            sub_category: data.styling_details.sub_category || '',
            fabric: data.structured_attrs?.fabric || '',
            styling_notes: data.styling_details.styling_notes || ''
        })
    }

    const handleSave = async () => {
        try {
            setSaving(true)
            const updates: any = {
                name: formData.name,
                category: formData.category,
                colors: formData.colors.split(',').map((c: string) => c.trim()).filter(Boolean),
                texture: formData.texture,
                brand: formData.brand,
                cut: formData.cut || undefined,
                fit: formData.fit || undefined,
                style: formData.style || undefined,
                sub_category: formData.sub_category || undefined,
                styling_notes: formData.styling_notes || undefined
            }

            // Only include fabric if it has a value
            if (formData.fabric) {
                updates.fabric = formData.fabric
            }

            // Use different API methods based on item type
            if (isConsideringItem) {
                await api.updateConsideringItem(user, itemId, updates)
            } else {
                await api.updateItem(user, itemId, updates)
            }

            await fetchItem(isConsideringItem)
            setIsEditing(false)
        } catch (err) {
            console.error('Failed to update item:', err)
            alert('Failed to save changes')
        } finally {
            setSaving(false)
        }
    }

    const handleDelete = () => {
        // Navigation after successful delete (actual deletion is handled by DeleteItemModal)
        if (isConsideringItem) {
            router.push(`/closet?user=${user}&category=Considering`)
        } else {
            router.push(`/closet?user=${user}`)
        }
    }

    if (loading) return <div className="p-8 text-center">Loading...</div>
    if (!item) return <div className="p-8 text-center">Item not found</div>

    // Handle image path for both wardrobe items and considering items
    const getImagePath = () => {
        const path = isConsideringItem 
            ? item.image_path 
            : (item.system_metadata?.image_path || item.image_path)
        
        if (!path) return null
        
        if (path.startsWith('http')) {
            return path
        }
        return `/api/images/${path.split('/').pop()}`
    }

    const imagePath = getImagePath()

    return (
        <div className="min-h-screen bg-white pb-24">
            {/* Header */}
            <div className="sticky top-0 bg-white z-10 border-b border-gray-100 flex justify-between items-center p-4">
                {isEditing ? (
                    <button
                        onClick={() => { setIsEditing(false); initializeForm(item); }}
                        className="text-gray-500"
                    >
                        Cancel
                    </button>
                ) : (
                    <Link
                        href={`/closet?user=${user}${searchParams.get('category') ? `&category=${searchParams.get('category')}` : ''}`}
                        className="text-gray-500"
                    >
                        ← Back to Closet
                    </Link>
                )}

                {isEditing ? (
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="text-blue-600 font-medium disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save'}
                    </button>
                ) : (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="text-blue-600 font-medium"
                    >
                        Edit
                    </button>
                )}
            </div>

            <div className="max-w-md mx-auto">
                {/* Image */}
                {imagePath && (
                    <div className="aspect-[3/4] bg-gray-50 w-full relative">
                        <img
                            src={imagePath}
                            alt={item.styling_details?.name || 'Item'}
                            className="w-full h-full object-contain"
                        />
                    </div>
                )}

                {/* Rotate Button (Edit Mode Only) */}
                {isEditing && (
                    <div className="px-6 pt-4">
                        <button
                            onClick={async () => {
                                try {
                                    setSaving(true)
                                    const res = isConsideringItem
                                        ? await api.rotateConsideringItem(user, itemId)
                                        : await api.rotateItem(user, itemId)
                                    // Force image refresh by updating item with new path
                                    if (isConsideringItem) {
                                        setItem((prev: any) => ({
                                            ...prev,
                                            image_path: res.new_image_path
                                        }))
                                    } else {
                                        setItem((prev: any) => ({
                                            ...prev,
                                            system_metadata: {
                                                ...prev.system_metadata,
                                                image_path: res.new_image_path
                                            }
                                        }))
                                    }
                                } catch (err) {
                                    console.error('Failed to rotate item:', err)
                                    alert('Failed to rotate image')
                                } finally {
                                    setSaving(false)
                                }
                            }}
                            disabled={saving}
                            className="w-full py-2 text-gray-700 font-medium border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2 text-sm"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
                                <path d="M21 3v5h-5" />
                            </svg>
                            Rotate Image 90°
                        </button>
                    </div>
                )}

                {/* Content */}
                <div className="p-6 space-y-6">
                    {isEditing ? (
                        // Edit Mode
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                <select
                                    value={formData.category}
                                    onChange={e => setFormData({ ...formData, category: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg bg-white"
                                >
                                    {CATEGORIES.map(cat => (
                                        <option key={cat} value={cat.toLowerCase()}>{cat}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Colors</label>
                                <input
                                    type="text"
                                    value={formData.colors}
                                    onChange={e => setFormData({ ...formData, colors: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="Blue, white"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Texture</label>
                                <input
                                    type="text"
                                    value={formData.texture}
                                    onChange={e => setFormData({ ...formData, texture: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Brand</label>
                                <input
                                    type="text"
                                    value={formData.brand}
                                    onChange={e => setFormData({ ...formData, brand: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="Optional"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Cut</label>
                                <input
                                    type="text"
                                    value={formData.cut}
                                    onChange={e => setFormData({ ...formData, cut: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="e.g., regular, cropped, wide-leg"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Fit</label>
                                <input
                                    type="text"
                                    value={formData.fit}
                                    onChange={e => setFormData({ ...formData, fit: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="e.g., fitted, loose, relaxed"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Style</label>
                                <input
                                    type="text"
                                    value={formData.style}
                                    onChange={e => setFormData({ ...formData, style: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="e.g., casual, formal, minimalist"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Sub Category</label>
                                <input
                                    type="text"
                                    value={formData.sub_category}
                                    onChange={e => setFormData({ ...formData, sub_category: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="e.g., tee, jeans, blazer"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Fabric</label>
                                <input
                                    type="text"
                                    value={formData.fabric}
                                    onChange={e => setFormData({ ...formData, fabric: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    placeholder="e.g., cotton, wool, silk"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Styling Notes</label>
                                <textarea
                                    value={formData.styling_notes}
                                    onChange={e => setFormData({ ...formData, styling_notes: e.target.value })}
                                    className="w-full p-3 border border-gray-200 rounded-lg"
                                    rows={4}
                                    placeholder="AI-generated styling suggestions..."
                                />
                            </div>

                            {/* AI Override Notice */}
                            {(formData.name !== item.styling_details.name || formData.category !== item.styling_details.category) && (
                                <div className="bg-yellow-50 p-3 rounded-lg text-sm text-yellow-800 flex gap-2">
                                    <span>💡</span>
                                    <div>
                                        <p className="font-medium">AI detected: "{item.styling_details.name}"</p>
                                        <p>You are correcting this information.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        // View Mode
                        <div className="space-y-6">
                            <div>
                                <h1 className="text-2xl font-serif font-semibold mb-1">{item.styling_details?.name || 'Unnamed Item'}</h1>
                                <p className="text-gray-500 capitalize">{item.styling_details?.category || 'Unknown'}</p>
                            </div>

                            {/* Source URL (for considering items) */}
                            {isConsideringItem && item.source_url && (
                                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                                    <h3 className="text-sm font-medium text-gray-900 mb-2">🔗 Source URL</h3>
                                    <a 
                                        href={item.source_url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline text-sm break-all"
                                    >
                                        {item.source_url}
                                    </a>
                                </div>
                            )}

                            {/* Price (for considering items) */}
                            {isConsideringItem && item.price && (
                                <div className="bg-green-50 p-4 rounded-lg border border-green-100">
                                    <span className="text-sm text-gray-500">Price: </span>
                                    <span className="text-lg font-semibold text-green-700">${item.price.toFixed(2)}</span>
                                </div>
                            )}

                            {/* Metadata Grid */}
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-500 block mb-1">Colors</span>
                                    <span className="font-medium">
                                        {Array.isArray(item.styling_details?.colors)
                                            ? item.styling_details.colors.join(', ')
                                            : item.styling_details?.colors || 'Unknown'}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-500 block mb-1">Texture</span>
                                    <span className="font-medium capitalize">{item.styling_details?.texture || 'Unknown'}</span>
                                </div>
                                {item.styling_details?.brand && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Brand</span>
                                        <span className="font-medium">{item.styling_details.brand}</span>
                                    </div>
                                )}
                                {item.styling_details?.cut && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Cut</span>
                                        <span className="font-medium capitalize">{item.styling_details.cut}</span>
                                    </div>
                                )}
                                {item.styling_details?.fit && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Fit</span>
                                        <span className="font-medium capitalize">{item.styling_details.fit}</span>
                                    </div>
                                )}
                                {item.styling_details?.style && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Style</span>
                                        <span className="font-medium capitalize">{item.styling_details.style}</span>
                                    </div>
                                )}
                                {item.structured_attrs?.fabric && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Fabric</span>
                                        <span className="font-medium capitalize">{item.structured_attrs.fabric}</span>
                                    </div>
                                )}
                                {item.structured_attrs?.subcategory && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Subcategory</span>
                                        <span className="font-medium capitalize">{item.structured_attrs.subcategory}</span>
                                    </div>
                                )}
                            </div>

                            {item.styling_details?.styling_notes && (
                                <div className="border-t border-b border-gray-100 py-4">
                                    <h3 className="text-sm font-medium text-gray-900 mb-2">📝 AI Styling Notes</h3>
                                    <p className="text-gray-600 text-sm leading-relaxed">
                                        {item.styling_details.styling_notes}
                                    </p>
                                </div>
                            )}

                            {/* Delete Button - only for considering items */}
                            {isConsideringItem && (
                                <button
                                    onClick={() => setShowDeleteModal(true)}
                                    disabled={deleting}
                                    className="w-full py-3 text-red-600 font-medium border border-red-100 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                                >
                                    {deleting ? 'Deleting...' : 'Delete from Considering'}
                                </button>
                            )}
                            
                            {/* Delete Button - for wardrobe items */}
                            {!isConsideringItem && (
                                <button
                                    onClick={() => setShowDeleteModal(true)}
                                    className="w-full py-3 text-red-600 font-medium border border-red-100 rounded-lg hover:bg-red-50 transition-colors"
                                >
                                    Delete Item
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <DeleteItemModal
                isOpen={showDeleteModal}
                onClose={() => setShowDeleteModal(false)}
                onDelete={handleDelete}
                item={item}
                user={user}
            />
        </div>
    )
}

export default function ItemDetailPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading item...</div>}>
            <ItemDetailContent />
        </Suspense>
    )
}
