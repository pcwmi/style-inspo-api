import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import { api } from '@/lib/api'
import imageCompression from 'browser-image-compression'
// @ts-ignore
import EXIF from 'exif-js'

interface UploadModalProps {
    isOpen: boolean
    onClose: () => void
    onUploadComplete: (count: number, jobIds: string[]) => void
    user: string
}

export interface UploadModalRef {
    triggerFileInput: () => void
}

interface FileStatus {
    file: File
    status: 'pending' | 'compressing' | 'uploading' | 'complete' | 'error'
    progress: number
    originalSize: number
    compressedSize?: number
    error?: string
    jobId?: string
}

const UploadModal = forwardRef<UploadModalRef, UploadModalProps>(({ isOpen, onClose, onUploadComplete, user }, ref) => {
    const [uploads, setUploads] = useState<FileStatus[]>([])
    const fileInputRef = useRef<HTMLInputElement>(null)
    const [isDragOver, setIsDragOver] = useState(false)
    const [isMobile, setIsMobile] = useState(false)

    // Detect mobile on mount
    useEffect(() => {
        const mobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) ||
                      ('ontouchstart' in window) ||
                      (navigator.maxTouchPoints > 0)
        setIsMobile(mobile)
    }, [])

    // Expose triggerFileInput method to parent
    useImperativeHandle(ref, () => ({
        triggerFileInput: () => {
            fileInputRef.current?.click()
        }
    }))

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            await processFiles(Array.from(e.target.files))
        }
    }

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragOver(false)
        if (e.dataTransfer.files) {
            await processFiles(Array.from(e.dataTransfer.files))
        }
    }

    const rotateImage = (file: File): Promise<File> => {
        return new Promise((resolve) => {
            // @ts-ignore
            EXIF.getData(file, function () {
                // @ts-ignore
                const orientation = EXIF.getTag(this, "Orientation")
                if (!orientation || orientation === 1) {
                    resolve(file)
                    return
                }

                const img = new Image()
                img.onload = () => {
                    const canvas = document.createElement('canvas')
                    const ctx = canvas.getContext('2d')!

                    if ([5, 6, 7, 8].indexOf(orientation) > -1) {
                        canvas.width = img.height
                        canvas.height = img.width
                    } else {
                        canvas.width = img.width
                        canvas.height = img.height
                    }

                    switch (orientation) {
                        case 2: ctx.transform(-1, 0, 0, 1, img.width, 0); break
                        case 3: ctx.transform(-1, 0, 0, -1, img.width, img.height); break
                        case 4: ctx.transform(1, 0, 0, -1, 0, img.height); break
                        case 5: ctx.transform(0, 1, 1, 0, 0, 0); break
                        case 6: ctx.transform(0, 1, -1, 0, img.height, 0); break
                        case 7: ctx.transform(0, -1, -1, 0, img.height, img.width); break
                        case 8: ctx.transform(0, -1, 1, 0, 0, img.width); break
                        default: ctx.transform(1, 0, 0, 1, 0, 0)
                    }

                    ctx.drawImage(img, 0, 0)
                    canvas.toBlob((blob) => {
                        if (blob) {
                            const newFile = new File([blob], file.name, { type: file.type })
                            resolve(newFile)
                        } else {
                            resolve(file)
                        }
                    }, file.type)
                }
                img.src = URL.createObjectURL(file)
            })
        })
    }

    const processFiles = async (files: File[]) => {
        const newUploads = files.map(file => ({
            file,
            status: 'pending' as const,
            progress: 0,
            originalSize: file.size
        }))

        setUploads(prev => [...prev, ...newUploads])

        // Process sequentially to avoid overwhelming browser/network
        for (let i = 0; i < newUploads.length; i++) {
            const uploadIndex = uploads.length + i
            const file = newUploads[i].file

            try {
                // 1. Rotate
                updateFileStatus(file.name, 'compressing', 10)
                const rotatedFile = await rotateImage(file)

                // 2. Compress
                updateFileStatus(file.name, 'compressing', 30)
                const options = {
                    maxSizeMB: 1,
                    maxWidthOrHeight: 1920,
                    useWebWorker: true
                }
                const compressedFile = await imageCompression(rotatedFile, options)

                setUploads(prev => {
                    const next = [...prev]
                    const index = next.findIndex(f => f.file.name === file.name)
                    if (index !== -1) {
                        next[index] = { ...next[index], compressedSize: compressedFile.size }
                    }
                    return next
                })

                // 3. Upload
                // Mock progress since fetch doesn't support it natively easily without XHR
                // We'll just show "uploading" state
                updateFileStatus(file.name, 'uploading', 50)
                const result = await api.uploadItem(user, compressedFile, true)

                updateFileStatus(file.name, 'complete', 100, {
                    jobId: result.job_id
                })
            } catch (err) {
                console.error('Upload failed:', err)
                updateFileStatus(file.name, 'error', 0, { error: 'Failed to upload' })
            }
        }

        // After all files have been processed, check for completion
        const allUploads = await new Promise<FileStatus[]>(resolve => {
            setUploads(prev => {
                resolve(prev);
                return prev;
            });
        });

        const completedFiles = allUploads.filter(f => f.status === 'complete');
        const completedCount = completedFiles.length;
        const jobIds = completedFiles.map(f => f.jobId).filter(Boolean) as string[];

        if (completedCount > 0) {
            setTimeout(() => {
                onUploadComplete(completedCount, jobIds);
                onClose();
                setUploads([]); // Clear uploads after closing
            }, 1500);
        } else {
            // If no files completed, just close after a short delay
            setTimeout(() => {
                onClose();
                setUploads([]);
            }, 1000);
        }
    }

    const updateFileStatus = (fileName: string, status: FileStatus['status'], progress: number, extra?: Partial<FileStatus>) => {
        setUploads(prev => prev.map(f => {
            if (f.file.name === fileName) {
                return { ...f, status, progress, ...extra }
            }
            return f
        }))
    }

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B'
        const k = 1024
        const sizes = ['B', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-serif font-semibold">Upload Photos</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 p-2"
                    >
                        ✕
                    </button>
                </div>

                {uploads.length === 0 ? (
                    <div
                        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400 active:bg-gray-50'
                            }`}
                        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            multiple
                            accept="image/*"
                            onChange={handleFileSelect}
                            capture="environment"
                        />
                        <div className="text-4xl mb-4">📷</div>
                        <p className="text-gray-600 font-medium mb-2">{isMobile ? 'Tap to upload photos' : 'Click to upload or drag photos here'}</p>
                        <p className="text-sm text-gray-400">JPG, PNG up to 10MB</p>
                    </div>
                ) : (
                    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                        {uploads.map((upload, i) => (
                            <div key={i} className="bg-gray-50 p-3 rounded-lg">
                                <div className="flex justify-between mb-2">
                                    <span className="font-medium truncate max-w-[200px]">{upload.file.name}</span>
                                    <span className="text-sm text-gray-500">
                                        {upload.status === 'complete' ? '✅' :
                                            upload.status === 'error' ? '❌' :
                                                `${upload.progress}%`}
                                    </span>
                                </div>

                                <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
                                    <div
                                        className={`h-full transition-all duration-300 ${upload.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                                            }`}
                                        style={{ width: `${upload.progress}%` }}
                                    />
                                </div>

                                <div className="flex justify-between text-xs text-gray-500">
                                    <span>
                                        {upload.compressedSize ? (
                                            <>Compressed {formatSize(upload.originalSize)} → {formatSize(upload.compressedSize)}</>
                                        ) : (
                                            formatSize(upload.originalSize)
                                        )}
                                    </span>
                                    <span>{upload.status}</span>
                                </div>

                                {upload.error && (
                                    <p className="text-xs text-red-500 mt-1">{upload.error}</p>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
})

UploadModal.displayName = 'UploadModal'

export default UploadModal
