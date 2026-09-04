import { describe, expect, it } from 'vitest'
import { resolveConfigPath } from './resolveConfigPath'

describe('resolveConfigPath (ADR-006-AC-06)', () => {
  it('joins the configured directory and the id with a single slash', () => {
    expect(resolveConfigPath('/home/user/chains', 'HIST-005')).toBe(
      '/home/user/chains/HIST-005.yaml',
    )
  })

  it('does not duplicate the slash when the directory already ends with one', () => {
    expect(resolveConfigPath('/home/user/chains/', 'HIST-005')).toBe(
      '/home/user/chains/HIST-005.yaml',
    )
  })

  it('trims surrounding whitespace from the id', () => {
    expect(resolveConfigPath('/chains', '  HIST-005  ')).toBe('/chains/HIST-005.yaml')
  })
})
