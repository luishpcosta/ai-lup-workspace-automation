# Atividades e Acceptance Criteria — ADR-002

> Referência: `ADR-002-plugins-poc-pipeline-sdd.md`. Cada atividade pertence a um
> componente e tem 1+ AC vinculada. ACs de contrato descrevem o payload explicitamente
> (campos, tipos e obrigatoriedade elicitados na Fase 3.5), não apenas "deve funcionar".

## Componente: Plugin Workspace Setup

### Atividade ADR-002-AT-01: Provisionamento de workspace, branch e infraestrutura opcional

- **Descrição**: Implementar o plugin que garante o repositório local (clone/pull),
  cria/troca para a branch de trabalho a partir da branch base, instala dependências e,
  se configurado, sobe infraestrutura local via `docker compose up -d`.
- **Depende de**: Plugin Interface (ADR-001-AT-03)

**AC ADR-002-AC-01** (contrato de payload)
```
Dado que a etapa é resolvida pelo Engine
params obrigatórios: repo_url (string), branch_base (string), branch_name (string), historia_id (string)
params opcionais: install_cmd (string), docker_compose_path (string)
output: workspace_path (string), branch (string), base_commit_sha (string), status ("ready")
```

**AC ADR-002-AC-02**
```
Dado repo_url e branch_base válidos, sem docker_compose_path informado
Quando o plugin executa
Então o repositório é clonado/atualizado, a branch branch_name é criada a partir de branch_base, install_cmd (se informado) é executado, e o output retorna workspace_path, branch, base_commit_sha (o commit exato de onde branch_base estava) e status "ready"
```

**AC ADR-002-AC-03**
```
Dado docker_compose_path informado e a subida dos serviços falhando (ex.: porta ocupada)
Quando o plugin tenta subir a infraestrutura
Então o plugin levanta TransientError, permitindo que o Retry Handler (ADR-001) reaplique a política de retry da etapa, em vez de marcar a etapa como falha permanente na primeira tentativa
```

---

## Componente: Plugin Claude Code Runner

### Atividade ADR-002-AT-02: Execução em modo coding

- **Descrição**: Invocar o Claude Code CLI headless, conectado via MCP à documentação
  Docusaurus, para implementar a história indicada seguindo o SDD instalado no
  repositório-alvo.
- **Depende de**: Plugin Workspace Setup (AT-01), Plugin Interface (ADR-001-AT-03)

**AC ADR-002-AC-04** (contrato de payload — modo coding)
```
Dado que a etapa é resolvida pelo Engine com params.modo = "coding"
params obrigatórios: modo ("coding"), mcp_config_path (string), historia_id (string)
workdir: NÃO é um param — o plugin lê de context.input["workspace_path"] (recebido via usa_output_anterior da etapa Workspace Setup)
output obrigatório: status ("success"|"failed"), summary (string), session_log_path (string), docs_referenced (lista de string, pode ser vazia), + carry-forward de todos os campos recebidos em context.input (nesta cadeia: workspace_path, branch, base_commit_sha)
```

**AC ADR-002-AC-05**
```
Dado context.input.workspace_path recebido da etapa Workspace Setup (via usa_output_anterior) e mcp_config_path apontando para a doc Docusaurus
Quando o plugin executa em modo coding
Então invoca o Claude Code CLI nesse diretório, com MCP conectado, implementando a história historia_id seguindo o SDD do repositório, e retorna session_log_path apontando para um arquivo com o transcript completo da sessão, docs_referenced com os ids de ADR/AC/PRD que o agente efetivamente consultou via MCP durante a sessão, e os campos de context.input repassados por carry-forward (para a etapa de revisão, 2 hops adiante, ainda saber em qual workspace_path rodar)
```

### Atividade ADR-002-AT-03: Execução em modo review

- **Descrição**: Invocar o Claude Code CLI em uma nova janela de contexto (sessão sem
  histórico da etapa de coding), aplicando uma skill de revisão sobre a PR gerada.
- **Depende de**: Plugin Git/PR (AT-05) — via carry-forward do Shell/Script Runner
  (AT-04), que repassa `pr_number`/`pr_url` sem consumi-los —, Plugin Interface
  (ADR-001-AT-03)

**AC ADR-002-AC-06** (contrato de payload — modo review)
```
Dado que a etapa é resolvida pelo Engine com params.modo = "review"
params obrigatórios: modo ("review"), mcp_config_path (string), skill (string), pr_number (int) ou pr_url (string)
workdir: NÃO é um param — o plugin lê de context.input["workspace_path"] (chegou por carry-forward através de Git/PR e Shell/Script Runner)
output obrigatório: status ("success"|"failed"), summary (string), session_log_path (string)
```

**AC ADR-002-AC-07**
```
Dado pr_number/pr_url recebidos via usa_output_anterior da etapa Shell/Script Runner (que os repassou por carry-forward a partir da etapa Git/PR, sem alterá-los) e skill = "code-review"
Quando o plugin executa em modo review
Então inicia uma sessão nova do Claude Code (sem reaproveitar o histórico/contexto da sessão de coding), aplica a skill indicada sobre a mudança da PR identificada por pr_number/pr_url, e retorna session_log_path com o transcript completo dessa sessão de revisão
```

**AC ADR-002-AC-08** (auditoria)
```
Dado que a execução do Claude Code Runner falha (em qualquer modo, TransientError ou falha permanente)
Quando o plugin propaga a falha ao Engine (contrato ADR-001: falha = exceção, sem output estruturado)
Então o transcript da sessão até o ponto da falha ainda existe em disco, em um caminho determinístico e derivável sem depender de output: <workspace_path>/.workflow-logs/<run_id>/<step_name>.log — a mensagem da exceção inclui esse caminho, e qualquer processo de auditoria pode localizá-lo sem precisar de um output que a etapa falha não produz
```

---

## Componente: Plugin Git/PR

### Atividade ADR-002-AT-05: Criação/atualização de PR com rastreabilidade obrigatória

- **Descrição**: Criar ou atualizar uma PR via `gh` CLI, populando título/corpo a partir
  de templates que devem referenciar explicitamente a história e os docs consultados.
  Posicionado na cadeia logo após a etapa de coding (não após o polling) para receber
  `docs_referenced` diretamente via `usa_output_anterior`, sem precisar de um segundo
  hop de carry-forward.
- **Depende de**: Claude Code Runner em modo coding (AT-02), Plugin Interface
  (ADR-001-AT-03)

**AC ADR-002-AC-12** (contrato de payload)
```
Dado que a etapa é resolvida pelo Engine
params obrigatórios: action ("create_pr"|"update_pr"), branch (string), base_branch (string), title_template (string), body_template (string), historia_id (string)
params opcionais: labels (lista de string)
params condicional: pr_number (int) — obrigatório quando action = "update_pr"; ignorado/ausente quando action = "create_pr"
output: pr_number (int), pr_url (string), status (string), + carry-forward de todos os campos recebidos em context.input (nesta cadeia: docs_referenced, summary da etapa de coding)
```

**AC ADR-002-AC-13**
```
Dado action = "create_pr", branch e base_branch válidos, e title_template/body_template renderizáveis
Quando o plugin executa
Então cria a PR via gh CLI com título e corpo renderizados, aplica labels (se informado), e retorna pr_number, pr_url, status e os campos de context.input repassados por carry-forward
```

**AC ADR-002-AC-14** (auditoria — validação obrigatória)
```
Dado que o body_template renderizado NÃO contém referência a historia_id (dos próprios params) ou a nenhum dos ids presentes em context.input.docs_referenced (recebido da etapa de coding)
Quando o plugin valida o corpo antes de criar a PR
Então o plugin falha de forma permanente (não retriable), sem abrir a PR, em vez de criar uma PR sem rastreabilidade da origem
```

**AC ADR-002-AC-15**
```
Dado action = "update_pr" e pr_number de uma PR já existente informado nos params
Quando o plugin executa
Então atualiza a PR existente (identificada por pr_number, título/corpo/labels) sem criar uma nova PR duplicada
```

---

## Componente: Plugin Shell/Script Runner

### Atividade ADR-002-AT-04: Execução de script local com suporte a timeout

- **Descrição**: Executar um script `.sh` ou `.bat` via subprocess (ex.: polling de
  status de CI/checks da PR já aberta pela etapa Git/PR), respeitando timeout
  configurável, e repassando por carry-forward `pr_number`/`pr_url` para a etapa de
  review seguinte.
- **Depende de**: Plugin Git/PR (AT-05), Plugin Interface (ADR-001-AT-03)

**AC ADR-002-AC-09** (contrato de payload)
```
Dado que a etapa é resolvida pelo Engine
params obrigatórios: script_path (string), interpreter ("bash"|"bat")
params opcionais: args (lista de string), timeout_seconds (int)
output: exit_code (int), stdout (string), stderr (string), + carry-forward de todos os campos recebidos em context.input (nesta cadeia: pr_number, pr_url, docs_referenced vindos da etapa Git/PR)
env: cada campo de context.input é exposto ao subprocess como variável de ambiente WORKFLOW_INPUT_<CHAVE_MAIUSCULA> (ex.: pr_number -> WORKFLOW_INPUT_PR_NUMBER)
```

**AC ADR-002-AC-10**
```
Dado um script_path válido e interpreter compatível com o sistema operacional
Quando o plugin executa
Então roda o script via subprocess com os args informados, aguarda finalização, e retorna exit_code, stdout e stderr capturados, junto com os campos de context.input repassados por carry-forward
```

**AC ADR-002-AC-11**
```
Dado timeout_seconds configurado e o script ainda em execução após esse tempo
Quando o plugin detecta o estouro do timeout
Então encerra o processo e levanta TransientError, permitindo retry pela política da etapa (ex.: polling que ainda não teve tempo de completar)
```

---

## Componente: Chain Loader (extensão da ADR-001)

### Atividade ADR-002-AT-07: Resolução de variáveis compartilhadas (`vars`)

- **Descrição**: Estender o parser do Chain Loader (ADR-001-AT-02) para aceitar um bloco
  opcional `vars:` no nível raiz da config, e interpolar `{{ vars.<chave> }}` dentro de
  valores string dos `params` de qualquer etapa antes de repassá-los ao Engine.
- **Depende de**: Chain Loader (ADR-001-AT-02)

**AC ADR-002-AC-18** (contrato de payload — extensão de config)
```
Dado um arquivo de config com um bloco vars (mapa de chave -> valor string) no nível raiz
Quando o Chain Loader processa o arquivo
Então toda ocorrência de {{ vars.<chave> }} dentro de um valor string em params de qualquer etapa é substituída pelo valor correspondente em vars, antes da etapa ser passada ao Engine
```

**AC ADR-002-AC-19**
```
Dado um arquivo de config sem o bloco vars
Quando o Chain Loader processa o arquivo
Então o comportamento é idêntico ao definido na ADR-001 (nenhuma interpolação ocorre) — extensão é retrocompatível com configs existentes
```

**AC ADR-002-AC-20**
```
Dado uma etapa cujo params referencia {{ vars.<chave> }} para uma chave ausente no bloco vars da config
Quando o Chain Loader processa o arquivo
Então a validação falha antes de qualquer etapa ser executada, com mensagem indicando qual chave de vars não foi encontrada (mesmo momento/comportamento da validação de plugin inexistente, ADR-001-AC-04)
```

---

## Componente: Logger (extensão da ADR-001)

### Atividade ADR-002-AT-06: Campos de correlação para auditoria ponta a ponta

- **Descrição**: Estender os eventos de log já emitidos pelo Logger (ADR-001-AT-09)
  para incluir um objeto `correlacao` com identificadores relevantes presentes na etapa,
  permitindo reconstruir o rastro doc → código → PR → review sem depender de migração
  de schema no State Store.
- **Depende de**: Logger (ADR-001-AT-09)

**AC ADR-002-AC-16** (contrato de payload — extensão de log)
```
Dado um evento de log de qualquer etapa (início, retry, fim)
Quando context.params ou o output daquela etapa contém algum de: historia_id, branch, pr_number, pr_url
Então o registro de log inclui esses campos sob a chave "correlacao", além dos campos já exigidos pela ADR-001 (run_id, step_name, evento, timestamp)
```

**AC ADR-002-AC-17**
```
Dado uma etapa cujo context.params/output não contém nenhum campo de correlação conhecido
Quando o evento é logado
Então o registro é emitido normalmente, sem a chave "correlacao" (não é obrigatória quando não há dado de correlação disponível)
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-002 | AT-01 | AC-01, AC-02, AC-03 | Plugin Workspace Setup | Pendente |
| RF-02 | ADR-002 | AT-02, AT-03 | AC-04 a AC-08 | Plugin Claude Code Runner | Pendente |
| RF-03 | ADR-002 | AT-04 | AC-09, AC-10, AC-11 | Plugin Shell/Script Runner | Pendente |
| RF-04 | ADR-002 | AT-05 | AC-12 a AC-15 | Plugin Git/PR | Pendente |
| RNF-01 | ADR-002 | AT-06 | AC-16, AC-17 | Logger | Pendente |
| RNF-02 | ADR-002 | AT-02, AT-03 | AC-04, AC-06, AC-08 | Plugin Claude Code Runner | Pendente |
| RNF-03 | ADR-002 | AT-01 | AC-01, AC-02 | Plugin Workspace Setup | Pendente |
| RNF-04 | ADR-002 | AT-05 | AC-14 | Plugin Git/PR | Pendente |
| RF-05 | ADR-002 | AT-07 | AC-18, AC-19, AC-20 | Chain Loader | Pendente |
| RNF-05 (herdado) | ADR-001 | — | — | (ver ADR-001) | N/A |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
