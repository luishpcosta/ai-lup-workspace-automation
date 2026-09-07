import { useState } from 'react'
import { clearConfig, getEffectiveConfig, getFieldSources, setConfig } from '../lib/config'

// ADR-006-AT-01 / AC-01, AC-02: tela forçada enquanto não há configuração salva.
// ADR-007: `configDir` deu lugar a `specsBaseUrl`.
// ADR-009-AT-02: ganha a pasta de trabalho (RF-03) e passa a distinguir "valor que
// você digitou" de "default vindo do painel-config.json" (RF-04/AC-04) — antes os
// campos usavam placeholder com aparência de valor real, o que fazia um formulário
// vazio parecer preenchido.
const FIELDS = [
  {
    name: 'baseUrl',
    label: 'URL base do backend',
    hint: 'Onde o motor de workflow está servindo, no formato http://host:porta.',
    required: true,
  },
  {
    name: 'specsBaseUrl',
    label: 'URL base do repositório remoto de specs',
    hint: 'A origem de onde o navegador busca docs-index.json, sem barra no final.',
    required: true,
  },
  {
    name: 'reposRoot',
    label: 'Pasta de trabalho',
    hint: 'Caminho cujas subpastas viram as opções do seletor de repositórios. Vazio: usa a raiz configurada no backend.',
    required: false,
  },
]

export default function SettingsScreen({ initial, onSaved }) {
  const effective = getEffectiveConfig()
  const [values, setValues] = useState(() => ({
    baseUrl: initial?.baseUrl ?? effective.baseUrl,
    specsBaseUrl: initial?.specsBaseUrl ?? effective.specsBaseUrl,
    reposRoot: initial?.reposRoot ?? effective.reposRoot,
  }))
  const [sources, setSources] = useState(() => getFieldSources())

  function handleSubmit(event) {
    event.preventDefault()
    onSaved(setConfig(values))
  }

  function handleRestoreDefaults() {
    const restored = clearConfig()
    setValues(restored)
    setSources(getFieldSources())
  }

  // Só faz sentido oferecer "restaurar" quando há algo salvo sobrepondo o arquivo.
  const hasUserOverride = Object.values(sources).includes('user')

  return (
    <div className="settings-screen">
      <form onSubmit={handleSubmit} aria-label="Configuração" className="panel settings-form">
        <div>
          <h1>Configuração</h1>
          <p className="settings-hint">
            Informe onde o motor de workflow está rodando e onde ficam as specs antes de
            continuar.
          </p>
        </div>

        {FIELDS.map((field) => (
          <div key={field.name} className="field">
            <div className="field__label-row">
              <label htmlFor={field.name}>
                {field.label}
                {!field.required && <span className="field__optional"> (opcional)</span>}
              </label>
              {sources[field.name] === 'file' && values[field.name] === effective[field.name] && (
                <span className="field__badge">default do arquivo</span>
              )}
            </div>
            <input
              id={field.name}
              type="text"
              value={values[field.name]}
              onChange={(event) =>
                setValues((prev) => ({ ...prev, [field.name]: event.target.value }))
              }
              required={field.required}
            />
            <p className="settings-hint">{field.hint}</p>
          </div>
        ))}

        <div className="settings-actions">
          <button type="submit" className="btn-primary">
            Salvar
          </button>
          {hasUserOverride && (
            <button type="button" className="btn-link" onClick={handleRestoreDefaults}>
              Restaurar defaults do arquivo
            </button>
          )}
        </div>

        <p className="settings-hint settings-footnote">
          Os defaults vêm de <code>public/painel-config.json</code>, lido a cada
          carregamento — dá para editá-lo sem rebuild. O que você salva aqui tem
          precedência sobre ele.
        </p>
      </form>
    </div>
  )
}
