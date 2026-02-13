interface UploadChoiceModalProps {
    isOpen: boolean
    onClose: () => void
    onSelectIndividual: () => void
    onSelectOutfit: () => void
}

export default function UploadChoiceModal({ isOpen, onClose, onSelectIndividual, onSelectOutfit }: UploadChoiceModalProps) {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-5">
                    <h2 className="text-lg font-serif font-semibold">Add to Closet</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 p-2"
                    >
                        ✕
                    </button>
                </div>

                <div className="space-y-3">
                    <button
                        onClick={onSelectIndividual}
                        className="w-full text-left p-4 rounded-xl border-2 border-gray-200 hover:border-terracotta hover:bg-terracotta/5 transition group"
                    >
                        <div className="flex items-start gap-3">
                            <span className="text-2xl">📷</span>
                            <div>
                                <div className="font-medium text-gray-900 group-hover:text-terracotta transition">Upload Individual Items</div>
                                <div className="text-sm text-gray-500 mt-0.5">One photo per garment</div>
                            </div>
                        </div>
                    </button>

                    <button
                        onClick={onSelectOutfit}
                        className="w-full text-left p-4 rounded-xl border-2 border-gray-200 hover:border-terracotta hover:bg-terracotta/5 transition group"
                    >
                        <div className="flex items-start gap-3">
                            <span className="text-2xl">👗</span>
                            <div>
                                <div className="font-medium text-gray-900 group-hover:text-terracotta transition">Extract from Outfit Photo</div>
                                <div className="text-sm text-gray-500 mt-0.5">Full outfit — we'll separate each piece</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    )
}
