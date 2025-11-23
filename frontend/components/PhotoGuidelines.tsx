import { useState, useEffect } from 'react'

interface PhotoGuidelinesProps {
    isOpen: boolean
    onClose: () => void
    onContinue: () => void
}

export default function PhotoGuidelines({ isOpen, onClose, onContinue }: PhotoGuidelinesProps) {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-serif font-semibold">📸 Tips for Great Photos</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 p-2"
                    >
                        ✕
                    </button>
                </div>

                <div className="space-y-4 mb-8">
                    <div className="flex gap-3">
                        <span className="text-green-500 font-bold">✓</span>
                        <p className="text-gray-600">Lay item flat on a neutral surface (bed, floor, table)</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-green-500 font-bold">✓</span>
                        <p className="text-gray-600">Take photo from directly above</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-green-500 font-bold">✓</span>
                        <p className="text-gray-600">Include entire item (don't crop arms, legs, etc.)</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-green-500 font-bold">✓</span>
                        <p className="text-gray-600">Good lighting (natural light works best)</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-green-500 font-bold">✓</span>
                        <p className="text-gray-600">Avoid busy backgrounds (plain white/beige is ideal)</p>
                    </div>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg mb-6">
                    <p className="text-sm text-blue-800 text-center">
                        These help the AI understand your pieces better!
                    </p>
                </div>

                <button
                    onClick={onContinue}
                    className="w-full bg-black text-white py-3 rounded-full font-medium hover:bg-gray-800 transition-colors"
                >
                    Got it, let's start!
                </button>
            </div>
        </div>
    )
}
