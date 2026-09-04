# Spec: Plugins de Prova de Conceito — Pipeline SDD Ponta a Ponta

**Feature ID:** 002-plugins-poc-pipeline-sdd
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-03

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

O motor de workflow (feature `001-motor-workflow-plugins`) está implementado e verificado, mas sem plugins reais — o diretório `./plugins/` está vazio. Precisamos de um conjunto mínimo de plugins concretos que provem o conceito ponta a ponta com um cenário real: uma documentação Docusaurus (convertida em servidor MCP) contendo PB, PRD, ADR, AC e Histórias; o workflow deve preparar o ambiente, implementar uma história seguindo o SDD do repositório-alvo via Claude Code, aguardar checks via polling, abrir/popular a PR, e disparar uma revisão via Claude Code em nova janela de contexto — com rastro auditável em cada etapa.

Origem: demanda informal elicitada via skill `issue-to-adr`, registrada em `adr/ADR-002-plugins-poc-pipeline-sdd.md` (depende de `adr/ADR-001-motor-workflow-plugins.md`).

## User Stories

- Como desenvolvedor, quero declarar uma história do backlog documentado (Docusaurus/MCP) numa config de workflow e ter o pipeline preparar o ambiente, implementar via Claude Code seguindo o SDD do repositório, abrir a PR e disparar uma revisão automática, para não repetir esse ciclo manualmente a cada história.
- Como responsável por auditar o pipeline, quero que cada etapa deixe rastro suficiente (transcript completo das sessões do Claude Code, correlação entre história/branch/PR nos logs, referência explícita no corpo da PR), para validar depois o que a IA de fato leu, decidiu e alterou — mesmo sem acompanhar a execução em tempo real.
- Como autor de uma config de workflow, quero declarar `historia_id`/`branch_name` uma única vez e reusar em várias etapas, para não arriscar inconsistência por duplicação manual do mesmo valor.

## Functional Requirements

- FR-1: O motor prepara um workspace local (repositório, branch e, opcionalmente, infraestrutura dockerizada) antes de qualquer etapa de codificação, via plugin.
- FR-2: O motor invoca o Claude Code CLI, via plugin, em dois modos — implementação de uma história seguindo o SDD do repositório-alvo, e revisão de uma PR em uma nova janela de contexto — ambos conectados via MCP à documentação do projeto.
- FR-3: O motor executa um script local (`.sh`/`.bat`), via plugin, tipicamente para aguardar checks de CI de uma PR.
- FR-4: O motor cria/atualiza uma Pull Request, via plugin, populando seus metadados a partir de templates que referenciam a origem da mudança.
- FR-5: A config declarativa da cadeia suporta um bloco de variáveis compartilhadas, resolvidas antes de cada etapa, para evitar duplicar o mesmo valor manualmente em múltiplas etapas.

## Non-Functional Requirements

- NFR-1: Todo evento de log relevante inclui campos de correlação (história, branch, PR) quando disponíveis, além dos já exigidos pela feature `001`.
- NFR-2: A execução do Claude Code (qualquer modo) deixa sempre um transcript completo em disco, mesmo quando a etapa falha.
- NFR-3: A preparação do workspace registra o commit exato de onde a branch base partiu, para permitir reconstruir o estado inicial de qualquer execução.
- NFR-4: Uma Pull Request só é criada se seu corpo referenciar explicitamente a história e os documentos consultados na etapa de implementação — nunca uma PR sem essa rastreabilidade.
- NFR-5 (herdado de `001`): uso local/individual, execução sequencial, sem concorrência multi-usuário.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-002-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given `repo_url`/`branch_base` válidos e nenhuma infraestrutura opcional declarada, when o plugin de preparação de ambiente executa, then o repositório é clonado/atualizado, a branch de trabalho é criada a partir da base, dependências são instaladas se configurado, e o workspace fica pronto. _(satisfies FR-1)_
- **AC-02** — Given os mesmos dados do AC-01, then o output inclui o caminho do workspace, a branch e o commit exato de onde a branch base partiu. _(satisfies FR-1, NFR-3)_
- **AC-03** — Given infraestrutura dockerizada opcional configurada e sua subida falhando, when o plugin tenta subir os serviços, then a falha é sinalizada como retriable (não interrompe a cadeia na primeira tentativa). _(satisfies FR-1)_
- **AC-04** — Given os parâmetros de uma etapa de implementação (modo coding), when o plugin do Claude Code executa, then ele invoca a CLI conectada via MCP à documentação, implementando a história seguindo o SDD do repositório. _(satisfies FR-2)_
- **AC-05** — Given a mesma execução do AC-04, then o output inclui um transcript completo da sessão e a lista de documentos efetivamente consultados via MCP. _(satisfies FR-2, NFR-2)_
- **AC-06** — Given os parâmetros de uma etapa de revisão (modo review) com a PR já aberta, when o plugin do Claude Code executa, then ele inicia uma sessão nova (sem histórico da etapa de implementação) e aplica uma skill de revisão sobre a mudança. _(satisfies FR-2)_
- **AC-07** — Given a mesma execução do AC-06, then o output inclui um transcript completo dessa sessão de revisão. _(satisfies FR-2, NFR-2)_
- **AC-08** — Given que a execução do Claude Code (qualquer modo) falha, when a falha é propagada, then o transcript parcial da sessão continua existindo em um caminho previsível, sem depender de um output que a etapa falha não produz. _(satisfies NFR-2)_
- **AC-09** — Given um script local válido, when o plugin de execução de script roda, then ele executa o script e retorna código de saída, stdout e stderr. _(satisfies FR-3)_
- **AC-10** — Given a mesma execução do AC-09 recebendo dados da etapa anterior (ex.: identificação da PR), then esses dados chegam ao script e também são preservados no output da etapa, para a etapa seguinte poder acessá-los. _(satisfies FR-3)_
- **AC-11** — Given um tempo limite configurado e o script ainda em execução após esse tempo, when o plugin detecta o estouro, then a falha é sinalizada como retriable. _(satisfies FR-3)_
- **AC-12** — Given os dados de uma PR a ser criada (branch, base, templates, história), when o plugin de PR executa, then a PR é criada com título/corpo renderizados e os metadados informados. _(satisfies FR-4)_
- **AC-13** — Given a mesma execução do AC-12, then o output preserva os dados recebidos da etapa anterior, além dos dados da PR criada, para a etapa seguinte da cadeia. _(satisfies FR-4)_
- **AC-14** — Given que o corpo renderizado da PR não referencia a história nem nenhum documento consultado na etapa de implementação, when o plugin valida antes de criar a PR, then a criação é recusada (falha não-retriable) — nunca é criada uma PR sem essa rastreabilidade. _(satisfies FR-4, NFR-4)_
- **AC-15** — Given uma PR já existente e uma atualização solicitada, when o plugin executa, then a PR existente é atualizada, sem criar uma duplicata. _(satisfies FR-4)_
- **AC-16** — Given um evento de log de qualquer etapa cujos dados incluam identificadores de correlação (história, branch, PR), when o evento é registrado, then esses identificadores aparecem no log, além dos campos já exigidos pela feature `001`. _(satisfies NFR-1)_
- **AC-17** — Given um evento de log sem nenhum identificador de correlação disponível, then o evento é registrado normalmente, sem exigir esses campos. _(satisfies NFR-1)_
- **AC-18** — Given uma config de workflow com um bloco de variáveis compartilhadas, when a config é processada, then toda referência a essas variáveis dentro dos parâmetros de qualquer etapa é resolvida antes de a etapa rodar. _(satisfies FR-5)_
- **AC-19** — Given uma config de workflow sem esse bloco de variáveis, then o comportamento é idêntico ao da feature `001` (retrocompatível). _(satisfies FR-5)_
- **AC-20** — Given uma etapa que referencia uma variável ausente do bloco compartilhado, when a config é validada, then a validação falha antes de qualquer etapa rodar, indicando qual variável não foi encontrada. _(satisfies FR-5)_

## Edge Cases

- Subida de infraestrutura opcional falha → retriable, não falha permanente na primeira tentativa (AC-03).
- Claude Code falha em qualquer modo → transcript parcial ainda existe em caminho previsível (AC-08).
- Tempo limite do script excedido → retriable, não falha permanente imediata (AC-11).
- Corpo de PR sem referência à história/documentos consultados → PR nunca é criada (AC-14).
- Config referenciando variável compartilhada inexistente → falha de validação antes de qualquer etapa rodar (AC-20).
- Servidor MCP de projeto auto-descoberto não fica disponível em execução não-interativa (achado operacional, não uma AC formal) → o design nunca depende de descoberta automática de MCP, sempre aponta explicitamente para a documentação a usar.

## Out of Scope (Non-Goals)

- Plugin genérico de chamada HTTP/REST arbitrária.
- Plugin dedicado só para infraestrutura Docker (capacidade absorvida no plugin de preparação de ambiente).
- Seleção automática da próxima história pendente — a história de cada execução é declarada explicitamente.
- Loop automático entre histórias dentro de uma única execução da cadeia.

## Open Questions

Nenhuma pendente e bloqueante. Assunção registrada (não bloqueante): seleção automática da "próxima história pendente" fica fora de escopo — ver `adr/ADR-002-plugins-poc-pipeline-sdd.md`, seção Contexto.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-03 | Quais ferramentas externas os plugins de POC devem invocar? | Claude Code CLI, shell genérico, HTTP/REST, Git, MCP, infra Docker local |
| 2026-09-03 | Existe um cenário concreto pra validar ponta a ponta? | Sim — pipeline SDD: MCP → coding → polling → PR → review |
| 2026-09-03 | Quantos plugins fazem sentido para o POC? | Moderado (3-4), decidido como 4 após reconciliar com o cenário |
| 2026-09-03 | MCP precisa de plugin dedicado de busca de contexto? | Não — Claude Code CLI já suporta MCP nativamente (`--mcp-config`); eliminado como plugin separado |
| 2026-09-03 | Infraestrutura Docker precisa de plugin dedicado? | Não — absorvida como capacidade opcional do plugin de preparação de ambiente |
| 2026-09-03 | Requisito de auditabilidade? | Levantado explicitamente pelo usuário como transversal — motivou `session_log_path` obrigatório, correlação no Logger, `base_commit_sha`, e validação obrigatória no corpo da PR |
| 2026-09-03 | Como resolver falha do Claude Code sem output estruturado (contrato: falha = exceção)? | Convenção de caminho determinístico para o transcript, derivável sem depender de output |
| 2026-09-03 | Como o Git/PR recebe dados de duas etapas atrás (docs consultados)? | Convenção de carry-forward — cada plugin intermediário inclui o próprio `input` no seu `output`; cadeia reordenada (PR logo após coding) para minimizar hops |
| 2026-09-03 | `historia_id` implícito no template ou explícito? | Formalizado como `param` explícito do plugin de PR |
| 2026-09-03 | Flags reais da CLI do Claude Code para MCP/modo headless? | Verificado contra `claude --version` (2.1.260): `-p`, `--mcp-config`, `--strict-mcp-config`, `--output-format json`, `--json-schema`, `--permission-mode`, `--permission-prompts none`; achado: `.mcp.json` de projeto auto-descoberto fica "Pending approval" em modo não-interativo |
| 2026-09-03 | Como o script de polling acessa dados da etapa anterior (ex. número da PR)? | Campos de `context.input` expostos como variáveis de ambiente `WORKFLOW_INPUT_*` |
| 2026-09-03 | Duplicação manual de `historia_id`/`branch_name` entre etapas é aceitável? | Não — Chain Loader estendido com bloco `vars:` e interpolação `{{ vars.<chave> }}`, retrocompatível |
