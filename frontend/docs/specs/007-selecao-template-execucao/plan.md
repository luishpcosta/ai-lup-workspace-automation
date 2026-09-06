# Plan: Disparo por Template — Specs Remotas e Repositórios Locais

**Feature ID:** 007-selecao-template-execucao
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-06

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

`TriggerForm.jsx` (ADR-006-AT-03) é reescrito para orquestrar dois componentes novos:
`TemplateSelector` (busca `GET /workflows`, lista/seleciona um `template_id`) e
`DynamicParamsForm` (recebe o `params_schema` do template selecionado e renderiza um
campo por entrada — texto/texto longo/seleção única/múltipla escolha, conforme
`type`/`source` declarados pelo próprio motor). Um campo com `source: "local_repos"`
delega para `RepoPicker` (`GET /workspace/repos`); um campo com `source:
"spec_multiselect"` delega para `SpecPicker` (fetch direto em
`${specsBaseUrl}/docs-index.json`, novo `lib/specsClient.js`, separado de
`apiClient.js` por falar com uma origem diferente do backend do motor). Submeter chama
`apiClient.js::createRunFromTemplate(templateId, params)` → `POST /runs/from-template`.

`configDir`/`resolveConfigPath.js` (ADR-006) são removidos — órfãos assim que o
disparo deixa de resolver ID→path por convenção. `RunsList`/`RunDetail`/`StreamPanel`/
`InstructionBox`/`App.jsx` não mudam de contrato — só o conteúdo de `TriggerForm`
muda, mantendo `onDispatched`/`refreshToken` exatamente como estavam (AC-10, regressão).

Decisão completa, alternativas e o lado motor-workflow desta mudança em
`../../../backend/adr/ADR-007-templates-workflow-execucao-adhoc.md`.

## Architecture & Components

- `src/lib/config.js` — `getConfig()`/`setConfig({baseUrl, specsBaseUrl})` (troca
  `configDir` por `specsBaseUrl` — RF-1).
- `src/lib/apiClient.js` — adiciona `getWorkflows()` (`GET /workflows`),
  `getLocalRepos()` (`GET /workspace/repos`), `createRunFromTemplate(templateId,
  params)` (`POST /runs/from-template`); remove `createRun(configPath)` (sem
  chamador). `getRuns`/`getRunDetail`/`postInstruction`/`cancelRun`/`openStream`
  inalterados.
- `src/lib/specsClient.js` (novo) — `fetchSpecsIndex(specsBaseUrl)`,
  `fetchSpecContent(specsBaseUrl, contentPath)`; fetch direto, sem
  `requireConfig()`/contrato de erro do motor (origem diferente) — RF-5, NFR-2.
- `src/components/SettingsScreen.jsx` — campo `specsBaseUrl` no lugar de `configDir`.
- `src/components/TemplateSelector.jsx` (novo) — `GET /workflows`, `<select>` de
  template, mostra a descrição do selecionado — RF-2.
- `src/components/DynamicParamsForm.jsx` (novo) — um campo por entrada de
  `template.params_schema`; delega pra `RepoPicker`/`SpecPicker` conforme `source`,
  senão renderiza texto/texto longo — RF-3.
- `src/components/RepoPicker.jsx` (novo) — `GET /workspace/repos` via `apiClient.js`,
  `<select>` de repositório; lista vazia mostra explicação, não um select vazio — RF-4.
- `src/components/SpecPicker.jsx` (novo) — `fetchSpecsIndex` via `specsClient.js`,
  checkbox por spec, `onChange` recebe a lista de ids selecionados — RF-5.
- `src/components/TriggerForm.jsx` (reescrito) — orquestra os dois de cima, chama
  `createRunFromTemplate`, mantém a mesma UX de resultado inline (sucesso/erro) e o
  mesmo `onDispatched` que já existia — RF-6, RF-7.
- **Removidos**: `src/lib/resolveConfigPath.js` (+ teste).

**Backend** (`../../../adr/ADR-007-templates-workflow-execucao-adhoc.md`, contexto
`motor-workflow`): três rotas novas (`GET /workflows`, `GET /workspace/repos`,
`POST /runs/from-template`) e um modo novo no Claude Code Runner — consumidas por este
plan, implementadas e verificadas naquele contexto (`backend/docs/specs/
006-workflow-templates-execucao-adhoc/`).

## Data Model

`localStorage["painel-config"] = {"baseUrl": string, "specsBaseUrl": string}` — troca
`configDir` por `specsBaseUrl` (RF-1). Nenhum outro estado persistido no cliente; o
resultado de `GET /workflows`/`GET /workspace/repos`/`docs-index.json` é buscado a cada
render do formulário de disparo, sem cache entre sessões (mesma postura da feature `006`).

## Interfaces / Contracts

Contratos novos consumidos, já publicados por `ADR-007-templates-workflow-execucao-adhoc.md`:

- `GET /workflows` → `[{id, label, description, params_schema: [{name, label, type, required, source}]}]`
- `GET /workspace/repos` → `[{name, path}]`
- `POST /runs/from-template` `{"template_id": str, "params": dict}` → 202 `{"chain_name", "status": "started"}` | 400 `invalid_params` | 404 `template_not_found`
- `GET ${specsBaseUrl}/docs-index.json` (repositório remoto, não o motor) → `[{id, title, contentPath, documentName, root_dir}]`

Contratos existentes reaproveitados sem alteração (feature `006`): `GET /runs*`,
`GET /runs/{chain_name}/stream`, `POST /runs/{chain_name}/instrucoes`,
`POST /runs/{chain_name}/cancelar`.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02 | `lib/config.js`, `components/SettingsScreen.jsx` |
| FR-2 / AC-03 | `components/TemplateSelector.jsx` |
| FR-3 / AC-04 | `components/DynamicParamsForm.jsx` |
| FR-4 / AC-05 | `components/RepoPicker.jsx`, `lib/apiClient.js::getLocalRepos` |
| FR-5 / AC-06 | `components/SpecPicker.jsx`, `lib/specsClient.js` |
| FR-6 / AC-07, AC-08 | `components/TriggerForm.jsx`, `lib/apiClient.js::createRunFromTemplate` |
| FR-7 / AC-09 | `config/workflow_templates/implementar-historia-sdd.yaml` (backend) listado igual a qualquer outro template |
| FR-8 / AC-10 | Nenhuma mudança em `RunsList.jsx`/`RunDetail.jsx`/`StreamPanel.jsx`/`InstructionBox.jsx`/`App.jsx` |
| NFR-1, NFR-3 (herdados) | Mesmo tratamento de erro tipado já existente (`apiClient.js`), estendido a `specsClient.js` com seu próprio tipo (`SpecsError`) |
| NFR-2 | `specsClient.js` nunca importa/chama `apiClient.js` nem `getConfig().baseUrl` |

## Constitution Compliance

- **Spec before code** (princípio 1): este plan só passa a ser implementado depois que
  `tasks.md` fechar o gate de cobertura.
- **Contrato REST é do backend** (princípio 5): os três contratos novos consumidos
  (`/workflows`, `/workspace/repos`, `/runs/from-template`) já existem e estão
  publicados em `ADR-007-templates-workflow-execucao-adhoc.md`, do contexto
  `motor-workflow` — este plan só consome, não propõe.
- **Configuração em runtime** (princípio 6): `baseUrl`/`specsBaseUrl` só existem em
  `localStorage`, nunca hardcoded em código ou build.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Consulta ao repositório remoto de specs | Fetch direto do browser (`specsClient.js`) | Proxy pelo backend | Decisão do usuário — o backend não precisa saber nada sobre esse repositório, só receber os ids já escolhidos |
| Seleção de workflow | `TemplateSelector` + `DynamicParamsForm` genéricos, guiados por `params_schema` | Um componente de formulário por template conhecido de antemão | Novo template no backend não exige deploy novo de frontend — o formulário se adapta ao schema recebido |
| `configDir`/`resolveConfigPath.js` | Removidos | Manter como modo avançado alternativo | Decisão do usuário — sem chamador depois da reescrita do `TriggerForm`; disparo por `config_path` bruto continua possível via API/CLI direta, fora do painel |
| Disparo em lote (ADR-006 RF-03) | Fora de escopo nesta reformulação | Adaptar o lote para múltiplas submissões do formulário dinâmico | Params agora são estruturados (repositório + prompt + specs), não uma lista plana de ids — "lote" perde o sentido direto que tinha; repetir o envio cobre o caso de uso |

## Risks

- Testes desta feature não cobrem um navegador real — mesma limitação já registrada na
  feature `006` (Vitest + Testing Library, `fetch` mockado).
- `SpecPicker`/`RepoPicker` fazem uma consulta de rede a cada vez que o formulário é
  aberto (sem cache) — aceitável para o volume baixo/uso individual já assumido desde a
  feature `006`; revisitar se o número de specs/repositórios crescer muito.
