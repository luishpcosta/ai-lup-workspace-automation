import { useEffect, useState } from 'react'
import { openStream } from '../lib/apiClient'

// ADR-006-AT-04 / AC-07 (stream ao vivo), AC-08 (sem sessão ativa -> não reconecta em loop).
// A troca de chainName/refreshToken é feita via `key` no componente pai (RunDetail),
// o que remonta este componente com estado limpo em vez de resetar dentro do efeito
// (evita setState síncrono no corpo do efeito — react-hooks/set-state-in-effect).
export default function StreamPanel({ chainName, onRefresh }) {
  const [lines, setLines] = useState([])
  const [status, setStatus] = useState('loading') // 'loading' | 'streaming' | 'inactive' | 'error'
  const [errorMessage, setErrorMessage] = useState(null)

  useEffect(() => {
    const controller = new AbortController()

    openStream(chainName, {
      signal: controller.signal,
      onLine: (line) => {
        setStatus('streaming')
        setLines((prev) => [...prev, line])
      },
    })
      .then(() => {
        // Stream terminou (etapa deixou de estar "running") — sem retry automático (AC-08).
      })
      .catch((err) => {
        if (err?.code === 'not_streamable') {
          setStatus('inactive')
        } else {
          setStatus('error')
          setErrorMessage(err?.message ?? 'Erro desconhecido ao abrir o stream.')
        }
      })

    return () => controller.abort()
  }, [chainName])

  return (
    <section className="panel" aria-label="Stream ao vivo">
      <h3>Stream ao vivo</h3>
      <button type="button" className="btn-secondary" onClick={onRefresh}>
        Atualizar
      </button>
      {status === 'inactive' && <p>Sem sessão ativa no momento.</p>}
      {status === 'error' && <p role="alert">{errorMessage}</p>}
      <pre>{lines.join('\n')}</pre>
    </section>
  )
}
