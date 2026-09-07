import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import RunDetail from './RunDetail'

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function stubStreamAndInstruction() {
  vi.spyOn(apiClient, 'openStream').mockRejectedValue(
    new ApiError({ kind: 'http', status: 409, code: 'not_streamable' }),
  )
}

describe('RunDetail (ADR-006-AC-05)', () => {
  it('renders step-by-step status from GET /runs/{chain_name}', async () => {
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'failed',
      steps: [
        { step_name: 'implementar', status: 'failed', attempt_count: 1, error_message: 'boom' },
      ],
    })
    render(<RunDetail chainName="hist-005" onBack={() => {}} />)
    expect(await screen.findByText('implementar')).toBeInTheDocument()
    expect(screen.getByText('boom')).toBeInTheDocument()
  })

  it('shows a clear error when the chain_name does not exist (404)', async () => {
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockRejectedValue(
      new ApiError({ kind: 'http', status: 404, code: 'not_found', message: 'unknown chain_name' }),
    )
    render(<RunDetail chainName="ghost" onBack={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('unknown chain_name')
  })
})

describe('RunDetail — cancel (ADR-006-AC-10)', () => {
  it.each([
    ['cancelled', 'Run cancelado.'],
    ['already_running', 'A etapa já está em execução e não pode ser interrompida.'],
    ['not_cancellable', 'Este run não pode mais ser cancelado.'],
  ])('reflects the %s outcome from POST /cancelar', async (status, expectedText) => {
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'running',
      steps: [],
    })
    vi.spyOn(apiClient, 'cancelRun').mockResolvedValue({ status })
    render(<RunDetail chainName="hist-005" onBack={() => {}} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))
    expect(await screen.findByText(expectedText)).toBeInTheDocument()
  })
})

describe('RunDetail — atualização automática (ADR-011-AC-10/AC-11)', () => {
  it('reflects a step advancing on its own while the run is still going, without a manual click', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail')
      .mockResolvedValueOnce({
        chain_name: 'hist-005',
        status: 'running',
        steps: [{ step_name: 'implementar', status: 'running', attempt_count: 1 }],
      })
      .mockResolvedValueOnce({
        chain_name: 'hist-005',
        status: 'completed',
        steps: [{ step_name: 'implementar', status: 'completed', attempt_count: 1 }],
      })

    render(<RunDetail chainName="hist-005" onBack={() => {}} />)
    await screen.findByText('implementar')
    expect(apiClient.getRunDetail).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })

    expect(apiClient.getRunDetail).toHaveBeenCalledTimes(2)
    // duas ocorrências: badge de status geral + badge da etapa, ambos "Concluído"
    expect(await screen.findAllByText('Concluído')).toHaveLength(2)
  })

  it('stops polling once the run reaches a terminal status', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'completed',
      steps: [{ step_name: 'implementar', status: 'completed', attempt_count: 1 }],
    })

    render(<RunDetail chainName="hist-005" onBack={() => {}} />)
    await screen.findByText('implementar')
    expect(apiClient.getRunDetail).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000)
    })

    expect(apiClient.getRunDetail).toHaveBeenCalledTimes(1)
  })
})

describe('RunDetail — arquivamento (ADR-011-AC-15)', () => {
  it('archives a run from the detail header', async () => {
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'completed',
      steps: [],
      archived: false,
    })
    const archiveRun = vi
      .spyOn(apiClient, 'archiveRun')
      .mockResolvedValue({ chain_name: 'hist-005', archived: true })

    render(<RunDetail chainName="hist-005" onBack={() => {}} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Arquivar' }))

    expect(archiveRun).toHaveBeenCalledWith('hist-005')
    expect(await screen.findByRole('button', { name: 'Desarquivar' })).toBeInTheDocument()
  })

  it('shows an archived run normally, with an unarchive action available', async () => {
    stubStreamAndInstruction()
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'completed',
      steps: [],
      archived: true,
    })

    render(<RunDetail chainName="hist-005" onBack={() => {}} />)

    expect(await screen.findByRole('button', { name: 'Desarquivar' })).toBeInTheDocument()
  })
})
