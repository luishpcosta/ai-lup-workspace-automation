import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import RunDetail from './RunDetail'

afterEach(() => {
  vi.restoreAllMocks()
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
