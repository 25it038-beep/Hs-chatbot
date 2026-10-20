import React from 'react'
import {
  ExternalLink,
  Bot,
  Laptop,
  Cpu,
  Sparkles,
  ArrowUpRight,
  Shield,
  Layers,
} from 'lucide-react'
import { HS_PRODUCTS, type ProductItem } from '@/config/products'
import { Button } from '@/components/ui/button'

const ICON_MAP = {
  studio: Sparkles,
  bot: Bot,
  desktop: Laptop,
  core: Cpu,
}

export function ProductShowcase() {
  return (
    <div className="w-full space-y-3">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-brand/10 text-brand">
            <Layers size={14} />
          </span>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground">
            HS AI Solutions Ecosystem
          </h2>
        </div>
        <span className="text-[10px] text-muted-foreground/60 hidden sm:inline">
          Official Products
        </span>
      </div>

      {/* Grid of Product Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3">
        {HS_PRODUCTS.map((product) => {
          const Icon = ICON_MAP[product.icon] || Sparkles
          const isStudio = product.id === 'hs-ai-studio'

          return (
            <div
              key={product.id}
              className={`rounded-xl border p-3.5 transition-all duration-300 flex flex-col justify-between relative group ${
                isStudio
                  ? 'border-brand/40 bg-brand/5 shadow-[0_0_15px_rgba(139,92,246,0.08)] hover:border-brand/60 hover:bg-brand/10'
                  : 'border-border/70 bg-card/50 hover:border-border hover:bg-card/80'
              }`}
            >
              {/* Card Header & Badge */}
              <div className="mb-2">
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <div
                      className={`p-1.5 rounded-lg ${
                        isStudio
                          ? 'bg-brand/20 text-brand'
                          : 'bg-muted/80 text-muted-foreground group-hover:text-foreground'
                      }`}
                    >
                      <Icon size={14} />
                    </div>
                    <div>
                      <h3 className="text-xs font-semibold text-foreground tracking-tight">
                        {product.name}
                      </h3>
                      <p className="text-[10px] text-muted-foreground/70 font-medium">
                        {product.brand}
                      </p>
                    </div>
                  </div>

                  {product.badge && (
                    <span
                      className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded-full border whitespace-nowrap ${
                        isStudio
                          ? 'bg-brand/20 text-brand border-brand/30'
                          : product.isCurrent
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-muted/60 text-muted-foreground/80 border-border/60'
                      }`}
                    >
                      {product.badge}
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                  {product.description}
                </p>
              </div>

              {/* Action Button */}
              <div className="pt-2 border-t border-border/30 mt-auto">
                {product.actionUrl ? (
                  <a
                    href={product.actionUrl}
                    target={product.isExternal ? '_blank' : '_self'}
                    rel={product.isExternal ? 'noopener noreferrer' : undefined}
                    className={`inline-flex items-center justify-between w-full text-[11px] font-semibold px-2.5 py-1.5 rounded-lg transition-all duration-200 group-hover:underline ${
                      isStudio
                        ? 'bg-brand text-brand-foreground hover:bg-brand/90 shadow-xs'
                        : 'bg-muted/70 hover:bg-muted text-foreground'
                    }`}
                  >
                    <span>{product.actionLabel}</span>
                    {product.isExternal ? (
                      <ArrowUpRight size={12} className="opacity-80" />
                    ) : (
                      <ExternalLink size={11} className="opacity-70" />
                    )}
                  </a>
                ) : (
                  <div className="text-[10px] font-medium text-muted-foreground/60 px-1 py-0.5 flex items-center justify-between">
                    <span>{product.actionLabel}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/80" />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
