import { useEffect, useState } from 'react'
import { cancelRun, getRunDetail } from '../lib/apiClient'
import InstructionBox from './InstructionBox'
import StreamPanel from './StreamPanel'

const CANCEL_OUTCOME_MESSAGES = {
  cancelled: 'Run cancelado.',
  already_running: 'A etapa já está em execução e não pode ser interrompida.',
  not_cancellable: 'Este run não pode mais ser cancelado.',
  not_found: 'Run não encontrado.',
}

// ADR-006-AT-02 / AC-05 (detalhe por etapa), AT-05 / AC-10 (cancelar). Hospeda
// StreamPanel/InstructionBox (AT-04) — eles cuidam sozinhos do caso "sem etapa ativa".
export default function RunDetail({ chainName, onBack }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [streamRefreshToken, setStreamRefreshToken] = useState(0)
  const [cancelMessage, setCancelMessage] = useState(null)

  useEffect(() => {
    let cancelled = false
    getRunDetail(chainName)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [chainName])

  async function handleCancel() {
    setCancelMessage(null)
    try {
      const result = await cancelRun(chainName)
      setCancelMessage(CANCEL_OUTCOME_MESSAGES[result.status] ?? result.status)
    } catch (err) {
      const outcome = CANCEL_OUTCOME_MESSAGES[err.code] ?? err.message
      setCancelMessage(outcome)
    }
  }

  return (
    <section aria-label={`Detalhe de ${chainName}`}>
      <button type="button" className="btn-secondary" onClick={onBack}>
        ← Voltar
      </button>
      <h2>{chainName}</h2>

      {error && <p role="alert">Erro ao carregar detalhe: {error.message}</p>}
      {!error && !detail && <p>Carregando detalhe…</p>}
      {detail && (
        <>
          <p>Status geral: {detail.status}</p>
          <div className="panel">
            <table aria-label="Etapas">
              <thead>
                <tr>
                  <th>etapa</th>
                  <th>status</th>
                  <th>tentativas</th>
                  <th>erro</th>
                </tr>
              </thead>
              <tbody>
                {detail.steps.map((step) => (
                  <tr key={step.step_name}>
                    <td>{step.step_name}</td>
                    <td>{step.status}</td>
                    <td>{step.attempt_count}</td>
                    <td>{step.error_message ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button type="button" className="btn-warn" onClick={handleCancel}>
            Cancelar
          </button>
          {cancelMessage && <p>{cancelMessage}</p>}

          <StreamPanel
            key={`${chainName}-${streamRefreshToken}`}
            chainName={chainName}
            onRefresh={() => setStreamRefreshToken((token) => token + 1)}
          />
          <InstructionBox chainName={chainName} />
        </>
      )}
    </section>
  )
}
