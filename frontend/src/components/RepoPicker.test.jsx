import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiClient from '../lib/apiClient'
import { setConfig } from '../lib/config'
import RepoPicker from './RepoPicker'

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test' })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('RepoPicker (ADR-007 RF-02)', () => {
  it('lists repos returned by GET /workspace/repos and reports the selected path', async () => {
    vi.spyOn(apiClient, 'getLocalRepos').mockResolvedValue([
      { name: 'ai-lup-poc-target-cli', path: '/repos/ai-lup-poc-target-cli' },
      { name: 'another-repo', path: '/repos/another-repo' },
    ])
    const onChange = vi.fn()
    render(<RepoPicker id="repo" value="" onChange={onChange} />)

    const select = await screen.findByRole('combobox')
    await userEvent.selectOptions(select, 'ai-lup-poc-target-cli')

    expect(onChange).toHaveBeenCalledWith('/repos/ai-lup-poc-target-cli')
  })

  it('shows a hint instead of an empty dropdown when no repo is configured', async () => {
    vi.spyOn(apiClient, 'getLocalRepos').mockResolvedValue([])
    render(<RepoPicker id="repo" value="" onChange={() => {}} />)

    expect(await screen.findByText(/Nenhum repositório local configurado/)).toBeInTheDocument()
  })

  it('shows the error message when the request fails', async () => {
    vi.spyOn(apiClient, 'getLocalRepos').mockRejectedValue(new Error('backend fora do ar'))
    render(<RepoPicker id="repo" value="" onChange={() => {}} />)

    expect(await screen.findByText(/backend fora do ar/)).toBeInTheDocument()
  })
})
