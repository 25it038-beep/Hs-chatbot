export interface AiTip {
  id: number
  category: string
  title: string
  content: string
  iconName: 'Sparkles' | 'Code' | 'Layers' | 'HelpCircle' | 'FileText' | 'MessageSquare' | 'AlertTriangle' | 'ListOrdered' | 'Mic' | 'Terminal' | 'ShieldCheck' | 'CheckCircle2'
  tag: string
}

export const AI_TIPS: AiTip[] = [
  {
    id: 1,
    category: 'Prompt Craft',
    title: 'Provide Clear Context & Goal Constraints',
    content: 'State your end goal, intended audience, and formatting constraints upfront. High-context prompts consistently produce sharper, production-ready responses without back-and-forth.',
    iconName: 'Sparkles',
    tag: 'Prompting',
  },
  {
    id: 2,
    category: 'Software Engineering',
    title: 'Share Error Traces & Minimal Reproductions',
    content: 'When debugging code, paste the exact stack trace, the surrounding function, and the expected vs. actual output. This enables targeted fixes rather than speculative solutions.',
    iconName: 'Code',
    tag: 'Coding',
  },
  {
    id: 3,
    category: 'Architecture & Design',
    title: 'Break Complex Systems into Architectural Milestones',
    content: 'Ask HS Bot to sketch database schemas and API boundaries before writing implementation logic. Modular planning prevents technical debt and simplifies refactoring.',
    iconName: 'Layers',
    tag: 'Architecture',
  },
  {
    id: 4,
    category: 'Concept Clarity',
    title: 'Anchor Abstract Concepts with Concrete Analogies',
    content: 'Struggling with a dense algorithm or distributed system pattern? Prompt: "Explain this using an everyday real-world analogy, then demonstrate with a minimal code snippet."',
    iconName: 'HelpCircle',
    tag: 'Learning',
  },
  {
    id: 5,
    category: 'File Intelligence',
    title: 'Attach PDFs, DOCX & Data for Grounded Analysis',
    content: 'Upload documents directly into the chat. HS Bot extracts key insights, synthesizes reports, and cites relevant sections rather than generalizing.',
    iconName: 'FileText',
    tag: 'Documents',
  },
  {
    id: 6,
    category: 'Iterative Refinement',
    title: 'Refine Results Iteratively with Follow-Ups',
    content: 'Treat conversation as collaborative pair-programming. Use follow-up prompts like "Make this more concise", "Add unit tests", or "Handle edge cases for null inputs."',
    iconName: 'MessageSquare',
    tag: 'Workflow',
  },
  {
    id: 7,
    category: 'Model Awareness',
    title: 'Know When to Combine AI with Human Judgment',
    content: 'Language models excel at pattern recognition, synthesis, and scaffolding. Always validate safety-critical logic, cryptographic implementations, and business math.',
    iconName: 'AlertTriangle',
    tag: 'Best Practices',
  },
  {
    id: 8,
    category: 'Task Decomposition',
    title: 'Deconstruct Heavy Tasks into Discrete Steps',
    content: 'Instead of requesting an entire app in one prompt, instruct the bot: "Outline step 1 through 4. Await my approval after each step before writing code."',
    iconName: 'ListOrdered',
    tag: 'Strategy',
  },
  {
    id: 9,
    category: 'Voice Interaction',
    title: 'Leverage Hands-Free Live Voice for Brainstorming',
    content: 'Tap "Live Voice" in the top bar to speak naturally. Low-latency streaming lets you talk through ideas and receive instant audio responses without touching the keyboard.',
    iconName: 'Mic',
    tag: 'Voice Mode',
  },
  {
    id: 10,
    category: 'Deep Comprehension',
    title: 'Request Line-by-Line Code Breakdowns',
    content: 'Whenever HS Bot delivers unfamiliar syntax or novel algorithms, ask: "Walk me through how lines 12–25 manipulate memory and what time complexity they introduce."',
    iconName: 'Terminal',
    tag: 'Explanations',
  },
  {
    id: 11,
    category: 'Data Privacy',
    title: 'Sanitize Sensitive Credentials & Secrets',
    content: 'Never input real API keys, database connection strings with passwords, or customer PII into prompts. Use environment placeholders like `process.env.API_KEY`.',
    iconName: 'ShieldCheck',
    tag: 'Security',
  },
  {
    id: 12,
    category: 'Quality Assurance',
    title: 'Cross-Check AI Output Against Official Specs',
    content: 'Verify version-specific library calls and APIs against official documentation, especially when migrating packages or using freshly released frameworks.',
    iconName: 'CheckCircle2',
    tag: 'Verification',
  },
]
