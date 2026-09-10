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

describe('StreamPanel — resumo legível de tool no card fechado', () => {
  it('shows the description field already on the collapsed card, not just the tool name', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 't1',
                name: 'Bash',
                input: { command: 'npm install', description: 'Instala as dependências do frontend' },
              },
            ],
          },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('Bash')).toBeInTheDocument()
    // "description" ganha prioridade sobre "command" — é o campo que a própria
    // tool Bash já preenche para leitura humana.
    expect(screen.getByText('Instala as dependências do frontend')).toBeInTheDocument()
    expect(screen.queryByText('npm install')).not.toBeInTheDocument()
  })

  it('falls back to the command field when there is no description', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [{ type: 'tool_use', id: 't1', name: 'Bash', input: { command: 'git status' } }],
          },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('git status')).toBeInTheDocument()
  })

  it('falls back to any string field for an unrecognized tool shape', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [{ type: 'tool_use', id: 't1', name: 'MinhaFerramenta', input: { alvo: 'src/App.jsx' } }],
          },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('src/App.jsx')).toBeInTheDocument()
  })

  it('shows nothing extra when the tool has no string field to summarize', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: { content: [{ type: 'tool_use', id: 't1', name: 'Contador', input: { total: 3 } }] },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('Contador')).toBeInTheDocument()
    expect(screen.queryByText('3')).not.toBeInTheDocument()
  })

  it('shows the pending question text on the collapsed ask_user card too, not just in InstructionBox', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 't1',
                name: 'mcp__ask-user__ask_user',
                input: { question: 'Qual branch devo usar?' },
              },
            ],
          },
        }),
      )
    })
    render(<StreamPanel chainName="hist-005" plugin="claude_code_runner" />)

    expect(await screen.findByText('Qual branch devo usar?')).toBeInTheDocument()
  })
})

describe('StreamPanel — pergunta pendente (ask_user, coding_local_interativo)', () => {
  it('reports a pending ask_user tool call via onPendingQuestion using the real namespaced tool name', async () => {
    // Regression: verified live against the real `claude` CLI, an MCP tool call
    // is reported as `mcp__<server>__<tool>` (here `mcp__ask-user__ask_user`),
    // never the bare `ask_user` the server itself declares — matching only the
    // bare name meant the question was never recognized, silently falling back
    // to the generic raw-JSON tool card with no way to answer.
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              {
                type: 'tool_use',
                id: 't1',
                name: 'mcp__ask-user__ask_user',
                input: { question: 'Qual branch devo usar?', options: ['feature/a', 'feature/b'] },
              },
            ],
          },
        }),
      )
    })
    const onPendingQuestion = vi.fn()
    render(
      <StreamPanel chainName="hist-005" plugin="claude_code_runner" onPendingQuestion={onPendingQuestion} />,
    )

    await screen.findByText('mcp__ask-user__ask_user')
    expect(onPendingQuestion).toHaveBeenLastCalledWith({
      text: 'Qual branch devo usar?',
      options: ['feature/a', 'feature/b'],
    })
  })

  it('also recognizes the bare ask_user name, as a fallback for an SDK/version that does not namespace', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [{ type: 'tool_use', id: 't1', name: 'ask_user', input: { question: 'Qual?' } }],
          },
        }),
      )
    })
    const onPendingQuestion = vi.fn()
    render(
      <StreamPanel chainName="hist-005" plugin="claude_code_runner" onPendingQuestion={onPendingQuestion} />,
    )

    await screen.findByText('ask_user')
    expect(onPendingQuestion).toHaveBeenLastCalledWith({ text: 'Qual?', options: [] })
  })

  it('reports null once the ask_user call resolves (tool_result arrives)', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              { type: 'tool_use', id: 't1', name: 'mcp__ask-user__ask_user', input: { question: 'Qual?' } },
            ],
          },
        }),
      )
      onLine(
        JSON.stringify({
          type: 'user',
          message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'resposta do usuário' }] },
        }),
      )
    })
    const onPendingQuestion = vi.fn()
    render(
      <StreamPanel chainName="hist-005" plugin="claude_code_runner" onPendingQuestion={onPendingQuestion} />,
    )

    await screen.findByText('concluído')
    expect(onPendingQuestion).toHaveBeenLastCalledWith(null)
  })

  it('reports null on unmount, so a new run never inherits a stale question', async () => {
    vi.spyOn(apiClient, 'openStream').mockImplementation(async (_chainName, { onLine }) => {
      onLine(
        JSON.stringify({
          type: 'assistant',
          message: {
            content: [
              { type: 'tool_use', id: 't1', name: 'mcp__ask-user__ask_user', input: { question: 'Qual?' } },
            ],
          },
        }),
      )
    })
    const onPendingQuestion = vi.fn()
    const { unmount } = render(
      <StreamPanel chainName="hist-005" plugin="claude_code_runner" onPendingQuestion={onPendingQuestion} />,
    )
    await screen.findByText('mcp__ask-user__ask_user')

    unmount()

    expect(onPendingQuestion).toHaveBeenLastCalledWith(null)
  })
})
