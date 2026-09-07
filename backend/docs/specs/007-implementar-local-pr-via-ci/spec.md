# Spec: Implementar em Repositório Local, PR via CI do Repositório-Alvo

**Feature ID:** 007-implementar-local-pr-via-ci
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-06

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

O único workflow que hoje implementa código de verdade (`implementar-historia-sdd`,
feature `002`) exige uma URL de repositório git para clonar do zero, e abre a PR ele
mesmo. Um repositório local já existente e já instrumentado com seu próprio harness SDD
e seu próprio fluxo de Git (branch/push/CI) não tem como ser usado por esse workflow —
o usuário só consegue *investigar* (feature `006`, modo `investigar`, sem escrever
código) contra um repositório local, nunca implementar.

Origem: demanda informal elicitada diretamente em conversa, registrada em
`adr/ADR-008-implementar-local-pr-via-ci-repo-alvo.md` (depende de
`adr/ADR-002-plugins-poc-pipeline-sdd.md`, `adr/ADR-005-stream-interacao-agente.md`,
`adr/ADR-007-templates-workflow-execucao-adhoc.md`).

## User Stories

- Como usuário com um repositório local já clonado e já instrumentado com seu próprio
  fluxo de Git (ex.: branch `feature/*` + CI que abre PR sozinha), quero pedir uma
  implementação contra esse repositório sem que o motor clone de novo nem decida o
  nome da branch por mim.
- Como usuário do mesmo cenário, quero que a PR seja aberta pela própria CI do
  repositório-alvo — não quero que o motor abra a PR ele mesmo, para não duplicar ou
  conflitar com a instrumentação que já existe lá.
- Como usuário que disparou essa implementação, quero saber com confiança se a PR
  realmente abriu (não só confiar no relato do agente) antes de considerar a execução
  concluída.

## Functional Requirements

- FR-1: Existe um workflow selecionável que implementa uma mudança contra um
  repositório local já existente, sem clonar e sem que o motor crie a branch — quem
  decide/cria a branch é o próprio repositório-alvo, seguindo sua própria instrumentação.
- FR-2: Esse workflow não abre a PR ele mesmo — depois que a implementação é enviada
  (push), a execução confirma que uma PR foi aberta por outra via (a CI do
  repositório-alvo) antes de considerar essa etapa concluída.
- FR-3: Se a PR não aparecer depois de um tempo de espera limitado, a execução falha de
  forma visível — não fica travada indefinidamente, e não é marcada como concluída sem
  a PR confirmada.
- FR-4: O restante do fluxo de disparo (escolher esse workflow, escolher o repositório
  local, descrever o que implementar, escolher documentos de referência) usa exatamente
  o mecanismo de seleção por template já existente (feature `006`) — nenhuma peça nova
  de descoberta/formulário é necessária.

## Non-Functional Requirements

- NFR-1 (herdado de `001`/`002`): o contrato externo dos plugins existentes (parâmetros/
  saída, sinalização de erro retriable) não muda para os modos/ações já existentes.
- NFR-2: o mecanismo de monitoria/stream/instruções/cancelamento já existente (feature
  `004`/`005`) funciona para este workflow sem nenhuma mudança nele.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-008-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given um repositório local já existente informado como parâmetro do workflow, when a etapa de implementação roda, then nenhum clone acontece e o agente opera diretamente nesse repositório. _(satisfies FR-1)_
- **AC-02** — Given o mesmo cenário do AC-01, when o parâmetro do repositório não é informado, then a etapa falha antes de qualquer chamada externa, com um erro claro. _(satisfies FR-1)_
- **AC-03** — Given a etapa de implementação concluída com sucesso, when o agente reporta o resultado, then o nome da branch para a qual ele deu push está disponível para a etapa seguinte. _(satisfies FR-1, FR-2)_
- **AC-04** (regressão) — Given os modos de execução do agente já existentes (implementação com preparação prévia, revisão, investigação), when a suíte de testes roda após esta feature, then nenhum deles muda de comportamento. _(satisfies NFR-1)_
- **AC-05** — Given a branch reportada pela etapa de implementação, when a etapa de confirmação roda e encontra uma PR aberta para essa branch, then a execução considera essa etapa concluída com sucesso, sem ter aberto a PR ela mesma. _(satisfies FR-2)_
- **AC-06** — Given o mesmo cenário do AC-05, when nenhuma PR é encontrada ainda, then a etapa é tratada como temporariamente incompleta (retriable), não como falha definitiva na primeira verificação. _(satisfies FR-3)_
- **AC-07** — Given o mesmo cenário do AC-05, when a branch esperada não está disponível para a etapa de confirmação, then falha de forma permanente e clara, sem tentar verificar nada. _(satisfies FR-2)_
- **AC-08** — Given repetidas tentativas de confirmação sem sucesso, when o limite de tentativas é atingido, then a execução é marcada como falha, visível como qualquer outra falha de etapa. _(satisfies FR-3)_
- **AC-09** (regressão) — Given as ações de abrir/atualizar PR já existentes, when a suíte de testes roda após esta feature, then nenhuma delas muda de comportamento. _(satisfies NFR-1)_
- **AC-10** — Given o workflow novo declarado no mecanismo de templates já existente, when a listagem de workflows é consultada, then ele aparece com um parâmetro de repositório local, um parâmetro de texto livre para o que implementar, e um parâmetro opcional de documentos de referência. _(satisfies FR-4)_
- **AC-11** — Given o workflow novo disparado de ponta a ponta contra um repositório-alvo real e instrumentado, when a execução roda até o fim, then o repositório-alvo recebe uma branch nova com a mudança, e a execução só é considerada concluída depois que a PR correspondente é confirmada. _(satisfies FR-1, FR-2, FR-3 — verificação manual, não automatizável em CI deste monorepo)_
- **AC-12** (regressão) — Given os workflows existentes (`investigar-impacto`, `implementar-historia-sdd`), when a listagem de workflows é consultada após esta feature, then continuam aparecendo exatamente como antes. _(satisfies NFR-1)_

## Edge Cases

- Repositório local não informado → falha antes de qualquer chamada externa (AC-02).
- Branch não disponível para a etapa de confirmação → falha permanente imediata, sem tentativa (AC-07).
- PR nunca aparece dentro do limite de tentativas → falha visível, não travamento silencioso (AC-08).
- Agente reporta um nome de branch que não corresponde ao que de fato recebeu push → a confirmação procura a branch errada e esgota as tentativas sem achar PR, mesmo que uma PR real tenha aberto (limitação conhecida, ver ADR-008, Consequências — sem validação cruzada nesta versão).

## Out of Scope (Non-Goals)

- Qualquer mudança no workflow `implementar-historia-sdd` existente (clone + branch pelo motor + PR pelo motor) — continua existindo, intocado, para quem precisa desse fluxo.
- Qualquer mudança no frontend — o mecanismo de seleção por template (feature `006`) já cobre um workflow novo sem alteração de código.
- Validar que o nome de branch reportado pelo agente corresponde de fato à branch que recebeu push (edge case conhecido, não coberto nesta versão).
- Qualquer mudança nos mecanismos de monitoria/stream/instruções/cancelamento já existentes.

## Open Questions

Nenhuma pendente e bloqueante. O tempo de espera para a etapa de confirmação (quantas tentativas, com que intervalo) é uma assunção registrada em `adr/ADR-008-implementar-local-pr-via-ci-repo-alvo.md` (Contexto), ajustável sem mudança de código, não validada contra uma CI real mais lenta que a do repositório-alvo de referência.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-06 | O workflow deve oferecer variantes (com/sem PR, PR pelo motor com checks/review completos)? | Não — uma única opção: implementação local + PR confirmada via CI do próprio repositório-alvo |
| 2026-09-06 | Como confirmar que a PR realmente abriu? | Verificação ativa (polling) com limite de tentativas — não uma checagem única, não apenas o relato do agente |
