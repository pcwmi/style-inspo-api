interface PhotoGuidelinesProps {
    isOpen: boolean
    onClose: () => void
    onContinue: () => void
}

export default function PhotoGuidelines({ isOpen, onClose, onContinue }: PhotoGuidelinesProps) {
    if (!isOpen) return null

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-5 shadow-xl animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-serif font-semibold">Quick Photo Tips</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 p-2"
                    >
                        ✕
                    </button>
                </div>

                <div className="space-y-3 mb-5">
                    <div className="flex gap-3">
                        <span className="text-terracotta font-bold">✓</span>
                        <p className="text-gray-600">Lay flat or hang against any neutral background</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-terracotta font-bold">✓</span>
                        <p className="text-gray-600">Make sure the whole item is visible</p>
                    </div>

                    <div className="flex gap-3">
                        <span className="text-terracotta font-bold">✓</span>
                        <p className="text-gray-600">Natural light helps</p>
                    </div>
                </div>

                <button
                    onClick={onContinue}
                    className="w-full bg-terracotta text-white py-3 rounded-lg font-medium hover:opacity-90 transition-opacity"
                >
                    Got it, let's start!
                </button>
            </div>
        </div>
    )
}
