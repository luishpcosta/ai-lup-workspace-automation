import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import { setConfig } from '../lib/config'
import TriggerForm from './TriggerForm'

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TriggerForm (ADR-006-AC-06)', () => {
  it('resolves each id to <configDir>/<id>.yaml and dispatches one POST /runs per id', async () => {
    const spy = vi.spyOn(apiClient, 'createRun').mockImplementation(async (configPath) => ({
      chain_name: configPath.split('/').pop().replace('.yaml', ''),
      status: 'started',
    }))
    render(<TriggerForm />)
    await userEvent.type(screen.getByLabelText(/IDs de documento/), 'HIST-005\nHIST-006')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))

    expect(spy).toHaveBeenCalledWith('/chains/HIST-005.yaml')
    expect(spy).toHaveBeenCalledWith('/chains/HIST-006.yaml')
    expect(await screen.findByText(/HIST-005: iniciado/)).toBeInTheDocument()
    expect(screen.getByText(/HIST-006: iniciado/)).toBeInTheDocument()
  })

  it('a single invalid id in the batch fails on its own without stopping the others (AC-13)', async () => {
    vi.spyOn(apiClient, 'createRun').mockImplementation(async (configPath) => {
      if (configPath.includes('DOES-NOT-EXIST')) {
        throw new ApiError({ kind: 'http', status: 400, code: 'invalid_config', message: 'invalid config' })
      }
      return { chain_name: 'hist-005', status: 'started' }
    })
    render(<TriggerForm />)
    await userEvent.type(screen.getByLabelText(/IDs de documento/), 'HIST-005\nDOES-NOT-EXIST')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))

    expect(await screen.findByText(/HIST-005: iniciado/)).toBeInTheDocument()
    expect(await screen.findByText('invalid config')).toBeInTheDocument()
  })

  it('calls onDispatched after the batch settles, so the caller can refresh the list', async () => {
    vi.spyOn(apiClient, 'createRun').mockResolvedValue({ chain_name: 'hist-005', status: 'started' })
    const onDispatched = vi.fn()
    render(<TriggerForm onDispatched={onDispatched} />)
    await userEvent.type(screen.getByLabelText(/IDs de documento/), 'HIST-005')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))
    await screen.findByText(/HIST-005: iniciado/)
    expect(onDispatched).toHaveBeenCalledTimes(1)
  })
})
