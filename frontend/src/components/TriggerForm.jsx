import { useState } from 'react'
import { createRunFromTemplate } from '../lib/apiClient'
import DynamicParamsForm from './DynamicParamsForm'
import TemplateSelector from './TemplateSelector'

// ADR-007: substitui o disparo por texto livre + convenção de nome de arquivo
// (ADR-006-AT-03) por template + formulário dinâmico. `implementar-historia-sdd`
// (pipeline completo existente) e `investigar-impacto` (novo) aparecem na mesma
// lista, escolhidos via TemplateSelector — nenhuma tela/aba separada.
export default function TriggerForm({ onDispatched }) {
  const [template, setTemplate] = useState(null)
  const [values, setValues] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [results, setResults] = useState([])

  function handleSelectTemplate(selected) {
    setTemplate(selected)
    setValues({})
  }

  function handleParamChange(name, value) {
    setValues((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!template || submitting) return
    setSubmitting(true)
    try {
      const { chain_name: chainName } = await createRunFromTemplate(template.id, values)
      setResults((prev) => [
        { id: `${Date.now()}`, status: 'success', chainName },
        ...prev,
      ])
      setValues({})
      onDispatched?.()
    } catch (err) {
      setResults((prev) => [{ id: `${Date.now()}`, status: 'error', message: err.message }, ...prev])
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="trigger">
      <div className="section-head">
        <h2>Disparar execução</h2>
      </div>
      <form onSubmit={handleSubmit} aria-label="Disparar execução" className="panel">
        <TemplateSelector value={template?.id} onSelect={handleSelectTemplate} />
        <DynamicParamsForm template={template} values={values} onChange={handleParamChange} />
        <button type="submit" className="btn-primary" disabled={submitting || !template}>
          {submitting ? 'Disparando…' : 'Disparar'}
        </button>
        {results.length > 0 && (
          <ul aria-label="Resultado do disparo" className="dispatch-log">
            {results.map((result) => (
              <li
                key={result.id}
                className={`dispatch-log__item dispatch-log__item--${result.status}`}
              >
                {result.status === 'success' && (
                  <>
                    <span className="status__dot status__dot--running" aria-hidden="true" />
                    <span className="dispatch-log__text">iniciado ({result.chainName})</span>
                  </>
                )}
                {result.status === 'error' && (
                  <>
                    <span className="status__dot status__dot--failed" aria-hidden="true" />
                    <span role="alert">{result.message}</span>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </form>
    </section>
  )
}
