import { useState } from 'react'
import { createRun } from '../lib/apiClient'
import { getConfig } from '../lib/config'
import { resolveConfigPath } from '../lib/resolveConfigPath'

function parseIds(raw) {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

// ADR-006-AT-03 / AC-06 (disparo em lote), AC-13 (erro de um item não cancela os demais).
export default function TriggerForm({ onDispatched }) {
  const [raw, setRaw] = useState('')
  const [results, setResults] = useState([])
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const ids = parseIds(raw)
    if (ids.length === 0) return

    const { configDir } = getConfig()
    setSubmitting(true)
    setResults(ids.map((id) => ({ id, status: 'pending' })))

    const outcomes = await Promise.all(
      ids.map(async (id) => {
        const configPath = resolveConfigPath(configDir, id)
        try {
          const { chain_name } = await createRun(configPath)
          return { id, status: 'success', chainName: chain_name }
        } catch (err) {
          return { id, status: 'error', message: err.message }
        }
      }),
    )

    setResults(outcomes)
    setSubmitting(false)
    onDispatched?.()
  }

  return (
    <section>
      <h2>Disparar execuções</h2>
      <form onSubmit={handleSubmit} aria-label="Disparar execuções" className="panel">
        <label htmlFor="ids">IDs de documento de referência (um por linha)</label>
        <textarea
          id="ids"
          value={raw}
          onChange={(event) => setRaw(event.target.value)}
          rows={4}
        />
        <button type="submit" className="btn-primary" disabled={submitting}>
          Disparar
        </button>
        {results.length > 0 && (
          <ul aria-label="Resultado do disparo">
            {results.map((result) => (
              <li key={result.id}>
                {result.id}:{' '}
                {result.status === 'pending' && 'disparando…'}
                {result.status === 'success' && `iniciado (${result.chainName})`}
                {result.status === 'error' && <span role="alert">{result.message}</span>}
              </li>
            ))}
          </ul>
        )}
      </form>
    </section>
  )
}
