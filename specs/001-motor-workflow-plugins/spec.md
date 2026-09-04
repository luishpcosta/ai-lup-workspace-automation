# Spec: Motor de Workflow com Plugins Python

**Feature ID:** 001-motor-workflow-plugins
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-08-31

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

Hoje, orquestrar uma sequência de chamadas a ferramentas locais (como o Claude Code) exige escrever um script imperativo novo a cada combinação de etapas. Precisamos de um motor de workflow reutilizável, para uso local, que execute uma cadeia configurável de etapas — no conceito de "chain" (semelhante ao LangChain) — e que qualquer pessoa possa estender com uma nova ferramenta via plugin Python, sem alterar o núcleo do motor.

Origem: demanda informal elicitada via skill `issue-to-adr`, registrada em `adr/ADR-001-motor-workflow-plugins.md`.

## User Stories

- Como desenvolvedor que usa ferramentas de linha de comando localmente, quero declarar uma cadeia de etapas em um arquivo de configuração, para automatizar um fluxo de trabalho sem escrever código de orquestração toda vez.
- Como autor de uma nova integração, quero adicionar um plugin Python seguindo um contrato simples, para que o motor o reconheça sem precisar alterar o núcleo do motor.
- Como usuário de um workflow que falhou no meio, quero retomar a execução a partir da etapa que falhou, para não reprocessar etapas já concluídas.

## Functional Requirements

- FR-1: O motor executa workflows definidos declarativamente (arquivo de configuração) como uma cadeia ordenada de etapas.
- FR-2: Cada etapa da cadeia invoca uma ferramenta externa (ex.: Claude Code) por meio de um plugin Python.
- FR-3: O motor descobre plugins automaticamente ao varrer um diretório de plugins local.
- FR-4: O motor persiste o progresso da execução e permite retomar a partir da etapa que falhou, sem repetir etapas já concluídas.
- FR-5: O motor aplica retry automático, configurável por etapa/plugin, em falhas transitórias.
- FR-6: O motor emite logs estruturados em JSON para os eventos de execução.
- FR-7: O output de uma etapa pode, opcionalmente, alimentar o input da etapa seguinte.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-001-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given um arquivo de config válido e nenhuma execução incompleta anterior, when o usuário roda o comando de execução, then uma nova execução é criada e a cadeia é executada do início. _(satisfies FR-1, FR-4)_
- **AC-02** — Given uma execução anterior com status "failed" para o mesmo workflow, when o usuário roda o comando de execução novamente, then a execução retoma a partir da primeira etapa não concluída, sem repetir as já concluídas. _(satisfies FR-4)_
- **AC-03** — Given um arquivo de config com uma lista de etapas referenciando plugins existentes, when o motor processa o arquivo, then retorna uma cadeia ordenada com plugin, params e a flag `usa_output_anterior` (default false). _(satisfies FR-1)_
- **AC-04** — Given um arquivo de config referenciando um plugin inexistente, when o motor valida o arquivo, then a validação falha antes de qualquer etapa rodar, indicando qual plugin não foi encontrado. _(satisfies FR-1, FR-3)_
- **AC-05** — Given que o motor chama um plugin para executar uma etapa, when a chamada ocorre, then o plugin recebe `input`/`params`/`run_id`/`step_name` e retorna um output serializável em JSON; falhas retriable são sinalizadas por uma exceção própria (`TransientError`), qualquer outra exceção é falha permanente. _(satisfies FR-2, FR-5)_
- **AC-06** — Given um diretório de plugins com um módulo válido, when o motor inicializa, then o plugin fica disponível para uso pelo nome declarado na config. _(satisfies FR-3)_
- **AC-07** — Given um módulo no diretório de plugins que não implementa o contrato esperado, when o motor inicializa, then o módulo é rejeitado com erro claro, sem impedir o carregamento dos demais plugins válidos. _(satisfies FR-3)_
- **AC-08** — Given uma cadeia onde uma etapa declara `usa_output_anterior: true`, when essa etapa executa, then seu input é igual ao output da etapa anterior. _(satisfies FR-7)_
- **AC-09** — Given uma etapa que não declara `usa_output_anterior` (ou declara false), when essa etapa executa, then seu input é vazio, independentemente do output da etapa anterior. _(satisfies FR-7)_
- **AC-10** — Given que uma etapa termina com sucesso, when o motor segue para a próxima etapa, then o progresso já está persistido como concluído antes de a próxima etapa começar. _(satisfies FR-4)_
- **AC-11** — Given que uma etapa falha permanentemente, when o motor trata essa falha, then a execução é interrompida e nenhuma etapa seguinte roda. _(satisfies FR-4)_
- **AC-12** — Given uma etapa com política de retry de N tentativas, when o plugin falha transitoriamente e tem sucesso dentro do limite, then o resultado bem-sucedido é usado, sem propagar as falhas anteriores como erro final. _(satisfies FR-5)_
- **AC-13** — Given uma etapa com política de retry esgotada, when todas as tentativas falham transitoriamente, then a falha é propagada como falha permanente. _(satisfies FR-5)_
- **AC-14** — Given o schema de persistência, when uma execução e suas etapas são registradas, then os dados ficam disponíveis nas tabelas `workflow_runs` e `step_executions` com os campos definidos em `plan.md`. _(satisfies FR-4)_
- **AC-15** — Given uma execução em andamento, when qualquer evento de início/retry/fim de etapa ocorre, then um registro estruturado em JSON é emitido com, no mínimo: identificador da execução, nome da etapa, tipo de evento e timestamp. _(satisfies FR-6)_

## Edge Cases

- Config referenciando plugin inexistente → falha na validação, antes de executar qualquer etapa (AC-04).
- Reinício do processo no meio de uma execução → o estado persistido permite retomar de onde parou (AC-02, AC-10).
- Retry esgotado → falha permanente, sem loop infinito de tentativas (AC-13).
- Plugin mal formado no diretório de plugins → não impede o carregamento dos demais plugins válidos (AC-07).

## Out of Scope (Non-Goals)

- Execução paralela/assíncrona entre etapas da cadeia (pode virar uma feature futura, sem quebrar o contrato de plugin).
- Publicação do motor como pacote distribuído (PyPI ou índice privado).
- Suporte a múltiplos usuários concorrentes, execução remota ou servidor.

## Open Questions

Nenhuma pendente e bloqueante. Assunção registrada (não bloqueante): volume/escala assumido como uso individual e baixo — ver `adr/ADR-001-motor-workflow-plugins.md`, seção Contexto.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-08-30 | Execução síncrona ou assíncrona entre etapas? | Sequencial/síncrona nesta primeira versão |
| 2026-08-30 | Retomar do zero ou do ponto de falha? | Retomar do ponto de falha, via estado persistido |
| 2026-08-30 | Como plugins são descobertos? | Varredura de diretório de plugins local |
| 2026-08-30 | Como distribuir o motor? | Uso interno via clone do repositório, sem publicação |
| 2026-08-30 | Política de retry fixa ou configurável? | Configurável por etapa/plugin |
| 2026-08-30 | Logging estruturado ou texto simples? | Estruturado em JSON |
| 2026-08-31 | Como definir a cadeia (código vs. config)? | Config declarativa referenciando plugins Python |
| 2026-08-31 | Output de uma etapa alimenta a próxima? | Opcional, configurável por etapa |
| 2026-08-31 | Como sinalizar erro transitório vs. permanente? | Exceção tipada `TransientError` |
| 2026-08-31 | Assinatura do método de plugin? | `run(context) -> output` |
