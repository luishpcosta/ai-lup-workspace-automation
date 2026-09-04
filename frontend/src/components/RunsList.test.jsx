import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import RunsList from './RunsList'

afterEach(() => {
  vi.restoreAllMocks()
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
