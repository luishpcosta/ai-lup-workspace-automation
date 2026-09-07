import { useState } from 'react'
import { getConfig } from './lib/config'
import SettingsScreen from './components/SettingsScreen'
import RunsList from './components/RunsList'
import RunDetail from './components/RunDetail'
import TriggerForm from './components/TriggerForm'
import ThemeToggle from './components/ThemeToggle'

// ADR-006: navegação entre telas é um switch de estado simples (sem router
// externo) — só 3 telas nesta versão (plan.md, Key Decisions).
export default function App() {
  const [config, setConfig] = useState(() => getConfig())
  const [reconfiguring, setReconfiguring] = useState(false)
  const [selectedChainName, setSelectedChainName] = useState(null)
  const [runsRefreshToken, setRunsRefreshToken] = useState(0)

  if (!config || reconfiguring) {
    return (
      <>
        <ThemeToggle floating />
        <SettingsScreen
          initial={config}
          onSaved={(saved) => {
            setConfig(saved)
            setReconfiguring(false)
          }}
        />
      </>
    )
  }

  const onList = !selectedChainName

  return (
    <main className="dashboard">
      <header className="topbar">
        <div className="topbar__identity">
          <h1>Painel de Controle — Motor de Workflow</h1>
          <p className="topbar__endpoint" title="Motor de workflow em uso">
            {config.baseUrl}
          </p>
        </div>
        <div className="topbar__actions">
          {onList && (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setRunsRefreshToken((token) => token + 1)}
            >
              Atualizar
            </button>
          )}
          <ThemeToggle />
          <button type="button" className="btn-secondary" onClick={() => setReconfiguring(true)}>
            Configurações
          </button>
        </div>
      </header>

      {selectedChainName ? (
        <RunDetail chainName={selectedChainName} onBack={() => setSelectedChainName(null)} />
      ) : (
        <div className="dashboard__grid">
          <div className="dashboard__queue">
            <RunsList onSelect={setSelectedChainName} refreshToken={runsRefreshToken} />
          </div>
          <aside className="dashboard__aside">
            <TriggerForm onDispatched={() => setRunsRefreshToken((token) => token + 1)} />
          </aside>
        </div>
      )}
    </main>
  )
}
