import { useState } from 'react'
import { getConfig } from './lib/config'
import SettingsScreen from './components/SettingsScreen'
import RunsList from './components/RunsList'
import RunDetail from './components/RunDetail'
import TriggerForm from './components/TriggerForm'

// ADR-006: navegação entre telas é um switch de estado simples (sem router
// externo) — só 3 telas nesta versão (plan.md, Key Decisions).
export default function App() {
  const [config, setConfig] = useState(() => getConfig())
  const [reconfiguring, setReconfiguring] = useState(false)
  const [selectedChainName, setSelectedChainName] = useState(null)
  const [runsRefreshToken, setRunsRefreshToken] = useState(0)

  if (!config || reconfiguring) {
    return (
      <SettingsScreen
        initial={config}
        onSaved={(saved) => {
          setConfig(saved)
          setReconfiguring(false)
        }}
      />
    )
  }

  return (
    <main>
      <header>
        <h1>Painel de Controle — Motor de Workflow</h1>
        <button type="button" onClick={() => setReconfiguring(true)}>
          Configurações
        </button>
      </header>

      {selectedChainName ? (
        <RunDetail chainName={selectedChainName} onBack={() => setSelectedChainName(null)} />
      ) : (
        <>
          <TriggerForm onDispatched={() => setRunsRefreshToken((token) => token + 1)} />
          <RunsList onSelect={setSelectedChainName} refreshToken={runsRefreshToken} />
        </>
      )}
    </main>
  )
}
