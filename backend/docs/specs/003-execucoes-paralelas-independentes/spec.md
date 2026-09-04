# Spec: Execuções Paralelas Independentes (run-many)

**Feature ID:** 003-execucoes-paralelas-independentes
**Phase:** Tasks
**Owner:** <who>
**Last updated:** 2026-09-04

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

O motor (feature `001`) roda uma cadeia por vez. Quando o usuário tem várias histórias que sabe de antemão serem independentes (repositórios/microsserviços diferentes, sem interseção), rodar uma de cada vez desperdiça tempo sem necessidade — não há razão pra serializar trabalho que não compete por nenhum recurso comum.

Origem: demanda informal elicitada via skill `issue-to-adr`, registrada em `adr/ADR-003-execucoes-paralelas-independentes.md` (depende de `adr/ADR-001-motor-workflow-plugins.md`).

## User Stories

- Como usuário com várias histórias independentes prontas (ex.: uma por microsserviço), quero disparar todas de uma vez e deixar um teto controlar quantas rodam ao mesmo tempo, para não esperar uma terminar antes de começar a próxima sem necessidade.
- Como usuário rodando um lote, quero que a falha de uma história não derrube as outras, para não perder o progresso das que são independentes dela.
- Como usuário auditando depois, quero que cada história do lote tenha seu próprio rastro persistido (SQLite), para não ter uma única fonte de verdade compartilhada onde escritas concorrentes poderiam se atropelar.

## Functional Requirements

- FR-1: Um novo comando recebe uma lista de configs de cadeia e um teto de concorrência, e dispara essas execuções respeitando o teto.
- FR-2: Cada execução do lote persiste seu progresso num State Store isolado (não compartilhado com as demais execuções do lote).
- FR-3: A falha de uma execução do lote não interrompe as demais.
- FR-4: O comando bloqueia até todas as execuções do lote terminarem e reporta um resumo final por execução.

## Non-Functional Requirements

- NFR-1: Nenhuma detecção automática de conflito entre execuções do lote — o usuário é responsável por só agrupar histórias que sabe serem independentes.
- NFR-2: O teto de concorrência é configurável (não "sem limite").
- NFR-3 (herdado de `001`): cada execução individual dentro do lote continua sequencial internamente.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-003-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given N configs de cadeia válidos com nomes distintos, when o comando de lote é invocado, then todos são validados antes de qualquer execução começar. _(satisfies FR-1)_
- **AC-02** — Given dois configs do lote com o mesmo nome de cadeia, when o lote é validado, then a validação falha antes de disparar qualquer execução, indicando os configs em colisão. _(satisfies FR-1)_
- **AC-03** — Given um config inválido misturado com configs válidos, when o lote é validado, then os válidos disparam normalmente e o inválido aparece como falha imediata no resumo, sem consumir uma vaga do teto. _(satisfies FR-1, FR-4)_
- **AC-04** — Given um teto de concorrência N e mais de N configs válidos, when o lote executa, then no máximo N execuções rodam simultaneamente por vez. _(satisfies FR-1, NFR-2)_
- **AC-05** — Given execuções de histórias independentes rodando em paralelo, when elas chamam o mesmo plugin, then cada chamada usa o contexto da sua própria execução, sem estado cruzado entre elas. _(satisfies FR-1)_
- **AC-06** — Given uma execução do lote para uma cadeia nomeada X, when ela roda, then seu progresso é persistido isolado das demais execuções do lote. _(satisfies FR-2)_
- **AC-07** — Given uma execução do lote com progresso incompleto de uma rodada anterior, when o lote roda de novo com o mesmo config, then essa execução retoma da etapa que falhou, sem repetir as concluídas. _(satisfies FR-2)_
- **AC-08** — Given que todas as execuções do lote terminam, when o comando finaliza, then um resumo por execução (nome, identificador, status, motivo se falhou) é impresso. _(satisfies FR-4)_
- **AC-09** — Given que pelo menos uma execução falhou, when o comando termina, then o código de saída é diferente de zero; given que todas completaram, then o código de saída é zero. _(satisfies FR-4)_
- **AC-10** — Given que uma execução do lote falha enquanto outras estão em andamento, when a falha ocorre, then as demais continuam normalmente até seu próprio fim. _(satisfies FR-3)_

## Edge Cases

- Dois configs do mesmo lote com o mesmo nome de cadeia → falha de validação antes de qualquer execução (AC-02).
- Config inválido dentro de um lote majoritariamente válido → não bloqueia os demais (AC-03).
- Teto de concorrência maior que o número de configs → todos rodam de uma vez, sem fila (comportamento natural do pool, sem AC dedicada).
- Uma execução falha enquanto outras seguem rodando → sem cancelamento cruzado (AC-10).
- Execução retomada isoladamente fora do comando de lote (`workflow run` direto no `.db` daquela história) → mesma semântica de retomada da `001`, sem tratamento especial.

## Out of Scope (Non-Goals)

- Detecção automática de conflito entre execuções do lote (locking, análise de dependência).
- Execução distribuída/multi-máquina — tudo roda localmente, no mesmo processo pai.
- Parar o lote inteiro quando uma execução falha (`--fail-fast` no nível do lote).
- Retomada do "lote como um todo" como conceito próprio — só execuções individuais são retomáveis.
- Dashboard/UI — o resumo é texto de terminal.
- Qualquer relação com paralelismo de *etapas* dentro de uma cadeia (isso continua fora de escopo, herdado da `001`).

## Open Questions

Nenhuma pendente e bloqueante. Assunções registradas (não bloqueantes): volume esperado é "algumas" execuções simultâneas (teto pequeno, 2-5), não dezenas; nenhuma proteção contra rate-limit de ferramentas externas (Claude, GitHub) além do teto de concorrência — ver `adr/ADR-003-execucoes-paralelas-independentes.md`, seção Contexto e Consequências.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-04 | Isso é paralelismo de etapas dentro de uma cadeia, ou de execuções inteiras? | Execuções inteiras e independentes — etapas dentro de uma cadeia continuam sequenciais (herdado da 001) |
| 2026-09-04 | Como disparar as execuções paralelas? | Novo comando em lote (recebe vários configs de uma vez), não múltiplos processos manuais do usuário |
| 2026-09-04 | Quantas execuções simultâneas? | Teto pequeno e configurável (ex. 2-5), não ilimitado |
| 2026-09-04 | Detecção automática de conflito entre histórias do lote? | Não — fora de escopo, responsabilidade do usuário |
| 2026-09-04 | State Store compartilhado ou isolado por execução? | Isolado — um arquivo SQLite por execução do lote, evita contenção de escrita concorrente |
