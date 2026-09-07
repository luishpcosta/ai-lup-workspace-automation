# Spec: Configuração de Boot em Runtime e Pasta de Trabalho

**Feature ID:** 008-config-boot-runtime-pasta-trabalho
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-06

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

A feature `007` (ADR-007) já resolvia disparo por template/repositório local/specs
remotas, mas três atritos de uso surgiram no dia a dia do painel:

1. Toda instalação nova cai na tela de configuração e exige digitar as duas URLs à mão,
   mesmo quando o ambiente local é sempre o mesmo.
2. Os campos dessa tela usavam **placeholders com valores reais** (`http://localhost:8000`,
   uma URL de specs existente), o que faz o formulário vazio parecer preenchido.
3. A raiz de repositórios locais (`--local-repos-root`) só existe como flag de linha de
   comando do processo `serve`. Subir o backend sem ela — o caminho comum — deixa o
   seletor de repositórios permanentemente vazio, sem forma de corrigir sem derrubar e
   resubir o processo com a flag certa.

Origem: demanda informal elicitada diretamente em conversa, registrada em
`adr/ADR-009-config-boot-runtime-pasta-trabalho.md` (contexto `frontend`, `afeta:
[motor-workflow]` — depende de ADR-006/ADR-007).

## User Stories

- Como usuário que sobe o painel sempre no mesmo ambiente local, quero que ele já abra
  configurado, sem digitar as mesmas duas URLs de novo a cada instalação.
- Como usuário olhando a tela de configuração, quero distinguir um campo vazio de um
  campo já preenchido com um default — hoje os dois parecem a mesma coisa.
- Como usuário com mais de uma árvore de repositórios locais, quero trocar qual delas o
  seletor de repositórios usa, sem depender de reiniciar o backend com outra flag.
- Como usuário que edita a configuração default da máquina, quero um arquivo simples
  para isso, sem precisar rebuildar o painel.

## Functional Requirements

- FR-1: O painel sobe com configuração default vinda de um arquivo editável sem
  rebuild; com os campos obrigatórios preenchidos, entra direto no painel sem passar
  pela tela de configuração.
- FR-2: O backend resolve a raiz de repositórios também por variável de ambiente,
  mantendo a flag de linha de comando com precedência sobre ela.
- FR-3: A tela de configuração permite escolher a pasta de trabalho (raiz de
  repositórios) sem reiniciar o backend; a escolha persiste no navegador.
- FR-4: A tela de configuração deixa de usar placeholders com aparência de valor real e
  passa a indicar explicitamente quando um campo está usando o default do arquivo.

## Non-Functional Requirements

- NFR-1 (herdado de `006`/`007`): sem autenticação nesta versão.
- NFR-2: configuração continua sendo resolvida em runtime, nunca embutida no bundle
  (constitution, princípio 6) — um arquivo estático servido e lido por `fetch`, nunca
  uma variável de build.
- NFR-3: a mudança de contrato do backend é aditiva e retrocompatível — uma chamada
  existente sem o parâmetro novo mantém o comportamento de antes desta feature.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-009-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given um navegador sem nada salvo em localStorage e um arquivo de
  configuração com as duas URLs preenchidas, when a SPA carrega, then o painel abre
  direto na listagem de execuções, sem passar pela tela de configuração. _(FR-1)_
- **AC-02** — Given um valor salvo em localStorage diferente do arquivo, when a SPA
  carrega, then o valor usado é o salvo (o arquivo é default, não sobrescrita). _(FR-1)_
- **AC-03** — Given que o arquivo de configuração está ausente, é inválido, ou não tem
  os campos obrigatórios, when a SPA carrega, then a tela de configuração é exibida
  normalmente, sem erro não tratado. _(FR-1, NFR-2)_
- **AC-04** — Given que um campo está usando o valor default do arquivo, when o usuário
  abre a tela de configuração, then a tela indica explicitamente que aquele valor é
  default, não algo digitado; e nenhum campo usa placeholder com aparência de valor
  real. _(FR-4)_
- **AC-05** — Given que o usuário informa uma pasta de trabalho e salva, when o seletor
  de repositórios é carregado, then ele lista as subpastas daquela raiz sem que o
  backend tenha sido reiniciado, e a raiz escolhida sobrevive a um recarregamento da
  página. _(FR-3)_
- **AC-06** — Given que o frontend chama `GET /workspace/repos` com a raiz escolhida,
  when o parâmetro é informado, then o backend lista as subpastas daquele caminho em
  vez da raiz configurada no processo; raiz inexistente responde lista vazia, não erro.
  _(FR-3)_
- **AC-07** — Given um cliente que chama o endpoint de repositórios sem o parâmetro
  novo, when o backend está configurado com a raiz de sempre, then a resposta é
  idêntica à de antes desta feature. _(FR-3, NFR-3)_
- **AC-08** — Given a variável de ambiente de raiz definida e nenhuma flag explícita,
  when o processo `serve` sobe, then a raiz usada é a da variável; given a flag
  explícita também informada, then a flag vence. _(FR-2)_

## Edge Cases

- Arquivo de configuração ausente ou com JSON inválido → degrada para "sem default",
  tela de configuração aparece normalmente (AC-03).
- Usuário deixa um campo vazio ao salvar → aquele campo específico volta a usar o
  default do arquivo, os demais mantêm o que foi digitado (AC-02).
- Pasta de trabalho apontando para um caminho inexistente → seletor de repositórios
  mostra lista vazia com explicação, não um erro (AC-06, mesma semântica de `007`).
- Duas abas do navegador com pastas de trabalho diferentes → cada uma lê sua própria
  raiz do parâmetro de consulta; nada é sobrescrito no processo do backend (AC-06).

## Out of Scope (Non-Goals)

- Navegador de diretórios no backend (subir/descer na árvore de arquivos) — digitar/
  colar o caminho da raiz resolve o caso relatado.
- Restringir a pasta de trabalho a uma subárvore permitida — decisão explícita:
  ferramenta local, single-user, sem autenticação (mesma postura de `006`); o motor já
  executa contra repositórios locais arbitrários informados por parâmetro.
- Persistir a pasta de trabalho no backend (arquivo de configuração do processo) — a
  escolha vive no navegador, junto do resto da configuração do painel.
- Qualquer mudança em listagem, detalhe, stream, instrução, cancelamento ou disparo por
  template além do estritamente necessário para não quebrá-los.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-06 | Defaults de boot vêm de `.env` do Vite ou de um arquivo lido em runtime? | Arquivo estático (`painel-config.json`) lido por `fetch` no boot — `.env` do Vite embutiria o valor no bundle, violando o princípio 6 |
| 2026-09-06 | A pasta de trabalho é trocável via rota de escrita nova, ou parâmetro no `GET` existente? | Parâmetro de consulta opcional no `GET /workspace/repos` — é um filtro de leitura, não estado do motor; sem estado mutável no servidor, retrocompatível |
| 2026-09-06 | O endpoint deve restringir a pasta de trabalho a uma subárvore permitida? | Não — sem restrição, mesma postura local/single-user já assumida desde `006` |
