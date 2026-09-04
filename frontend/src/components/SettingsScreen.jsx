import { useState } from 'react'
import { setConfig } from '../lib/config'

// ADR-006-AT-01 / AC-01, AC-02: tela forçada enquanto não há configuração salva.
export default function SettingsScreen({ initial, onSaved }) {
  const [baseUrl, setBaseUrl] = useState(initial?.baseUrl ?? '')
  const [configDir, setConfigDir] = useState(initial?.configDir ?? '')

  function handleSubmit(event) {
    event.preventDefault()
    const saved = setConfig({ baseUrl, configDir })
    onSaved(saved)
  }

  return (
    <div className="settings-screen">
      <form onSubmit={handleSubmit} aria-label="Configuração" className="panel">
        <h1>Configuração</h1>
        <p className="settings-hint">
          Informe onde o motor de workflow está rodando antes de continuar.
        </p>
        <label htmlFor="baseUrl">URL base do backend</label>
        <input
          id="baseUrl"
          type="text"
          placeholder="http://localhost:8000"
          value={baseUrl}
          onChange={(event) => setBaseUrl(event.target.value)}
          required
        />
        <label htmlFor="configDir">Diretório-base de configs</label>
        <input
          id="configDir"
          type="text"
          placeholder="/caminho/para/chains"
          value={configDir}
          onChange={(event) => setConfigDir(event.target.value)}
          required
        />
        <button type="submit" className="btn-primary">
          Salvar
        </button>
      </form>
    </div>
  )
}
