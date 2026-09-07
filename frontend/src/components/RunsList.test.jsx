import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import RunsList from './RunsList'

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('RunsList (ADR-006-AC-04)', () => {
  it('renders every run returned by GET /runs', async () => {
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' },
      { chain_name: 'hist-006', workflow_name: 'w', status: 'running', updated_at: 't2' },
    ])
    render(<RunsList onSelect={() => {}} />)
    expect(await screen.findByText('hist-005')).toBeInTheDocument()
    expect(screen.getByText('hist-006')).toBeInTheDocument()
  })

  it('highlights a failed run with a visual marker, passively (ADR-006-AC-12)', async () => {
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'failed', updated_at: 't1' },
    ])
    render(<RunsList onSelect={() => {}} />)
    const row = (await screen.findByText('hist-005')).closest('tr')
    expect(row).toHaveClass('run-row-failed')
    expect(row).toHaveAttribute('data-status', 'failed')
  })

  it('calls onSelect with the chain_name when a row is clicked', async () => {
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' },
    ])
    const onSelect = vi.fn()
    render(<RunsList onSelect={onSelect} />)
    await userEvent.click(await screen.findByText('hist-005'))
    expect(onSelect).toHaveBeenCalledWith('hist-005')
  })

  it('shows a clear error instead of hanging when the backend is unreachable (AC-03)', async () => {
    vi.spyOn(apiClient, 'getRuns').mockRejectedValue(
      new ApiError({ kind: 'connection', message: 'Não foi possível conectar' }),
    )
    render(<RunsList onSelect={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível conectar')
  })
})

describe('RunsList — atualização automática (ADR-011-AC-08/AC-09)', () => {
  it('reflects a status change on its own while a run is active, without a manual click', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const getRuns = vi
      .spyOn(apiClient, 'getRuns')
      .mockResolvedValueOnce([
        { chain_name: 'hist-005', workflow_name: 'w', status: 'running', updated_at: 't1' },
      ])
      .mockResolvedValueOnce([
        { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't2' },
      ])

    render(<RunsList onSelect={() => {}} />)
    await screen.findByText('hist-005')
    expect(getRuns).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })

    expect(getRuns).toHaveBeenCalledTimes(2)
    expect(await screen.findByText('Concluído')).toBeInTheDocument()
  })

  it('stops polling once nothing is active anymore', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const getRuns = vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' },
    ])

    render(<RunsList onSelect={() => {}} />)
    await screen.findByText('hist-005')
    expect(getRuns).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000)
    })

    expect(getRuns).toHaveBeenCalledTimes(1)
  })
})

describe('RunsList — arquivamento (ADR-011-AC-13/AC-14)', () => {
  it('archives a run from its row and it disappears from the default listing', async () => {
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' },
    ])
    const archiveRun = vi.spyOn(apiClient, 'archiveRun').mockResolvedValue({
      chain_name: 'hist-005',
      archived: true,
    })

    render(<RunsList onSelect={() => {}} />)
    await screen.findByText('hist-005')
    await userEvent.click(screen.getByRole('button', { name: 'Arquivar' }))

    expect(archiveRun).toHaveBeenCalledWith('hist-005')
    expect(screen.queryByText('hist-005')).not.toBeInTheDocument()
  })

  it('switches to GET /runs?archived=true and shows "Desarquivar" when the "Arquivadas" tab is selected', async () => {
    const getRuns = vi.spyOn(apiClient, 'getRuns').mockImplementation(({ archived } = {}) =>
      Promise.resolve(
        archived
          ? [{ chain_name: 'hist-old', workflow_name: 'w', status: 'completed', updated_at: 't0' }]
          : [{ chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' }],
      ),
    )

    render(<RunsList onSelect={() => {}} />)
    await screen.findByText('hist-005')

    await userEvent.click(screen.getByRole('button', { name: /Arquivadas/ }))

    expect(await screen.findByText('hist-old')).toBeInTheDocument()
    expect(getRuns).toHaveBeenLastCalledWith({ archived: true })
    expect(screen.getByRole('button', { name: 'Desarquivar' })).toBeInTheDocument()
  })
})
