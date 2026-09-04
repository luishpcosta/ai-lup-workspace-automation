# Plan: Painel de Controle Frontend v1 (REST/SSE)

**Feature ID:** 006-frontend-painel-controle
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-04

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

SPA React + Vite, JavaScript (sem TypeScript — decisão desta fase, ver Key Decisions),
processo próprio (`npm run dev`), zero estado compartilhado com o backend além de
REST/SSE (`constitution.md`, princípios 5/6). Sem router externo — a navegação entre
telas (Configuração / Lista / Detalhe) é um `switch` de estado em `App.jsx`, dado o
escopo pequeno (3 telas). Testes com Vitest + Testing Library (jsdom), `fetch`
mockado — sem dependência de um navegador real ou de Playwright nesta versão (ver
Riscos).

Todas as chamadas passam por um client fino (`src/lib/apiClient.js`) que lê a URL
base configurada; o stream (`GET /stream`) usa `fetch` + `ReadableStream` (não
`EventSource`), porque o código precisa distinguir a resposta 409 (`not_streamable`) da
resposta 200 com corpo SSE — `EventSource` não expõe o status HTTP da conexão inicial
de forma utilizável para isso.

## Architecture & Components

- `src/lib/config.js` — `getConfig()`/`setConfig({baseUrl, configDir})`, persistidos em
  `localStorage` (chave única, JSON) — RF-1.
- `src/lib/resolveConfigPath.js` — função pura `resolveConfigPath(configDir, id) ->
  string`: concatena `configDir` (sem barra final duplicada) + `/` + `id` + `.yaml`.
  Sem leitura de filesystem — só construção de string (ADR-006, Decisão). Testável
  isoladamente, sem mock de rede.
- `src/lib/apiClient.js` — `getRuns()`, `getRunDetail(chainName)`,
  `createRun(configPath)`, `postInstruction(chainName, mensagem)`,
  `cancelRun(chainName)`, `openStream(chainName, {onLine, signal})`. Cada função lê
  `getConfig().baseUrl`; erros de rede/HTTP viram um erro tipado
  (`{kind: "connection"|"http", status?, code?, message}`) para as telas decidirem a
  mensagem exibida.
- `src/components/SettingsScreen.jsx` — formulário de URL base + diretório-base; grava
  via `config.js`; é a tela forçada quando `getConfig()` retorna vazio — AT-01.
- `src/components/RunsList.jsx` — `GET /runs`, destaque visual (classe CSS) quando
  `status` indica falha — AT-02.
- `src/components/RunDetail.jsx` — `GET /runs/{chain_name}`, tabela por etapa; hospeda
  `StreamPanel` e o botão de cancelar — AT-02, AT-05.
- `src/components/TriggerForm.jsx` — textarea (um ID por linha), resolve cada um via
  `resolveConfigPath`, dispara `createRun` por item, mostra sucesso/erro por linha sem
  interromper o lote — AT-03.
- `src/components/StreamPanel.jsx` — ao montar, chama `openStream`; 200 renderiza
  linhas conforme chegam (sem parsing); 409 mostra "sem sessão ativa no momento"; erro
  de conexão mostra mensagem clara. Sem retry automático (um botão manual "Atualizar"
  refaz a tentativa) — AT-04.
- `src/components/InstructionBox.jsx` — campo de texto + `postInstruction`; erro 409
  exibido inline — AT-04.

**Backend** (`backend/src/workflow_engine/adapters/http_api.py`, extensão pequena):
`CORSMiddleware` adicionado a `build_app()`, permitindo `GET`/`POST` e
`Content-Type`, sem credenciais — AT-06. Nenhuma rota, payload ou contrato de erro
muda.

## Data Model

Nenhum banco novo. Único estado persistido é client-side:
`localStorage["painel-config"] = {"baseUrl": string, "configDir": string}` (RF-1).
Todo o resto é obtido por chamada REST a cada renderização/ação — sem cache local
entre sessões.

## Interfaces / Contracts

Reaproveita integralmente os contratos já publicados nas ADR-004/ADR-005 — nenhum
payload novo:

- `GET /runs` → `[{chain_name, run_id, workflow_name, status, created_at, updated_at, source_db}]`
- `GET /runs/{chain_name}[?include=io]` → `{chain_name, run_id, status, created_at, updated_at, steps: [...]}` | 404 `{"error": {"code": "not_found", ...}}`
- `POST /runs` `{"config_path": str}` → 202 `{"chain_name", "status": "started"}` | 400 `invalid_config` | 409 `already_running`
- `GET /runs/{chain_name}/stream` → 200 `text/event-stream` (`data: <linha>\n\n`) | 409 `not_streamable`
- `POST /runs/{chain_name}/instrucoes` `{"mensagem": str}` → 202 | 409 `not_interactable`
- `POST /runs/{chain_name}/cancelar` → `{"status": "cancelled"}` | 409 `already_running`/`not_cancellable` | 404 `not_found`

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-03 | `lib/config.js`, `components/SettingsScreen.jsx`, `lib/apiClient.js` (erro de conexão tipado) |
| FR-2 / AC-04, AC-05, AC-12 | `components/RunsList.jsx`, `components/RunDetail.jsx` |
| FR-3 / AC-06, AC-13 | `lib/resolveConfigPath.js`, `components/TriggerForm.jsx` |
| FR-4 / AC-07, AC-08, AC-09 | `components/StreamPanel.jsx`, `components/InstructionBox.jsx`, `lib/apiClient.js::openStream` |
| FR-5 / AC-10 | Botão de cancelar em `RunDetail.jsx` + `apiClient.js::cancelRun` |
| NFR-1 | Nenhum código de autenticação em nenhuma camada |
| NFR-2 / AC-11 | `backend/.../http_api.py::build_app` (`CORSMiddleware`) |
| NFR-3 | Tratamento de erro tipado em `apiClient.js`, usado por toda tela |

## Constitution Compliance

- **Spec before code** (`frontend/constitution.md`, princípio 1): este plan só passa a
  ser implementado depois que `tasks.md` fechar o gate de cobertura.
- **Contrato REST é do backend** (princípio 5): nenhuma rota/payload novo proposto;
  única mudança de backend é `CORSMiddleware` (transporte, não contrato).
- **Configuração em runtime** (princípio 6): `baseUrl`/`configDir` só existem em
  `localStorage`, nunca hardcoded em código ou build.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Linguagem | JavaScript (sem TypeScript) | TypeScript | Escopo de v1 é pequeno (6 componentes, 1 client); tipagem estática adia entrega sem reduzir risco real nesta fase — pode ser adotado depois sem reescrever a arquitetura. |
| Stream HTTP | `fetch` + `ReadableStream` manual | `EventSource` nativo | `EventSource` não expõe o status HTTP (409 vs 200) de forma utilizável — a AC-08 exige distinguir "sem sessão ativa" de "erro de conexão", o que `fetch` permite diretamente. |
| Navegação entre telas | Estado local em `App.jsx` (sem router) | `react-router` | Só 3 telas nesta versão; introduzir um router é overhead sem benefício real ainda. |
| Testes | Vitest + Testing Library, `fetch`/stream mockados | Playwright (browser real) | Ambiente desta sessão não tem automação de navegador real disponível; testes de unidade/integração cobrem toda lógica de decisão (resolução de ID, tratamento de erro, montagem condicional) — ver Riscos para o que fica sem cobertura. |

## Risks

- Testes desta feature não cobrem um navegador real — a interação visual (destaque
  CSS, layout) não é verificada automaticamente, só a lógica (dado o estado X, o
  componente renderiza/chama Y). Verificação real desta sessão inclui, adicionalmente,
  subir `workflow serve` de verdade e confirmar via `curl`/`fetch` que o CORS
  realmente funciona cross-origin — não é só suposição de que o middleware está certo.
- Convenção `<diretório-base>/<id>.yaml` é rígida (sem normalização de maiúsculas,
  espaços ou caracteres especiais no `id`) — herdado da ADR-006, não resolvido aqui.
