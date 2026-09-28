/**
 * HSBot Next-Gen File Engine
 * Provides client-side document inspection, metadata extraction,
 * token estimation, tabular parsing, and intelligent action suggestion.
 */

export interface ParsedFileMetadata {
  id: string
  file: File
  name: string
  size: number
  type: string
  extension: string
  category: 'code' | 'document' | 'data' | 'image' | 'archive' | 'audio' | 'text' | 'unknown'
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
  status?: 'UPLOADING' | 'PROCESSING' | 'ANALYZING' | 'READY' | 'PARTIALLY_SUPPORTED' | 'FAILED'
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
  sql: { category: 'code', language: 'SQL' },
  sh: { category: 'code', language: 'Bash' },
  rs: { category: 'code', language: 'Rust' },
  go: { category: 'code', language: 'Go' },
  java: { category: 'code', language: 'Java' },
  cpp: { category: 'code', language: 'C++' },
  c: { category: 'code', language: 'C' },
  php: { category: 'code', language: 'PHP' },

  // Documents
  pdf: { category: 'document' },
  doc: { category: 'document' },
  docx: { category: 'document' },
  pptx: { category: 'document' },
  ppt: { category: 'document' },
  txt: { category: 'text' },
  md: { category: 'text', language: 'Markdown' },
  rtf: { category: 'document' },

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
  svg: { category: 'image' },

  // Archives
  zip: { category: 'archive' },
  tar: { category: 'archive' },
  gz: { category: 'archive' },

  // Audio
  mp3: { category: 'audio' },
  wav: { category: 'audio' },
  ogg: { category: 'audio' },
  m4a: { category: 'audio' },
}

export function detectFileCategory(filename: string, mimeType = ''): { category: ParsedFileMetadata['category']; language?: string; ext: string } {
  const parts = filename.split('.')
  const ext = (parts.length > 1 ? parts.pop()?.toLowerCase() : '') || ''

  if (EXTENSION_CATEGORIES[ext]) {
    return { ...EXTENSION_CATEGORIES[ext], ext }
  }

  if (mimeType.startsWith('image/')) return { category: 'image', ext }
  if (mimeType.startsWith('audio/')) return { category: 'audio', ext }
  if (mimeType.includes('pdf')) return { category: 'document', ext }
  if (mimeType.includes('word') || mimeType.includes('officedocument')) return { category: 'document', ext }
  if (mimeType.includes('spreadsheet') || mimeType.includes('csv')) return { category: 'data', ext }
  if (mimeType.startsWith('text/')) return { category: 'text', ext }

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
  const { category, language, name } = metadata
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

/**
 * Parses and inspects a File object locally without network latency
 */
export async function inspectFileLocally(file: File): Promise<ParsedFileMetadata> {
  const { category, language, ext } = detectFileCategory(file.name, file.type)
  const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

  const meta: ParsedFileMetadata = {
    id,
    file,
    name: file.name,
    size: file.size,
    type: file.type,
    extension: ext,
    category,
    language,
    suggestedPrompts: [],
    status: (category === 'unknown') ? 'PARTIALLY_SUPPORTED' : 'READY',
  }

  meta.suggestedPrompts = generateSuggestedPrompts(meta)

  // Image Preview
  if (category === 'image') {
    try {
      meta.imagePreviewUrl = URL.createObjectURL(file)
    } catch {}
    return meta
  }

  // Text / Code / CSV parsing (up to 4MB for instant responsiveness)
  const isReadableText =
    category === 'code' ||
    category === 'text' ||
    ext === 'csv' ||
    ext === 'tsv' ||
    ext === 'json' ||
    file.type.startsWith('text/')

  if (isReadableText && file.size < 4 * 1024 * 1024) {
    try {
      const text = await readFileAsText(file)
      meta.previewText = text
      meta.charCount = text.length
      meta.lineCount = text.split('\n').length
      meta.wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
      meta.estimatedTokens = Math.ceil(text.length / 3.8)

      // CSV parsing
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
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}
