import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { loadDefaults } from '../lib/config'
import SettingsScreen from './SettingsScreen'

async function withDefaultsFile(body) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => body })
  await loadDefaults()
  vi.restoreAllMocks()
}

async function withoutDefaultsFile() {
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('sem arquivo'))
  await loadDefaults()
  vi.restoreAllMocks()
}

beforeEach(async () => {
  window.localStorage.clear()
  await withoutDefaultsFile()
})

afterEach(() => {
  vi.restoreAllMocks()
})

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
      reposRoot: '',
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

describe('SettingsScreen — pasta de trabalho e defaults (ADR-009)', () => {
  it('saves the working folder alongside the two URLs (AC-05)', async () => {
    const onSaved = vi.fn()
    render(<SettingsScreen onSaved={onSaved} />)

    await userEvent.type(screen.getByLabelText('URL base do backend'), 'http://localhost:8000')
    await userEvent.type(
      screen.getByLabelText('URL base do repositório remoto de specs'),
      'https://example.test',
    )
    await userEvent.type(
      screen.getByLabelText(/Pasta de trabalho/),
      'C:/dev/local-workflow-pipeline',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(onSaved).toHaveBeenCalledWith({
      baseUrl: 'http://localhost:8000',
      specsBaseUrl: 'https://example.test',
      reposRoot: 'C:/dev/local-workflow-pipeline',
    })
  })

  it('marks a value that came from painel-config.json as a default, not typed input (AC-04)', async () => {
    await withDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    render(<SettingsScreen onSaved={() => {}} />)

    expect(screen.getByLabelText('URL base do backend')).toHaveValue('http://default:8000')
    // Os dois campos vindos do arquivo se anunciam; a pasta de trabalho, vazia, não.
    expect(screen.getAllByText('default do arquivo')).toHaveLength(2)
  })

  it('does not mark a value the user actually saved as a file default (AC-04)', async () => {
    await withDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    window.localStorage.setItem(
      'painel-config',
      JSON.stringify({ baseUrl: 'http://escolhido:9000', specsBaseUrl: 'https://escolhido.test' }),
    )
    render(<SettingsScreen onSaved={() => {}} />)

    expect(screen.getByLabelText('URL base do backend')).toHaveValue('http://escolhido:9000')
    expect(screen.queryByText('default do arquivo')).not.toBeInTheDocument()
  })

  it('restores the file defaults, discarding what was saved (AC-04)', async () => {
    await withDefaultsFile({
      baseUrl: 'http://default:8000',
      specsBaseUrl: 'https://default.test/specs',
    })
    window.localStorage.setItem(
      'painel-config',
      JSON.stringify({ baseUrl: 'http://escolhido:9000', specsBaseUrl: 'https://escolhido.test' }),
    )
    render(<SettingsScreen onSaved={() => {}} />)

    await userEvent.click(screen.getByRole('button', { name: 'Restaurar defaults do arquivo' }))

    expect(screen.getByLabelText('URL base do backend')).toHaveValue('http://default:8000')
    expect(window.localStorage.getItem('painel-config')).toBeNull()
  })

  it('uses no placeholder that could be mistaken for a real value (AC-04)', () => {
    render(<SettingsScreen onSaved={() => {}} />)

    for (const label of [
      'URL base do backend',
      'URL base do repositório remoto de specs',
      /Pasta de trabalho/,
    ]) {
      expect(screen.getByLabelText(label)).not.toHaveAttribute('placeholder')
    }
  })
})
