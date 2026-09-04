import { useEffect, useState } from 'react'
import { getRuns } from '../lib/apiClient'

// ADR-006-AT-02 / AC-04 (listagem), AC-12 (destaque visual passivo de falha).
export default function RunsList({ onSelect, refreshToken }) {
  const [runs, setRuns] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getRuns()
      .then((data) => {
        if (!cancelled) setRuns(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [refreshToken])

  if (error) {
    return <p role="alert">Erro ao carregar execuções: {error.message}</p>
  }
  if (runs === null) {
    return <p>Carregando execuções…</p>
  }
  if (runs.length === 0) {
    return <p>Nenhuma execução registrada ainda.</p>
  }

  return (
    <table aria-label="Lista de execuções">
      <thead>
        <tr>
          <th>chain_name</th>
          <th>workflow_name</th>
          <th>status</th>
          <th>atualizado em</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr
            key={run.chain_name}
            data-status={run.status}
            className={run.status === 'failed' ? 'run-row-failed' : undefined}
            onClick={() => onSelect(run.chain_name)}
          >
            <td>{run.chain_name}</td>
            <td>{run.workflow_name}</td>
            <td>{run.status}</td>
            <td>{run.updated_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
