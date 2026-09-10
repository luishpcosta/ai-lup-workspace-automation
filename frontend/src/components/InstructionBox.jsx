import { useState } from 'react'
import { postAnswer, postInstruction } from '../lib/apiClient'

// ADR-006-AT-04 / AC-09: envia instrução livre para a etapa Claude Code Runner
// ativa. Evoluído para também ser o formulário de resposta em tempo real: quando
// existe uma pergunta pendente (tool `ask_user`, modo `coding_local_interativo`,
// repassada por RunDetail/StreamPanel via `pendingQuestion`), troca de modo —
// mostra a pergunta do agente e envia a resposta por um canal separado
// (`postAnswer`/`POST .../resposta`, que de fato destrava a execução) em vez do
// canal de instrução livre (`postInstruction`/`POST .../instrucoes`,
// fire-and-forget). Sem pergunta pendente, comportamento idêntico ao de sempre.
export default function InstructionBox({ chainName, pendingQuestion = null }) {
  const [mensagem, setMensagem] = useState('')
  const [resposta, setResposta] = useState('')
  // Estado de status/erro é independente por modo (não compartilhado): sem isso,
  // uma confirmação de uma chamada ainda em voo do outro modo poderia aparecer
  // depois que `pendingQuestion` muda de valor — ex.: "Resposta enviada." some ao
  // virar pergunta pendente, mas se a troca acontecer logo após responder, o
  // formulário de instrução (agora visível) herdaria essa mensagem por engano.
  const [instructionStatus, setInstructionStatus] = useState(null) // null | 'sent' | 'error'
  const [instructionError, setInstructionError] = useState(null)
  const [answerStatus, setAnswerStatus] = useState(null) // null | 'sent' | 'error'
  const [answerError, setAnswerError] = useState(null)

  async function sendAnswer(value) {
    setAnswerStatus(null)
    setAnswerError(null)
    try {
      await postAnswer(chainName, value)
      setAnswerStatus('sent')
      setResposta('')
    } catch (err) {
      setAnswerStatus('error')
      setAnswerError(err?.message ?? 'Erro desconhecido ao enviar a resposta.')
    }
  }

  async function handleAnswerSubmit(event) {
    event.preventDefault()
    await sendAnswer(resposta)
  }

  async function handleInstructionSubmit(event) {
    event.preventDefault()
    setInstructionStatus(null)
    setInstructionError(null)
    try {
      await postInstruction(chainName, mensagem)
      setInstructionStatus('sent')
      setMensagem('')
    } catch (err) {
      setInstructionStatus('error')
      setInstructionError(err?.message ?? 'Erro desconhecido ao enviar a instrução.')
    }
  }

  if (pendingQuestion) {
    return (
      <div className="panel" aria-label="Pergunta do agente">
        <p className="stream__question-text">
          <strong>O agente perguntou:</strong> {pendingQuestion.text}
        </p>
        {pendingQuestion.options.length > 0 ? (
          <div className="stream__question-options">
            {pendingQuestion.options.map((option) => (
              <button
                key={option}
                type="button"
                className="btn-primary"
                onClick={() => sendAnswer(option)}
              >
                {option}
              </button>
            ))}
          </div>
        ) : (
          <form onSubmit={handleAnswerSubmit}>
            <div className="field">
              <label htmlFor="resposta">Resposta</label>
              <input
                id="resposta"
                type="text"
                value={resposta}
                onChange={(event) => setResposta(event.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-primary">
              Responder
            </button>
          </form>
        )}
        {answerStatus === 'sent' && <p className="settings-hint">Resposta enviada.</p>}
        {answerStatus === 'error' && <p role="alert">{answerError}</p>}
      </div>
    )
  }

  return (
    <form onSubmit={handleInstructionSubmit} aria-label="Enviar instrução" className="panel">
      <div className="field">
        <label htmlFor="mensagem">Instrução</label>
        <input
          id="mensagem"
          type="text"
          value={mensagem}
          onChange={(event) => setMensagem(event.target.value)}
          required
        />
      </div>
      <button type="submit" className="btn-primary">
        Enviar
      </button>
      {instructionStatus === 'sent' && <p className="settings-hint">Instrução enviada.</p>}
      {instructionStatus === 'error' && <p role="alert">{instructionError}</p>}
    </form>
  )
}
