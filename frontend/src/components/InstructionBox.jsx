import { useState } from 'react'
import { postInstruction } from '../lib/apiClient'

// ADR-006-AT-04 / AC-09: envia instrução para a etapa Claude Code Runner ativa.
export default function InstructionBox({ chainName }) {
  const [mensagem, setMensagem] = useState('')
  const [status, setStatus] = useState(null) // null | 'sent' | 'error'
  const [errorMessage, setErrorMessage] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setStatus(null)
    setErrorMessage(null)
    try {
      await postInstruction(chainName, mensagem)
      setStatus('sent')
      setMensagem('')
    } catch (err) {
      setStatus('error')
      setErrorMessage(err?.message ?? 'Erro desconhecido ao enviar a instrução.')
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Enviar instrução">
      <label htmlFor="mensagem">Instrução</label>
      <input
        id="mensagem"
        type="text"
        value={mensagem}
        onChange={(event) => setMensagem(event.target.value)}
        required
      />
      <button type="submit">Enviar</button>
      {status === 'sent' && <p>Instrução enviada.</p>}
      {status === 'error' && <p role="alert">{errorMessage}</p>}
    </form>
  )
}
