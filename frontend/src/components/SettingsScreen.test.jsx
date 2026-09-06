import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import SettingsScreen from './SettingsScreen'

describe('SettingsScreen (ADR-007)', () => {
  it('saves baseUrl and specsBaseUrl and notifies the parent', async () => {
    const onSaved = vi.fn()
    render(<SettingsScreen onSaved={onSaved} />)

    await userEvent.type(screen.getByLabelText('URL base do backend'), 'http://localhost:8000')
    await userEvent.type(
      screen.getByLabelText('URL base do repositório remoto de specs'),
      'https://example.github.io/doc-repo-example',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(onSaved).toHaveBeenCalledWith({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.github.io/doc-repo-example',
    })
  })

  it('pre-fills fields from the initial value (reload keeps configuration visible)', () => {
    render(
      <SettingsScreen
        initial={{
          baseUrl: 'http://localhost:8000',
          specsBaseUrl: 'https://example.github.io/doc-repo-example',
        }}
        onSaved={() => {}}
      />,
    )
    expect(screen.getByLabelText('URL base do backend')).toHaveValue('http://localhost:8000')
    expect(screen.getByLabelText('URL base do repositório remoto de specs')).toHaveValue(
      'https://example.github.io/doc-repo-example',
    )
  })
})
