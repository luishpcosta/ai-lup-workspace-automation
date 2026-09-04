import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../lib/apiClient'
import * as apiClient from '../lib/apiClient'
import InstructionBox from './InstructionBox'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('InstructionBox (ADR-006-AC-09)', () => {
  it('sends the typed message to postInstruction and confirms delivery', async () => {
    const spy = vi.spyOn(apiClient, 'postInstruction').mockResolvedValue({ status: 'accepted' })
    render(<InstructionBox chainName="hist-005" />)
    await userEvent.type(screen.getByLabelText('Instrução'), 'pare e responda X')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    expect(spy).toHaveBeenCalledWith('hist-005', 'pare e responda X')
    expect(await screen.findByText('Instrução enviada.')).toBeInTheDocument()
  })

  it('shows a clear error on 409 not_interactable, without crashing', async () => {
    vi.spyOn(apiClient, 'postInstruction').mockRejectedValue(
      new ApiError({ kind: 'http', status: 409, code: 'not_interactable', message: 'no active step' }),
    )
    render(<InstructionBox chainName="hist-005" />)
    await userEvent.type(screen.getByLabelText('Instrução'), 'oi')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no active step')
  })
})
