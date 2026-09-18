// ============================================================
// HSBOT — ADVANCED USER PROMPT UNDERSTANDING ENGINE
// Implements Sections 0 - 48 of the HSBot Pipeline
// ============================================================

export type MessageType =
  | 'QUESTION'
  | 'INFORMATION_REQUEST'
  | 'CODE_REQUEST'
  | 'DEBUG_REQUEST'
  | 'FEATURE_REQUEST'
  | 'PROJECT_REQUEST'
  | 'MODIFICATION_REQUEST'
  | 'REFACTOR_REQUEST'
  | 'FILE_REQUEST'
  | 'DOCUMENT_REQUEST'
  | 'PRESENTATION_REQUEST'
  | 'SPREADSHEET_REQUEST'
  | 'RESEARCH_REQUEST'
  | 'AUTOMATION_REQUEST'
  | 'AGENT_TASK'
  | 'VOICE_COMMAND'
  | 'FOLLOW_UP'
  | 'CORRECTION'
  | 'APPROVAL'
  | 'REJECTION'
  | 'CANCELLATION'
  | 'CONTINUATION'
  | 'EXPORT_REQUEST'
  | 'CONVERSION_REQUEST'
  | 'REVIEW_REQUEST'

export interface RequirementItem {
  id: string
  text: string
  category: 'feature' | 'auth' | 'design' | 'db' | 'performance' | 'testing' | 'delivery' | 'other'
  importance: 'MANDATORY' | 'IMPORTANT' | 'OPTIONAL' | 'PREFERENCE' | 'CONSTRAINT' | 'EXCLUSION'
  source: 'EXPLICIT' | 'INFERRED' | 'DISCOVERED' | 'DEFAULT'
  verified?: boolean
  evidence?: string
}

export interface NegativeRequirement {
  action: string
  scope: string
  reason: string
  strictlyForbidden: boolean
}

export interface AmbiguityItem {
  phrase: string
  category: string
  impact: 'LOW' | 'MEDIUM' | 'HIGH'
  canInfer: boolean
  safeDefault: string
  requiresQuestion: boolean
  targetedQuestion?: string
  options: string[]
}

export interface ConflictItem {
  conflictType: 'DIRECT' | 'TECHNICAL' | 'ARCHITECTURAL' | 'SCOPE' | 'FILE' | 'VERSION'
  priorInstruction: string
  currentInstruction: string
  recommendedResolution: string
  resolutionOptions: string[]
}

export interface AcceptanceCriteriaItem {
  id: string
  description: string
  targetVerification: string
}

export interface AdaptiveQuestion {
  id: string
  question: string
  contextReason: string
  options: string[]
  allowCustom?: boolean
  selectedOption?: string
  answered?: boolean
}

export interface UnderstandingModel {
  rawPrompt: string
  normalizedPrompt: string
  messageTypes: MessageType[]
  primaryGoal: string
  desiredOutcome: string
  actionType: string
  targetScope: 'file' | 'project' | 'workspace'
  targetFile?: string
  qualityIntent: string[]
  userKnowledgeLevel: 'NON_TECHNICAL' | 'GENERAL' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'

  explicitRequirements: RequirementItem[]
  implicitRequirements: RequirementItem[]
  negativeRequirements: NegativeRequirement[]

  constraints: Record<string, any>
  preferences: string[]

  referencesResolved: Record<string, string>
  referenceConfidence: 'HIGH' | 'MEDIUM' | 'LOW'

  ambiguities: AmbiguityItem[]
  conflicts: ConflictItem[]
  missingInfo: string[]

  adaptiveQuiz: AdaptiveQuestion[]
  acceptanceCriteria: AcceptanceCriteriaItem[]

  summaryText: string
  decision: 'ANSWER' | 'ASK' | 'PLAN' | 'EXECUTE'
  confidenceScore: number
  qualityGatePassed: boolean
}

export class PromptUnderstandingEngine {
  /**
   * Section 27 & 28: Voice Transcript Normalization & Typo Healing
   */
  static normalizePrompt(prompt: string): string {
    let cleaned = prompt.trim()
    cleaned = cleaned.replace(/\bp\s*d\s*f\b/gi, 'PDF')
    cleaned = cleaned.replace(/\bd\s*o\s*c\s*x?\b/gi, 'DOCX')
    cleaned = cleaned.replace(/\bp\s*p\s*t\s*x?\b/gi, 'PPTX')
    cleaned = cleaned.replace(/\bx\s*l\s*s\s*x?\b/gi, 'XLSX')
    cleaned = cleaned.replace(/\bgenrate\b/gi, 'generate')
    cleaned = cleaned.replace(/\bcreae\b/gi, 'create')
    return cleaned
  }

  /**
   * Section 3: Message Type Classification
   */
  static classifyMessageTypes(text: string): MessageType[] {
    const lower = text.toLowerCase()
    const types: MessageType[] = []

    if (/^(what|how|why|when|where|who|which|can you explain|explain|is it)\b/.test(lower)) {
      types.push('QUESTION')
      types.push('INFORMATION_REQUEST')
    }

    if (/\b(error|bug|broken|fix|fail|traceback|exception|crash)\b/.test(lower)) {
      types.push('DEBUG_REQUEST')
    }
    if (/\b(refactor|clean up|restructure|organize code)\b/.test(lower)) {
      types.push('REFACTOR_REQUEST')
    }
    if (/\b(add|implement|support|feature|integrate|extend)\b/.test(lower)) {
      types.push('FEATURE_REQUEST')
    }
    if (/\b(build an app|create an app|new project|make an app|full stack|college management|system)\b/.test(lower)) {
      types.push('PROJECT_REQUEST')
    } else if (/\b(change|update|modify|tweak|adjust|edit)\b/.test(lower)) {
      types.push('MODIFICATION_REQUEST')
    } else {
      types.push('CODE_REQUEST')
    }

    if (/\bpdf\b/.test(lower)) types.push('DOCUMENT_REQUEST')
    if (/\b(pptx|presentation|slide|slides)\b/.test(lower)) types.push('PRESENTATION_REQUEST')
    if (/\b(xlsx|spreadsheet|excel|sheet)\b/.test(lower)) types.push('SPREADSHEET_REQUEST')
    if (/\b(zip|package|export|download)\b/.test(lower)) types.push('EXPORT_REQUEST')
    if (/\b(automate|cron|schedule|bot|crawl|scrape)\b/.test(lower)) types.push('AUTOMATION_REQUEST')

    if (/\b(actually|i meant|correction|scratch that)\b/.test(lower)) types.push('CORRECTION')
    if (/^(yes|proceed|that's correct|looks good|ok|sure|approve)$/.test(lower.trim())) types.push('APPROVAL')
    if (/^(no|cancel|stop|abort|reject)$/.test(lower.trim())) types.push('REJECTION')

    return types.length > 0 ? types : ['AGENT_TASK']
  }

  /**
   * Section 4 & 5: Primary Goal Extraction & Desired Outcome
   */
  static extractGoalAndOutcome(text: string, types: MessageType[]): { action: string; goal: string; outcome: string } {
    const lower = text.toLowerCase()
    let action = 'engineer_solution'

    if (types.includes('DEBUG_REQUEST')) action = 'debug_and_repair'
    else if (types.includes('MODIFICATION_REQUEST')) action = 'modify_existing'
    else if (types.includes('PROJECT_REQUEST')) action = 'synthesize_project'
    else if (types.includes('DOCUMENT_REQUEST') || types.includes('PRESENTATION_REQUEST')) action = 'generate_document'
    else if (types.includes('QUESTION')) action = 'explain_and_answer'

    let goal = `Deliver solution for: ${text.slice(0, 60)}`
    if (lower.includes('college') && lower.includes('event')) {
      goal = 'College Event Management Application with registration, user authentication, and interactive schedules'
    } else if (lower.includes('dashboard')) {
      goal = 'Interactive Data Dashboard with filtering, metrics, and navigation'
    } else if (lower.includes('login') || lower.includes('auth')) {
      goal = 'Secure Authentication and Session Access Flow'
    } else if (lower.includes('pdf')) {
      goal = 'Formal Structured PDF Document Artifact'
    } else if (lower.includes('presentation') || lower.includes('slide')) {
      goal = 'Structured Presentation Slide Deck'
    }

    let outcome = 'working code'
    if (types.includes('DOCUMENT_REQUEST')) outcome = 'PDF'
    else if (types.includes('PRESENTATION_REQUEST')) outcome = 'PPTX'
    else if (types.includes('SPREADSHEET_REQUEST')) outcome = 'XLSX'
    else if (types.includes('EXPORT_REQUEST') || lower.includes('zip')) outcome = 'ZIP'
    else if (types.includes('QUESTION')) outcome = 'explanation'
    else if (types.includes('PROJECT_REQUEST')) outcome = 'complete application'

    return { action, goal, outcome }
  }

  /**
   * Section 11: Negative Requirements (FORBIDDEN_ACTIONS)
   */
  static extractNegativeRequirements(text: string): NegativeRequirement[] {
    const lower = text.toLowerCase()
    const forbidden: NegativeRequirement[] = []

    if (/\b(don't|dont|do not|never|without)\s+(modify|touch|change|alter|break|rewrite)\s+(the\s+)?backend\b/.test(lower) || lower.includes("don't change the backend") || lower.includes("use my existing project")) {
      forbidden.push({
        action: 'MODIFY_BACKEND',
        scope: 'backend/',
        reason: 'Explicit user constraint: do not modify existing backend code or API schemas.',
        strictlyForbidden: true
      })
    }

    if (/\b(don't|dont|do not|never|no)\s+(use|add|include)?\s*firebase\b/.test(lower)) {
      forbidden.push({
        action: 'USE_FIREBASE',
        scope: 'dependencies',
        reason: 'Explicit user constraint: do not introduce Firebase SDK or modules.',
        strictlyForbidden: true
      })
    }

    if (/\b(don't|dont|do not|preserve|keep)\s+(redesign|change|alter)\s+(the\s+)?(current\s+)?ui\b/.test(lower) || lower.includes('preserve design') || lower.includes('same design')) {
      forbidden.push({
        action: 'OVERRIDE_CURRENT_DESIGN',
        scope: 'design_system',
        reason: 'Explicit user constraint: preserve current UI design language.',
        strictlyForbidden: true
      })
    }

    if (/\b(don't|dont|do not|never)\s+(delete|remove|erase)\s+(any|existing)?\s*files\b/.test(lower)) {
      forbidden.push({
        action: 'DELETE_FILES',
        scope: 'workspace',
        reason: 'Explicit user constraint: strictly avoid deleting existing files.',
        strictlyForbidden: true
      })
    }

    if (/\b(don't|dont|do not)\s+break\s+(anything|existing)\b/.test(lower) || lower.includes("don't break anything")) {
      forbidden.push({
        action: 'BREAK_EXISTING_FEATURES',
        scope: 'all',
        reason: 'Explicit user constraint: preserve all existing invariants and backwards compatibility.',
        strictlyForbidden: true
      })
    }

    return forbidden
  }

  /**
   * Sections 6 & 7: Explicit & Implicit Requirements
   */
  static extractRequirements(text: string): { explicit: RequirementItem[]; implicit: RequirementItem[] } {
    const lower = text.toLowerCase()
    const explicit: RequirementItem[] = []
    const implicit: RequirementItem[] = []
    let counter = 1

    // Auth
    if (/\b(login|signin|sign in|auth|authentication)\b/.test(lower)) {
      explicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'User Authentication (login & credential validation)',
        category: 'auth',
        importance: 'MANDATORY',
        source: 'EXPLICIT'
      })
      implicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'Form validation and session state persistence',
        category: 'auth',
        importance: 'IMPORTANT',
        source: 'INFERRED'
      })
      implicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'Logout capability and protected route handling',
        category: 'auth',
        importance: 'IMPORTANT',
        source: 'INFERRED'
      })
    }

    // Registrations
    if (/\b(registration|registrations|register|signup|sign up)\b/.test(lower)) {
      explicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'User Registration flow with field validation',
        category: 'auth',
        importance: 'MANDATORY',
        source: 'EXPLICIT'
      })
    }

    // Event Management
    if (lower.includes('college') || lower.includes('event')) {
      explicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'Event Management Catalog (creation, browsing, and details)',
        category: 'feature',
        importance: 'MANDATORY',
        source: 'EXPLICIT'
      })
      implicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: 'Event scheduling and attendance tracking',
        category: 'feature',
        importance: 'IMPORTANT',
        source: 'INFERRED'
      })
    }

    // UI Quality / Theme
    if (/\b(premium ui|clean ui|best ui|modern|dark mode|responsive)\b/.test(lower)) {
      let desc = 'Premium responsive UI with coherent typography and styling'
      if (lower.includes('dark')) desc += ' with Dark Mode support'
      explicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: desc,
        category: 'design',
        importance: 'IMPORTANT',
        source: 'EXPLICIT'
      })
    }

    // Fallback if no specific feature matched
    if (explicit.length === 0) {
      explicit.push({
        id: `REQ-${String(counter++).padStart(3, '0')}`,
        text: `Implement requested engineering capability: ${text.slice(0, 50)}`,
        category: 'feature',
        importance: 'MANDATORY',
        source: 'EXPLICIT'
      })
    }

    // Always include verification & testing invariant
    explicit.push({
      id: `REQ-${String(counter++).padStart(3, '0')}`,
      text: 'Automated test suite and error-free code compilation',
      category: 'testing',
      importance: 'IMPORTANT',
      source: 'INFERRED'
    })

    return { explicit, implicit }
  }

  /**
   * Sections 16, 17, 18 & 36: Ambiguities, Conflicts, and Adaptive Quiz
   */
  static detectAmbiguitiesAndQuiz(
    text: string,
    explicitReqs: RequirementItem[],
    negativeReqs: NegativeRequirement[]
  ): { ambiguities: AmbiguityItem[]; conflicts: ConflictItem[]; quiz: AdaptiveQuestion[] } {
    const lower = text.toLowerCase()
    const ambiguities: AmbiguityItem[] = []
    const conflicts: ConflictItem[] = []
    const quiz: AdaptiveQuestion[] = []
    let qCount = 1

    // Target audience ambiguity for college/event apps
    if (lower.includes('college') && (lower.includes('event') || lower.includes('management'))) {
      if (!/(student|faculty|admin|teacher)/.test(lower)) {
        const amb: AmbiguityItem = {
          phrase: 'college events management',
          category: 'target_audience',
          impact: 'MEDIUM',
          canInfer: false,
          safeDefault: 'Both Students & Faculty',
          requiresQuestion: true,
          targetedQuestion: 'Who are the primary users of the event management system?',
          options: ['Students', 'Faculty', 'Both Students & Faculty']
        }
        ambiguities.push(amb)
        quiz.push({
          id: `QUIZ-Q${qCount++}`,
          question: amb.targetedQuestion!,
          contextReason: 'Target audience determines navigation tabs and authorization roles.',
          options: amb.options,
          allowCustom: true
        })
      }
    }

    // Design direction ambiguity if asked for "best ui" or "modern ui"
    if (lower.includes('best ui') || lower.includes('better ui')) {
      if (!/(minimal|dark|enterprise|light)/.test(lower)) {
        const amb: AmbiguityItem = {
          phrase: 'best ui',
          category: 'visual_style',
          impact: 'LOW',
          canInfer: true,
          safeDefault: 'Premium Modern Minimal',
          requiresQuestion: false,
          targetedQuestion: 'Which aesthetic style should the interface follow?',
          options: ['Premium Dark', 'Clean Minimal', 'Enterprise Slate', 'Preserve Current']
        }
        ambiguities.push(amb)
      }
    }

    // Conflict detection: e.g. "don't modify backend" and asking to create new backend API
    const noBackend = negativeReqs.some((nr) => nr.action === 'MODIFY_BACKEND')
    const wantsNewBackend = /backend/.test(lower) && /(add|create|new api|rewrite)/.test(lower)
    if (noBackend && wantsNewBackend) {
      conflicts.push({
        conflictType: 'DIRECT',
        priorInstruction: 'Constraint: Do not modify backend',
        currentInstruction: 'Request: Add new backend API',
        recommendedResolution: 'Preserve backend intact and use client-side state, or confirm backend modification.',
        resolutionOptions: ['Preserve backend (use client mock state)', 'Allow adding new backend endpoint']
      })
    }

    return { ambiguities, conflicts, quiz }
  }

  /**
   * Section 33: Acceptance Criteria
   */
  static buildAcceptanceCriteria(
    explicit: RequirementItem[],
    negative: NegativeRequirement[]
  ): AcceptanceCriteriaItem[] {
    const criteria: AcceptanceCriteriaItem[] = []
    let c = 1

    for (const req of explicit) {
      criteria.push({
        id: `AC-${String(c++).padStart(2, '0')}`,
        description: `Verify that ${req.text} functions reliably`,
        targetVerification: `Automated test and inspection for category '${req.category}'`
      })
    }

    for (const neg of negative) {
      criteria.push({
        id: `AC-${String(c++).padStart(2, '0')}`,
        description: `Ensure invariant: ${neg.reason}`,
        targetVerification: `Diff inspection confirms '${neg.scope}' remains preserved`
      })
    }

    return criteria
  }

  /**
   * Main Pipeline Execution (Section 1)
   */
  static analyze(prompt: string, targetFile?: string, scope: 'file' | 'project' | 'workspace' = 'workspace'): UnderstandingModel {
    const normalizedPrompt = this.normalizePrompt(prompt)
    const messageTypes = this.classifyMessageTypes(normalizedPrompt)
    const { action, goal, outcome } = this.extractGoalAndOutcome(normalizedPrompt, messageTypes)

    const negativeRequirements = this.extractNegativeRequirements(normalizedPrompt)
    const { explicit, implicit } = this.extractRequirements(normalizedPrompt)
    const { ambiguities, conflicts, quiz } = this.detectAmbiguitiesAndQuiz(normalizedPrompt, explicit, negativeRequirements)
    const acceptanceCriteria = this.buildAcceptanceCriteria(explicit, negativeRequirements)

    const summaryParts = [
      `I understand that you want to **${goal}**.`
    ]

    const reqList = explicit.slice(0, 4).map((r) => `• ${r.text}`).join('\n')
    if (reqList) summaryParts.push(`Key requirements:\n${reqList}`)

    if (negativeRequirements.length > 0) {
      const negList = negativeRequirements.map((n) => `• Invariant: ${n.reason}`).join('\n')
      summaryParts.push(`Preserved Constraints:\n${negList}`)
    }

    summaryParts.push(`Deliverable outcome: **${outcome}**`)
    const summaryText = summaryParts.join('\n\n')

    // Decision: Section 1 & Section 41
    let decision: 'ANSWER' | 'ASK' | 'PLAN' | 'EXECUTE' = 'PLAN'
    if (messageTypes.includes('QUESTION') && explicit.length <= 1 && !/(build|create|make|fix)/.test(normalizedPrompt.toLowerCase())) {
      decision = 'ANSWER'
    } else if (quiz.length > 0) {
      decision = 'ASK'
    } else {
      decision = 'PLAN'
    }

    return {
      rawPrompt: prompt,
      normalizedPrompt,
      messageTypes,
      primaryGoal: goal,
      desiredOutcome: outcome,
      actionType: action,
      targetScope: scope,
      targetFile,
      qualityIntent: ['Production-ready', 'High precision', 'Verified'],
      userKnowledgeLevel: 'GENERAL',
      explicitRequirements: explicit,
      implicitRequirements: implicit,
      negativeRequirements,
      constraints: {},
      preferences: [],
      referencesResolved: {},
      referenceConfidence: 'HIGH',
      ambiguities,
      conflicts,
      missingInfo: quiz.map((q) => q.question),
      adaptiveQuiz: quiz,
      acceptanceCriteria,
      summaryText,
      decision,
      confidenceScore: conflicts.length === 0 ? 0.96 : 0.70,
      qualityGatePassed: conflicts.length === 0
    }
  }
}
