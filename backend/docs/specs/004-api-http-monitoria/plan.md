# Plan: API HTTP e Monitoria de Workflows (workflow serve)

**Feature ID:** 004-api-http-monitoria
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-04

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Novo composition root `adapters/http_api.py` (FastAPI + Uvicorn — já disponíveis no
ambiente: `fastapi 0.136.3`, `uvicorn 0.51.0`), comando `workflow serve`. Reaproveita
`WorkflowEngine`/`FileSystemPluginRegistry`/`YamlJsonChainLoader`/`SqliteStateStore`
exatamente como `run-many` (`003`): um `ThreadPoolExecutor` dispara uma thread por
execução, cada uma com seu próprio `SqliteStateStore(<watch-dir>/<chain_name>.db)`.

**Monitoria não acopla disparo a leitura**: `GET /runs`/`GET /runs/{chain_name}` leem
os arquivos `.db` de `--watch-dir` via `sqlite3` diretamente (conexão read, fechada
logo após a query) — não passam pelo `SqliteStateStore`/`StateStorePort`, porque essas
rotas HTTP só precisam **ler** linhas já persistidas, e usar o port completo (que
também cria o schema/abre conexão de escrita) seria peso desnecessário para uma leitura
pontual. Isso é o que permite enxergar execuções disparadas por `run`/`run-many` no
terminal, sem qualquer acoplamento com quem as criou.

Decisão completa, contrato HTTP e alternativas em
`adr/ADR-004-api-http-monitoria.md`.

## Architecture & Components

**`src/workflow_engine/adapters/http_api.py`** (novo):
- `RunRequest` (Pydantic): `{config_path: str}`.
- `ServerState`: estado do processo `serve` — `registry` (`FileSystemPluginRegistry`,
  descoberto uma vez, compartilhado entre threads — plugins não têm estado mutável
  entre chamadas, ver ADR-002/ADR-003), `watch_dir`, `pool`
  (`ThreadPoolExecutor(max_workers=--max-parallel)`), `active: dict[str, TrackedRun]`
  (`chain_name -> Future` + metadados, protegido por `threading.Lock`) — só contém
  execuções **disparadas por este processo** (é o que torna `cancelar` capaz de
  distinguir "minha execução" de "execução de outro processo").
  - `trigger(config_path) -> (chain_name, error_code)`: carrega/valida o config
    (`YamlJsonChainLoader`, igual à `001`/`003`), rejeita se já há uma entrada ativa
    (não `done()`) para aquele `chain_name`, senão submete ao pool.
  - `cancel(chain_name) -> outcome`: `"cancelled"` (via `Future.cancel()`, só funciona
    se a thread não começou), `"already_running"` (existe e já rodando),
    `"not_cancellable"` (existe um `.db` para esse nome mas não foi disparado por este
    processo), `"not_found"` (nem isso).
- Rotas: `POST /runs`, `GET /runs`, `GET /runs/{chain_name}`, `POST
  /runs/{chain_name}/cancelar` — cada uma só traduz o resultado de `ServerState`/das
  funções de leitura em `HTTPException`/corpo de resposta; nenhuma lógica de negócio
  na camada de rota.
- Funções de leitura (`list_runs`, `get_run_detail`) — `sqlite3.connect` direto nos
  arquivos de `--watch-dir`, schema idêntico ao já definido em
  `adapters/sqlite_state_store.py` (`workflow_runs`/`step_executions`, ADR-001) — sem
  duplicar/alterar esse schema.
- `cmd_serve(args)` — monta `ServerState`, constrói o `FastAPI` app, roda
  `uvicorn.run(app, host="127.0.0.1", port=args.port)`.

**`src/workflow_engine/adapters/cli.py`** (extensão pontual): novo subparser `serve`
(`--port`, `--plugins-dir`, `--watch-dir` default `./run-many-state` — mesmo default
do `run-many`, `--max-parallel` default `3`, `--correlation-keys`), dispatch em
`main()`. Nenhuma mudança em `cmd_run`/`cmd_run_many`.

**Nenhum outro arquivo muda**: `WorkflowEngine`, `RetryHandler`, `SqliteStateStore`,
`FileSystemPluginRegistry`, `YamlJsonChainLoader`, plugins da `002` — todos reusados
como já existem.

## Data Model

Nenhuma mudança de schema. `GET /runs`/`GET /runs/{chain_name}` leem
`workflow_runs`/`step_executions` (schema da ADR-001) — nenhum status novo (`cancelled`
não existe como valor de `status`: uma execução cancelada **antes de começar** nunca
chega a criar uma linha em `workflow_runs`, porque `create_run` só é chamado de dentro
de `WorkflowEngine.run()`, que nunca chega a executar quando `Future.cancel()`
funciona).

## Interfaces / Contracts

Contrato HTTP completo (corpo, status codes, formato de erro) documentado na
ADR-004, seção Decisão. Resumo:

- Erro uniforme: `{"error": {"code": "<slug>", "message": "<texto>"}}`.
- `POST /runs` → 202 `{"chain_name", "status": "started"}` | 400 `invalid_config` | 409 `already_running`.
- `GET /runs` → 200 `[{"chain_name", "run_id", "status", "created_at", "updated_at", "source_db"}]`.
- `GET /runs/{chain_name}` → 200 (com `steps[]`, `?include=io` para payload completo) | 404 `not_found`.
- `POST /runs/{chain_name}/cancelar` → 200 `{"status": "cancelled"}` | 409 `already_running` | 409 `not_cancellable` | 404 `not_found`.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01 | `adapters/cli.py` (subparser `serve`, dispatch) |
| FR-2 / AC-02, AC-03, AC-04 | `adapters/http_api.py::ServerState.trigger` + rota `POST /runs` |
| FR-3 / AC-05 | `adapters/http_api.py::list_runs` + rota `GET /runs` |
| FR-4 / AC-06, AC-07 | `adapters/http_api.py::get_run_detail` + rota `GET /runs/{chain_name}` |
| FR-5 / AC-08, AC-09, AC-09b, AC-10 | `adapters/http_api.py::ServerState.cancel` + rota `POST /runs/{chain_name}/cancelar` |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md`
  fechar o gate de cobertura.
- **Plugin contract is stable** (princípio 5): nenhum plugin muda.
- **Hexagonal boundary is one-way** (princípio 6): `http_api.py` é um adapter (só
  importa `application`/`domain` via as mesmas portas que `cli.py` já usa) — mesma
  categoria de `cli.py`, não introduz import de `adapters` em `domain`/`application`.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Framework HTTP | FastAPI + Uvicorn | Flask, stdlib `http.server` | `StreamingResponse`/rotas async nativas, necessárias para SSE na feature `005` |
| Leitura de monitoria | `sqlite3` direto nos arquivos `.db`, sem passar pelo `StateStorePort` | Reusar `SqliteStateStore` também para leitura | Leitura pontual não precisa do overhead de abrir uma conexão de escrita com schema; mantém a fronteira clara entre "quem escreve" (Engine) e "quem só lê" (API) |
| Rastreamento de execuções ativas | Dict em memória `chain_name -> Future`, só do que este processo disparou | Também tentar rastrear execuções de outros processos | Impossível de forma confiável sem IPC — é exatamente por isso que `cancelar` distingue "minha execução" de "execução de outro processo" (ver ADR-004) |
| Cancelamento de etapa em execução | Não suportado (409 honesto) | Registrar tentativa e simular sucesso | Nenhuma promessa falsa — `subprocess.run` bloqueante dentro dos plugins não expõe o processo externo para matar de verdade (ver ADR-004, Consequências) |

## Risks

- Sem autenticação — ver ADR-004, Riscos (NFR-1 herdado, uso local/individual).
- Leitura de muitos arquivos `.db` em `GET /runs` pode ficar lenta com o tempo (sem
  paginação nesta versão — ver ADR-004).
- Cancelamento de etapa em execução permanece não suportado até uma ADR futura que
  reveja como plugins expõem (ou não) o processo externo que invocam.
