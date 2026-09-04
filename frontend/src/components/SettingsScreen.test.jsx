import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import SettingsScreen from './SettingsScreen'

describe('SettingsScreen (ADR-006-AC-01)', () => {
  it('saves baseUrl and configDir and notifies the parent', async () => {
    const onSaved = vi.fn()
    render(<SettingsScreen onSaved={onSaved} />)

    await userEvent.type(screen.getByLabelText('URL base do backend'), 'http://localhost:8000')
    await userEvent.type(screen.getByLabelText('Diretório-base de configs'), '/chains')
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(onSaved).toHaveBeenCalledWith({ baseUrl: 'http://localhost:8000', configDir: '/chains' })
  })

  it('pre-fills fields from the initial value (AC-02: reload keeps configuration visible)', () => {
    render(
      <SettingsScreen
        initial={{ baseUrl: 'http://localhost:8000', configDir: '/chains' }}
        onSaved={() => {}}
      />,
    )
    expect(screen.getByLabelText('URL base do backend')).toHaveValue('http://localhost:8000')
    expect(screen.getByLabelText('Diretório-base de configs')).toHaveValue('/chains')
  })
})
