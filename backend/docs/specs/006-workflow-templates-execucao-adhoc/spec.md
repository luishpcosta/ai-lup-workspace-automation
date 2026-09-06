# Spec: Templates de Workflow e Execução Ad-hoc (Repo Local + Modo Investigar)

**Feature ID:** 006-workflow-templates-execucao-adhoc
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-06

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

O frontend (feature `006` do contexto `frontend`) hoje dispara execuções resolvendo um
ID de texto livre para um `config_path` por convenção exata de nome de arquivo — o
usuário precisa saber de cor esse ID e confiar que o arquivo já existe no disco do
backend. Não existe forma de listar quais workflows (combinações de plugins) estão
disponíveis, nem de rodar contra um repositório local já existente sem clonar de novo.

Origem: demanda informal elicitada diretamente em conversa, registrada em
`adr/ADR-007-templates-workflow-execucao-adhoc.md` (depende de
`adr/ADR-001-motor-workflow-plugins.md`, `adr/ADR-002-plugins-poc-pipeline-sdd.md`,
`adr/ADR-004-api-http-monitoria.md`, `adr/ADR-005-stream-interacao-agente.md`).

## User Stories

- Como usuário do painel, quero ver uma lista de workflows disponíveis (com os
  parâmetros que cada um espera), para escolher qual rodar sem precisar saber de cor um
  ID de arquivo.
- Como usuário com vários repositórios já clonados localmente, quero escolher em qual
  deles um workflow roda, sem que o motor precise cloná-lo de novo.
- Como usuário que quer só investigar o impacto de uma mudança, quero mandar um prompt
  livre + quais documentos consultar, e receber um relatório — sem que isso abra uma PR.
- Como usuário que já usa o pipeline completo de implementação (código + PR + review),
  quero continuar disparando exatamente esse mesmo pipeline, agora como um workflow
  selecionável entre outros.

## Functional Requirements

- FR-1: Um endpoint lista os workflows disponíveis, cada um com os parâmetros que
  espera receber para ser disparado.
- FR-2: Um endpoint lista os repositórios disponíveis num diretório de trabalho
  configurado no processo do motor; sem esse diretório configurado, a lista é vazia
  (não um erro).
- FR-3: Um endpoint dispara um workflow a partir do seu identificador e dos parâmetros
  fornecidos, com a mesma resposta de disparo já usada para uma execução por arquivo
  direto.
- FR-4: Parâmetros obrigatórios faltando impedem o disparo, com um erro claro
  nomeando o problema; um identificador de workflow desconhecido também é rejeitado
  claramente.
- FR-5: Dois disparos do mesmo workflow, mesmo simultâneos, nunca colidem entre si —
  cada um é uma execução independente e identificável.
- FR-6: Existe um modo de execução do agente que recebe um prompt livre e uma lista de
  documentos a consultar, investiga o repositório-alvo, e retorna um relatório — sem
  criar branch, sem commit/push, sem abrir PR.
- FR-7: O modo de investigação funciona tanto rodando dentro de um repositório já
  preparado por uma etapa anterior quanto rodando diretamente sobre um repositório
  informado como parâmetro do próprio workflow (sem etapa de preparação antes).
- FR-8: O pipeline completo de implementação já existente (preparar ambiente, codificar,
  abrir PR, aguardar CI, revisar) continua disponível, agora também como um workflow
  selecionável entre os demais — sem nenhuma mudança de comportamento.

## Non-Functional Requirements

- NFR-1: Um workflow disparado por esta via é monitorável, transmissível (stream) e
  interagível pelos mesmos mecanismos já existentes para qualquer outra execução — sem
  exigir nenhuma mudança neles.
- NFR-2 (herdado de `001`/`002`): o contrato externo do plugin (parâmetros/saída,
  sinalização de erro retriable) não muda.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-007-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given um workflow declarado num diretório de workflows, when a listagem é consultada, then ele aparece com seu identificador, nome amigável, descrição e o schema dos parâmetros que espera. _(satisfies FR-1)_
- **AC-02** — Given um workflow malformado misturado com um válido, when a listagem é consultada, then só o malformado é ignorado — o válido continua disponível. _(satisfies FR-1)_
- **AC-03** — Given um param obrigatório de um workflow não enviado no disparo, when a validação roda, then o disparo é recusado, nomeando o param faltando. _(satisfies FR-4)_
- **AC-04** — Given todos os params obrigatórios enviados, when o workflow é materializado para execução, then cada param declarado está disponível na execução (o valor enviado, ou um default vazio se opcional e não enviado), preservando o tipo original do valor enviado. _(satisfies FR-1, FR-4)_
- **AC-05** — Given um param cujo valor é uma referência inteira a outro valor (não parte de um texto maior), when o workflow resolve esse param, then o tipo original do valor referenciado é preservado (ex.: uma lista continua lista, não vira texto). _(satisfies FR-1)_
- **AC-06** — Given um param cujo valor é uma referência embutida num texto maior, when o workflow resolve esse param, then o resultado é texto, como já acontecia antes desta feature. _(satisfies NFR-2)_
- **AC-07** — Given workflows descobertos, when a listagem é consultada, then retorna identificador/nome/descrição/schema de parâmetros de cada um. _(satisfies FR-1)_
- **AC-08** — Given um diretório de trabalho local configurado com subpastas, when a listagem de repositórios é consultada, then retorna cada subpasta imediata (não arquivos soltos). _(satisfies FR-2)_
- **AC-09** — Given nenhum diretório de trabalho local configurado, when a listagem de repositórios é consultada, then retorna uma lista vazia, nunca um erro. _(satisfies FR-2)_
- **AC-10** — Given um identificador de workflow válido e parâmetros que satisfazem o que ele espera, when o disparo é solicitado, then uma execução real começa, monitorável e completável, com a mesma forma de resposta já usada para disparo por arquivo direto. _(satisfies FR-3, NFR-1)_
- **AC-11** — Given parâmetros faltando um campo obrigatório, when o disparo é solicitado, then é recusado com um erro claro, e nada é executado. _(satisfies FR-4)_
- **AC-12** — Given um identificador de workflow desconhecido, when o disparo é solicitado, then é recusado com um erro claro. _(satisfies FR-4)_
- **AC-13** — Given dois disparos do mesmo workflow com parâmetros diferentes, when ambos são solicitados, then cada um recebe um identificador de execução distinto — nenhuma colisão. _(satisfies FR-5)_
- **AC-14** — Given um repositório já existente informado diretamente como parâmetro (sem etapa de preparação antes), when o modo de investigação roda, then opera dentro desse repositório, e o resultado final contém o relatório e os documentos efetivamente consultados. _(satisfies FR-6, FR-7)_
- **AC-15** — Given nenhum repositório disponível (nem por parâmetro, nem por uma etapa anterior), when o modo de investigação roda, then falha claramente antes de qualquer chamada externa. _(satisfies FR-6)_
- **AC-16** — Given o modo de investigação, when a instrução ao agente é montada, then instrui explicitamente para não criar branch, não commitar/dar push, não abrir PR — diferente dos modos de implementação/revisão existentes. _(satisfies FR-6)_
- **AC-17** (regressão) — Given o pipeline completo de implementação já existente, when disparado como workflow selecionável, then produz exatamente o mesmo resultado que produzia disparado por arquivo direto. _(satisfies FR-8)_

## Edge Cases

- Workflow malformado no diretório de workflows → ignorado, não derruba a listagem (AC-02).
- Diretório de trabalho local não configurado ou inexistente → lista vazia, não erro (AC-09).
- Dois disparos concorrentes do mesmo workflow → identificadores distintos, sem colisão (AC-13).
- Modo de investigação sem repositório disponível de nenhuma fonte → falha antes de qualquer chamada externa, não trava esperando (AC-15).
- Param opcional de um workflow não enviado → resolve para um valor vazio, não quebra a execução (AC-04).

## Out of Scope (Non-Goals)

- Qualquer mudança no contrato de disparo por arquivo direto já existente (`config_path`) — continua funcionando exatamente como antes.
- Consulta a repositórios remotos de documentação — isso é resolvido inteiramente do lado do frontend (ver `frontend/docs/specs/007-selecao-template-execucao/spec.md`), este contexto só recebe os identificadores de documento já escolhidos.
- Limpeza automática de execuções/arquivos gerados por disparos anteriores.
- Autenticação — mesma postura já assumida desde `001`.
- Qualquer mudança nos mecanismos de monitoria/stream/instruções/cancelamento já existentes (ADR-004/005) — só reusados, não alterados.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-06 | O frontend deve consultar o repositório remoto de specs direto, ou via proxy do backend? | Direto do browser (fetch) — o backend não precisa saber nada sobre esse repositório remoto, só receber os ids de documento já escolhidos |
| 2026-09-06 | Rodar num repositório local deve clonar de novo, ou usar o checkout existente? | Usar o checkout existente diretamente — sem etapa de clone |
| 2026-09-06 | Seleção de "quais plugins usar" deve ser composição livre na UI, ou templates pré-definidos? | Templates pré-definidos — o motor expõe a lista, o frontend só escolhe e preenche parâmetros |
| 2026-09-06 | O modo de investigação deve ser um plugin novo, ou um modo a mais no plugin existente? | Modo a mais no plugin Claude Code Runner existente — reusa toda a infraestrutura de streaming/instruções já validada |
