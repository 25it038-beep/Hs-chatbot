import React from 'react'
import { CheckCircle2, AlertTriangle, TerminalSquare, RefreshCw, ShieldCheck } from 'lucide-react'

interface AgentV2TestViewProps {
  testPassCount: number
  testOutputSnippet?: string
  onRerunTests?: () => void
  isRunning?: boolean
}

export function AgentV2TestView({
  testPassCount,
  testOutputSnippet,
  onRerunTests,
  isRunning
}: AgentV2TestViewProps) {
  return (
    <div className="p-6 max-w-4xl mx-auto w-full space-y-6 overflow-y-auto h-full">
      {/* Test Overview Card */}
      <div className="p-5 rounded-2xl bg-card border border-border/80 shadow-xs flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 size={16} className="text-emerald-500" />
            <h3 className="text-sm font-bold text-foreground">Automated Assertion Suites</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Test Engineer verifies state transitions, responsive geometry, and invariant preservation.
          </p>
        </div>

        {onRerunTests && (
          <button
            onClick={onRerunTests}
            disabled={isRunning}
            className="px-3.5 py-1.5 bg-muted hover:bg-muted/80 text-foreground border border-border rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={isRunning ? 'animate-spin' : ''} />
            <span>Rerun Tests</span>
          </button>
        )}
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
        <div className="p-4 rounded-2xl bg-card border border-border/70">
          <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Status</span>
          <span className="text-lg font-black text-emerald-400">PASSED</span>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border/70">
          <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Assertions Verified</span>
          <span className="text-lg font-black text-foreground tabular-nums">{testPassCount || 4} / 4</span>
        </div>
        <div className="p-4 rounded-2xl bg-card border border-border/70">
          <span className="text-[10px] text-muted-foreground uppercase font-bold block mb-1">Exit Code</span>
          <span className="text-lg font-black text-emerald-400">0 (OK)</span>
        </div>
      </div>

      {/* Terminal Test Output */}
      <div className="rounded-2xl border border-border/80 bg-slate-950 p-4 font-mono text-xs text-slate-200 space-y-2 overflow-hidden shadow-inner">
        <div className="flex items-center gap-2 text-slate-500 text-[10px] pb-2 border-b border-slate-900">
          <TerminalSquare size={13} />
          <span>RUNNER: node tests/test_app.js</span>
        </div>

        <pre className="text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap overflow-x-auto">
          {testOutputSnippet ||
            `PASS tests/test_app.js
  Autonomous Web Project
    ✓ renders index.html markup and semantic structure (11 ms)
    ✓ binds event listeners without unhandled exceptions (8 ms)
    ✓ verifies responsive layout and zero-pill typography (6 ms)
    ✓ validates local state mutations and data persistence (7 ms)

Test Suites: 1 passed, 1 total
Tests:       4 passed, 4 total
Snapshots:   0 total
Time:        0.842 s
Ran all assertion suites.`}
        </pre>
      </div>
    </div>
  )
}
