import { useEffect, useMemo, useState } from 'react'
import { archiveRun, getRuns, unarchiveRun } from '../lib/apiClient'
import { describeStatus, formatAbsoluteTime, formatDuration, formatRelativeTime } from '../lib/format'

// ADR-006-AT-02 / AC-04 (listagem), AC-12 (destaque visual passivo de falha).
// A faixa de resumo acumula duas funções de propósito: mostra a contagem por
// status e é o próprio filtro da fila — o operador clica no número que o
// preocupa em vez de procurar um controle de filtro separado.
const FILTERS = [
  { id: 'running', label: 'Em execução', tone: 'running' },
  { id: 'failed', label: 'Falharam', tone: 'failed' },
  { id: 'completed', label: 'Concluídas', tone: 'completed' },
  { id: 'all', label: 'Total', tone: 'neutral' },
]

// ADR-011-AC-08/AC-09: enquanto há execução não-terminal na resposta mais recente,
// reconsulta GET /runs sozinho, sem exigir clique em "Atualizar" — para assim que
// não há mais nada ativo, para não gerar requisição periódica sem propósito.
const POLL_INTERVAL_MS = 3000
const ACTIVE_STATUSES = new Set(['running', 'pending'])

export default function RunsList({ onSelect, refreshToken }) {
  const [runs, setRuns] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  // ADR-011-AC-13/AC-14: "Arquivadas" é um modo à parte dos filtros de status —
  // troca a própria consulta (GET /runs?archived=true), não filtra em memória.
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    let cancelled = false
    let timeoutId = null

    // Auto-agendado (setTimeout recursivo, não setInterval fixo): cada rodada só
    // agenda a próxima se a resposta que acabou de chegar tiver algo ativo — decide
    // com o dado fresco, não com o estado (que só atualiza depois do fetch resolver,
    // então checar `runs` aqui dentro sempre veria o valor da rodada anterior).
    function load() {
      getRuns({ archived: showArchived })
        .then((data) => {
          if (cancelled) return
          setRuns(data)
          setError(null)
          const hasActive = data.some((run) => ACTIVE_STATUSES.has(run.status))
          if (!showArchived && hasActive) {
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
  }, [refreshToken, showArchived])

  async function handleArchiveToggle(chainName) {
    try {
      if (showArchived) {
        await unarchiveRun(chainName)
      } else {
        await archiveRun(chainName)
      }
      setRuns((prev) => (prev ?? []).filter((run) => run.chain_name !== chainName))
    } catch (err) {
      setError(err)
    }
  }

  const counts = useMemo(() => {
    const source = runs ?? []
    return {
      all: source.length,
      running: source.filter((run) => run.status === 'running').length,
      failed: source.filter((run) => run.status === 'failed').length,
      completed: source.filter((run) => run.status === 'completed').length,
    }
  }, [runs])

  const visible = useMemo(() => {
    if (!runs) return []
    if (showArchived) return runs
    return filter === 'all' ? runs : runs.filter((run) => run.status === filter)
  }, [runs, filter, showArchived])

  return (
    <section className="runs" aria-label="Execuções">
      <div className="summary-strip">
        {FILTERS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={`summary-card summary-card--${entry.tone}`}
            aria-pressed={!showArchived && filter === entry.id}
            data-zero={!runs || counts[entry.id] === 0}
            disabled={!runs || showArchived}
            onClick={() => setFilter(filter === entry.id ? 'all' : entry.id)}
          >
            <span className="summary-card__value">{runs && !showArchived ? counts[entry.id] : '—'}</span>
            <span className="summary-card__label">{entry.label}</span>
          </button>
        ))}
        {/* ADR-011-AC-14: aba dedicada — troca a própria consulta (GET
            /runs?archived=true), não é mais um filtro em memória sobre a mesma lista. */}
        <button
          type="button"
          className="summary-card summary-card--neutral"
          aria-pressed={showArchived}
          onClick={() => {
            setShowArchived((prev) => !prev)
            setFilter('all')
          }}
        >
          <span className="summary-card__value">🗄</span>
          <span className="summary-card__label">Arquivadas</span>
        </button>
      </div>

      <div className="section-head">
        <h2>{showArchived ? 'Execuções arquivadas' : 'Execuções'}</h2>
        {!showArchived && filter !== 'all' && (
          <button type="button" className="btn-link" onClick={() => setFilter('all')}>
            Limpar filtro
          </button>
        )}
        {showArchived && (
          <button type="button" className="btn-link" onClick={() => setShowArchived(false)}>
            Voltar à listagem
          </button>
        )}
      </div>

      {error && (
        <p className="state-block" role="alert">
          Erro ao carregar execuções: {error.message}
        </p>
      )}

      {!error && runs === null && (
        <div className="panel panel--flush" aria-busy="true">
          <p className="visually-hidden">Carregando execuções…</p>
          {[0, 1, 2].map((row) => (
            <div key={row} className="skeleton-row">
              <span className="skeleton skeleton--wide" />
              <span className="skeleton skeleton--narrow" />
            </div>
          ))}
        </div>
      )}

      {!error && runs !== null && runs.length === 0 && (
        <p className="state-block state-block--empty">
          {showArchived ? 'Nenhuma execução arquivada.' : 'Nenhuma execução registrada ainda.'}
        </p>
      )}

      {!error && runs !== null && runs.length > 0 && visible.length === 0 && (
        <p className="state-block state-block--empty">Nenhuma execução com esse status.</p>
      )}

      {!error && runs !== null && visible.length > 0 && (
        <div className="panel panel--flush">
          <table aria-label="Lista de execuções">
            <thead>
              <tr>
                <th scope="col">Execução</th>
                <th scope="col">Status</th>
                <th scope="col" className="col-duration">
                  Duração
                </th>
                <th scope="col" className="col-time">
                  Atualizado
                </th>
                <th scope="col" className="col-actions">
                  <span className="visually-hidden">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((run) => {
                const status = describeStatus(run.status)
                return (
                  <tr
                    key={run.chain_name}
                    data-status={run.status}
                    data-awaiting-input={run.awaiting_input || undefined}
                    className={`row-clickable${run.status === 'failed' ? ' run-row-failed' : ''}${run.awaiting_input ? ' run-row-awaiting' : ''}`}
                    tabIndex={0}
                    onClick={() => onSelect(run.chain_name)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelect(run.chain_name)
                      }
                    }}
                  >
                    <td>
                      <span className="run-name">{run.chain_name}</span>
                      {run.workflow_name !== run.chain_name && (
                        <span className="run-workflow">{run.workflow_name}</span>
                      )}
                    </td>
                    <td>
                      <span className={`status status--${status.tone}`}>
                        <span className="status__dot" aria-hidden="true" />
                        {status.label}
                      </span>
                      {/* ADR-013: o agente pausou numa pergunta (ask_user) — sinal
                          visível na listagem, sem precisar entrar na execução para
                          notar (GET /runs traz `awaiting_input` derivado do arquivo
                          .pergunta.json enquanto a run está `running`). */}
                      {run.awaiting_input && (
                        <span className="run-awaiting-badge" title="O agente está esperando uma resposta">
                          ❓ Aguardando resposta
                        </span>
                      )}
                    </td>
                    <td className="col-duration">{formatDuration(run.duration_seconds)}</td>
                    <td className="col-time" title={formatAbsoluteTime(run.updated_at)}>
                      {formatRelativeTime(run.updated_at)}
                    </td>
                    <td className="col-actions">
                      <button
                        type="button"
                        className="btn-link"
                        onClick={(event) => {
                          event.stopPropagation()
                          handleArchiveToggle(run.chain_name)
                        }}
                      >
                        {showArchived ? 'Desarquivar' : 'Arquivar'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
