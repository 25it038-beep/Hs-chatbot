import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, File, X, FileText, Image as ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatBytes } from '@/lib/utils'
import { api } from '@/lib/api'
import type { FileInfo } from '@/types'

interface FileUploadProps {
  onFilesUploaded: (files: FileInfo[]) => void
  maxFiles?: number
}

export function FileUpload({ onFilesUploaded, maxFiles = 10 }: FileUploadProps) {
  const [uploading, setUploading] = React.useState(false)
  const [uploaded, setUploaded] = React.useState<FileInfo[]>([])
  const [error, setError] = React.useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setError(null)
    if (acceptedFiles.length === 0) return
    setUploading(true)
    try {
      const result = await api.uploadMultiple(acceptedFiles)
      setUploaded(prev => [...prev, ...result.files])
      onFilesUploaded(result.files)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onFilesUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles,
    maxSize: 50 * 1024 * 1024,
  })

  const removeFile = (index: number) => {
    setUploaded(prev => prev.filter((_, i) => i !== index))
  }

  const getIcon = (type: string) => {
    if (type.startsWith('image/')) return <ImageIcon size={16} />
    return <FileText size={16} />
  }

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50 hover:bg-muted/30'
        )}
      >
        <input {...getInputProps()} />
        <Upload size={24} className="mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop files, or click to browse'}
        </p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          PDF, DOCX, TXT, Images, Code, and more (max 50MB each)
        </p>
      </div>

      {uploading && (
        <div className="flex items-center gap-2 mt-3 text-sm text-muted-foreground">
          <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full" />
          Uploading...
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive mt-2">{error}</p>
      )}

      {uploaded.length > 0 && (
        <div className="mt-3 space-y-1">
          {uploaded.map((file, index) => (
            <div
              key={`${file.id}-${index}`}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 text-sm"
            >
              {getIcon(file.content_type)}
              <span className="flex-1 truncate">{file.filename}</span>
              <span className="text-xs text-muted-foreground">{formatBytes(file.size)}</span>
              <button
                onClick={() => removeFile(index)}
                className="p-0.5 hover:text-destructive transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
