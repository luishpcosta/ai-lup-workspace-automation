import { useState } from 'react'
import { setConfig } from '../lib/config'

// ADR-006-AT-01 / AC-01, AC-02: tela forçada enquanto não há configuração salva.
// ADR-007: `configDir` deu lugar a `specsBaseUrl` — o disparo agora é por template
// (TriggerForm.jsx), e o repositório remoto de specs é consultado direto do browser.
export default function SettingsScreen({ initial, onSaved }) {
  const [baseUrl, setBaseUrl] = useState(initial?.baseUrl ?? '')
  const [specsBaseUrl, setSpecsBaseUrl] = useState(initial?.specsBaseUrl ?? '')

  function handleSubmit(event) {
    event.preventDefault()
    const saved = setConfig({ baseUrl, specsBaseUrl })
    onSaved(saved)
  }

  return (
    <div className="settings-screen">
      <form onSubmit={handleSubmit} aria-label="Configuração" className="panel">
        <h1>Configuração</h1>
        <p className="settings-hint">
          Informe onde o motor de workflow está rodando e onde ficam as specs antes de
          continuar.
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
        <label htmlFor="specsBaseUrl">URL base do repositório remoto de specs</label>
        <input
          id="specsBaseUrl"
          type="text"
          placeholder="https://luishpcosta.github.io/doc-repo-example"
          value={specsBaseUrl}
          onChange={(event) => setSpecsBaseUrl(event.target.value)}
          required
        />
        <button type="submit" className="btn-primary">
          Salvar
        </button>
      </form>
    </div>
  )
}
