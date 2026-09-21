import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '@/lib/utils'
import { Copy, Check, Terminal, Eye, Code as CodeIcon, Download } from 'lucide-react'
import { saveAs } from 'file-saver'

function CodeBlock({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) {
  const [copied, setCopied] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'code' | 'preview'>('code')
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : ''
  const code = String(children).replace(/\n$/, '')

  const isHtml = language === 'html' || code.includes('<!DOCTYPE') || code.includes('<html')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadFile = () => {
    const ext = language === 'html' ? 'html' : language === 'css' ? 'css' : language === 'javascript' || language === 'js' ? 'js' : 'txt'
    const fileName = language === 'html' ? 'index.html' : `file.${ext}`
    const blob = new Blob([code], { type: ext === 'html' ? 'text/html' : 'text/plain' })
    saveAs(blob, fileName)
  }

  if (match || isHtml) {
    return (
      <div className="relative group rounded-xl overflow-hidden my-3 sm:my-4 border border-border/50 shadow-md max-w-full">
        <div className="flex items-center justify-between px-3 sm:px-4 py-2 bg-[#282c34] border-b border-black/40">
          <div className="flex items-center gap-2.5">
            <span className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
              <span className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
            </span>
            <span className="flex items-center gap-1.5 text-xs font-medium text-[#abb2bf]">
              <Terminal size={12} />
              {language || (isHtml ? 'html' : 'code')}
            </span>

            {/* If HTML, offer Code vs Live Preview switch */}
            {isHtml && (
              <div className="ml-2 flex items-center bg-black/30 rounded-lg p-0.5 border border-white/5">
                <button
                  onClick={() => setActiveTab('code')}
                  className={`flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded transition-all ${
                    activeTab === 'code' ? 'bg-primary text-white shadow-xs' : 'text-[#abb2bf] hover:text-white'
                  }`}
                  title="View Source Code"
                >
                  <CodeIcon size={11} />
                  <span>Code</span>
                </button>
                <button
                  onClick={() => setActiveTab('preview')}
                  className={`flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded transition-all ${
                    activeTab === 'preview' ? 'bg-indigo-600 text-white shadow-xs' : 'text-[#abb2bf] hover:text-white'
                  }`}
                  title="Interactive Live Preview"
                >
                  <Eye size={11} />
                  <span>Live Preview</span>
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {isHtml && (
              <button
                onClick={handleDownloadFile}
                className="flex items-center gap-1 text-xs text-[#abb2bf] hover:text-white hover:bg-white/10 px-2 py-1 rounded-lg transition-all"
                title="Download HTML file"
                aria-label="Download HTML file"
              >
                <Download size={12} />
                <span className="hidden xs:inline">Save</span>
              </button>
            )}

            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs text-[#abb2bf] hover:text-white hover:bg-white/10 px-2 py-1 rounded-lg transition-all"
              aria-label={`Copy ${language || 'code'}`}
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {isHtml && activeTab === 'preview' ? (
          <div className="w-full bg-white h-[380px] sm:h-[450px] relative overflow-hidden">
            <iframe
              title="Code Preview"
              srcDoc={
                code.includes('<!DOCTYPE') || code.includes('<html')
                  ? code
                  : `<!DOCTYPE html><html><head><meta charset="utf-8"/><script src="https://cdn.tailwindcss.com"></script></head><body>${code}</body></html>`
              }
              className="w-full h-full border-0"
              sandbox="allow-scripts allow-modals allow-forms allow-same-origin"
            />
          </div>
        ) : (
          <div className="overflow-x-auto scrollbar-thin max-w-full">
            <SyntaxHighlighter
              style={oneDark}
              language={language || 'html'}
              PreTag="div"
              customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.8125rem', lineHeight: 1.6, backgroundColor: '#282c34' }}
              showLineNumbers={code.split('\n').length > 3}
            >
              {code}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    )
  }

  return (
    <code className={cn('bg-muted/80 px-1.5 py-0.5 rounded-md text-xs sm:text-sm font-mono text-[0.8125rem] border border-border/30 break-words', className)} {...props}>
      {children}
    </code>
  )
}

interface MarkdownRendererProps {
  content: string
  className?: string
  allowImages?: boolean
}

function renderChildrenWithCitations(children: React.ReactNode): React.ReactNode {
  if (typeof children === 'string') {
    const parts = children.split(/(\[\d+\])/g)
    if (parts.length > 1) {
      return parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/)
        if (match) {
          const num = match[1]
          return (
            <button
              key={i}
              type="button"
              onClick={() => {
                const el = document.getElementById(`source-card-${num}`)
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                  el.classList.add('ring-2', 'ring-primary')
                  setTimeout(() => el.classList.remove('ring-2', 'ring-primary'), 2000)
                }
              }}
              className="inline-flex items-center justify-center min-w-[1.2rem] h-4 px-1 rounded-full text-[10px] font-bold bg-primary/15 text-primary hover:bg-primary hover:text-primary-foreground transition-all align-super mx-0.5 cursor-pointer shadow-xs border border-primary/20"
              title={`Source [${num}]`}
            >
              {num}
            </button>
          )
        }
        return part
      })
    }
  }
  if (Array.isArray(children)) {
    return children.map((c, i) => (
      <React.Fragment key={i}>{renderChildrenWithCitations(c)}</React.Fragment>
    ))
  }
  return children
}

export function MarkdownRenderer({ content, className, allowImages = true }: MarkdownRendererProps) {
  return (
    <div className={cn('markdown-content max-w-none text-[13px] sm:text-[15px] leading-7 overflow-hidden break-words text-foreground/90', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        components={{
          script: () => null,
          code: CodeBlock,
          pre: ({ children }) => <>{children}</>,
          input: (props) => {
            if (props.type === 'checkbox') {
              return (
                <input
                  type="checkbox"
                  checked={Boolean(props.checked)}
                  disabled
                  className="mr-1.5 align-middle accent-[var(--color-brand)]"
                />
              )
            }
            return <input {...props} />
          },
          p: ({ children }) => <p className="my-2 sm:my-2.5 leading-7">{renderChildrenWithCitations(children)}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 sm:pl-6 my-2 sm:my-2.5 space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 sm:pl-6 my-2 sm:my-2.5 space-y-1.5">{children}</ol>,
          li: ({ children }) => <li className="leading-7">{renderChildrenWithCitations(children)}</li>,
          h1: ({ children }) => <h1 className="text-xl sm:text-2xl font-semibold tracking-tight mt-7 mb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg sm:text-xl font-semibold tracking-tight mt-6 mb-2.5">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base sm:text-lg font-semibold tracking-tight mt-5 mb-2">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-[3px] border-primary/25 pl-3 sm:pl-4 my-2.5 text-muted-foreground italic bg-muted/20 py-1.5 sm:py-2 pr-3 rounded-r-xl">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto scrollbar-thin my-3 sm:my-4 rounded-xl border border-border/50 shadow-sm max-w-full">
              <table className="min-w-full border-collapse text-xs sm:text-sm">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border/50 px-3 sm:px-4 py-2 sm:py-2.5 bg-muted/50 font-medium text-left text-[11px] sm:text-xs uppercase tracking-wider text-muted-foreground/80">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border/20 px-3 sm:px-4 py-2 sm:py-2.5 text-xs sm:text-sm">{children}</td>
          ),
          hr: () => <hr className="my-4 sm:my-6 border-border/30" />,
          a: ({ href, children }) => {
            if (!href) return <span>{children}</span>;

            // Check if link is an inline citation like [1] or 1
            const childStr = typeof children === 'string'
              ? children.trim()
              : Array.isArray(children) && typeof children[0] === 'string'
              ? children[0].trim()
              : ''
            const citationMatch = childStr.match(/^\[?(\d+)\]?$/)
            if (citationMatch) {
              const num = citationMatch[1]
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => {
                    const el = document.getElementById(`source-card-${num}`)
                    if (el) {
                      e.preventDefault()
                      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                      el.classList.add('ring-2', 'ring-primary')
                      setTimeout(() => el.classList.remove('ring-2', 'ring-primary'), 2000)
                    }
                  }}
                  className="inline-flex items-center justify-center min-w-[1.2rem] h-4 px-1 rounded-full text-[10px] font-bold bg-primary/15 text-primary hover:bg-primary hover:text-primary-foreground transition-all align-super no-underline mx-0.5 cursor-pointer shadow-xs border border-primary/20"
                  title={`Source [${num}] - ${href}`}
                >
                  {num}
                </a>
              )
            }

            const isYouTube = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/.test(href);
            if (isYouTube) {
              const match = href.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
              const videoId = match?.[1];
              if (videoId) {
                return (
                  <div className="my-4">
                    <div className="aspect-video w-full max-w-3xl rounded-xl overflow-hidden border border-border/50 shadow-lg">
                      <iframe
                        src={`https://www.youtube.com/embed/${videoId}`}
                        title={String(children || 'YouTube video')}
                        className="w-full h-full"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                    <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity break-all text-sm mt-2 inline-block" target="_blank" rel="noreferrer">
                      {children || href}
                    </a>
                  </div>
                );
              }
            }
            const isVimeo = /vimeo\.com\/(\d+)/.test(href);
            if (isVimeo) {
              const match = href.match(/vimeo\.com\/(\d+)/);
              const videoId = match?.[1];
              if (videoId) {
                return (
                  <div className="my-4">
                    <div className="aspect-video w-full max-w-3xl rounded-xl overflow-hidden border border-border/50 shadow-lg">
                      <iframe
                        src={`https://player.vimeo.com/video/${videoId}`}
                        title={String(children || 'Vimeo video')}
                        className="w-full h-full"
                        allow="autoplay; fullscreen; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                    <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity break-all text-sm mt-2 inline-block" target="_blank" rel="noreferrer">
                      {children || href}
                    </a>
                  </div>
                );
              }
            }
            return (
              <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity break-all" target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
          img: ({ src, alt }) => (
            !allowImages
              ? (
                <a href={src} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity break-all" target="_blank" rel="noreferrer">
                  {alt || src}
                </a>
              )
              : src?.startsWith('data:')
                ? <img src={src} alt={alt || 'Generated image'} className="max-w-full h-auto rounded-xl my-3 shadow-md" style={{ maxHeight: '512px' }} loading="lazy" />
                : <img src={src} alt={alt || 'Image'} className="max-w-full h-auto rounded-xl my-3 shadow-md" loading="lazy" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}