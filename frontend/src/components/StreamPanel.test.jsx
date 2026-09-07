import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import StreamPanel from './StreamPanel'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('StreamPanel (ADR-006-AC-07, AC-08)', () => {
  it('renders each line delivered by openStream, in order, as it arrives', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine('{"type":"a"}')
      onLine('{"type":"b"}')
    })
    render(<StreamPanel chainName="hist-005" />)
    expect(await screen.findByText(/"type":"a"/)).toBeInTheDocument()
    expect(screen.getByText(/"type":"b"/)).toBeInTheDocument()
  })

  it('shows "sem sessão ativa" on a not_streamable error, without retrying automatically', async () => {
    const openStreamSpy = vi
      .spyOn(apiClient, 'openStream')
      .mockRejectedValue(new ApiError({ kind: 'http', status: 409, code: 'not_streamable' }))
    render(<StreamPanel chainName="hist-005" />)
    expect(await screen.findByText('Sem sessão ativa no momento.')).toBeInTheDocument()
    expect(openStreamSpy).toHaveBeenCalledTimes(1)
  })

  it('shows a clear connection error distinct from "sem sessão ativa"', async () => {
    vi.spyOn(apiClient, 'openStream').mockRejectedValue(
      new ApiError({ kind: 'connection', message: 'Não foi possível conectar' }),
    )
    render(<StreamPanel chainName="hist-005" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar')
  })
})

describe('StreamPanel — leitura formatada por plugin (ADR-010-AC-05/AC-06/AC-07)', () => {
  it('renders assistant text and tool traces instead of raw JSON, for a known plugin', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text: 'Olá, tudo bem?' }] } }))
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: { cmd: 'ls' } }] },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('Olá, tudo bem?')).toBeInTheDocument()
    expect(screen.getByText('Bash')).toBeInTheDocument()
    expect(screen.getByText('executando')).toBeInTheDocument()
    expect(screen.getByText('Claude Code')).toBeInTheDocument()
    expect(screen.queryByText(/"type":"assistant"/)).not.toBeInTheDocument()
  })

  it('toggles to the raw log and back without losing content', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text: 'Oi' }] } }))
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)
    await screen.findByText('Oi')

    await userEvent.click(screen.getByRole('button', { name: 'Ver log bruto' }))
    expect(await screen.findByText(/"type":"assistant"/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Ver leitura formatada' }))
    expect(await screen.findByText('Oi')).toBeInTheDocument()
  })

  it('falls back to raw log with no toggle when the plugin has no dedicated formatter', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine('some plain log line')
    })
    render(<StreamPanel chainName="hist-005" plugin="shell_script_runner" />)

    expect(await screen.findByText('some plain log line')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Ver log bruto|Ver leitura formatada/ })).not.toBeInTheDocument()
  })

  it('falls back to raw for a non-JSON line without crashing, even with a known plugin', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine('not valid json {{')
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('not valid json {{')).toBeInTheDocument()
  })
})
