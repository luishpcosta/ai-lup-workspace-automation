import { render, screen, waitFor } from '@testing-library/react'
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

describe('InstructionBox — pergunta pendente (ask_user, coding_local_interativo)', () => {
  it('shows the agent question and sends a free-text answer via postAnswer, not postInstruction', async () => {
    const answerSpy = vi.spyOn(apiClient, 'postAnswer').mockResolvedValue({ status: 'accepted' })
    const instructionSpy = vi.spyOn(apiClient, 'postInstruction')
    render(
      <InstructionBox
        chainName="hist-005"
        pendingQuestion={{ text: 'Qual branch devo usar?', options: [] }}
      />,
    )

    expect(screen.getByText(/Qual branch devo usar\?/)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Resposta'), 'feature/minha-mudanca')
    await userEvent.click(screen.getByRole('button', { name: 'Responder' }))

    expect(answerSpy).toHaveBeenCalledWith('hist-005', 'feature/minha-mudanca')
    expect(instructionSpy).not.toHaveBeenCalled()
    expect(await screen.findByText('Resposta enviada.')).toBeInTheDocument()
  })

  it('renders one button per option and sends the clicked option as the answer', async () => {
    const answerSpy = vi.spyOn(apiClient, 'postAnswer').mockResolvedValue({ status: 'accepted' })
    render(
      <InstructionBox
        chainName="hist-005"
        pendingQuestion={{ text: 'Qual abordagem?', options: ['A', 'B'] }}
      />,
    )

    expect(screen.queryByLabelText('Resposta')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'B' }))

    expect(answerSpy).toHaveBeenCalledWith('hist-005', 'B')
  })

  it('shows a clear error on 409 not_interactable when answering, without crashing', async () => {
    vi.spyOn(apiClient, 'postAnswer').mockRejectedValue(
      new ApiError({ kind: 'http', status: 409, code: 'not_interactable', message: 'no active step' }),
    )
    render(
      <InstructionBox chainName="hist-005" pendingQuestion={{ text: 'Qual?', options: [] }} />,
    )
    await userEvent.type(screen.getByLabelText('Resposta'), 'x')
    await userEvent.click(screen.getByRole('button', { name: 'Responder' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no active step')
  })

  it('does not leak "Resposta enviada." into the instruction form once the question resolves (status is per-mode)', async () => {
    vi.spyOn(apiClient, 'postAnswer').mockResolvedValue({ status: 'accepted' })
    const { rerender } = render(
      <InstructionBox chainName="hist-005" pendingQuestion={{ text: 'Qual?', options: [] }} />,
    )
    await userEvent.type(screen.getByLabelText('Resposta'), 'feature/x')
    await userEvent.click(screen.getByRole('button', { name: 'Responder' }))
    await screen.findByText('Resposta enviada.')

    // A pergunta é resolvida (tool_result chega no stream) — RunDetail passa a
    // repassar pendingQuestion=null, trocando de volta para o formulário de
    // instrução livre. Ele nunca enviou nada, então não deve mostrar nenhuma
    // confirmação — nem a da resposta que acabou de ser enviada no outro modo.
    rerender(<InstructionBox chainName="hist-005" pendingQuestion={null} />)

    expect(screen.getByLabelText('Instrução')).toBeInTheDocument()
    expect(screen.queryByText('Resposta enviada.')).not.toBeInTheDocument()
    expect(screen.queryByText('Instrução enviada.')).not.toBeInTheDocument()
  })

  it('does not leak "Instrução enviada." into the question form when a question arrives right after sending an instruction', async () => {
    vi.spyOn(apiClient, 'postInstruction').mockResolvedValue({ status: 'accepted' })
    const { rerender } = render(<InstructionBox chainName="hist-005" pendingQuestion={null} />)
    await userEvent.type(screen.getByLabelText('Instrução'), 'oi')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    await screen.findByText('Instrução enviada.')

    // O agente chama ask_user logo em seguida — RunDetail passa a repassar uma
    // pendingQuestion real. O usuário ainda não respondeu nada nesse modo, então
    // não deve aparecer nenhuma confirmação de resposta.
    rerender(
      <InstructionBox chainName="hist-005" pendingQuestion={{ text: 'Qual?', options: [] }} />,
    )

    await waitFor(() => {
      expect(screen.getByLabelText('Resposta')).toBeInTheDocument()
    })
    expect(screen.queryByText('Resposta enviada.')).not.toBeInTheDocument()
    expect(screen.queryByText('Instrução enviada.')).not.toBeInTheDocument()
  })
})
