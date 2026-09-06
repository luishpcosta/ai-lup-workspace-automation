---
contexto: frontend
depende_de: [motor-workflow]
---

# Contexto: frontend

Painel de controle web (SPA, React + Vite) que consome a API HTTP/SSE do
motor-workflow (`workflow serve`, ADR-004/ADR-005) para disparar, visualizar,
acompanhar ao vivo e interagir com execuções; ver `../adr/ADR-006-*.md` para a decisão
fundadora deste contexto. A partir de `ADR-007-templates-workflow-execucao-adhoc.md`
(contexto `motor-workflow`, `afeta: [frontend]`), o disparo passou a ser por **workflow
(template)** em vez de texto livre + convenção de nome de arquivo — as três rotas novas
que isso introduziu (`GET /workflows`, `GET /workspace/repos`,
`POST /runs/from-template`) são a única "rota de negócio nova" consumida por este
contexto; nenhuma delas foi proposta a partir daqui (princípio 5 da constitution).

## Linguagem

**Base URL (do backend)**:
Endereço (`host:porta`) de um processo `workflow serve` configurado pelo usuário na
tela de configuração do app e persistido em `localStorage` do navegador — não existe
valor padrão nem descoberta automática.
_Evitar_: API endpoint, server address.

**chain_name**:
Mesmo termo do contexto [motor-workflow](../../backend/docs/motor-workflow/CONTEXT.md)
— identifica de forma única um run na listagem e no detalhe. O frontend nunca gera
ou deriva esse valor: ele vem sempre de uma resposta do backend.

**Stream ao vivo**:
Conexão SSE aberta em `GET /runs/{chain_name}/stream` enquanto uma etapa Claude Code
Runner está `running`; v1 mostra o transcript cru (texto), sem parsing do schema de
eventos do Claude Code.
_Evitar_: live log, tail (usar sempre "stream ao vivo", para distinguir da leitura
única de detalhe).

**Workflow (template)**:
Uma entrada de `GET /workflows` (`{id, label, description, params_schema}`) — o motor
decide quais plugins compõem cada workflow (ADR-007); o frontend só lista, deixa o
usuário escolher um, e gera o formulário de disparo a partir do `params_schema`
declarado. `TemplateSelector.jsx`/`DynamicParamsForm.jsx` nunca hardcodam o nome ou os
campos de um template específico.
_Evitar_: "plugin" para se referir a um workflow inteiro (um workflow é uma composição
de um ou mais plugins do motor — ver `../../backend/docs/motor-workflow/CONTEXT.md`).

**Repositório local**:
Uma entrada de `GET /workspace/repos` (`{name, path}`) — subpasta imediata do diretório
configurado no processo `serve` (`--local-repos-root`, ADR-007). O frontend nunca lê o
filesystem local diretamente; `path` é o valor opaco enviado de volta como parâmetro de
um workflow (ex.: `repo_path` do template `investigar-impacto`).

**Specs de referência**:
Uma ou mais entradas de `${specsBaseUrl}/docs-index.json` (repositório remoto de
documentação, configurado na tela de Configuração) — buscadas por um fetch **direto do
browser** (`lib/specsClient.js`), nunca através do backend do motor (ADR-007, decisão do
usuário). O que chega ao motor é só a lista de ids escolhidos, como parâmetro de um
workflow (ex.: `docs_referenced`) — o motor busca o conteúdo de fato via MCP, já
configurado na máquina onde o `serve` roda.
_Evitar_: "ID de documento de referência" para este conceito — esse termo (ADR-006) era
o texto livre digitado no disparo antigo por convenção de nome de arquivo, removido
pela `ADR-007`; specs agora são escolhidas por seleção, não digitadas.

**`params` (payload REST, `POST /runs/from-template`)**:
Objeto `{template_id: string, params: dict}` — `params` é montado por
`DynamicParamsForm.jsx` a partir dos valores preenchidos/selecionados pelo usuário,
com as chaves exatas que `template.params_schema` declara. Quem valida campos
obrigatórios faltando é o backend (`validate_params` → 400 `invalid_params`).
