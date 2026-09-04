# Plan: Execuções Paralelas Independentes (run-many)

**Feature ID:** 003-execucoes-paralelas-independentes
**Phase:** Tasks
**Spec:** ./spec.md
**Last updated:** 2026-09-04

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Novo subcomando `run-many` inteiramente dentro de `adapters/cli.py` (composition
root) — nenhuma mudança em `domain/`, `application/` ou nos plugins existentes.
`concurrent.futures.ThreadPoolExecutor(max_workers=--max-parallel)` dispara uma
thread por execução; cada plugin já delega trabalho pesado a `subprocess.run` (git,
`claude`, `gh`, scripts de polling), que libera o GIL enquanto espera o processo
externo — múltiplas threads Python conseguem ter processos externos rodando de
verdade em paralelo, sem precisar de `multiprocessing`.

Decisão completa, diagrama e alternativas consideradas em
`adr/ADR-003-execucoes-paralelas-independentes.md`.

## Architecture & Components

**`src/workflow_engine/adapters/cli.py`** (único arquivo tocado):
- `build_parser()`: novo subparser `run-many` — argumentos `configs` (`nargs="+"`),
  `--plugins-dir` (default `./plugins`, igual ao `run`), `--db-dir` (default
  `./run-many-state`), `--max-parallel` (default `3`), `--correlation-keys` (mesmo
  default do `run`).
- `cmd_run_many(args)`:
  1. `FileSystemPluginRegistry(args.plugins_dir).discover()` — **uma vez**,
     compartilhado entre todas as threads (plugins não têm estado mutável entre
     chamadas — ver ADR-003, Decisão).
  2. Para cada config: `YamlJsonChainLoader().load(config, known_plugins=...)` —
     valida todos antes de disparar qualquer execução (AC-01, AC-03).
  3. Valida que nenhum par de `ChainDefinition.name` colide no lote (AC-02).
  4. `ThreadPoolExecutor(max_workers=args.max_parallel)`; para cada
     `(config_path, chain)` válido, submete um job que:
     - abre `SqliteStateStore(db_dir / f"{chain.name}.db")` (AC-06, AC-07);
     - constrói um `WorkflowEngine` novo (registry compartilhado, state_store e
       `JsonEventLogger()` próprios da thread);
     - chama `engine.run(chain, config_path)`, capturando sucesso
       (`run_id`) ou `WorkflowFailed` (AC-10 — cada thread segue seu próprio destino,
       sem cancelar as demais).
  5. Aguarda todos os futures (`as_completed`), monta e imprime o resumo (AC-08),
     decide o exit code (AC-09).
- `BatchResult` — `dataclass` local a `cli.py` (não é um port/model de domínio, é só
  estrutura de relatório do comando; hexagonal boundary intacto).

**Nenhum outro arquivo muda**: `WorkflowEngine`, `RetryHandler`, `SqliteStateStore`,
`JsonEventLogger`, `FileSystemPluginRegistry`, `YamlJsonChainLoader` e os 4 plugins da
`002` são reusados exatamente como já existem.

## Data Model

Nenhuma mudança de schema. Mesmo schema `workflow_runs`/`step_executions` da `001`,
só que em arquivos `.db` separados (um por execução do lote, nomeado por
`chain.name`) em vez de um `workflow_state.db` único.

## Interfaces / Contracts

- **CLI**: `workflow run-many <config...> [--plugins-dir DIR] [--db-dir DIR]
  [--max-parallel N] [--correlation-keys KEYS]`.
- **Saída**: um resumo de texto, uma linha por execução:
  `[OK|FAILED] <chain.name> (run_id=<id>)[: <erro, se falhou>]`, seguido de uma linha
  de totais (`X/Y completed`). Exit code `0` se todas completaram, `1` se alguma
  falhou.
- **`.db` por execução**: `<db-dir>/<chain.name>.db` — mesmo schema de
  `workflow_runs`/`step_executions` já documentado na `001`.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-03, AC-04, AC-05 | `adapters/cli.py::cmd_run_many` (validação do lote + `ThreadPoolExecutor`) |
| FR-2 / AC-06, AC-07 | `adapters/cli.py::cmd_run_many` (um `SqliteStateStore` por execução, nomeado por `chain.name`) |
| FR-3 / AC-10 | `adapters/cli.py::cmd_run_many` (cada future tratado independentemente, exceção de um não cancela os demais) |
| FR-4 / AC-08, AC-09 | `adapters/cli.py::cmd_run_many` (resumo + exit code) |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md`
  fechar o gate de cobertura.
- **Plugin contract is stable** (princípio 5): nenhum plugin muda; `Plugin.run(context)
  -> output` e `TransientError` continuam exatamente como na `001`/`002`.
- **Hexagonal boundary is one-way** (princípio 6): toda a feature fica dentro de
  `adapters/cli.py` — nenhum import novo em `domain/`/`application/`.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Mecanismo de paralelismo | `ThreadPoolExecutor` | `multiprocessing` (um processo por execução) | O trabalho pesado já é `subprocess` (libera o GIL); processos separados exigiriam serializar/recriar o registry sem ganho real de paralelismo |
| State Store por execução do lote | Um arquivo `.db` isolado por execução, nomeado por `chain.name` | SQLite compartilhado com modo WAL + retry | Isolar por arquivo elimina contenção de escrita concorrente sem exigir configuração adicional; auditoria "tudo junto" fica em arquivos separados, mas cada um já é auditável isoladamente |
| Detecção de conflito entre histórias do lote | Nenhuma — responsabilidade do usuário | Bloqueio simples por `repo_url` repetido no lote | Usuário confirmou explicitamente que fica fora de escopo |
| Comportamento em falha parcial | Demais execuções continuam normalmente | `--fail-fast` no nível do lote (cancela as demais) | Contradiz a premissa de independência entre as histórias do lote |

## Risks

- `--max-parallel` alto pode esbarrar em rate-limit real de ferramentas externas
  (API do Claude, GitHub) — o motor não tem nenhuma lógica de backpressure além do
  teto fixo do pool.
- Se a premissa de independência do usuário estiver errada (duas histórias do lote
  afetam o mesmo repo/recurso), não há detecção nem proteção — corrida real de
  escrita pode acontecer silenciosamente (decisão consciente, ver ADR-003).
- Auditoria de "todas as execuções do lote juntas" exige olhar vários arquivos `.db`
  em vez de uma consulta só.
