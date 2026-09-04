import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './lib/apiClient'
import * as apiClient from './lib/apiClient'
import App from './App'

beforeEach(() => {
  window.localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App (ADR-006-AC-01, AC-02)', () => {
  it('forces the settings screen when nothing is configured yet', () => {
    render(<App />)
    expect(screen.getByRole('form', { name: 'Configuração' })).toBeInTheDocument()
  })

  it('goes straight to the dashboard when a configuration already exists', async () => {
    window.localStorage.setItem(
      'painel-config',
      JSON.stringify({ baseUrl: 'http://localhost:8000', configDir: '/chains' }),
    )
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([])
    render(<App />)
    expect(screen.getByText('Painel de Controle — Motor de Workflow')).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Configuração' })).not.toBeInTheDocument()
    await screen.findByText('Nenhuma execução registrada ainda.')
  })
})

describe('App — navigation to detail and back', () => {
  it('opens a run detail on row click, and returns to the list on "Voltar"', async () => {
    window.localStorage.setItem(
      'painel-config',
      JSON.stringify({ baseUrl: 'http://localhost:8000', configDir: '/chains' }),
    )
    vi.spyOn(apiClient, 'getRuns').mockResolvedValue([
      { chain_name: 'hist-005', workflow_name: 'w', status: 'completed', updated_at: 't1' },
    ])
    vi.spyOn(apiClient, 'getRunDetail').mockResolvedValue({
      chain_name: 'hist-005',
      status: 'completed',
      steps: [],
    })
    vi.spyOn(apiClient, 'openStream').mockRejectedValue(
      new ApiError({ kind: 'http', status: 409, code: 'not_streamable' }),
    )

    render(<App />)
    await userEvent.click(await screen.findByText('hist-005'))
    expect(await screen.findByRole('region', { name: 'Detalhe de hist-005' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '← Voltar' }))
    expect(await screen.findByRole('table', { name: 'Lista de execuções' })).toBeInTheDocument()
  })
})
