import { useEffect, useState } from 'react'
import { getWorkflows } from '../lib/apiClient'

// ADR-007 RF-01: o motor expõe os workflows disponíveis (GET /workflows); o
// frontend só escolhe um e preenche o formulário que o próprio workflow descreve
// (DynamicParamsForm) — nenhum conhecimento de template específico fica hardcoded.
export default function TemplateSelector({ value, onSelect }) {
  const [templates, setTemplates] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getWorkflows()
      .then((data) => {
        if (!cancelled) setTemplates(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) return <p role="alert">Erro ao carregar workflows: {error.message}</p>
  if (templates === null) return <p>Carregando workflows…</p>
  if (templates.length === 0) return <p>Nenhum workflow configurado no backend.</p>

  const selected = templates.find((template) => template.id === value)

  return (
    <div>
      <label htmlFor="template">Workflow</label>
      <select
        id="template"
        value={value ?? ''}
        onChange={(event) => {
          const next = templates.find((template) => template.id === event.target.value)
          onSelect(next ?? null)
        }}
        required
      >
        <option value="" disabled>
          Selecione um workflow
        </option>
        {templates.map((template) => (
          <option key={template.id} value={template.id}>
            {template.label}
          </option>
        ))}
      </select>
      {selected && <p className="settings-hint">{selected.description}</p>}
    </div>
  )
}
