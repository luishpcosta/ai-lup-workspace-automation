import { useEffect, useState } from 'react'
import { archiveRun, cancelRun, getRunDetail, unarchiveRun } from '../lib/apiClient'
import { describeStatus } from '../lib/format'
import InstructionBox from './InstructionBox'
import StreamPanel from './StreamPanel'

// Cancelar um run já terminado não faz nada além de devolver `not_cancellable`,
// então o botão só existe quando ainda há o que interromper.
const CANCELLABLE = new Set(['running', 'pending'])
// ADR-011-AC-10/AC-11: mesmo critério de "ainda em andamento" decide quando a
// tela continua reconsultando o detalhe sozinha.
const NON_TERMINAL = new Set(['running', 'pending'])
const POLL_INTERVAL_MS = 3000

const CANCEL_OUTCOME_MESSAGES = {
  cancelled: 'Run cancelado.',
  already_running: 'A etapa já está em execução e não pode ser interrompida.',
  not_cancellable: 'Este run não pode mais ser cancelado.',
  not_found: 'Run não encontrado.',
}

// ADR-006-AT-02 / AC-05 (detalhe por etapa), AT-05 / AC-10 (cancelar). Hospeda
// StreamPanel/InstructionBox (AT-04) — eles cuidam sozinhos do caso "sem etapa ativa".
// `pendingQuestion` é fiação pura entre os dois: StreamPanel deriva do stream se há
// uma chamada `ask_user` (modo coding_local_interativo) pendente e devolve via
// `onPendingQuestion`; InstructionBox vira formulário de resposta enquanto existir.
// ADR-010-AC-05: repassa a StreamPanel o `plugin` do step em execução (novo campo
// aditivo de GET /runs/{chain_name}), para que ela escolha a leitura formatada certa.
// ADR-011-AC-10/AC-12: reconsulta GET /runs/{chain_name} sozinho enquanto o status
// geral for não-terminal — some o `setInterval` ao trocar de execução/desmontar.
export default function RunDetail({ chainName, onBack }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)
  const [streamRefreshToken, setStreamRefreshToken] = useState(0)
  const [cancelMessage, setCancelMessage] = useState(null)
  const [archiveError, setArchiveError] = useState(null)
  const [pendingQuestion, setPendingQuestion] = useState(null)

  useEffect(() => {
    let cancelled = false
    let timeoutId = null

    // Auto-agendado (setTimeout recursivo, não setInterval fixo): cada rodada só
    // agenda a próxima se o status que acabou de chegar ainda for não-terminal —
    // decide com o dado fresco da resposta, não com o estado (que só atualiza
    // depois do fetch resolver).
    function load() {
      getRunDetail(chainName)
        .then((data) => {
          if (cancelled) return
          setDetail(data)
          setError(null)
          if (NON_TERMINAL.has(data.status)) {
            timeoutId = setTimeout(load, POLL_INTERVAL_MS)
          }
        })
        .catch((err) => {
          if (!cancelled) setError(err)
        })
    }

    load()

    return () => {
      cancelled = true
      if (timeoutId) clearTimeout(timeoutId)
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

  async function handleArchiveToggle() {
    setArchiveError(null)
    try {
      const result = detail.archived ? await unarchiveRun(chainName) : await archiveRun(chainName)
      setDetail((current) => (current ? { ...current, archived: result.archived } : current))
    } catch (err) {
      setArchiveError(err.message)
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
        {detail && (
          <div className="detail__actions">
            {CANCELLABLE.has(detail.status) && (
              <button type="button" className="btn-warn" onClick={handleCancel}>
                Cancelar
              </button>
            )}
            <button type="button" className="btn-secondary" onClick={handleArchiveToggle}>
              {detail.archived ? 'Desarquivar' : 'Arquivar'}
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="state-block" role="alert">
          Erro ao carregar detalhe: {error.message}
        </p>
      )}
      {!error && !detail && <p className="state-block">Carregando detalhe…</p>}
      {cancelMessage && <p className="state-block">{cancelMessage}</p>}
      {archiveError && (
        <p className="state-block" role="alert">
          {archiveError}
        </p>
      )}

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
            plugin={detail.steps.find((step) => step.status === 'running')?.plugin}
            onRefresh={() => setStreamRefreshToken((token) => token + 1)}
            onPendingQuestion={setPendingQuestion}
          />
          <InstructionBox chainName={chainName} pendingQuestion={pendingQuestion} />
        </>
      )}
    </section>
  )
}
