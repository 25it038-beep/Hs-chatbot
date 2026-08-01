import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '@/lib/utils'
import { Copy, Check, Terminal } from 'lucide-react'

function CodeBlock({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) {
  const [copied, setCopied] = React.useState(false)
  const match = /language-(\w+)/.exec(className || '')
  const language = match ? match[1] : ''
  const code = String(children).replace(/\n$/, '')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (match) {
    return (
      <div className="relative group rounded-xl overflow-hidden my-3 sm:my-4 border border-border/50 shadow-sm max-w-full">
        <div className="flex items-center justify-between px-3 sm:px-4 py-2 bg-muted/80 border-b border-border/30">
          <div className="flex items-center gap-2">
            <Terminal size={12} className="text-muted-foreground/60" />
            <span className="text-xs font-medium text-muted-foreground/80">{language}</span>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-muted-foreground/60 hover:text-foreground hover:bg-muted/50 px-2 py-1 rounded-lg transition-all"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
        <div className="overflow-x-auto scrollbar-thin max-w-full">
          <SyntaxHighlighter
            style={oneDark}
            language={language}
            PreTag="div"
            customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.8125rem', lineHeight: 1.6 }}
            showLineNumbers={code.split('\n').length > 3}
          >
            {code}
          </SyntaxHighlighter>
        </div>
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
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('markdown-content max-w-none text-xs sm:text-sm leading-relaxed overflow-hidden break-words', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code: CodeBlock,
          pre: ({ children }) => <>{children}</>,
          p: ({ children }) => <p className="my-2 sm:my-2.5 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 sm:pl-6 my-2 sm:my-2.5 space-y-1 sm:space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 sm:pl-6 my-2 sm:my-2.5 space-y-1 sm:space-y-1.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          h1: ({ children }) => <h1 className="text-lg sm:text-xl font-semibold tracking-tight mt-5 mb-2.5">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base sm:text-lg font-semibold tracking-tight mt-4 mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm sm:text-base font-semibold tracking-tight mt-3 mb-1.5">{children}</h3>,
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
          a: ({ href, children }) => (
            <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity break-all" target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
          img: ({ src, alt }) => (
            src?.startsWith('data:')
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
