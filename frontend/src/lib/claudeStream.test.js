import { describe, expect, it } from 'vitest'
import { buildClaudeTurns } from './claudeStream'

function line(obj) {
  return JSON.stringify(obj)
}

describe('buildClaudeTurns (ADR-010-AC-05/AC-07)', () => {
  it('turns assistant text blocks into text turns', () => {
    const lines = [
      line({ type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'Olá' }] } }),
    ]
    expect(buildClaudeTurns(lines)).toEqual([{ kind: 'text', text: 'Olá' }])
  })

  it('pairs a tool_use with its later tool_result, tracking status', () => {
    const lines = [
      line({
        type: 'assistant',
        message: { content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: { cmd: 'ls' } }] },
      }),
      line({
        type: 'user',
        message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'a.txt', is_error: false }] },
      }),
    ]
    const turns = buildClaudeTurns(lines)
    expect(turns).toHaveLength(1)
    expect(turns[0]).toMatchObject({ kind: 'tool', name: 'Bash', status: 'done', output: 'a.txt' })
  })

  it('marks a tool as failed when tool_result reports is_error', () => {
    const lines = [
      line({ type: 'assistant', message: { content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: {} }] } }),
      line({
        type: 'user',
        message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'boom', is_error: true }] },
      }),
    ]
    expect(buildClaudeTurns(lines)[0]).toMatchObject({ status: 'failed' })
  })

  it('a tool_use with no matching tool_result yet stays running', () => {
    const lines = [
      line({ type: 'assistant', message: { content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: {} }] } }),
    ]
    expect(buildClaudeTurns(lines)[0]).toMatchObject({ status: 'running' })
  })

  it('turns the final result event into a summary', () => {
    const ok = buildClaudeTurns([line({ type: 'result', is_error: false, result: 'tudo certo' })])
    expect(ok).toEqual([{ kind: 'summary', ok: true, text: 'tudo certo' }])

    const failed = buildClaudeTurns([line({ type: 'result', is_error: true, result: 'deu ruim' })])
    expect(failed).toEqual([{ kind: 'summary', ok: false, text: 'deu ruim' }])
  })

  it('ignores system (init) events — no turn produced', () => {
    expect(buildClaudeTurns([line({ type: 'system', subtype: 'init' })])).toEqual([])
  })

  it('falls back to a raw turn for a non-JSON line, without throwing', () => {
    expect(() => buildClaudeTurns(['not json {{'])).not.toThrow()
    expect(buildClaudeTurns(['not json {{'])).toEqual([{ kind: 'raw', text: 'not json {{' }])
  })

  it('skips blank lines', () => {
    expect(buildClaudeTurns(['', '   '])).toEqual([])
  })
})
