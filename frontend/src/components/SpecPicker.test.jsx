import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setConfig } from '../lib/config'
import * as specsClient from '../lib/specsClient'
import SpecPicker from './SpecPicker'

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.github.io/doc-repo-example' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('SpecPicker / Knowledge Bases (ADR-007 RF-01, ADR-010 RF-02)', () => {
  it('fetches the index using the configured specsBaseUrl and selects an option', async () => {
    const spy = vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([
      { id: '005-a', title: 'Spec A' },
      { id: '004-b', title: 'Spec B' },
    ])
    const onChange = vi.fn()
    render(<SpecPicker id="specs" value={[]} onChange={onChange} />)

    const input = await screen.findByLabelText('Knowledge Bases')
    expect(spy).toHaveBeenCalledWith('https://example.github.io/doc-repo-example')

    await userEvent.click(input)
    await userEvent.click(await screen.findByText('Spec A'))
    expect(onChange).toHaveBeenCalledWith(['005-a'])
  })

  it('renders as a bar-style multi-select combobox, not a checkbox list', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([{ id: '005-a', title: 'Spec A' }])
    render(<SpecPicker id="specs" value={[]} onChange={() => {}} />)

    const input = await screen.findByLabelText('Knowledge Bases')
    expect(input).toHaveAttribute('role', 'combobox')
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('removing the last selected value (Backspace) reports it out of the array', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([{ id: '005-a', title: 'Spec A' }])
    const onChange = vi.fn()
    render(<SpecPicker id="specs" value={['005-a']} onChange={onChange} />)

    await screen.findByText('Spec A')
    const input = screen.getByLabelText('Knowledge Bases')
    await userEvent.type(input, '{backspace}')

    expect(onChange).toHaveBeenCalledWith([])
  })

  it('shows the error message when the remote fetch fails', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockRejectedValue(new Error('404 ao buscar specs'))
    render(<SpecPicker id="specs" value={[]} onChange={() => {}} />)

    expect(await screen.findByText(/Erro ao listar Knowledge Bases.*404 ao buscar specs/)).toBeInTheDocument()
  })

  it('shows an empty state when the remote repository has no Knowledge Bases', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([])
    render(<SpecPicker id="specs" value={[]} onChange={() => {}} />)

    expect(await screen.findByText('Nenhuma Knowledge Base encontrada no repositório remoto.')).toBeInTheDocument()
  })
})
