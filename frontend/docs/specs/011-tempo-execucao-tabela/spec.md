# Spec: Tempo de execução na tabela de execuções

**Feature ID:** 011-tempo-execucao-tabela
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-07

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

Usuário perguntou se já seria possível trazer o "tempo de execução" de cada workflow
para a tabela de execuções do painel, a partir do dado que já existe na base — sem
pedir nova instrumentação. Registrado em
`adr/ADR-012-tempo-execucao-tabela.md`: a resposta é sim, os timestamps de início/fim
já são persistidos e lidos pela API hoje, só nunca foram subtraídos nem expostos como
duração.

## User Stories

- Como usuário olhando a tabela de execuções, quero ver quanto tempo cada execução
  levou (ou está levando) sem precisar abrir o detalhe ou fazer conta manual com os
  timestamps.
- Como usuário acompanhando uma execução em andamento, quero ver esse tempo crescer
  sozinho enquanto a execução avança, do mesmo jeito que o resto da tabela já
  atualiza sozinha.

## Functional Requirements

- FR-1: A tabela de execuções mostra, por execução, o tempo total gasto (duração).
- FR-2: Para uma execução em andamento, a duração mostrada reflete o tempo decorrido
  até agora, e aumenta enquanto a tela atualiza sozinha (reaproveitando o
  comportamento já existente da ADR-011).
- FR-3: Para uma execução terminada (concluída ou com falha), a duração mostrada é
  fixa: o tempo total do início ao fim.

## Non-Functional Requirements

- NFR-1: sem nova instrumentação, coluna de armazenamento ou evento — usa somente os
  timestamps (`created_at`/`updated_at`) já persistidos e já lidos pela API hoje.
- NFR-2: a mudança de contrato do backend (`duration_seconds`) é aditiva e
  retrocompatível — um cliente que ignora campos desconhecidos não é afetado.
- NFR-3: sem novo mecanismo de atualização automática — reaproveita o polling já
  existente do painel (ADR-011), sem endpoint/timer novo.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-012-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given a listagem de execuções, then cada item traz um campo aditivo de
  duração, sem remover nenhum campo existente. _(FR-1, NFR-1, NFR-2)_
- **AC-02** — Given o detalhe de uma execução, then a resposta traz o mesmo campo
  aditivo de duração, sem remover nenhum campo existente. _(FR-1, NFR-1, NFR-2)_
- **AC-03** — Given uma execução já terminada, when a duração é consultada mais de
  uma vez, then o valor é sempre o mesmo (fixo, correspondente ao tempo total gasto).
  _(FR-3)_
- **AC-04** — Given uma execução em andamento, when a duração é consultada mais de
  uma vez com um intervalo real entre as consultas, then o valor nunca diminui.
  _(FR-2)_
- **AC-05** — Given uma execução com timestamp de início ausente ou corrompido, when
  a duração é consultada, then a resposta continua bem-sucedida, só sem um valor de
  duração para essa execução (nenhum erro). _(NFR-1)_
- **AC-06** — Given a tabela de execuções, then uma coluna de duração aparece entre
  "Status" e "Atualizado", com o tempo formatado de forma compacta e legível. _(FR-1)_
- **AC-07** — Given uma execução em andamento visível na tabela, when a atualização
  automática já existente traz uma nova resposta, then o valor de duração exibido
  aumenta, sem exigir clique em "Atualizar". _(FR-2, NFR-3)_

## Edge Cases

- Execução com timestamp de início ausente/corrompido (ex.: `.db` de uma versão muito
  antiga ou editado manualmente) — duração aparece como indisponível, sem quebrar o
  resto da linha/tabela (AC-05).
- Execução cancelada — tratada como status terminal para fins de duração (valor
  fixo), mesmo raciocínio de "completed"/"failed".

## Out of Scope (Non-Goals)

- Duração por etapa na tela de detalhe (`RunDetail`) — o dado (`started_at`/
  `finished_at` por step) já é exposto pela API hoje, mas exibir isso na UI de
  detalhe é uma extensão futura, fora deste pedido (que foi especificamente sobre "a
  tabela").
- Qualquer novo mecanismo de atualização automática (SSE/WebSocket/polling
  dedicado) — reaproveita o que a ADR-011 já implementou.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

Nenhuma necessária — demanda e decisões de desenho couberam inteiramente nas
convenções já estabelecidas pelas ADRs anteriores (campo aditivo calculado na borda
de leitura, sem novo mecanismo de push).
