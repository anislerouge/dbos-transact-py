/**
 * Convert a Python repr string to something JSON.parse can handle.
 * Handles: single quotes -> double quotes, tuples () -> arrays [],
 * trailing commas before closing brackets, True/False/None -> JSON equivalents.
 */
function pythonToJson(s: string): string {
  let out = ''
  let inString = false
  let stringChar = ''

  for (let i = 0; i < s.length; i++) {
    const ch = s[i]

    if (inString) {
      if (ch === '\\') {
        out += ch + (s[i + 1] || '')
        i++
        continue
      }
      if (ch === stringChar) {
        inString = false
        out += '"'
        continue
      }
      // Escape double quotes inside a single-quoted string
      if (ch === '"') {
        out += '\\"'
        continue
      }
      out += ch
    } else {
      if (ch === "'" || ch === '"') {
        inString = true
        stringChar = ch
        out += '"'
      } else if (ch === '(') {
        out += '['
      } else if (ch === ')') {
        out += ']'
      } else {
        out += ch
      }
    }
  }

  // Remove trailing commas before ] or }
  out = out.replace(/,\s*([}\]])/g, '$1')

  // Replace Python literals
  out = out.replace(/\bTrue\b/g, 'true')
  out = out.replace(/\bFalse\b/g, 'false')
  out = out.replace(/\bNone\b/g, 'null')

  return out
}

/** Parse DBOS workflow input (Python repr or JSON) into args/kwargs. */
export function parseWorkflowInput(raw: string | null): { args: unknown[]; kwargs: Record<string, unknown> } {
  if (!raw) return { args: [], kwargs: {} }

  // Try JSON first
  try {
    const parsed = JSON.parse(raw)
    return {
      args: Array.isArray(parsed.args) ? parsed.args : [],
      kwargs: parsed.kwargs && typeof parsed.kwargs === 'object' ? parsed.kwargs : {},
    }
  } catch {
    // Not valid JSON, try Python repr conversion
  }

  try {
    const jsonStr = pythonToJson(raw)
    const parsed = JSON.parse(jsonStr)
    return {
      args: Array.isArray(parsed.args) ? parsed.args : [],
      kwargs: parsed.kwargs && typeof parsed.kwargs === 'object' ? parsed.kwargs : {},
    }
  } catch {
    return { args: [], kwargs: {} }
  }
}
