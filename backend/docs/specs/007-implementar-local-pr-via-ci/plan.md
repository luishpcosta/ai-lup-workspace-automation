# Plan: Implementar em Repositório Local, PR via CI do Repositório-Alvo

**Feature ID:** 007-implementar-local-pr-via-ci
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-06

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Duas adições pontuais aos plugins existentes (`claude_code_runner.py`, `git_pr.py`) —
nenhum plugin novo, nenhum arquivo `.sh` novo, nenhuma mudança em domínio/aplicação/HTTP
API/frontend. Um workflow novo (`config/workflow_templates/implementar-local.yaml`) liga
as duas peças usando o mecanismo de templates já existente (feature `006`).

`coding_local` (modo novo no Claude Code Runner) roda sem `workspace_setup` antes — lê
`workspace_path` de `context.params` (mesma convenção já usada por `investigar`, feature
`006`) — e instrui o agente a seguir o fluxo de Git **do próprio repositório-alvo**
(branch, commit, push), sem abrir PR. Como o motor não decide o nome da branch, o agente
reporta o nome no JSON estruturado de retorno (`branch`, campo novo no schema).

`confirm_pr` (ação nova no Git/PR) faz o inverso do que `create_pr` faz: só *verifica*
(`gh pr list --head <branch>`), nunca cria. Ausência de PR levanta `TransientError` — a
política `retry:` já existente no motor (mesma usada por `aguardar_checks` em
`implementar-historia-sdd`) faz o polling com limite de tentativas.

Decisão completa, diagrama e alternativas consideradas em
`adr/ADR-008-implementar-local-pr-via-ci-repo-alvo.md`.

## Architecture & Components

**`plugins/claude_code_runner.py`**:
- `_CODING_LOCAL_SCHEMA` (novo): `summary` (string), `docs_referenced` (array),
  `branch` (string) — todos obrigatórios.
- `run()`: novo branch `modo == "coding_local"` → `_run_coding_local`.
- `_run_coding_local(context)`: `workdir = input_data.get("workspace_path") or
  params.get("workspace_path")` (mesma convenção de `_run_investigar`); falha com
  `ValueError` se ausente. Monta prompt via `_coding_local_prompt(prompt_text,
  docs_referenced)`, roda `_build_cmd`/`_run_streaming_session` (sem alteração),
  extrai `summary`/`docs_referenced`/`branch` do JSON estruturado. Retorna
  `{status: "success", summary, docs_referenced, branch, workspace_path: workdir,
  session_log_path}` — inclui `workspace_path` explicitamente (diferente de
  `investigar`, que não precisa disso a jusante).
- `_coding_local_prompt(prompt_text, docs_referenced)`: instrui a implementar
  `prompt_text` (mais hint de `docs_referenced`, se houver — mesmo padrão de
  `_investigar_prompt`), a **ler e seguir o fluxo de Git documentado no próprio
  repositório** antes de agir (não assume convenção nenhuma do motor: não diz
  "branch atual", não diz "feature/"), a nunca dar push direto na branch principal, a
  commitar/dar push da branch que criar, e a **não abrir a PR** — e a retornar
  `branch` com o nome exato dessa branch.

**`plugins/git_pr.py`**:
- `import json` (novo, para parsear a saída de `gh pr list`).
- `run()`: `action = params["action"]` continua sendo lido primeiro, mas a
  renderização de `title`/`body` (que exige `title_template`/`body_template`) só
  acontece se `action != "confirm_pr"` — `confirm_pr` retorna cedo, direto de
  `_confirm_pr`.
- `_confirm_pr(input_data, cwd)`: `branch = input_data.get("branch")`; ausente →
  `ValueError` (falha permanente, nenhuma chamada a `gh`). Roda `gh pr list --head
  <branch> --json number,url --jq ".[0]"` com `cwd`; reusa `_raise_if_failed`
  (`TransientError` para stderr com padrão já conhecido, `RuntimeError` caso
  contrário). Saída vazia → `TransientError` (ainda não abriu). Saída não-vazia →
  `json.loads`, retorna `{pr_number, pr_url, status: "confirmed"}`.

**`config/workflow_templates/implementar-local.yaml`** (novo): mesma convenção de
arquivo único (chain config + metadata) da feature `006`. `params_schema`: `repo_path`
(`source: local_repos`), `prompt` (textarea), `docs_referenced` (`source:
spec_multiselect`, opcional) — mesmo shape de `investigar-impacto.yaml`. Dois `steps:`:
`implementar` (`claude_code_runner`, `modo: coding_local`, `usa_output_anterior: false`,
mesmo `mcp_config_path: ./config/mcp-docs-proxy.json` de `investigar-impacto`) seguido de
`confirmar_pr` (`git_pr`, `action: confirm_pr`, `usa_output_anterior: true`, `retry:
{max_attempts: 5, initial_delay: 30.0, multiplier: 1.5}`).

## Data Model

Nenhuma mudança. Sem schema novo, sem tabela nova, sem diretório novo.

## Interfaces / Contracts

- **Modo `coding_local` do Claude Code Runner**: `params = {modo: "coding_local",
  prompt: str, docs_referenced?: list[str], workspace_path?: str, mcp_config_path:
  str}` (ou `workspace_path` vindo de `context.input`, mesma convenção de
  `coding`/`review`); output `{status, summary, docs_referenced, branch,
  workspace_path, session_log_path}`.
- **Ação `confirm_pr` do Git/PR**: `params = {action: "confirm_pr"}`,
  `context.input` precisa conter `branch` (e `workspace_path`, usado como `cwd`);
  output em sucesso `{...carry-forward, pr_number: int | None, pr_url: str, status:
  "confirmed"}`; `TransientError` se ainda não achou PR ou se `gh` falhar
  transientemente; `ValueError` se `branch` ausente.
- **`GET /workflows`**: sem mudança de contrato — só um arquivo novo descoberto pelo
  registry já existente (feature `006`).

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-03 | `plugins/claude_code_runner.py::_run_coding_local` |
| FR-2 / AC-05, AC-07 | `plugins/git_pr.py::_confirm_pr` |
| FR-3 / AC-06, AC-08 | `retry:` do step `confirmar_pr` em `implementar-local.yaml` (mecanismo já existente, sem mudança de código) |
| FR-4 / AC-10 | `config/workflow_templates/implementar-local.yaml` (`params_schema`) |
| NFR-1 (herdado) / AC-04, AC-09 | Regressão de `_run_coding`/`_run_review`/`_run_investigar`/`_create_pr`/`_update_pr` |
| NFR-2 / AC-11 | Reuso de monitoria/stream/instruções (feature `004`/`005`), sem mudança neles |
| AC-12 (regressão) | Nenhum arquivo de template existente é alterado |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md`
  fechar o gate de cobertura.
- **Plugin contract is stable**: `Plugin.run(context) -> output` / `TransientError`
  não mudam — `coding_local`/`confirm_pr` são valores novos de `params["modo"]`/
  `params["action"]`, mesmo contrato externo dos dois plugins.
- **Hexagonal boundary is one-way**: nenhuma mudança em domínio/aplicação — só
  plugins (já são a camada de infraestrutura/adapter externa ao motor) e um arquivo
  de config.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Como confirmar que a PR abriu | Ação nova (`confirm_pr`) no plugin `git_pr` existente | Script `.sh` novo via `shell_script_runner` | `shell_script_runner` resolve `script_path` relativo contra `workspace_path` (cwd do processo), não contra o motor — um script do motor precisaria de resolução absoluta, arriscando regressão no uso existente (`poll_ci_checks.sh`, vendorizado no repo-alvo clonado) |
| Quem cria a branch | O próprio agente, seguindo a instrumentação do repositório-alvo | `workspace_setup` cria a branch a partir de parâmetros do motor | O repositório-alvo já tem sua própria convenção (ex.: `feature/<slug>`, CI reagindo a esse prefixo) — o motor decidir o nome romperia essa convenção |
| Onde a branch reportada trafega | Campo `branch` no schema JSON de saída do modo `coding_local`, carregado a jusante via `context.input` | Motor descobre a branch inspecionando o git do workspace (`git branch --show-current`) após a etapa | Mais simples, mesma mecânica já usada para `summary`/`docs_referenced` (agente relata via `--json-schema`); risco documentado (ADR-008, Consequências) — não há validação cruzada nesta versão |
| Tempo de espera da confirmação | `retry: {max_attempts: 5, initial_delay: 30.0, multiplier: 1.5}` no `.yaml` do template, não hardcoded no plugin | Timeout fixo dentro do plugin | Mesma convenção já usada por `aguardar_checks` — ajustável por template sem mudança de código, cada repositório-alvo pode ter uma CI com duração diferente |

## Risks

- Ver `adr/ADR-008-implementar-local-pr-via-ci-repo-alvo.md`, seção Consequências/Riscos
  (nome de branch sob responsabilidade do agente; tempo de retry não validado contra CI
  real mais lenta).
