# Spec: Atualização automática do painel/detalhe + arquivamento de execuções

**Feature ID:** 010-atualizacao-arquivamento-execucoes
**Phase:** Tasks
**Owner:** <who>
**Last updated:** 2026-09-07

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

Três atritos relatados pelo usuário em conversa (sem PRD, elicitado via skill
`issue-to-adr`), registrados em
`adr/ADR-011-atualizacao-automatica-arquivamento-execucoes.md`:

1. Ao disparar uma execução, o painel de execuções só reflete o novo run e seu
   avanço real de status através de um clique manual em "Atualizar".
2. A tela de detalhe de uma execução busca as etapas uma única vez, ao entrar na
   tela — não acompanha o avanço real das etapas enquanto a execução roda.
3. O painel acumula execuções concluídas/antigas sem forma de tirá-las de vista,
   sem perder o histórico.

## User Stories

- Como usuário que acabou de disparar uma execução, quero ver o painel de execuções
  refletir seu progresso real (novo item, mudanças de status) sem precisar clicar em
  "Atualizar" toda hora.
- Como usuário acompanhando o detalhe de uma execução em andamento, quero ver a
  tabela de etapas avançar sozinha conforme cada etapa termina e a próxima começa.
- Como usuário com várias execuções concluídas acumuladas, quero arquivá-las para
  reduzir ruído no painel, mantendo a opção de vê-las de novo (e desarquivar) quando
  precisar — sem perder o histórico da execução.

## Functional Requirements

- FR-1: O painel de execuções atualiza sozinho, sem exigir clique, enquanto houver
  ao menos uma execução em andamento — cobrindo o momento logo após um disparo.
- FR-2: A tela de detalhe de uma execução atualiza sozinha o status geral e a tabela
  de etapas enquanto a execução estiver em andamento.
- FR-3: O usuário pode arquivar uma execução (a partir do painel ou do detalhe); ela
  some da listagem padrão do painel.
- FR-4: O usuário pode ver as execuções arquivadas (filtro dedicado na mesma tela) e
  desarquivar qualquer uma delas, trazendo-a de volta à listagem padrão.

## Non-Functional Requirements

- NFR-1 (herdado de `006`/`007`/`009`/`009` anteriores): sem autenticação nesta versão.
- NFR-2: arquivar uma execução nunca apaga seu histórico — é reversível a qualquer
  momento via desarquivar; a execução arquivada continua acessível pelo detalhe.
- NFR-3: a atualização automática não usa um mecanismo de push novo (sem
  WebSocket/SSE novo) — reaproveita as consultas já existentes, num intervalo curto,
  consistente com o volume baixo já assumido em features anteriores (uso local
  individual).
- NFR-4: a mudança de contrato do backend (campo `archived` e rotas de
  arquivar/desarquivar) é aditiva e retrocompatível — um cliente que ignora campos
  desconhecidos não é afetado.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-011-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given um arquivo de execução criado antes desta feature, when
  qualquer rota de arquivamento/listagem é chamada para essa execução, then a
  operação completa normalmente (migração de dado transparente). _(NFR-4)_
- **AC-02** — Given um chain_name existente e não arquivado, when a ação de
  arquivar é chamada, then a execução passa a constar como arquivada, e repetir a
  ação não muda o resultado (idempotente). _(FR-3)_
- **AC-03** — Given um chain_name existente e arquivado, when a ação de
  desarquivar é chamada, then a execução deixa de constar como arquivada, e repetir
  a ação não muda o resultado (idempotente). _(FR-4, NFR-2)_
- **AC-04** — Given um chain_name que não existe, when arquivar ou desarquivar é
  chamado, then a resposta indica execução não encontrada. _(FR-3, FR-4)_
- **AC-05** — Given o contrato de arquivar/desarquivar, then ele está descrito
  explicitamente (payload, resposta de sucesso, contrato de erro, idempotência) em
  `adr/ADR-011-acs.md`. _(NFR-4)_
- **AC-06** — Given a listagem de execuções, when consultada sem filtro, then só
  execuções não arquivadas aparecem (comportamento de hoje preservado); when
  consultada com o filtro de arquivadas, then só as arquivadas aparecem. _(FR-4)_
- **AC-07** — Given o detalhe de uma execução, then a resposta indica se ela está
  arquivada, sem remover nenhum campo existente. _(FR-3, FR-4, NFR-4)_
- **AC-08** — Given o painel de execuções aberto com uma execução em andamento,
  when o status dessa execução muda no backend sem ação do usuário na tela, then o
  painel reflete o novo status em até um intervalo curto, sem exigir clique em
  "Atualizar". _(FR-1)_
- **AC-09** — Given o painel de execuções aberto sem nenhuma execução em andamento,
  when o tempo passa, then nenhuma nova requisição automática é disparada. _(NFR-3)_
- **AC-10** — Given a tela de detalhe aberta para uma execução em andamento, when
  uma etapa termina e a próxima começa no backend sem ação do usuário na tela, then
  a tabela de etapas reflete os novos status em até um intervalo curto, sem exigir
  clique em "Atualizar". _(FR-2)_
- **AC-11** — Given a tela de detalhe aberta para uma execução já terminada
  (concluída ou com falha), when o tempo passa, then nenhuma nova requisição
  automática é disparada para o detalhe. _(NFR-3)_
- **AC-12** — Given o usuário navega para outra execução ou volta à listagem
  enquanto a atualização automática do detalhe anterior estava ativa, when a troca
  de tela acontece, then a atualização automática anterior é cancelada (nenhuma
  requisição órfã continua). _(FR-2)_
- **AC-13** — Given uma execução visível na listagem padrão, when o usuário arquiva
  essa execução pela tela, then ela some da listagem padrão sem precisar recarregar
  a página. _(FR-3)_
- **AC-14** — Given o filtro de execuções arquivadas selecionado, then só execuções
  arquivadas aparecem, cada uma com ação de desarquivar; when o usuário desarquiva
  uma, then ela sai da lista de arquivadas. _(FR-4)_
- **AC-15** — Given uma execução arquivada acessada diretamente pelo detalhe, when a
  tela renderiza, then o conteúdo aparece normalmente (arquivar nunca bloqueia o
  acesso ao detalhe), com ação de desarquivar disponível ali. _(FR-3, FR-4, NFR-2)_

## Edge Cases

- Execução arquivada enquanto ainda está em andamento (`running`/`pending`) —
  arquivar não interrompe/cancela a execução, só some da listagem padrão; a
  atualização automática do detalhe continua funcionando normalmente se o usuário
  estiver com ele aberto.
- Usuário troca de tela (ex.: detalhe → listagem) enquanto a atualização automática
  estava em andamento — nenhuma requisição órfã continua rodando em segundo plano
  (AC-12).
- Arquivo de execução muito antigo, criado antes desta feature existir — arquivar
  funciona normalmente (migração de dado transparente, AC-01).

## Out of Scope (Non-Goals)

- Arquivamento em lote (arquivar várias execuções de uma vez) — fica para uma
  necessidade futura, se aparecer; nesta versão a ação é por execução.
- Exclusão definitiva de uma execução (apagar o histórico) — arquivar nunca apaga
  dado; excluir é uma decisão maior, fora deste pedido.
- Qualquer mecanismo de push (WebSocket/SSE) para lista/detalhe — decisão registrada
  na ADR-011, Alternativas consideradas.

## Open Questions

Nenhuma pendente e bloqueante — as duas decisões arquiteturais relevantes (onde o
estado de arquivamento persiste, e se é reversível) já foram levadas ao usuário e
resolvidas antes deste spec (ver Clarifications Log).

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-07 | O estado de "arquivada" deve viver só no navegador (localStorage) ou persistido no backend? | Persistido no backend — precisa sobreviver a troca de navegador/dispositivo (decisão explícita do usuário) |
| 2026-09-07 | Arquivar precisa ser reversível (tela para ver/desarquivar)? | Sim — filtro "Arquivadas" com ação de desarquivar; arquivar nunca é uma exclusão disfarçada |
