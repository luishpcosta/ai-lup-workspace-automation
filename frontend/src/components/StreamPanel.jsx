import { useEffect, useMemo, useState } from 'react'
import { openStream } from '../lib/apiClient'
import { buildClaudeTurns } from '../lib/claudeStream'

// ADR-006-AC-04 / AC-07 (stream ao vivo), AC-08 (sem sessão ativa -> não reconecta em loop).
// A troca de chainName/refreshToken é feita via `key` no componente pai (RunDetail),
// o que remonta este componente com estado limpo em vez de resetar dentro do efeito
// (evita setState síncrono no corpo do efeito — react-hooks/set-state-in-effect).
//
// ADR-010 (RF-03/RF-04/RF-05): `plugin` identifica a plataforma agêntica do step em
// execução (vindo de GET /runs/{chain_name}, repassado por RunDetail). Um formatador
// dedicado por plugin transforma o stream-json em turnos legíveis; sem formatador
// conhecido, ou linha não reconhecida, o painel cai no log bruto (RNF-02) — nunca
// quebra a tela.
const STREAM_FORMATTERS = { claude_code_runner: buildClaudeTurns }

const PLATFORM_LABELS = { claude_code_runner: 'Claude Code' }

const TOOL_STATUS_LABEL = { running: 'executando', done: 'concluído', failed: 'falhou' }

function ToolTurn({ turn }) {
  return (
    <details className="stream-tool" data-status={turn.status}>
      <summary className="stream-tool__summary">
        <span className={`status__dot status__dot--${turn.status === 'done' ? 'completed' : turn.status === 'failed' ? 'failed' : 'running'}`} aria-hidden="true" />
        <span className="stream-tool__name">{turn.name}</span>
        <span className="stream-tool__status">{TOOL_STATUS_LABEL[turn.status] ?? turn.status}</span>
      </summary>
      <div className="stream-tool__detail">
        {turn.input !== undefined && (
          <>
            <h4>Entrada</h4>
            <pre>{JSON.stringify(turn.input, null, 2)}</pre>
          </>
        )}
        {turn.output != null && (
          <>
            <h4>Saída</h4>
            <pre>{turn.output}</pre>
          </>
        )}
      </div>
    </details>
  )
}

function FormattedTurns({ turns }) {
  if (turns.length === 0) return <p className="settings-hint">Aguardando o agente…</p>
  return (
    <div className="stream-turns">
      {turns.map((turn, index) => {
        const key = `${turn.kind}-${index}`
        if (turn.kind === 'text') {
          return (
            <p key={key} className="stream-turn stream-turn--text">
              {turn.text}
            </p>
          )
        }
        if (turn.kind === 'tool') {
          return <ToolTurn key={turn.id ?? key} turn={turn} />
        }
        if (turn.kind === 'summary') {
          return (
            <p key={key} className={`stream-turn stream-turn--summary ${turn.ok ? 'stream-turn--ok' : 'stream-turn--failed'}`}>
              {turn.text}
            </p>
          )
        }
        // 'raw': linha que não pôde ser interpretada (ADR-010-AC-07) — mostrada
        // inline, sem interromper a leitura das linhas seguintes.
        return (
          <p key={key} className="stream-turn stream-turn--raw">
            {turn.text}
          </p>
        )
      })}
    </div>
  )
}

export default function StreamPanel({ chainName, plugin, onRefresh }) {
  const [lines, setLines] = useState([])
  const [status, setStatus] = useState('loading') // 'loading' | 'streaming' | 'inactive' | 'error'
  const [errorMessage, setErrorMessage] = useState(null)

  const formatter = plugin ? STREAM_FORMATTERS[plugin] : undefined
  const [rawMode, setRawMode] = useState(false)

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

  const turns = useMemo(() => (formatter ? formatter(lines) : []), [formatter, lines])
  const showFormatted = Boolean(formatter) && !rawMode

  return (
    <section className="panel stream" aria-label="Stream ao vivo">
      <div className="section-head">
        <h3>
          Stream ao vivo
          {plugin && <span className="stream__platform-badge">{PLATFORM_LABELS[plugin] ?? plugin}</span>}
        </h3>
        <div className="stream__head-actions">
          {formatter && (
            <button type="button" className="btn-link" onClick={() => setRawMode((v) => !v)}>
              {rawMode ? 'Ver leitura formatada' : 'Ver log bruto'}
            </button>
          )}
          <button type="button" className="btn-secondary" onClick={onRefresh}>
            Atualizar
          </button>
        </div>
      </div>
      {status === 'inactive' && <p className="settings-hint">Sem sessão ativa no momento.</p>}
      {status === 'error' && <p role="alert">{errorMessage}</p>}
      {lines.length > 0 && (showFormatted ? <FormattedTurns turns={turns} /> : <pre>{lines.join('\n')}</pre>)}
    </section>
  )
}
