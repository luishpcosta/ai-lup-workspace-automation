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

describe('SpecPicker (ADR-007 RF-01)', () => {
  it('fetches the index using the configured specsBaseUrl and toggles ids on click', async () => {
    const spy = vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([
      { id: '005-a', title: 'Spec A' },
      { id: '004-b', title: 'Spec B' },
    ])
    const onChange = vi.fn()
    render(<SpecPicker id="specs" value={[]} onChange={onChange} />)

    expect(await screen.findByText('Spec A')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledWith('https://example.github.io/doc-repo-example')

    await userEvent.click(screen.getByLabelText('Spec A'))
    expect(onChange).toHaveBeenCalledWith(['005-a'])
  })

  it('unchecking an already-selected spec removes it from the list', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([{ id: '005-a', title: 'Spec A' }])
    const onChange = vi.fn()
    render(<SpecPicker id="specs" value={['005-a']} onChange={onChange} />)

    const checkbox = await screen.findByLabelText('Spec A')
    expect(checkbox).toBeChecked()
    await userEvent.click(checkbox)

    expect(onChange).toHaveBeenCalledWith([])
  })

  it('shows the error message when the remote fetch fails', async () => {
    vi.spyOn(specsClient, 'fetchSpecsIndex').mockRejectedValue(new Error('404 ao buscar specs'))
    render(<SpecPicker id="specs" value={[]} onChange={() => {}} />)

    expect(await screen.findByText(/404 ao buscar specs/)).toBeInTheDocument()
  })
})
