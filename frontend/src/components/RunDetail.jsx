import { useEffect, useState } from 'react'
import { cancelRun, getRunDetail } from '../lib/apiClient'
import { describeStatus } from '../lib/format'
import InstructionBox from './InstructionBox'
import StreamPanel from './StreamPanel'

// Cancelar um run já terminado não faz nada além de devolver `not_cancellable`,
// então o botão só existe quando ainda há o que interromper.
const CANCELLABLE = new Set(['running', 'pending'])

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

  const overall = detail ? describeStatus(detail.status) : null

  return (
    <section aria-label={`Detalhe de ${chainName}`} className="detail">
      <button type="button" className="btn-secondary" onClick={onBack}>
        ← Voltar
      </button>

      <div className="detail__head">
        <div className="detail__identity">
          <h2>{chainName}</h2>
          {overall && (
            <span className={`status status--${overall.tone}`}>
              <span className="status__dot" aria-hidden="true" />
              {overall.label}
            </span>
          )}
        </div>
        {detail && CANCELLABLE.has(detail.status) && (
          <button type="button" className="btn-warn" onClick={handleCancel}>
            Cancelar
          </button>
        )}
      </div>

      {error && (
        <p className="state-block" role="alert">
          Erro ao carregar detalhe: {error.message}
        </p>
      )}
      {!error && !detail && <p className="state-block">Carregando detalhe…</p>}
      {cancelMessage && <p className="state-block">{cancelMessage}</p>}

      {detail && (
        <>
          <h3 className="detail__section-title">Etapas</h3>
          {detail.steps.length === 0 ? (
            <p className="state-block state-block--empty">Nenhuma etapa registrada.</p>
          ) : (
            <div className="panel panel--flush">
              <table aria-label="Etapas">
                <thead>
                  <tr>
                    <th scope="col">Etapa</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="col-attempts">
                      Tentativas
                    </th>
                    <th scope="col">Erro</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.steps.map((step) => {
                    const stepStatus = describeStatus(step.status)
                    return (
                      <tr key={step.step_name} data-status={step.status}>
                        <td>
                          <span className="run-name">{step.step_name}</span>
                        </td>
                        <td>
                          <span className={`status status--${stepStatus.tone}`}>
                            <span className="status__dot" aria-hidden="true" />
                            {stepStatus.label}
                          </span>
                        </td>
                        <td className="col-attempts">{step.attempt_count}</td>
                        <td className="col-error">{step.error_message ?? '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

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
