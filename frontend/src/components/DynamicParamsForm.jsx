import RepoPicker from './RepoPicker'
import SpecPicker from './SpecPicker'

// ADR-007 RF-01: renderiza um campo por entrada de `template.params_schema` — o
// `source` declarado pelo motor decide o widget (RepoPicker/SpecPicker/texto),
// sem o frontend precisar conhecer o template específico de antemão.
export default function DynamicParamsForm({ template, values, onChange }) {
  if (!template) return null

  return (
    <>
      {template.params_schema.map((param) => {
        const fieldId = `param-${param.name}`
        return (
          <div key={param.name} className="field dynamic-param">
            <label htmlFor={fieldId}>
              {param.label}
              {param.required ? ' *' : ''}
            </label>
            {param.source === 'local_repos' && (
              <RepoPicker
                id={fieldId}
                value={values[param.name] ?? ''}
                onChange={(next) => onChange(param.name, next)}
              />
            )}
            {param.source === 'spec_multiselect' && (
              <SpecPicker
                id={fieldId}
                value={values[param.name] ?? []}
                onChange={(next) => onChange(param.name, next)}
              />
            )}
            {!param.source && param.type === 'textarea' && (
              <textarea
                id={fieldId}
                value={values[param.name] ?? ''}
                onChange={(event) => onChange(param.name, event.target.value)}
                required={param.required}
                rows={4}
              />
            )}
            {!param.source && param.type !== 'textarea' && (
              <input
                id={fieldId}
                type="text"
                value={values[param.name] ?? ''}
                onChange={(event) => onChange(param.name, event.target.value)}
                required={param.required}
              />
            )}
          </div>
        )
      })}
    </>
  )
}
