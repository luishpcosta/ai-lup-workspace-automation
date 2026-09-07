# Plan: Refinamentos de UX — Tema, Knowledge Bases e Stream Legível

**Feature ID:** 009-refinamentos-ux-stream-legivel
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-07

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Três mudanças independentes, implementadas juntas por terem sido pedidas na mesma
demanda:

**FR-1 (tema)**: puramente CSS/JSX. `ThemeToggle` sai de entre os dois botões em
`App.jsx` e vira o último filho de `.topbar__actions`; `index.css` ganha uma margem
esquerda maior (ou um separador) só nesse elemento, para lê-lo como "preferência à
parte" em vez de mais um botão da lista.

**FR-2/FR-3 (Knowledge Bases)**: `SpecPicker.jsx` é reescrito sobre `react-select`
(`isMulti`), mantendo exatamente o contrato de props que `DynamicParamsForm.jsx` já
usa (`id`, `value: string[]`, `onChange(next: string[])`) e a mesma fonte de dado
(`specsClient.js::fetchSpecsIndex`, inalterado). `react-select` é estilizado via
`classNamePrefix="select"` contra os tokens já existentes em `index.css` (sem
Tailwind, sem CSS-in-JS — o projeto é vanilla CSS). O rótulo "Knowledge Bases" vem de
duas pontas: o `label` do parâmetro no template YAML (dado que já flui até
`DynamicParamsForm` via `params_schema`) e os textos internos do próprio picker
(carregando/vazio/erro).

**FR-3/FR-4/FR-5 (stream legível)**: `get_run_detail` (`http_api.py`) resolve
`plugin` por step a partir do `config_path` já persistido em `workflow_runs` — a
mesma leitura que `_resolve_active_claude_step` já faz para decidir se um step é
"streamável" (ADR-005), só que aqui vira parte da resposta em vez de uma decisão
interna. `RunDetail.jsx` acha o step com `status === 'running'` em `detail.steps` e
passa seu `plugin` para `StreamPanel`. `StreamPanel` escolhe o formatador por um
registro `{plugin: formatter}`; hoje só `claude_code_runner` tem entrada
(`lib/claudeStream.js`, novo). Sem entrada no registro, ou linha não-JSON, o
componente usa o `<pre>` de log bruto que já existe hoje — nunca removido, sempre
acessível por um botão no cabeçalho do painel.

Decisão completa, alternativas consideradas e riscos em
`adr/ADR-010-refinamentos-ux-knowledge-bases-stream-legivel.md`.

## Architecture & Components

- `src/App.jsx` / `src/index.css` — reposicionamento do `ThemeToggle` na topbar — FR-1.
- `src/components/SpecPicker.jsx` (reescrito) — `react-select` `isMulti`, mesmo
  contrato de props, textos renomeados para "Knowledge Base(s)" — FR-2.
- `src/index.css` — remove a regra de lista de checkboxes (`ul[aria-label='Specs de
  referência']`), adiciona overrides `.select__*` (classNamePrefix) para o tema do
  projeto (claro/escuro) — FR-2.
- `package.json` — nova dependência `react-select` — FR-2.
- `backend/config/workflow_templates/claude-implementar-local.yaml` —
  `docs_referenced.label: "Knowledge Bases"` — FR-2.
- `src/lib/claudeStream.js` (novo) — `parseClaudeStreamLine(line)` /
  `reduceClaudeTurns(turns, line)`: interpreta uma linha `stream-json` do `claude`
  CLI (`type`: `system`/`user`/`assistant`/`result`; blocos `text`/`tool_use`/
  `tool_result` de `message.content`) e acumula turnos (texto, rastro de ferramenta,
  resumo final); lança/retorna `null` para linha não reconhecida, nunca lança para o
  chamador quebrar a tela — FR-4.
- `src/components/StreamPanel.jsx` (redesenhado) — recebe `plugin` via prop; escolhe
  formatador por um registro `STREAM_FORMATTERS = {claude_code_runner:
  reduceClaudeTurns}`; renderiza turnos formatados por padrão quando há formatador
  para o `plugin`; alterna para `<pre>` (log bruto, comportamento atual) por botão no
  cabeçalho ou automaticamente quando não há formatador/linha não reconhecida — FR-3,
  FR-4, FR-5, NFR-3.
- `src/components/RunDetail.jsx` — acha o step `running` em `detail.steps` e passa seu
  `plugin` para `StreamPanel` — FR-3.
- `backend/src/workflow_engine/adapters/http_api.py::get_run_detail` — resolve
  `plugin` por step a partir de `config_path` (mesma técnica de
  `_resolve_active_claude_step`); `null` se o YAML não puder ser recarregado — FR-3,
  NFR-2.

**Backend**: a única mudança de contrato (`plugin` aditivo em `GET
/runs/{chain_name}`) é pequena o bastante para não abrir pasta de spec própria no
contexto `motor-workflow` — mesmo padrão já usado pela ADR-006 (CORS) e ADR-009
(`?root=`). Decisão e contrato completos estão na ADR-010
(`adr/ADR-010-refinamentos-ux-knowledge-bases-stream-legivel.md`).

## Data Model

Nenhuma mudança de schema SQLite — `plugin` é derivado em runtime do YAML da chain
(`config_path`, já uma coluna existente de `workflow_runs`), nunca persistido.

Formato de turno produzido por `claudeStream.js` (interno ao frontend, não é
contrato de rede):
```
{ kind: 'text', role: 'assistant', text: string }
{ kind: 'tool', name: string, status: 'running'|'done'|'failed', input?: any, output?: any }
{ kind: 'summary', ok: boolean, text: string }
```

## Interfaces / Contracts

Contrato novo, aditivo, publicado em `adr/ADR-010-acs.md` (AC-08/AC-09):

- `GET /runs/{chain_name}` → cada item de `steps[]` ganha `plugin: string | null`.
  Todo campo existente (`chain_name`, `run_id`, `status`, `created_at`, `updated_at`,
  `steps[].step_name/status/attempt_count/started_at/finished_at/error_message`, e
  `input`/`output` quando `include=io`) mantém nome e tipo inalterados.

Nenhum outro contrato muda: `GET /runs`, `GET /workflows`, `GET /workspace/repos`,
`POST /runs/from-template`, `GET /runs/{chain_name}/stream`, instrução e cancelamento
continuam exatamente como em `008`/`009` (ADR-009).

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01 | `App.jsx`, `index.css` (reposicionamento do `ThemeToggle`) |
| FR-2 / AC-02, AC-03, AC-04 | `SpecPicker.jsx` (react-select), `claude-implementar-local.yaml` (label) |
| FR-3 / AC-05, AC-08 | `http_api.py::get_run_detail` (`plugin` por step), `RunDetail.jsx` (repassa `plugin`) |
| FR-4 / AC-05 | `lib/claudeStream.js`, `StreamPanel.jsx` (leitura formatada default) |
| FR-5 / AC-06 | `StreamPanel.jsx` (alternador formatado/bruto) |
| NFR-1 (herdado) | Nenhuma mudança — sem autenticação |
| NFR-2 | `plugin` aditivo, campos existentes preservados (AC-09 em `ADR-010-acs.md`) |
| NFR-3 | `StreamPanel.jsx` cai no log bruto para linha não reconhecida/plugin sem formatador (AC-07) |
| NFR-4 | `SpecPicker.jsx` preserva o contrato de props (`value`/`onChange`) — payload ao motor idêntico |

## Constitution Compliance

- **Spec before code** (princípio 1): este spec e a ADR-010 são escritos antes da
  implementação — Tasks gate abaixo precisa passar antes do primeiro commit de código
  desta feature.
- **Contrato REST é do backend** (princípio 5): o campo `plugin` novo está decidido e
  publicado em `adr/ADR-010-refinamentos-ux-knowledge-bases-stream-legivel.md`,
  revisitando `afeta: [motor-workflow]` — este plan só consome a decisão.
- **Configuração em runtime** (princípio 6): nenhuma mudança nesta feature toca
  configuração de boot — `react-select` e o rótulo do template não são configuração,
  são UI/dado estático versionado.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Como identificar a plataforma agêntica antes de abrir o stream | `plugin` aditivo em `GET /runs/{chain_name}` | Detectar pela primeira linha do stream; endpoint novo só para isso | A informação já existe no YAML da chain e a resposta de detalhe já é carregada antes do stream — aditivo sobre um contrato existente, sem espera nem heurística |
| Widget do campo de conhecimento | `react-select` (`isMulti`) | Manter lista de checkboxes, só trocar rótulo | Pedido explícito do usuário é o padrão de interação do combobox, não só a palavra nova |
| Escopo da renomeação "Knowledge Bases" | Só rótulo visível (label do template + textos do picker) | Renomear também identificadores internos (`docs_referenced`, `spec_multiselect`, nome de arquivo) | Sem ganho funcional em renomear identificadores internos agora — "small, reversible steps" |
| Parser do stream | Dedicado ao formato `stream-json` do `claude` CLI, com fallback para log bruto por linha | Lib de chat/streaming genérica | O stream já é estruturado e conhecido (ADR-005); uma lib genérica de chat resolveria um problema mais amplo que o pedido |

## Risks

- `react-select` é uma dependência de runtime nova — aumenta o bundle frente à lista
  de checkboxes anterior; aceito porque é exatamente o padrão de interação pedido.
- O parser de `claudeStream.js` conhece a forma do `stream-json` verificada em
  `plugins/claude_code_runner.py` nesta versão do `claude` CLI; se essa forma mudar,
  o fallback de log bruto por linha não reconhecida evita quebra de tela, mas a
  leitura formatada pode ficar incompleta até o parser ser atualizado (risco já
  registrado na ADR-010).
