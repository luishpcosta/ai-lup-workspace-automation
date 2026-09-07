import { useEffect, useState } from 'react'
import Select from 'react-select'
import { getConfig } from '../lib/config'
import { fetchSpecsIndex } from '../lib/specsClient'

// ADR-007 RF-01: specs vêm de um fetch DIRETO do browser em
// ${specsBaseUrl}/docs-index.json — nunca passa pelo backend do motor
// (specsClient.js, não apiClient.js).
//
// ADR-010-AC-02/AC-03: o widget passa de lista de checkboxes para um combobox de
// multi-seleção em barra (react-select), rotulado "Knowledge Bases" ao usuário — mas
// o contrato de props (`value`/`onChange` como array de ids) não muda, então
// DynamicParamsForm/TriggerForm continuam alheios a essa troca.
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

  if (error) return <p role="alert">Erro ao listar Knowledge Bases: {error.message}</p>
  if (specs === null) return <p>Carregando Knowledge Bases…</p>
  if (specs.length === 0) return <p>Nenhuma Knowledge Base encontrada no repositório remoto.</p>

  const options = specs.map((spec) => ({ value: spec.id, label: spec.title ?? spec.id }))
  const selected = options.filter((option) => value.includes(option.value))

  return (
    <Select
      unstyled
      inputId={id}
      aria-label="Knowledge Bases"
      isMulti
      options={options}
      value={selected}
      onChange={(next) => onChange(next.map((option) => option.value))}
      placeholder="Buscar Knowledge Bases…"
      noOptionsMessage={() => 'Nenhuma Knowledge Base encontrada'}
      className="basic-multi-select"
      classNamePrefix="select"
    />
  )
}
