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

    // Edit form state
    const [formData, setFormData] = useState({
        name: '',
        category: '',
        colors: '',
        style_tags: '',
        texture: '',
        brand: ''
    })

    useEffect(() => {
        fetchItem()
    }, [itemId, user])

    const fetchItem = async () => {
        try {
            setLoading(true)
            const data = await api.getItem(user, itemId)
            setItem(data)
            initializeForm(data)
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
            brand: data.styling_details.brand || ''
        })
    }

    const handleSave = async () => {
        try {
            setSaving(true)
            const updates = {
                name: formData.name,
                category: formData.category,
                colors: formData.colors.split(',').map((c: string) => c.trim()).filter(Boolean),
                texture: formData.texture,
                brand: formData.brand
                // Note: style_tags update might need backend support if not in styling_details
            }

            await api.updateItem(user, itemId, updates)
            await fetchItem()
            setIsEditing(false)
        } catch (err) {
            console.error('Failed to update item:', err)
            alert('Failed to save changes')
        } finally {
            setSaving(false)
        }
    }

    const handleDelete = () => {
        router.push(`/closet?user=${user}`)
    }

    if (loading) return <div className="p-8 text-center">Loading...</div>
    if (!item) return <div className="p-8 text-center">Item not found</div>

    const imagePath = item.system_metadata.image_path.startsWith('http')
        ? item.system_metadata.image_path
        : `/api/images/${item.system_metadata.image_path.split('/').pop()}`

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
                <div className="aspect-[3/4] bg-gray-50 w-full relative">
                    <img
                        src={imagePath}
                        alt={item.styling_details.name}
                        className="w-full h-full object-contain"
                    />
                </div>

                {/* Rotate Button (Edit Mode Only) */}
                {isEditing && (
                    <div className="px-6 pt-4">
                        <button
                            onClick={async () => {
                                try {
                                    setSaving(true)
                                    const res = await api.rotateItem(user, itemId)
                                    // Force image refresh by updating item with new path
                                    setItem((prev: any) => ({
                                        ...prev,
                                        system_metadata: {
                                            ...prev.system_metadata,
                                            image_path: res.new_image_path
                                        }
                                    }))
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
                                <h1 className="text-2xl font-serif font-semibold mb-1">{item.styling_details.name}</h1>
                                <p className="text-gray-500 capitalize">{item.styling_details.category}</p>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-500 block mb-1">Colors</span>
                                    <span className="font-medium">
                                        {Array.isArray(item.styling_details.colors)
                                            ? item.styling_details.colors.join(', ')
                                            : item.styling_details.colors}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-500 block mb-1">Texture</span>
                                    <span className="font-medium capitalize">{item.styling_details.texture}</span>
                                </div>
                                {item.styling_details.brand && (
                                    <div>
                                        <span className="text-gray-500 block mb-1">Brand</span>
                                        <span className="font-medium">{item.styling_details.brand}</span>
                                    </div>
                                )}
                            </div>

                            {item.styling_details.styling_notes && (
                                <div className="border-t border-b border-gray-100 py-4">
                                    <h3 className="text-sm font-medium text-gray-900 mb-2">📝 AI Styling Notes</h3>
                                    <p className="text-gray-600 text-sm leading-relaxed">
                                        {item.styling_details.styling_notes}
                                    </p>
                                </div>
                            )}

                            <button
                                onClick={() => setShowDeleteModal(true)}
                                className="w-full py-3 text-red-600 font-medium border border-red-100 rounded-lg hover:bg-red-50 transition-colors"
                            >
                                Delete Item
                            </button>
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
