import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiClient from '../lib/apiClient'
import { setConfig } from '../lib/config'
import TemplateSelector from './TemplateSelector'

const TEMPLATES = [
  {
    id: 'investigar-impacto',
    label: 'Investigar impacto',
    description: 'Investiga impacto sem PR.',
    params_schema: [],
  },
  {
    id: 'implementar-historia-sdd',
    label: 'Implementar história',
    description: 'Pipeline completo.',
    params_schema: [],
  },
]

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TemplateSelector (ADR-007 RF-01)', () => {
  it('lists workflows from GET /workflows and reports the selected one', async () => {
    vi.spyOn(apiClient, 'getWorkflows').mockResolvedValue(TEMPLATES)
    const onSelect = vi.fn()
    render(<TemplateSelector onSelect={onSelect} />)

    const select = await screen.findByLabelText('Disparar Execução Workflow')
    await userEvent.selectOptions(select, 'Investigar impacto')

    expect(onSelect).toHaveBeenCalledWith(TEMPLATES[0])
  })

  it('shows the selected template description', async () => {
    vi.spyOn(apiClient, 'getWorkflows').mockResolvedValue(TEMPLATES)
    render(<TemplateSelector value="investigar-impacto" onSelect={() => {}} />)

    expect(await screen.findByText('Investiga impacto sem PR.')).toBeInTheDocument()
  })

  it('shows the error message when the request fails', async () => {
    vi.spyOn(apiClient, 'getWorkflows').mockRejectedValue(new Error('backend fora do ar'))
    render(<TemplateSelector onSelect={() => {}} />)

    expect(await screen.findByText(/backend fora do ar/)).toBeInTheDocument()
  })
})
