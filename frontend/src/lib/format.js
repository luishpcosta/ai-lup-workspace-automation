// Apresentação de dados crus do motor (status em inglês, timestamps ISO) na
// língua e no formato do painel. Mantido fora dos componentes porque a lista e o
// detalhe precisam exibir os mesmos status com o mesmo rótulo e o mesmo tom.

const STATUS = {
  completed: { label: 'Concluído', tone: 'completed' },
  failed: { label: 'Falhou', tone: 'failed' },
  running: { label: 'Em execução', tone: 'running' },
  pending: { label: 'Pendente', tone: 'pending' },
  cancelled: { label: 'Cancelado', tone: 'pending' },
  skipped: { label: 'Ignorado', tone: 'pending' },
}

export function describeStatus(status) {
  return STATUS[status] ?? { label: status ?? '—', tone: 'pending' }
}

const RELATIVE_STEPS = [
  { limit: 60, divisor: 1, unit: 'second' },
  { limit: 3600, divisor: 60, unit: 'minute' },
  { limit: 86400, divisor: 3600, unit: 'hour' },
  { limit: 604800, divisor: 86400, unit: 'day' },
]

function parseDate(value) {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

// Devolve o valor cru quando não é uma data reconhecível — o motor é a fonte da
// verdade e um formato inesperado não deve virar "Invalid Date" na tela.
export function formatRelativeTime(value) {
  const date = parseDate(value)
  if (!date) return value ?? '—'

  const seconds = (date.getTime() - Date.now()) / 1000
  const magnitude = Math.abs(seconds)
  if (magnitude < 45) return 'agora mesmo'

  const formatter = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' })
  for (const step of RELATIVE_STEPS) {
    if (magnitude < step.limit) {
      return formatter.format(Math.round(seconds / step.divisor), step.unit)
    }
  }
  return new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' }).format(date)
}

export function formatAbsoluteTime(value) {
  const date = parseDate(value)
  if (!date) return value ?? ''
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

// pt-BR, compacto: "45s", "2min 14s", "1h 03min" — sem casas decimais, sem "e".
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—'
  const total = Math.max(0, Math.round(seconds))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}min`
  if (m > 0) return `${m}min ${String(s).padStart(2, '0')}s`
  return `${s}s`
}
