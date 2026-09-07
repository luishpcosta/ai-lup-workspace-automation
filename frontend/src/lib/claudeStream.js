// ADR-010 (RF-04/RF-05, AC-05/AC-07): interpreta as linhas `stream-json` do `claude`
// CLI (plugins/claude_code_runner.py, ADR-005) e as reduz a "turnos" legíveis —
// texto da IA como prosa, cada tool_use como um rastro com status/detalhe, e o
// evento final `result` como um resumo de encerramento. Puramente funcional: recebe
// as linhas brutas já acumuladas e devolve os turnos, sem estado próprio — quem
// mantém as linhas é StreamPanel.
//
// Nunca lança: uma linha que não é JSON vira um turno `raw` (RNF-02/AC-07) em vez de
// interromper a leitura das linhas seguintes.

function stringifyBlockContent(content) {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((block) => (typeof block === 'string' ? block : (block?.text ?? JSON.stringify(block))))
      .join('\n')
  }
  if (content == null) return ''
  return JSON.stringify(content, null, 2)
}

function summaryText(resultEvent) {
  const structured = resultEvent.structured_output
  if (structured && typeof structured === 'object') {
    return structured.summary ?? structured.relatorio ?? JSON.stringify(structured)
  }
  if (typeof resultEvent.result === 'string') return resultEvent.result
  return resultEvent.is_error ? 'A execução terminou com erro.' : 'Execução concluída.'
}

/**
 * @param {string[]} lines - linhas brutas já recebidas do stream, na ordem de chegada
 * @returns {Array<object>} turnos: {kind:'text'|'tool'|'summary'|'raw', ...}
 */
export function buildClaudeTurns(lines) {
  const turns = []
  const toolById = new Map()

  for (const raw of lines) {
    const trimmed = raw.trim()
    if (!trimmed) continue

    let event
    try {
      event = JSON.parse(trimmed)
    } catch {
      turns.push({ kind: 'raw', text: raw })
      continue
    }
    if (!event || typeof event !== 'object' || typeof event.type !== 'string') {
      turns.push({ kind: 'raw', text: raw })
      continue
    }

    if (event.type === 'assistant') {
      for (const block of event.message?.content ?? []) {
        if (block?.type === 'text' && block.text) {
          turns.push({ kind: 'text', text: block.text })
        } else if (block?.type === 'tool_use') {
          const turn = {
            kind: 'tool',
            id: block.id,
            name: block.name ?? 'ferramenta',
            input: block.input,
            status: 'running',
            output: null,
          }
          turns.push(turn)
          if (block.id) toolById.set(block.id, turn)
        }
      }
    } else if (event.type === 'user') {
      for (const block of event.message?.content ?? []) {
        if (block?.type !== 'tool_result') continue
        const turn = toolById.get(block.tool_use_id)
        if (!turn) continue
        turn.status = block.is_error ? 'failed' : 'done'
        turn.output = stringifyBlockContent(block.content)
      }
    } else if (event.type === 'result') {
      turns.push({ kind: 'summary', ok: !event.is_error, text: summaryText(event) })
    }
    // 'system' (init) e outros tipos não mapeados: intencionalmente sem turno próprio
    // — ruído para a leitura formatada; continuam disponíveis no log bruto.
  }

  return turns
}
