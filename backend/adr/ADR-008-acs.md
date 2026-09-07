# Atividades e Acceptance Criteria — ADR-008

> Referência: `ADR-008-implementar-local-pr-via-ci-repo-alvo.md`. Cada atividade
> pertence a um componente e tem 1+ AC vinculada.

## Componente: Plugin Claude Code Runner (`backend/plugins/claude_code_runner.py`)

### Atividade ADR-008-AT-01: Modo `coding_local`

- **Descrição**: Novo `modo` no `run()` do plugin. Lê `workspace_path` de
  `context.params` (sem `context.input` — não há `workspace_setup` antes na cadeia).
  Monta prompt que instrui o agente a implementar `params["prompt"]`, ler e seguir o
  fluxo de Git documentado no próprio repositório-alvo, e não abrir PR ele mesmo.
  Retorna `summary`/`docs_referenced`/`branch`/`workspace_path`/`session_log_path`.
- **Depende de**: nenhuma (reaproveita `_build_cmd`/`_run_streaming_session` já
  existentes, sem alteração neles).

**AC ADR-008-AC-01**
```
Dado um template cujo step usa `plugin: claude_code_runner` com `modo: "coding_local"`
  e `params.workspace_path` apontando para um checkout local existente
Quando o step roda e o agente reporta, no JSON final, `summary`, `docs_referenced`
  e `branch` (nome da branch para a qual deu push)
Então o `output` do step é `{status: "success", summary, docs_referenced, branch,
  workspace_path, session_log_path}` — `workspace_path` é o mesmo valor recebido em
  `params.workspace_path` (para o step seguinte usar via carry-forward)
```

**AC ADR-008-AC-02**
```
Dado o mesmo cenário do AC-01
Quando `context.params` não tem `workspace_path` (nem em `params` nem em
  `context.input`)
Então o plugin levanta `ValueError` com mensagem indicando que `workspace_path` é
  obrigatório para `modo: coding_local` — nenhum processo `claude` é iniciado
```

**AC ADR-008-AC-03**
```
Dado o mesmo cenário do AC-01
Quando o JSON final do agente não inclui `branch` (schema violado)
Então o plugin levanta o mesmo tipo de erro que já levanta hoje para `coding`/
  `investigar` quando o schema não é atendido (`RuntimeError`, via
  `_extract_structured`/validação de `--json-schema` do CLI) — comportamento
  idêntico ao já coberto por `_CODING_SCHEMA`/`_INVESTIGAR_SCHEMA`, sem lógica nova
```

**AC ADR-008-AC-04** (regressão)
```
Dado os modos existentes `coding`, `review`, `investigar`
Quando a suíte de testes do plugin roda após a mudança
Então nenhum teste existente desses três modos muda de comportamento ou quebra —
  `coding_local` é aditivo, sem alteração em `_run_coding`/`_run_review`/
  `_run_investigar`/`_coding_prompt`/`_review_prompt`/`_investigar_prompt`
```

---

## Componente: Plugin Git/PR (`backend/plugins/git_pr.py`)

### Atividade ADR-008-AT-02: Ação `confirm_pr`

- **Descrição**: Nova ação em `run()`, checada antes de `title_template`/
  `body_template` serem exigidos (essa ação não usa nenhum dos dois). Lê `branch` de
  `context.input` (carry-forward do step `coding_local`), roda `gh pr list --head
  <branch> --json number,url --jq ".[0]"` com `cwd = context.input["workspace_path"]`.
- **Depende de**: ADR-008-AT-01 (precisa do `branch`/`workspace_path` que
  `coding_local` produz).

**AC ADR-008-AC-05**
```
Dado um step `plugin: git_pr` com `params.action: "confirm_pr"` e `context.input`
  contendo `branch: "feature/x"` e `workspace_path: "/caminho/local"`
Quando `gh pr list --head feature/x` (rodado com cwd no workspace_path) retorna uma
  PR existente
Então o `output` do step é `{...carry-forward de context.input, pr_number: <int>,
  pr_url: <string>, status: "confirmed"}`
```

**AC ADR-008-AC-06**
```
Dado o mesmo cenário do AC-05
Quando `gh pr list --head feature/x` não retorna nenhuma PR (saída vazia)
Então o plugin levanta `TransientError` (não `RuntimeError`) — sinaliza ao motor que
  a etapa é retriable pela política `retry:` do step, sem marcar a run como falha
  permanente na primeira tentativa
```

**AC ADR-008-AC-07**
```
Dado o mesmo cenário do AC-05
Quando `context.input` não contém `branch`
Então o plugin levanta `ValueError` (falha permanente, não retriable) indicando que
  `branch` é obrigatório para `action: confirm_pr` — nenhuma chamada a `gh` é feita
```

**AC ADR-008-AC-08**
```
Dado o mesmo cenário do AC-05
Quando o comando `gh pr list` falha (`returncode != 0`) com stderr contendo um dos
  padrões já tratados como transiente (`timeout`, `econnreset`, `network`, "could
  not resolve host")
Então o plugin levanta `TransientError` — reaproveita `_raise_if_failed` já existente,
  sem lógica de classificação de erro nova
```

**AC ADR-008-AC-09** (regressão)
```
Dado as ações existentes `create_pr`/`update_pr`
Quando a suíte de testes do plugin roda após a mudança
Então nenhum teste existente dessas duas ações muda de comportamento ou quebra —
  `_validate_traceability`, `_create_pr`, `_update_pr` permanecem inalterados; a
  checagem de `action == "confirm_pr"` acontece antes da renderização de
  `title_template`/`body_template`, sem afetar o caminho das outras duas ações
```

---

## Componente: Templates de workflow (`backend/config/workflow_templates/`)

### Atividade ADR-008-AT-03: Template `implementar-local`

- **Descrição**: Novo arquivo `implementar-local.yaml`, mesma convenção da ADR-007
  (chain config + metadata no mesmo arquivo). Dois steps: `implementar`
  (`claude_code_runner`, `modo: coding_local`) seguido de `confirmar_pr` (`git_pr`,
  `action: confirm_pr`, com `retry: {max_attempts: 5, initial_delay: 30.0, multiplier:
  1.5}`). `params_schema`: `repo_path` (`source: local_repos`), `prompt` (textarea),
  `docs_referenced` (`source: spec_multiselect`, opcional).
- **Depende de**: ADR-008-AT-01, ADR-008-AT-02.

**AC ADR-008-AC-10**
```
Dado o backend rodando com `--local-repos-root` configurado e um repositório local
  disponível
Quando o usuário chama `GET /workflows`
Então `implementar-local` aparece na lista, com `params_schema` contendo `repo_path`
  (`source: local_repos`), `prompt` (sem `source`, `type: textarea`), `docs_referenced`
  (`source: spec_multiselect`) — sem nenhuma mudança em `GET /workflows` em si (mesma
  rota da ADR-007, só um arquivo novo descoberto por `FileSystemWorkflowTemplateRegistry`)
```

**AC ADR-008-AC-11**
```
Dado o template `implementar-local` disparado via `POST /runs/from-template` com
  `repo_path` apontando para um checkout local real, `prompt` descrevendo uma mudança
  pequena e verificável
Quando a run é executada de ponta a ponta contra um repositório-alvo real (verificação
  manual, não automatizável em CI deste monorepo — precisa de `claude`/`gh` reais)
Então: (a) nenhum clone acontece (o step `implementar` não tem `workspace_setup`
  antes); (b) o agente cria uma branch nova e dá push nela (verificável via `git log
  --all`/`git branch -a` no repositório-alvo); (c) a CI do repositório-alvo abre uma PR;
  (d) o step `confirmar_pr` retorna `status: confirmed` com o `pr_number`/`pr_url`
  corretos antes de `max_attempts` estourar
```

**AC ADR-008-AC-12** (regressão)
```
Dado os templates existentes `investigar-impacto` e `implementar-historia-sdd`
Quando `GET /workflows` é chamado após a mudança
Então os dois continuam aparecendo com o mesmo `params_schema` de antes — nenhum
  arquivo existente é alterado
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-008 | AT-03 | AC-10, AC-12 | Templates de workflow | Concluído |
| RF-02 | ADR-008 | AT-01 | AC-01, AC-02, AC-03, AC-04 | Claude Code Runner | Concluído |
| RF-03 | ADR-008 | AT-02 | AC-05, AC-06, AC-07, AC-08, AC-09 | Git/PR | Concluído |
| RF-04 | ADR-008 | AT-02, AT-03 | AC-05, AC-11 | Git/PR, Templates de workflow | Concluído (AC-11 verificado de ponta a ponta contra `ai-lup-poc-target-cli` real — PR #8) |
| RNF-01 | ADR-008 | — | — (sem mudança de código no frontend/HTTP API) | Frontend/HTTP API | Concluído (N/A por design) |
| RNF-02 (herdado) | ADR-008 | AT-01, AT-02 | AC-04, AC-09 | Claude Code Runner, Git/PR | Concluído |
| RNF-03 (herdado) | ADR-008 | AT-01, AT-02 | AC-04, AC-09 | Claude Code Runner, Git/PR | Concluído |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
