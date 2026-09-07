import { useEffect, useMemo, useState } from 'react'
import { getRuns } from '../lib/apiClient'
import { describeStatus, formatAbsoluteTime, formatRelativeTime } from '../lib/format'

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

export default function RunsList({ onSelect, refreshToken }) {
  const [runs, setRuns] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    let cancelled = false
    getRuns()
      .then((data) => {
        if (cancelled) return
        setRuns(data)
        setError(null)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [refreshToken])

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
    return filter === 'all' ? runs : runs.filter((run) => run.status === filter)
  }, [runs, filter])

  return (
    <section className="runs" aria-label="Execuções">
      <div className="summary-strip">
        {FILTERS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={`summary-card summary-card--${entry.tone}`}
            aria-pressed={filter === entry.id}
            data-zero={!runs || counts[entry.id] === 0}
            disabled={!runs}
            onClick={() => setFilter(filter === entry.id ? 'all' : entry.id)}
          >
            <span className="summary-card__value">{runs ? counts[entry.id] : '—'}</span>
            <span className="summary-card__label">{entry.label}</span>
          </button>
        ))}
      </div>

      <div className="section-head">
        <h2>Execuções</h2>
        {filter !== 'all' && (
          <button type="button" className="btn-link" onClick={() => setFilter('all')}>
            Limpar filtro
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
        <p className="state-block state-block--empty">Nenhuma execução registrada ainda.</p>
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
                <th scope="col" className="col-time">
                  Atualizado
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
                    className={`row-clickable${run.status === 'failed' ? ' run-row-failed' : ''}`}
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
                    </td>
                    <td className="col-time" title={formatAbsoluteTime(run.updated_at)}>
                      {formatRelativeTime(run.updated_at)}
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
