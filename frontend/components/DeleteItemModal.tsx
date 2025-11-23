'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

interface DeleteItemModalProps {
    isOpen: boolean
    onClose: () => void
    onDelete: () => void
    item: any
    user: string
}

export default function DeleteItemModal({ isOpen, onClose, onDelete, item, user }: DeleteItemModalProps) {
    const [isVisible, setIsVisible] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        if (isOpen) {
            setIsVisible(true)
            setError('')
        } else {
            setTimeout(() => setIsVisible(false), 300)
        }
    }, [isOpen])

    const handleDelete = async () => {
        if (!item) return

        setIsDeleting(true)
        setError('')

        try {
            await api.deleteItem(user, item.id)
            onDelete()
            onClose()
        } catch (err: any) {
            console.error('Delete error:', err)
            setError(err.message || 'Failed to delete item')
        } finally {
            setIsDeleting(false)
        }
    }

    if (!isVisible && !isOpen) return null

    return (
        <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}>
            <div
                className="absolute inset-0 bg-ink/50 backdrop-blur-sm"
                onClick={!isDeleting ? onClose : undefined}
            />

            <div className={`relative bg-white w-full max-w-sm rounded-2xl shadow-xl overflow-hidden transition-all duration-300 transform ${isOpen ? 'scale-100 translate-y-0' : 'scale-95 translate-y-4'}`}>
                <div className="p-6 text-center">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
                        🗑️
                    </div>

                    <h2 className="text-xl font-bold text-ink mb-2">Delete Item?</h2>
                    <p className="text-muted mb-6">
                        Are you sure you want to delete <span className="font-medium text-ink">{item?.styling_details?.name || 'this item'}</span>? This action cannot be undone.
                    </p>

                    {error && (
                        <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">
                            {error}
                        </div>
                    )}

                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            disabled={isDeleting}
                            className="flex-1 py-3 px-4 border border-sand rounded-xl font-medium text-ink hover:bg-sand/30 transition disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleDelete}
                            disabled={isDeleting}
                            className="flex-1 py-3 px-4 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 transition disabled:opacity-50 flex items-center justify-center"
                        >
                            {isDeleting ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                'Delete'
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
