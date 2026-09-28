/**
 * HSBot Next-Gen File Engine & Unified Composer Attachment Pipeline
 * Provides client-side document inspection, metadata extraction,
 * clipboard file extraction, validation, hashing, token estimation,
 * tabular parsing, and intelligent action suggestion.
 */

import type { FileInfo, Attachment } from '@/types'

export type AttachmentSource = 'clipboard' | 'picker' | 'drop' | 'drag_drop' | 'screenshot'
export type AttachmentUploadStatus = 'UPLOADING' | 'UPLOADED' | 'FAILED'
export type AttachmentProcessingStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'UNSUPPORTED' | 'FAILED'
export type AttachmentLifecycleStatus =
  | 'UPLOADING'
  | 'PROCESSING'
  | 'ANALYZING'
  | 'READY'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'FAILED'

export const MAX_COMPOSER_FILE_SIZE_BYTES = 50 * 1024 * 1024 // 50 MB

export interface ParsedFileMetadata {
  id: string
  localId: string
  file: File
  name: string
  size: number
  type: string
  extension: string
  category: 'code' | 'document' | 'data' | 'image' | 'archive' | 'audio' | 'text' | 'unknown'
  source: AttachmentSource
  uploadStatus: AttachmentUploadStatus
  processingStatus: AttachmentProcessingStatus
  status: AttachmentLifecycleStatus
  fileId?: string
  contentHash?: string
  errorMessage?: string
  uploadDurationMs?: number
  processingDurationMs?: number
  uploadedFileInfo?: FileInfo
  language?: string
  previewText?: string
  dataPreview?: {
    headers: string[]
    rows: string[][]
    totalRows: number
  }
  imagePreviewUrl?: string
  lineCount?: number
  wordCount?: number
  charCount?: number
  estimatedTokens?: number
  suggestedPrompts: string[]
}

const EXTENSION_CATEGORIES: Record<string, { category: ParsedFileMetadata['category']; language?: string }> = {
  // Code
  js: { category: 'code', language: 'JavaScript' },
  jsx: { category: 'code', language: 'React JSX' },
  ts: { category: 'code', language: 'TypeScript' },
  tsx: { category: 'code', language: 'React TSX' },
  py: { category: 'code', language: 'Python' },
  html: { category: 'code', language: 'HTML' },
  css: { category: 'code', language: 'CSS' },
  scss: { category: 'code', language: 'SCSS' },
  json: { category: 'data', language: 'JSON' },
  yaml: { category: 'code', language: 'YAML' },
  yml: { category: 'code', language: 'YAML' },
  toml: { category: 'code', language: 'TOML' },
  xml: { category: 'data', language: 'XML' },
  sql: { category: 'code', language: 'SQL' },
  sh: { category: 'code', language: 'Bash' },
  ps1: { category: 'code', language: 'PowerShell' },
  rs: { category: 'code', language: 'Rust' },
  go: { category: 'code', language: 'Go' },
  java: { category: 'code', language: 'Java' },
  cpp: { category: 'code', language: 'C++' },
  c: { category: 'code', language: 'C' },
  cs: { category: 'code', language: 'C#' },
  php: { category: 'code', language: 'PHP' },
  rb: { category: 'code', language: 'Ruby' },
  kt: { category: 'code', language: 'Kotlin' },
  swift: { category: 'code', language: 'Swift' },

  // Documents
  pdf: { category: 'document' },
  doc: { category: 'document' },
  docx: { category: 'document' },
  pptx: { category: 'document' },
  ppt: { category: 'document' },
  txt: { category: 'text' },
  md: { category: 'text', language: 'Markdown' },
  rtf: { category: 'document' },
  log: { category: 'text' },

  // Data / Spreadsheets
  csv: { category: 'data', language: 'CSV' },
  tsv: { category: 'data', language: 'TSV' },
  xlsx: { category: 'data', language: 'Excel' },
  xls: { category: 'data', language: 'Excel' },

  // Images
  png: { category: 'image' },
  jpg: { category: 'image' },
  jpeg: { category: 'image' },
  webp: { category: 'image' },
  gif: { category: 'image' },
  bmp: { category: 'image' },
  svg: { category: 'image' },

  // Archives
  zip: { category: 'archive' },

  // Audio
  mp3: { category: 'audio' },
  wav: { category: 'audio' },
  ogg: { category: 'audio' },
  m4a: { category: 'audio' },
}

const UNSUPPORTED_EXTENSIONS = new Set([
  'exe', 'dll', 'bat', 'cmd', 'msi', 'scr', 'com', 'pif', 'vbs', 'jar', 'apk', 'dmg', 'iso', 'bin', 'sys', 'drv',
])

const MIME_TO_EXT: Record<string, string> = {
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'image/jpg': 'jpg',
  'image/webp': 'webp',
  'image/gif': 'gif',
  'image/bmp': 'bmp',
  'image/svg+xml': 'svg',
  'application/pdf': 'pdf',
  'text/plain': 'txt',
  'text/markdown': 'md',
  'text/csv': 'csv',
  'text/tab-separated-values': 'tsv',
  'application/json': 'json',
  'application/zip': 'zip',
  'application/x-zip-compressed': 'zip',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/msword': 'doc',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'application/vnd.ms-excel': 'xls',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
  'application/vnd.ms-powerpoint': 'ppt',
}

export function detectFileCategory(filename: string, mimeType = ''): { category: ParsedFileMetadata['category']; language?: string; ext: string } {
  const parts = filename.split('.')
  let ext = (parts.length > 1 ? parts.pop()?.toLowerCase() : '') || ''
  if (!ext && mimeType) {
    ext = MIME_TO_EXT[mimeType.toLowerCase().trim()] || ''
  }

  if (ext && UNSUPPORTED_EXTENSIONS.has(ext)) {
    return { category: 'unknown', ext }
  }

  if (EXTENSION_CATEGORIES[ext]) {
    return { ...EXTENSION_CATEGORIES[ext], ext }
  }

  if (mimeType.startsWith('image/')) return { category: 'image', ext: ext || 'png' }
  if (mimeType.startsWith('audio/')) return { category: 'audio', ext }
  if (mimeType.includes('pdf')) return { category: 'document', ext: ext || 'pdf' }
  if (mimeType.includes('word') || mimeType.includes('officedocument.word')) return { category: 'document', ext: ext || 'docx' }
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return { category: 'document', ext: ext || 'pptx' }
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return { category: 'data', ext: ext || 'xlsx' }
  if (mimeType.includes('csv')) return { category: 'data', ext: ext || 'csv' }
  if (mimeType.startsWith('text/')) return { category: 'text', ext: ext || 'txt' }

  return { category: 'unknown', ext }
}

export function getFileCategoryBadgeStyle(category: ParsedFileMetadata['category']): {
  badgeClass: string
  iconName: string
  label: string
} {
  switch (category) {
    case 'code':
      return {
        badgeClass: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
        iconName: 'Code',
        label: 'Source Code',
      }
    case 'document':
      return {
        badgeClass: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
        iconName: 'FileText',
        label: 'Document',
      }
    case 'data':
      return {
        badgeClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
        iconName: 'Table',
        label: 'Structured Data',
      }
    case 'image':
      return {
        badgeClass: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
        iconName: 'Image',
        label: 'Image',
      }
    case 'archive':
      return {
        badgeClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
        iconName: 'Archive',
        label: 'Archive',
      }
    case 'audio':
      return {
        badgeClass: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
        iconName: 'Music',
        label: 'Audio',
      }
    default:
      return {
        badgeClass: 'bg-muted text-muted-foreground border-border',
        iconName: 'File',
        label: 'File',
      }
  }
}

export function generateSuggestedPrompts(metadata: Partial<ParsedFileMetadata>): string[] {
  const { category, name } = metadata
  const fname = name || 'this file'

  switch (category) {
    case 'code':
      return [
        `Review ${fname} for bugs, logic errors, and security issues.`,
        `Explain the architecture, key functions, and data flow in ${fname}.`,
        `Write comprehensive unit tests with edge cases for ${fname}.`,
        `Refactor ${fname} for clean code, type safety, and optimal performance.`,
      ]
    case 'data':
      return [
        `Analyze key trends, distributions, and summary statistics in ${fname}.`,
        `Identify anomalies, outliers, and missing values in this data.`,
        `Suggest 3 insightful visualizations or SQL queries to analyze ${fname}.`,
        `Clean and transform this dataset with sample Python/Pandas code.`,
      ]
    case 'document':
      return [
        `Generate an executive summary with bullet points from ${fname}.`,
        `Extract all actionable recommendations, deadlines, and responsibilities.`,
        `Summarize the key arguments, findings, and conclusions.`,
        `Create a study guide or quick-reference FAQ based on ${fname}.`,
      ]
    case 'image':
      return [
        `Describe this image in detail and extract all key visual elements.`,
        `Perform OCR and transcribe all readable text from this image.`,
        `Critique this UI/UX design and recommend modern improvements.`,
      ]
    default:
      return [
        `Summarize the contents of ${fname}.`,
        `Extract the most important points and insights.`,
        `Analyze this file and explain what it is used for.`,
      ]
  }
}

function readBlobSliceBytes(file: File, length: number): Promise<Uint8Array> {
  return new Promise((resolve, reject) => {
    const slice = file.slice(0, Math.min(file.size, length))
    if (typeof slice.arrayBuffer === 'function') {
      slice
        .arrayBuffer()
        .then(buf => resolve(new Uint8Array(buf)))
        .catch(reject)
      return
    }
    const reader = new FileReader()
    reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer))
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(slice)
  })
}

/**
 * Computes a fast, deterministic content hash for duplicate paste detection
 * without blocking the main thread on large files.
 */
export async function computeFileContentHash(file: File): Promise<string> {
  try {
    const sampleBytes = await readBlobSliceBytes(file, 64 * 1024)
    let fnv = 2166136261
    for (let i = 0; i < sampleBytes.length; i++) {
      fnv ^= sampleBytes[i]
      fnv = Math.imul(fnv, 16777619)
    }
    const hashHex = (fnv >>> 0).toString(16).padStart(8, '0')
    return `${file.size}:${file.type || 'raw'}:${hashHex}`
  } catch {
    return `${file.name}:${file.size}:${file.type}:${file.lastModified || 0}`
  }
}

/**
 * Validates file size, extension, MIME type, and binary magic bytes
 * so invalid, oversized, or unsupported files never get a fake Ready state.
 */
export async function validateComposerFile(file: File): Promise<{
  valid: boolean
  status: 'VALID' | 'UNSUPPORTED' | 'FAILED'
  errorMessage?: string
}> {
  if (!file) {
    return { valid: false, status: 'FAILED', errorMessage: "Couldn't process file" }
  }

  if (file.size > MAX_COMPOSER_FILE_SIZE_BYTES) {
    return {
      valid: false,
      status: 'FAILED',
      errorMessage: 'File exceeds 50 MB limit',
    }
  }

  if (file.size === 0) {
    return {
      valid: false,
      status: 'FAILED',
      errorMessage: "Couldn't process file (empty 0-byte file)",
    }
  }

  const { category, ext } = detectFileCategory(file.name || '', file.type || '')
  if (UNSUPPORTED_EXTENSIONS.has(ext) || category === 'unknown') {
    return {
      valid: false,
      status: 'UNSUPPORTED',
      errorMessage: `Unsupported format${ext ? ` (.${ext})` : ''} — cannot be analyzed`,
    }
  }

  try {
    const header = await readBlobSliceBytes(file, 64)
    if (ext === 'pdf' && header.length >= 4) {
      const ascii = new TextDecoder('ascii', { fatal: false }).decode(header)
      if (!ascii.includes('%PDF-')) {
        return {
          valid: false,
          status: 'FAILED',
          errorMessage: "Couldn't process file (corrupt or invalid PDF)",
        }
      }
    } else if (ext === 'png' && header.length >= 4) {
      if (!(header[0] === 0x89 && header[1] === 0x50 && header[2] === 0x4e && header[3] === 0x47)) {
        return {
          valid: false,
          status: 'FAILED',
          errorMessage: "Couldn't process file (corrupt PNG image)",
        }
      }
    } else if ((ext === 'jpg' || ext === 'jpeg') && header.length >= 3) {
      if (!(header[0] === 0xff && header[1] === 0xd8 && header[2] === 0xff)) {
        return {
          valid: false,
          status: 'FAILED',
          errorMessage: "Couldn't process file (corrupt JPEG image)",
        }
      }
    } else if ((ext === 'docx' || ext === 'xlsx' || ext === 'pptx' || ext === 'zip') && header.length >= 4) {
      const isPkZip = header[0] === 0x50 && header[1] === 0x4b
      const isOle = header[0] === 0xd0 && header[1] === 0xcf
      if (!isPkZip && !isOle) {
        return {
          valid: false,
          status: 'FAILED',
          errorMessage: `Couldn't process file (corrupt ${ext.toUpperCase()} archive)`,
        }
      }
    }
  } catch {
    return {
      valid: false,
      status: 'FAILED',
      errorMessage: "Couldn't process file",
    }
  }

  return { valid: true, status: 'VALID' }
}

/**
 * Extracts files and text from a browser ClipboardEvent DataTransfer object.
 * Handles both clipboardData.files and clipboardData.items, normalizes unnamed
 * clipboard blobs/screenshots into real File objects, and detects when the
 * browser/OS blocked file clipboard access.
 */
export function extractClipboardPayload(clipboardData: DataTransfer | null | undefined): {
  files: File[]
  text: string
  unexposedFileAttempt: boolean
} {
  if (!clipboardData) {
    return { files: [], text: '', unexposedFileAttempt: false }
  }

  const collectedFiles: File[] = []
  const seenKeys = new Set<string>()
  let hadNullFileItem = false

  const addUniqueFile = (rawFile: File | null, fallbackIndex: number) => {
    if (!rawFile) return
    let normalizedFile = rawFile
    const rawName = (rawFile.name || '').trim()
    const mime = (rawFile.type || '').toLowerCase().trim()
    const inferredExt = MIME_TO_EXT[mime] || (mime.startsWith('image/') ? 'png' : 'bin')

    if (!rawName || rawName === 'blob') {
      const prefix = mime.startsWith('image/') ? 'clipboard-image' : 'clipboard-file'
      const generatedName = `${prefix}-${fallbackIndex + 1}.${inferredExt}`
      normalizedFile = new File([rawFile], generatedName, {
        type: rawFile.type || 'application/octet-stream',
        lastModified: rawFile.lastModified || Date.now(),
      })
    }

    const dedupeKey = `${normalizedFile.name}:${normalizedFile.size}:${normalizedFile.type}:${normalizedFile.lastModified || 0}`
    if (!seenKeys.has(dedupeKey)) {
      seenKeys.add(dedupeKey)
      collectedFiles.push(normalizedFile)
    }
  }

  // 1. Inspect clipboardData.items first (captures screenshots, images, and OS file items)
  if (clipboardData.items && clipboardData.items.length > 0) {
    const items = Array.from(clipboardData.items)
    items.forEach((item, idx) => {
      if (item.kind === 'file') {
        const f = item.getAsFile()
        if (f) {
          addUniqueFile(f, idx)
        } else {
          hadNullFileItem = true
        }
      }
    })
  }

  // 2. Inspect clipboardData.files (captures multi-file Explorer paste & standard file lists)
  if (clipboardData.files && clipboardData.files.length > 0) {
    Array.from(clipboardData.files).forEach((f, idx) => {
      addUniqueFile(f, idx)
    })
  }

  let text = ''
  try {
    text = clipboardData.getData('text/plain') || ''
  } catch {
    text = ''
  }

  // If a single file was copied from OS File Explorer, some browsers also put just its filename
  // in text/plain. Do not duplicate the bare filename into the prompt text if it matches the file.
  if (collectedFiles.length === 1 && text.trim() === collectedFiles[0].name) {
    text = ''
  }

  const types = Array.from(clipboardData.types || [])
  const hasFileTypeIndicator = types.some(t =>
    t === 'Files' ||
    t === 'application/x-moz-file' ||
    t === 'public.file-url' ||
    t === 'NSFilenamesPboardType'
  )

  const unexposedFileAttempt =
    collectedFiles.length === 0 &&
    !text.trim() &&
    (hadNullFileItem || hasFileTypeIndicator)

  return {
    files: collectedFiles,
    text,
    unexposedFileAttempt,
  }
}

/**
 * Normalizes and inspects a File object locally into a ComposerAttachment
 * ready for the shared upload & processing pipeline.
 */
export async function inspectFileLocally(
  file: File,
  source: AttachmentSource = 'picker'
): Promise<ParsedFileMetadata> {
  const { category, language, ext } = detectFileCategory(file.name, file.type)
  const localId = `att-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  const contentHash = await computeFileContentHash(file)
  const validation = await validateComposerFile(file)

  let initialStatus: AttachmentLifecycleStatus = 'UPLOADING'
  let uploadStatus: AttachmentUploadStatus = 'UPLOADING'
  let processingStatus: AttachmentProcessingStatus = 'PENDING'

  if (!validation.valid) {
    initialStatus = validation.status === 'UNSUPPORTED' ? 'UNSUPPORTED' : 'FAILED'
    uploadStatus = 'FAILED'
    processingStatus = validation.status === 'UNSUPPORTED' ? 'UNSUPPORTED' : 'FAILED'
  }

  const meta: ParsedFileMetadata = {
    id: localId,
    localId,
    file,
    name: file.name,
    size: file.size,
    type: file.type || (ext ? `application/${ext}` : 'application/octet-stream'),
    extension: ext,
    category,
    source,
    uploadStatus,
    processingStatus,
    status: initialStatus,
    contentHash,
    errorMessage: validation.errorMessage,
    language,
    suggestedPrompts: [],
  }

  meta.suggestedPrompts = generateSuggestedPrompts(meta)

  // Image Preview Thumbnail
  if (category === 'image') {
    try {
      if (typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function') {
        meta.imagePreviewUrl = URL.createObjectURL(file)
      }
    } catch {}
    return meta
  }

  // Text / Code / CSV local preview (up to 4MB for instant responsiveness)
  const isReadableText =
    category === 'code' ||
    category === 'text' ||
    ext === 'csv' ||
    ext === 'tsv' ||
    ext === 'json' ||
    file.type.startsWith('text/')

  if (isReadableText && file.size < 4 * 1024 * 1024 && validation.valid) {
    try {
      const text = await readFileAsText(file)
      if (ext === 'json') {
        try {
          JSON.parse(text)
        } catch {
          meta.status = 'FAILED'
          meta.uploadStatus = 'FAILED'
          meta.processingStatus = 'FAILED'
          meta.errorMessage = "Couldn't process file (malformed JSON)"
          return meta
        }
      }
      meta.previewText = text
      meta.charCount = text.length
      meta.lineCount = text.split('\n').length
      meta.wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
      meta.estimatedTokens = Math.ceil(text.length / 3.8)

      // CSV / TSV preview parsing
      if (ext === 'csv' || ext === 'tsv') {
        const separator = ext === 'tsv' ? '\t' : ','
        const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0)
        if (lines.length > 0) {
          const headers = lines[0].split(separator).map(h => h.trim().replace(/^["']|["']$/g, ''))
          const rows = lines.slice(1, 11).map(line =>
            line.split(separator).map(c => c.trim().replace(/^["']|["']$/g, ''))
          )
          meta.dataPreview = {
            headers,
            rows,
            totalRows: lines.length - 1,
          }
        }
      }
    } catch (err) {
      console.warn('[FileEngine] Could not read file as text:', err)
    }
  }

  return meta
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (typeof file.text === 'function') {
      file.text().then(resolve).catch(reject)
      return
    }
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}

export function toAttachmentModel(meta: ParsedFileMetadata): Attachment {
  const fileId = meta.fileId || meta.uploadedFileInfo?.id || meta.id
  const contentUrl = `/api/files/${fileId}/content`
  return {
    id: fileId,
    fileId,
    name: meta.name,
    filename: meta.name,
    type: meta.category === 'image' ? 'image' : meta.category === 'code' ? 'code' : meta.category === 'data' ? 'spreadsheet' : 'document',
    mimeType: meta.type,
    extension: meta.extension,
    category: meta.category,
    size: meta.size,
    url: contentUrl,
    downloadUrl: contentUrl,
    download_url: contentUrl,
    previewUrl: meta.imagePreviewUrl,
    textPreview: meta.previewText ? meta.previewText.slice(0, 4000) : meta.uploadedFileInfo?.text_preview,
    source: meta.source,
    status: meta.status,
  }
}
