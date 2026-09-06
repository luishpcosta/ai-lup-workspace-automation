import { useEffect, useState } from 'react'
import { getConfig } from '../lib/config'
import { fetchSpecsIndex } from '../lib/specsClient'

// ADR-007 RF-01: specs vêm de um fetch DIRETO do browser em
// ${specsBaseUrl}/docs-index.json — nunca passa pelo backend do motor
// (specsClient.js, não apiClient.js).
export default function SpecPicker({ id, value, onChange }) {
  const [specs, setSpecs] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const { specsBaseUrl } = getConfig() ?? {}
    fetchSpecsIndex(specsBaseUrl)
      .then((data) => {
        if (!cancelled) setSpecs(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function toggle(specId) {
    if (value.includes(specId)) {
      onChange(value.filter((existing) => existing !== specId))
    } else {
      onChange([...value, specId])
    }
  }

  if (error) return <p role="alert">Erro ao listar specs remotas: {error.message}</p>
  if (specs === null) return <p>Carregando specs…</p>
  if (specs.length === 0) return <p>Nenhuma spec encontrada no repositório remoto.</p>

  return (
    <ul aria-label="Specs de referência" id={id}>
      {specs.map((spec) => (
        <li key={spec.id}>
          <label>
            <input
              type="checkbox"
              checked={value.includes(spec.id)}
              onChange={() => toggle(spec.id)}
            />{' '}
            {spec.title ?? spec.id}
          </label>
        </li>
      ))}
    </ul>
  )
}
