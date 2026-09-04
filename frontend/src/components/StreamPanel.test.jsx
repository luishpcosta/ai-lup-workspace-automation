import { render, screen } from '@testing-library/react'
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
