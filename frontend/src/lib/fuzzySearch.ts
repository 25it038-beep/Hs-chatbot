import type { SlashCommand, FuzzyMatchResult } from '@/types/command'

/**
 * Fuzzy search utility to filter commands in real time based on query input.
 * Supports exact trigger matching, prefix matching, substring matching, alias matching, and character sequence matching.
 */
export function fuzzySearch(commands: SlashCommand[], query: string): FuzzyMatchResult[] {
  const trimmed = query.trim().toLowerCase()
  if (!trimmed) {
    return commands.map(cmd => ({ command: cmd, score: 1 }))
  }

  // Normalize query: remove leading '/' if present for flexible matching
  const cleanQuery = trimmed.startsWith('/') ? trimmed.slice(1) : trimmed
  const queryWithSlash = '/' + cleanQuery

  const results: FuzzyMatchResult[] = []

  for (const cmd of commands) {
    const cmdTrigger = cmd.command.toLowerCase() // e.g. "/chat"
    const cmdCleanTrigger = cmdTrigger.startsWith('/') ? cmdTrigger.slice(1) : cmdTrigger // e.g. "chat"
    const cmdName = cmd.name.toLowerCase()
    const cmdDesc = cmd.description.toLowerCase()
    const aliases = (cmd.aliases || []).map(a => a.toLowerCase())

    let score = 0

    // 1. Exact command match
    if (cmdTrigger === trimmed || cmdCleanTrigger === cleanQuery) {
      score = 100
    }
    // 2. Prefix match on trigger or name
    else if (cmdTrigger.startsWith(trimmed) || cmdCleanTrigger.startsWith(cleanQuery)) {
      score = 90
    } else if (cmdName.startsWith(cleanQuery)) {
      score = 85
    }
    // 3. Alias exact or prefix match
    else if (aliases.some(alias => alias === trimmed || alias === '/' + cleanQuery || alias.replace(/^\//, '').startsWith(cleanQuery))) {
      score = 80
    }
    // 4. Substring match in command, name, or description
    else if (cmdCleanTrigger.includes(cleanQuery)) {
      score = 75
    } else if (cmdName.includes(cleanQuery)) {
      score = 70
    } else if (aliases.some(alias => alias.includes(cleanQuery))) {
      score = 65
    } else if (cmdDesc.includes(cleanQuery)) {
      score = 50
    }
    // 5. Sequential character fuzzy match (e.g., 'cr' -> 'code-review')
    else {
      const fuzzyScore = computeSequenceScore(cleanQuery, cmdCleanTrigger, cmdName)
      if (fuzzyScore > 0) {
        score = fuzzyScore
      }
    }

    if (score > 0) {
      results.push({
        command: cmd,
        score,
      })
    }
  }

  return results.sort((a, b) => b.score - a.score)
}

function computeSequenceScore(query: string, trigger: string, name: string): number {
  const target = trigger + ' ' + name
  let targetIdx = 0
  let queryIdx = 0
  let matches = 0

  while (queryIdx < query.length && targetIdx < target.length) {
    if (query[queryIdx] === target[targetIdx]) {
      matches++
      queryIdx++
    }
    targetIdx++
  }

  if (queryIdx === query.length) {
    // All characters matched sequentially
    const ratio = matches / target.length
    return Math.floor(30 + ratio * 20)
  }

  return 0
}
