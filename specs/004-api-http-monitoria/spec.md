# Spec: API HTTP e Monitoria de Workflows (workflow serve)

**Feature ID:** 004-api-http-monitoria
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-04

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

Até aqui, a única porta de entrada do motor é o CLI (`workflow run`/`run-many`, features `001`/`003`). O usuário quer outras portas de entrada — HTTP — para disparar e monitorar execuções, sem perder o CLI. A monitoria precisa enxergar execuções independentemente de terem sido disparadas pelo terminal ou pela API.

Origem: demanda informal elicitada via skill `issue-to-adr`, registrada em `adr/ADR-004-api-http-monitoria.md` (depende de `adr/ADR-001-motor-workflow-plugins.md` e `adr/ADR-003-execucoes-paralelas-independentes.md`).

## User Stories

- Como usuário que só tinha o terminal, quero disparar uma execução via HTTP (`POST /runs`) e receber uma resposta imediata, para poder integrar o motor com outras ferramentas sem depender de um processo de terminal aberto.
- Como usuário monitorando o sistema, quero listar e ver o detalhe de qualquer execução conhecida — disparada pelo terminal ou pela API — para não precisar saber de antemão por onde ela foi iniciada.
- Como usuário que disparou uma execução por engano, quero poder cancelá-la antes que comece a rodar, mesmo sabendo que uma etapa já em andamento não pode ser interrompida nesta versão.

## Functional Requirements

- FR-1: Um novo comando sobe um servidor HTTP, sem substituir os comandos de CLI existentes.
- FR-2: Um endpoint dispara uma execução de forma assíncrona — responde imediatamente, sem esperar a execução terminar.
- FR-3: Um endpoint lista execuções conhecidas, agregando todas as fontes de um diretório observado — inclui execuções disparadas pelo terminal, desde que apontem para esse mesmo diretório.
- FR-4: Um endpoint mostra o detalhe de uma execução (status por etapa, timestamps, erro se houver).
- FR-5: Um endpoint cancela uma execução ainda não iniciada (na fila) — para uma etapa já em andamento, informa que não é suportado em vez de simular um cancelamento.

## Non-Functional Requirements

- NFR-1 (herdado de `001`): uso local/individual — sem autenticação/multi-tenant nesta versão.
- NFR-2: contrato de erro HTTP uniforme em todos os endpoints.
- NFR-3: disparo duplicado concorrente do mesmo identificador de execução é rejeitado, não uma corrida silenciosa no State Store.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-004-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given o novo comando é invocado, when o servidor sobe, then os comandos de CLI existentes continuam funcionando de forma totalmente independente. _(satisfies FR-1)_
- **AC-02** — Given uma requisição de disparo com config válido, when processada, then responde imediatamente com um identificador de execução e status "iniciado", antes de a execução terminar. _(satisfies FR-2)_
- **AC-03** — Given um config inválido ou inexistente, when a requisição de disparo é processada, then responde com erro de validação, sem disparar nada. _(satisfies FR-2, NFR-2)_
- **AC-04** — Given uma execução já em andamento para um identificador, when uma segunda requisição de disparo resolve para o mesmo identificador, then responde com conflito, sem chamar o motor uma segunda vez sobre o mesmo estado. _(satisfies FR-2, NFR-3)_
- **AC-05** — Given arquivos de estado criados por fontes diferentes (servidor, lote, terminal) no mesmo diretório observado, when a listagem é consultada, then todos aparecem, independente de quem os criou. _(satisfies FR-3)_
- **AC-06** — Given uma execução existente, when o detalhe é consultado sem pedir dados extras, then retorna status por etapa sem os campos de payload grandes; pedindo os dados extras, então eles aparecem. _(satisfies FR-4)_
- **AC-07** — Given uma execução desconhecida, when o detalhe é consultado, then responde com erro de não encontrado. _(satisfies FR-4, NFR-2)_
- **AC-08** — Given uma execução disparada pelo servidor cuja etapa atual ainda não começou a rodar, when o cancelamento é solicitado, then a execução é cancelada de verdade antes de qualquer etapa rodar. _(satisfies FR-5)_
- **AC-09** — Given uma execução disparada pelo servidor cuja etapa atual já está em execução, when o cancelamento é solicitado, then responde informando que não é suportado, sem tentar matar nada nem marcar falha. _(satisfies FR-5)_
- **AC-09b** — Given uma execução que não foi disparada pelo servidor (ex.: pelo terminal), when o cancelamento é solicitado através do servidor, then responde recusando de forma explícita. _(satisfies FR-5)_
- **AC-10** — Given uma execução desconhecida, when o cancelamento é solicitado, then responde com erro de não encontrado. _(satisfies FR-5, NFR-2)_

## Edge Cases

- Dois disparos concorrentes para o mesmo identificador de execução → o segundo é rejeitado, não uma corrida no SQLite (AC-04).
- Execução disparada pelo terminal aparecendo na listagem/detalhe da API, mas não cancelável por ela (AC-05, AC-09b).
- Cancelamento pedido depois que a etapa já começou a rodar → resposta honesta de "não suportado", nunca uma falsa confirmação (AC-09).

## Out of Scope (Non-Goals)

- Autenticação/autorização (herdado de NFR-1 — uso local/individual).
- Cancelamento de uma etapa já em execução (limitação técnica real: plugins não expõem hoje o processo externo para quem os chama — ver ADR-004, Consequências).
- Streaming ao vivo da sessão do agente e interação em tempo real — cobertos pela feature `005` (depende desta).
- Paginação da listagem de execuções.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-04 | API síncrona ou assíncrona? | Assíncrona — dispara e retorna na hora |
| 2026-09-04 | Interação em tempo real com o agente entra nesta feature? | Não — feature separada (`005`), dependente desta |
| 2026-09-04 | Monitoria só vê o que a própria API disparou? | Não — precisa enxergar execuções do terminal também (requisito explícito do usuário) |
| 2026-09-04 | Cancelamento de etapa já em execução é viável agora? | Não — descoberto ao desenhar a implementação (plugins não expõem o processo externo); escopo revisado para só cancelar o que ainda está na fila |
