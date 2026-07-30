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
      <div className="relative group rounded-xl overflow-hidden my-4 border border-border/50 shadow-sm">
        <div className="flex items-center justify-between px-4 py-2 bg-muted/80 border-b border-border/30">
          <div className="flex items-center gap-2">
            <Terminal size={12} className="text-muted-foreground/60" />
            <span className="text-xs font-medium text-muted-foreground/80">{language}</span>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-muted-foreground/60 hover:text-foreground hover:bg-muted/50 px-2 py-1 rounded-lg transition-all"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy code'}</span>
          </button>
        </div>
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
    )
  }

  return (
    <code className={cn('bg-muted/80 px-1.5 py-0.5 rounded-md text-sm font-mono text-[0.8125rem] border border-border/30', className)} {...props}>
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
    <div className={cn('markdown-content max-w-none text-sm leading-relaxed', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code: CodeBlock,
          pre: ({ children }) => <>{children}</>,
          p: ({ children }) => <p className="my-2.5 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-6 my-2.5 space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-6 my-2.5 space-y-1.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          h1: ({ children }) => <h1 className="text-xl font-semibold tracking-tight mt-6 mb-3">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-semibold tracking-tight mt-5 mb-2.5">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold tracking-tight mt-4 mb-2">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-[3px] border-primary/25 pl-4 my-3 text-muted-foreground italic bg-muted/20 py-2 pr-3 rounded-r-xl">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-xl border border-border/50 shadow-sm">
              <table className="min-w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border/50 px-4 py-2.5 bg-muted/50 font-medium text-left text-xs uppercase tracking-wider text-muted-foreground/80">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border/20 px-4 py-2.5">{children}</td>
          ),
          hr: () => <hr className="my-6 border-border/30" />,
          a: ({ href, children }) => (
            <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80 transition-opacity" target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
          img: ({ src, alt }) => (
            src?.startsWith('data:')
              ? <img src={src} alt={alt || 'Generated image'} className="max-w-full rounded-xl my-3 shadow-md" style={{ maxHeight: '512px' }} loading="lazy" />
              : <img src={src} alt={alt || 'Image'} className="max-w-full rounded-xl my-3 shadow-md" loading="lazy" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
