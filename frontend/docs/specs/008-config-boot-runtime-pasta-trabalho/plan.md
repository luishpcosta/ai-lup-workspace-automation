# Plan: Configuração de Boot em Runtime e Pasta de Trabalho

**Feature ID:** 008-config-boot-runtime-pasta-trabalho
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-06

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

`lib/config.js` ganha uma segunda fonte de valores: `public/painel-config.json`,
servido como asset estático (não passa pelo bundler) e lido por `fetch` uma vez no
boot (`main.jsx`, antes do primeiro `render`), guardado em módulo. `getConfig()`
continua síncrono para o resto do app — computa o efetivo por campo (`localStorage` >
arquivo > vazio) a cada chamada, sem cache de resultado, então uma troca salva pela
tela reflete no próximo render sem reload.

`SettingsScreen.jsx` é redesenhado: cada campo mostra um selo "default do arquivo"
quando o valor em vigor não foi digitado pelo usuário (`getFieldSources()`), e nenhum
campo usa `placeholder` — o formato esperado foi para o texto de ajuda abaixo do
campo. Um terceiro campo, pasta de trabalho, é adicionado e persistido junto das duas
URLs existentes.

No lado do motor, a única mudança de contrato é aditiva: `GET /workspace/repos` passa
a aceitar `?root=` opcional. `RepoPicker.jsx`/`apiClient.js::getLocalRepos()` passam
esse parâmetro quando a pasta de trabalho está configurada; omitido, o backend usa a
raiz do processo, exatamente como antes desta feature. `cli.py` ganha
`LOCAL_REPOS_ROOT` como fonte de default de `--local-repos-root` — a flag explícita
continua vencendo.

Decisão completa, alternativas consideradas e riscos em
`adr/ADR-009-config-boot-runtime-pasta-trabalho.md`.

## Architecture & Components

- `public/painel-config.json` (novo) — `{baseUrl, specsBaseUrl, reposRoot}`, editável
  sem rebuild — FR-1.
- `src/lib/config.js` (reescrito) — `loadDefaults()` (fetch único no boot, nunca
  lança), `getDefaults()`, `getEffectiveConfig()`/`getConfig()` (precedência por
  campo), `getFieldSources()` (origem por campo: `'user' | 'file' | 'none'`),
  `setConfig()` (ganha `reposRoot`), `clearConfig()` (descarta o salvo, volta ao
  arquivo) — FR-1, FR-3, FR-4.
- `src/main.jsx` — chama `loadDefaults()` antes de `createRoot(...).render(...)` —
  FR-1.
- `src/components/SettingsScreen.jsx` (redesenhado) — campo `reposRoot` novo; selo
  "default do arquivo" por campo; sem `placeholder`; botão "Restaurar defaults do
  arquivo" quando há algo salvo sobrepondo o arquivo — FR-3, FR-4.
- `src/lib/apiClient.js::getLocalRepos()` — acrescenta `?root=` quando
  `getConfig().reposRoot` está preenchido — FR-3.
- `backend/src/workflow_engine/adapters/http_api.py::get_local_repos` — parâmetro de
  consulta opcional `root`, precedência sobre a raiz do processo — FR-3.
- `backend/src/workflow_engine/adapters/cli.py` — default de `--local-repos-root` via
  `os.environ.get("LOCAL_REPOS_ROOT")` — FR-2.
- `start-local.sh` — deriva `LOCAL_REPOS_ROOT` do diretório-pai do repo quando não
  informado, e ecoa a raiz em uso na saída de boot.

**Backend**: a mudança de contrato (`?root=` aditivo) e o novo default de CLI são
pequenos o bastante para não abrirem uma pasta de spec própria no contexto
`motor-workflow` — mesmo padrão já usado pela ADR-006 (CORS), cujo único impacto de
backend também ficou documentado só no plan do lado que pediu a mudança. Decisão e
contrato completos estão na ADR-009 (`adr/ADR-009-config-boot-runtime-pasta-trabalho.md`).

## Data Model

`localStorage["painel-config"] = {"baseUrl": string, "specsBaseUrl": string,
"reposRoot": string}` — `reposRoot` é novo, default `""`. `public/painel-config.json`
tem o mesmo formato e vive fora do `localStorage`; nunca é escrito pelo app, só lido.

## Interfaces / Contracts

Contrato novo, aditivo, publicado em `adr/ADR-009-acs.md` (AC-06/AC-07):

- `GET /workspace/repos?root=<path>` (parâmetro opcional) → `200 [{name, path}]`,
  mesmas regras de `007` (raiz ausente/inexistente/não-diretório → lista vazia, não
  erro). Sem `root`, comportamento idêntico ao de antes desta feature.

Nenhum outro contrato muda: `GET /runs*`, `GET /workflows`,
`POST /runs/from-template`, stream, instrução e cancelamento continuam exatamente como
em `007`.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-03 | `public/painel-config.json`, `lib/config.js::loadDefaults/getEffectiveConfig`, `main.jsx` |
| FR-2 / AC-08 | `backend/adapters/cli.py` (`--local-repos-root` default) |
| FR-3 / AC-05, AC-06, AC-07 | `components/SettingsScreen.jsx` (campo pasta de trabalho), `lib/apiClient.js::getLocalRepos`, `backend/adapters/http_api.py::get_local_repos` |
| FR-4 / AC-04 | `components/SettingsScreen.jsx` (selos + remoção de placeholders), `lib/config.js::getFieldSources` |
| NFR-1 (herdado) | Nenhuma mudança — sem autenticação |
| NFR-2 | `painel-config.json` é asset estático, nunca `import.meta.env`; `lib/config.js` só lê via `fetch` |
| NFR-3 | `GET /workspace/repos` sem `root` cobre a mesma asserção de `007` (AC-02/006-workflow-templates-execucao-adhoc), preservada em teste próprio |

## Constitution Compliance

- **Spec before code** (princípio 1): a ADR-009 e este spec foram escritos antes desta
  documentação de fechamento; o código já estava implementado e verificado quando o
  gate de Tasks foi solicitado — registrado aqui como documentação as-built, prática já
  usada nas features `001`-`007` deste harness.
- **Contrato REST é do backend** (princípio 5): o parâmetro novo em
  `GET /workspace/repos` está decidido e publicado em
  `adr/ADR-009-config-boot-runtime-pasta-trabalho.md`, revisitando `afeta:
  [motor-workflow]` — este plan só consome a decisão.
- **Configuração em runtime** (princípio 6): `painel-config.json` é servido como
  arquivo estático e lido por `fetch`; nenhum valor de configuração passa por
  `import.meta.env` ou é hardcoded em código/build.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Fonte dos defaults de boot | Arquivo estático (`painel-config.json`) lido por `fetch` | `.env` do Vite (`import.meta.env`) | `.env` é substituído em tempo de build — embutiria a configuração no bundle, violando o princípio 6; o arquivo estático é editável sem rebuild |
| Como a pasta de trabalho é trocada | Parâmetro de consulta opcional no `GET` existente | Rota nova `PUT /workspace/root` gravando estado no processo | A raiz é um filtro de leitura, não estado do motor; o parâmetro mantém o endpoint idempotente, sem estado global mutável, sem abas se atropelando, sem nada se perdendo no restart |
| Escopo de caminhos aceitos por `root` | Sem restrição | Restringir a uma subárvore de uma raiz-teto | Descartado na elicitação — limitaria justamente trocar de árvore de trabalho, que é o requisito; a postura de segurança não muda em relação ao que já existe (motor local, single-user, sem auth) |
| Precedência de configuração | `localStorage` (usuário) > arquivo > vazio, campo a campo | Arquivo sobrescreve sempre / usuário não pode voltar ao default | Campo a campo evita que salvar um valor apague os demais defaults; "Restaurar defaults do arquivo" cobre o caso de querer voltar |

## Risks

- Duas fontes de default (arquivo + `localStorage`) podem confundir se a tela não
  deixar a precedência visível — mitigado pelo selo "default do arquivo" por campo
  (AC-04).
- `root` sem restrição lista subpastas de qualquer caminho legível pelo processo do
  backend — não amplia a superfície real de hoje (o motor já executa contra
  repositórios locais arbitrários via parâmetro), mas precisa ser revisitado se
  `workflow serve` for exposto além de localhost/rede de confiança (mesmo risco já
  registrado na ADR-006).
