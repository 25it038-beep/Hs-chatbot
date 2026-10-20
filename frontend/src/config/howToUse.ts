export interface FeatureGuide {
  id: string
  title: string
  badge: string
  summary: string
  steps: string[]
  icon: 'message' | 'code' | 'file' | 'voice' | 'router' | 'command'
}

export const HOW_TO_USE_GUIDES: FeatureGuide[] = [
  {
    id: 'conversation',
    title: 'Conversational Reasoning',
    badge: 'Core Chat',
    summary: 'Interact in natural language with multi-turn context retention and thoughtful explanations.',
    steps: [
      'Type your question or request into the prompt bar at the bottom.',
      'Use quick suggestion chips for common tasks or write freely.',
      'Ask clarifying follow-ups — HS Bot retains the active thread context.',
    ],
    icon: 'message',
  },
  {
    id: 'code',
    title: 'Code Engineering & Debugging',
    badge: 'Engineering',
    summary: 'Generate production-ready code, isolate bugs from stack traces, and refactor architectures.',
    steps: [
      'Paste snippets or error traces directly with markdown code fences.',
      'Ask for unit test suites, performance optimization, or algorithm complexity.',
      'Use the copy button on code blocks to quickly incorporate solutions.',
    ],
    icon: 'code',
  },
  {
    id: 'files',
    title: 'Document & File Analysis',
    badge: 'Attachments',
    summary: 'Upload documents and datasets to synthesize summaries, extract data, and inspect structures.',
    steps: [
      'Click the paperclip or drag and drop PDFs, images, DOCX, or text files.',
      'Add a prompt like "Summarize key risks" or "Extract financial tables".',
      'Receive instant extracted summaries and preview generated documents.',
    ],
    icon: 'file',
  },
  {
    id: 'voice',
    title: 'Real-Time Live Voice',
    badge: 'Audio',
    summary: 'Hands-free interactive voice conversations with ultra-low latency audio streaming.',
    steps: [
      'Click "Live Voice" in the top bar to open the live speech console.',
      'Speak naturally into your microphone without pressing buttons.',
      'Hear responses spoken aloud in real-time and save transcripts to your chat history.',
    ],
    icon: 'voice',
  },
  {
    id: 'router',
    title: 'Intelligent Auto-Routing',
    badge: 'Multi-Model',
    summary: 'HS Bot evaluates every prompt to select the fastest and most capable AI model.',
    steps: [
      'Leave Auto-Router active for balanced speed and reasoning depth.',
      'Complex coding and multi-step reasoning automatically route to deep models.',
      'Fast general queries route to high-throughput endpoints for instant answers.',
    ],
    icon: 'router',
  },
  {
    id: 'tools',
    title: 'Slash Commands & Generators',
    badge: 'Productivity',
    summary: 'Trigger specialized tools directly from the prompt bar.',
    steps: [
      'Type `/` in the input field to open the interactive command palette.',
      'Use `/image` to create illustrations and visuals from descriptive text.',
      'Browse custom shortcuts to supercharge your everyday productivity.',
    ],
    icon: 'command',
  },
]
