import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiClient from '../lib/apiClient'
import { setConfig } from '../lib/config'
import * as specsClient from '../lib/specsClient'
import DynamicParamsForm from './DynamicParamsForm'

const TEMPLATE = {
  id: 'investigar-impacto',
  label: 'Investigar impacto',
  params_schema: [
    { name: 'prompt', label: 'O que investigar', type: 'textarea', required: true },
    { name: 'repo_path', label: 'Repositório local', type: 'select', required: true, source: 'local_repos' },
    {
      name: 'docs_referenced',
      label: 'Knowledge Bases',
      type: 'multiselect',
      required: false,
      source: 'spec_multiselect',
    },
  ],
}

beforeEach(() => {
  window.localStorage.clear()
  setConfig({ baseUrl: 'http://localhost:8000', specsBaseUrl: 'https://example.test' })
  vi.spyOn(apiClient, 'getLocalRepos').mockResolvedValue([])
  vi.spyOn(specsClient, 'fetchSpecsIndex').mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DynamicParamsForm (ADR-007 RF-01)', () => {
  it('renders nothing when no template is selected', () => {
    const { container } = render(
      <DynamicParamsForm template={null} values={{}} onChange={() => {}} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders a plain textarea for a param without a source, and reports edits', async () => {
    const onChange = vi.fn()
    render(<DynamicParamsForm template={TEMPLATE} values={{}} onChange={onChange} />)

    await userEvent.type(screen.getByLabelText(/O que investigar/), 'x')

    expect(onChange).toHaveBeenLastCalledWith('prompt', 'x')
  })

  it('delegates local_repos and spec_multiselect fields to their pickers', async () => {
    render(<DynamicParamsForm template={TEMPLATE} values={{}} onChange={() => {}} />)

    // RepoPicker/SpecPicker mounted for the sourced fields (own tests cover their behavior).
    expect(await screen.findByText(/Nenhum repositório local configurado/)).toBeInTheDocument()
    expect(await screen.findByText(/Nenhuma Knowledge Base encontrada/)).toBeInTheDocument()
  })

  it('marks required params with an asterisk', async () => {
    render(<DynamicParamsForm template={TEMPLATE} values={{}} onChange={() => {}} />)
    expect(screen.getByText('O que investigar *')).toBeInTheDocument()
    expect(screen.getByText('Knowledge Bases')).toBeInTheDocument()
    // let RepoPicker/SpecPicker's pending fetches settle before the test ends
    await screen.findByText(/Nenhum repositório local configurado/)
    await screen.findByText(/Nenhuma Knowledge Base encontrada/)
  })
})
