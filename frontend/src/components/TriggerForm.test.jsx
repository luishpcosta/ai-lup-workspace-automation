import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiClient from '../lib/apiClient'
import { ApiError } from '../lib/apiClient'
import { setConfig } from '../lib/config'
import TriggerForm from './TriggerForm'

const TEMPLATE = {
  id: 'investigar-impacto',
  label: 'Investigar impacto',
  description: 'Investiga impacto sem PR.',
  params_schema: [{ name: 'prompt', label: 'O que investigar', type: 'textarea', required: true }],
}

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test' })
  vi.spyOn(apiClient, 'getWorkflows').mockResolvedValue([TEMPLATE])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TriggerForm (ADR-007)', () => {
  it('selects a template, fills its dynamic form and dispatches POST /runs/from-template', async () => {
    const spy = vi
      .spyOn(apiClient, 'createRunFromTemplate')
      .mockResolvedValue({ chain_name: 'investigar-impacto--abc123', status: 'started' })
    render(<TriggerForm />)

    await userEvent.selectOptions(await screen.findByLabelText('Workflow'), 'Investigar impacto')
    await userEvent.type(screen.getByLabelText(/O que investigar/), 'qual o impacto de X?')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))

    expect(spy).toHaveBeenCalledWith('investigar-impacto', { prompt: 'qual o impacto de X?' })
    expect(await screen.findByText(/iniciado \(investigar-impacto--abc123\)/)).toBeInTheDocument()
  })

  it('the dispatch button stays disabled until a template is selected', async () => {
    render(<TriggerForm />)
    await screen.findByLabelText('Workflow')
    expect(screen.getByRole('button', { name: 'Disparar' })).toBeDisabled()
  })

  it('shows a clear inline error when the dispatch is rejected, without crashing the form', async () => {
    vi.spyOn(apiClient, 'createRunFromTemplate').mockRejectedValue(
      new ApiError({ kind: 'http', status: 400, code: 'invalid_params', message: 'missing prompt' }),
    )
    render(<TriggerForm />)

    await userEvent.selectOptions(await screen.findByLabelText('Workflow'), 'Investigar impacto')
    await userEvent.type(screen.getByLabelText(/O que investigar/), 'x')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))

    expect(await screen.findByText('missing prompt')).toBeInTheDocument()
  })

  it('calls onDispatched after a successful dispatch, so the caller can refresh the list', async () => {
    vi.spyOn(apiClient, 'createRunFromTemplate').mockResolvedValue({
      chain_name: 'investigar-impacto--abc123',
      status: 'started',
    })
    const onDispatched = vi.fn()
    render(<TriggerForm onDispatched={onDispatched} />)

    await userEvent.selectOptions(await screen.findByLabelText('Workflow'), 'Investigar impacto')
    await userEvent.type(screen.getByLabelText(/O que investigar/), 'x')
    await userEvent.click(screen.getByRole('button', { name: 'Disparar' }))

    await screen.findByText(/iniciado/)
    expect(onDispatched).toHaveBeenCalledTimes(1)
  })

  it('implementar-historia-sdd is selectable from the same form (no separate screen)', async () => {
    apiClient.getWorkflows.mockResolvedValue([
      TEMPLATE,
      {
        id: 'implementar-historia-sdd',
        label: 'Implementar história',
        description: 'Pipeline completo.',
        params_schema: [{ name: 'historia_id', label: 'ID da história', type: 'text', required: true }],
      },
    ])
    render(<TriggerForm />)

    const select = await screen.findByLabelText('Workflow')
    await userEvent.selectOptions(select, 'Implementar história')

    expect(screen.getByLabelText(/ID da história/)).toBeInTheDocument()
  })
})
