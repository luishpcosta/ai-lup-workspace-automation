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

// Resumo curto e legível do que a tool está fazendo, visível mesmo com o card
// fechado — sem isso, qualquer tool diferente de ask_user só mostrava o nome cru
// (ex.: "Bash"), exigindo abrir o <details> pra entender o que de fato rodou.
// Prioriza campos já pensados para leitura humana (`description`, que é
// exatamente o que a própria tool Bash do Claude Code preenche) antes de cair
// para um campo mais técnico (`command`/`query`/...); no fim, qualquer string
// presente no input serve de resumo — nunca deixa o card sem nada além do nome.
const DESCRIPTION_FIELD_PRIORITY = [
  'description',
  'command',
  'query',
  'pattern',
  'prompt',
  'question',
  'file_path',
  'path',
  'url',
]

function describeToolInput(input) {
  if (!input || typeof input !== 'object') return null
  for (const key of DESCRIPTION_FIELD_PRIORITY) {
    const value = input[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  for (const value of Object.values(input)) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

function ToolTurn({ turn }) {
  const description = describeToolInput(turn.input)
  return (
    <details className="stream-tool" data-status={turn.status}>
      <summary className="stream-tool__summary">
        <span className="stream-tool__summary-line">
          <span className={`status__dot status__dot--${turn.status === 'done' ? 'completed' : turn.status === 'failed' ? 'failed' : 'running'}`} aria-hidden="true" />
          <span className="stream-tool__name">{turn.name}</span>
          <span className="stream-tool__status">{TOOL_STATUS_LABEL[turn.status] ?? turn.status}</span>
        </span>
        {description && <span className="stream-tool__desc">{description}</span>}
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

// Turno de tool ask_user (mcp_servers/ask_user_server.py, modo
// coding_local_interativo) ainda 'running' == pergunta pendente sem tool_result
// ainda: a chamada bloqueia de verdade o agente (protocolo de tool-use), então só
// existe uma pendente por vez. Reaproveita o turno 'tool' genérico já parseado por
// claudeStream.js — sem 'kind' novo — só extrai o que InstructionBox precisa para
// virar o formulário de resposta.
//
// O `claude` CLI reporta tools MCP com o nome namespaced
// `mcp__<server>__<tool>` (verificado ao vivo: `mcp__ask-user__ask_user`, não o
// `ask_user` puro que o próprio servidor declara) — casar só o nome puro fazia
// a pergunta nunca ser reconhecida, caindo sempre no card genérico de tool (JSON
// cru, sem formulário de resposta). `endsWith('__ask_user')` cobre o nome
// namespaced com qualquer chave de server; `=== 'ask_user'` cobre um SDK/versão
// futura que não namespace.
function isAskUserTool(name) {
  return name === 'ask_user' || (typeof name === 'string' && name.endsWith('__ask_user'))
}

function findPendingQuestion(turns) {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const turn = turns[i]
    if (turn.kind === 'tool' && isAskUserTool(turn.name) && turn.status === 'running') {
      return { text: turn.input?.question ?? '', options: turn.input?.options ?? [] }
    }
  }
  return null
}

export default function StreamPanel({ chainName, plugin, onRefresh, onPendingQuestion }) {
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

  const pendingQuestion = useMemo(() => findPendingQuestion(turns), [turns])
  useEffect(() => {
    onPendingQuestion?.(pendingQuestion)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingQuestion])
  useEffect(
    () => () => {
      // Sem pergunta pendente ao desmontar (troca de execução — RunDetail
      // remonta este componente via `key`): evita que o InstructionBox fique
      // travado no modo "respondendo" de uma sessão antiga.
      onPendingQuestion?.(null)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

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
