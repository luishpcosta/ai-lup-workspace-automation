import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { loadDefaults } from './lib/config'

// ADR-009 RF-01: os defaults de `public/painel-config.json` são carregados antes do
// primeiro render, para que `getConfig()` continue síncrono no resto do app e a tela
// de configuração não pisque antes de o arquivo chegar. `loadDefaults` nunca lança.
loadDefaults().finally(() => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
