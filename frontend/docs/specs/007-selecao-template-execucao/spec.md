# Spec: Disparo por Template — Specs Remotas e Repositórios Locais

**Feature ID:** 007-selecao-template-execucao
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-06

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

A feature `006` (ADR-006) resolveu o disparo digitando um ID de texto livre, resolvido
por convenção exata de nome de arquivo contra um diretório-base configurado. Isso exige
que o usuário saiba de cor o ID e que o arquivo correspondente já exista no disco do
backend — não há forma de descobrir quais specs existem num repositório remoto de
documentação, nem de escolher em qual repositório local rodar, nem de ver quais
workflows (combinações de plugins) o motor sabe executar.

O usuário pediu explicitamente: navegar specs de um repositório remoto configurável e
selecionar uma ou mais; declarar uma pasta de trabalho local com vários repositórios e
escolher em qual rodar; e que o motor só precise saber "qual workflow" disparar — sem
perder nenhuma funcionalidade já existente (listar runs, ver detalhe, stream ao vivo,
mandar instrução, cancelar, e o próprio pipeline completo de implementação).

Origem: demanda informal elicitada diretamente em conversa, registrada em
`adr/ADR-007-templates-workflow-execucao-adhoc.md` (contexto `motor-workflow`, `afeta:
[frontend]` — depende de ADR-004/ADR-005/ADR-006).

## User Stories

- Como usuário, quero ver quais workflows o motor sabe executar e o que cada um espera
  como entrada, para escolher o certo sem precisar saber de cor um ID de arquivo.
- Como usuário com várias specs num repositório de documentação remoto, quero navegar e
  selecionar uma ou mais direto no painel, sem sair dele.
- Como usuário com vários repositórios já clonados localmente, quero escolher em qual
  deles um workflow roda, sem que o motor precise cloná-lo de novo.
- Como usuário que só quer investigar impacto de uma mudança, quero escrever um prompt
  livre, apontar as specs relevantes e o repositório-alvo, e disparar — sem passar por
  clone/branch/PR.
- Como usuário que já usa o pipeline completo de implementação (ADR-002), quero
  continuar disparando exatamente esse mesmo pipeline, agora escolhendo-o na mesma tela
  que os demais workflows.
- Como usuário que já usa listagem/detalhe/stream/instrução/cancelamento, quero que
  nada disso mude de comportamento — só a forma de iniciar uma nova execução.

## Functional Requirements

- FR-1: Uma tela de configuração permite informar a URL base do backend e a URL base de
  um repositório remoto de specs; os dois valores são persistidos no navegador.
- FR-2: O formulário de disparo lista os workflows que o motor sabe executar, com nome
  e descrição de cada um.
- FR-3: Ao escolher um workflow, o formulário exibido é gerado a partir do que aquele
  workflow espera receber — sem o frontend conhecer de antemão os detalhes de um
  workflow específico.
- FR-4: Um campo do formulário que espera um repositório local é preenchido a partir da
  lista de repositórios que o backend expõe (sem o frontend ler o filesystem).
- FR-5: Um campo do formulário que espera uma ou mais specs é preenchido navegando o
  repositório remoto de documentação configurado — consultado direto pelo navegador, sem
  passar pelo backend.
- FR-6: Disparar o formulário preenchido inicia uma execução real, com o mesmo tipo de
  confirmação/erro já usado no disparo existente.
- FR-7: O pipeline completo de implementação já existente continua disparável, como um
  workflow a mais na mesma lista — não uma tela ou fluxo separado.
- FR-8: Listagem de execuções, detalhe por etapa, stream ao vivo, envio de instrução e
  cancelamento continuam funcionando exatamente como antes — nenhuma mudança de contrato
  ou comportamento nesses fluxos.

## Non-Functional Requirements

- NFR-1 (herdado de `006`): sem autenticação nesta versão.
- NFR-2 (herdado de `006`): app e backend são processos independentes; nenhum estado
  compartilhado além de chamadas REST/SSE — e agora também nenhuma chamada ao backend
  para consultar o repositório remoto de specs (FR-5, consulta direta).
- NFR-3 (herdado de `006`): toda falha (conexão, erro de contrato, consulta remota
  indisponível) é exibida de forma clara — nenhuma tela trava esperando indefinidamente.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-007-acs.md` (componente frontend) para
rastreabilidade cruzada.

- **AC-01** — Given que o app abre sem configuração salva, when o usuário informa URL base do backend e URL base do repositório remoto de specs, then os dois valores são persistidos e usados em toda chamada subsequente. _(FR-1)_
- **AC-02** — Given configuração já existente, when o app é recarregado, then ele volta a usá-la automaticamente. _(FR-1, herdado de AC-02/006)_
- **AC-03** — Given que o motor expõe workflows, when o formulário de disparo carrega, then lista cada um com nome e descrição. _(FR-2)_
- **AC-04** — Given um workflow selecionado, when o formulário é exibido, then os campos mostrados correspondem exatamente ao que aquele workflow declara esperar — um campo por entrada, do tipo apropriado (texto, texto longo, escolha única, múltipla escolha). _(FR-3)_
- **AC-05** — Given um campo que espera um repositório local, when o formulário é exibido, then as opções vêm da lista de repositórios exposta pelo backend, nunca de uma leitura direta do filesystem pelo navegador. _(FR-4)_
- **AC-06** — Given um campo que espera uma ou mais specs, when o formulário é exibido, then as opções vêm de uma consulta direta ao repositório remoto configurado, sem passar pelo backend do motor. _(FR-5, NFR-2)_
- **AC-07** — Given um formulário preenchido com os campos obrigatórios de um workflow, when o usuário dispara, then a execução começa de verdade e aparece na listagem, com a mesma confirmação visual já usada antes. _(FR-6)_
- **AC-08** — Given um disparo rejeitado pelo motor (campo obrigatório faltando, ou workflow desconhecido), when a rejeição chega, then é exibida de forma clara e específica, sem travar o formulário. _(FR-6, NFR-3)_
- **AC-09** — Given o pipeline completo de implementação já existente, when o usuário abre o formulário de disparo, then ele aparece como um workflow selecionável ali mesmo, junto dos demais. _(FR-7)_
- **AC-10** (regressão) — Given listagem, detalhe, stream ao vivo, instrução e cancelamento já implementados na feature `006`, when esta feature é concluída, then todos continuam funcionando sem nenhuma mudança de comportamento observável. _(FR-8)_

## Edge Cases

- Repositório remoto de specs fora do ar ou mal configurado → erro claro nesse campo específico, sem travar o resto do formulário (AC-06, NFR-3).
- Nenhum repositório local configurado no backend → campo mostra claramente que não há opção disponível, não uma lista vazia sem explicação (AC-05).
- Workflow sem nenhum campo que precise de repositório local ou specs remotas (ex.: o pipeline de implementação) → formulário não exibe esses campos, e nenhuma consulta é feita para eles (AC-04).
- Disparo rejeitado por campo obrigatório faltando → erro nomeando o problema, formulário continua preenchido para correção (AC-08).

## Out of Scope (Non-Goals)

- Disparo em lote de múltiplos valores num único envio (capacidade existente na feature `006`, RF-03) — cada envio do formulário dispara uma execução; disparar várias é repetir o envio, uma vez por combinação de parâmetros desejada. O disparo por texto livre + convenção de nome de arquivo que essa capacidade usava deixa de existir (substituído pelo disparo por workflow).
- Preview do conteúdo markdown de uma spec dentro do formulário de seleção (só título/id são exibidos) — fica para uma iteração futura, se necessário.
- Qualquer mudança em listagem, detalhe, stream, instrução ou cancelamento além do que é estritamente necessário para não quebrá-los.
- Autenticação — mesma postura já assumida desde a feature `006`.
- Edição do diretório-raiz de repositórios locais pelo próprio app — é uma configuração do processo backend (`workflow serve --local-repos-root`), não uma tela do frontend.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-06 | O frontend deve consultar o repositório remoto de specs direto, ou via proxy do backend? | Direto do browser (fetch) — sem proxy no backend |
| 2026-09-06 | Repositório local: clonar de novo, ou usar o checkout existente? | Usar o checkout existente — motor roda direto nele |
| 2026-09-06 | Seleção de "quais plugins usar": composição livre na UI, ou templates pré-definidos? | Templates pré-definidos, expostos pelo motor |
| 2026-09-06 | `configDir`/disparo por convenção de nome de arquivo (feature `006`) ficam órfãos — o que fazer? | Remover — quem precisar disparar por arquivo direto usa a API/CLI do motor sem passar pelo painel |
| 2026-09-06 | Disparo em lote (RF-03 da feature `006`) tem equivalente direto no novo formulário estruturado? | Não — sai de escopo nesta reformulação (ver Non-Goals); cada envio dispara uma execução |
