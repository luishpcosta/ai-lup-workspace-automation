# Spec: Streaming ao Vivo e Interação com o Agente (Claude Code Runner)

**Feature ID:** 005-stream-interacao-agente
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-04

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those for `plan.md`.

## Problem / Motivation

A feature `004` deu porta de entrada HTTP e monitoria, mas não permite ver o agente codificando em tempo real nem interagir com ele. O usuário quer isso especificamente: "conectar via stream no runner pra vê-lo ou exibir o agente codificando até mesmo interagir se necessário".

Origem: demanda informal elicitada via skill `issue-to-adr`, registrada em `adr/ADR-005-stream-interacao-agente.md` (depende de `adr/ADR-002-plugins-poc-pipeline-sdd.md` e `adr/ADR-004-api-http-monitoria.md`).

## User Stories

- Como usuário acompanhando uma execução, quero ver ao vivo o que o Claude Code está fazendo (o que lê, o que decide, o que edita), para não precisar esperar a etapa terminar pra saber se está indo bem.
- Como usuário vendo o agente ir por um caminho que não é o que eu queria, quero poder mandar uma instrução nova enquanto ele ainda está rodando, para corrigir o rumo sem esperar a etapa terminar e recomeçar do zero.
- Como usuário que também usa o motor só pelo terminal, quero que ver/interagir funcione igual, não importa se a execução foi disparada por mim no terminal ou pela API.

## Functional Requirements

- FR-1: O plugin que invoca o Claude Code passa a rodar como processo de longa duração, mantendo entrada/saída abertas durante a etapa, em vez de uma chamada bloqueada de uma vez só.
- FR-2: O transcript da sessão é escrito incrementalmente, não só ao final.
- FR-3: Enquanto a sessão está ativa, uma instrução nova pode ser entregue ao agente em andamento.
- FR-4: Um endpoint retransmite ao vivo o transcript da etapa do Claude Code atualmente ativa para uma execução.
- FR-5: Um endpoint aceita uma instrução nova para a etapa do Claude Code atualmente ativa.

## Non-Functional Requirements

- NFR-1: O mecanismo de ver/interagir funciona da mesma forma independentemente de a execução ter sido disparada pelo terminal ou pela API.
- NFR-2: Sem uma etapa do Claude Code ativa para a execução, os endpoints de ver/interagir respondem com erro claro, nunca esperando indefinidamente.
- NFR-3 (herdado de `001`/`002`): o contrato externo do plugin (parâmetros/saída, sinalização de erro retriable) não muda.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-005-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given a etapa executa em qualquer um dos dois modos do Claude Code Runner, when o plugin invoca a ferramenta, then usa um processo de longa duração, e a saída final entregue ao motor tem exatamente a mesma forma documentada antes desta feature. _(satisfies FR-1, NFR-3)_
- **AC-02** — Given uma sessão em andamento, when o processo emite uma linha de saída, then essa linha já está no transcript antes de a sessão terminar. _(satisfies FR-2)_
- **AC-03** — Given que a sessão falha, when a falha é propagada, then o transcript parcial até o momento da falha continua existindo. _(satisfies FR-2, NFR-3)_
- **AC-04** — Given uma sessão ativa e uma instrução nova entregue para aquela etapa, when o mecanismo de entrega processa essa instrução, then ela chega ao agente em andamento e a resposta subsequente reflete essa instrução. _(satisfies FR-3)_
- **AC-05** — Given que a sessão termina, when uma instrução chega depois disso, then ela não tem efeito algum. _(satisfies FR-3)_
- **AC-06** — Given uma execução com uma etapa do Claude Code atualmente ativa, when o endpoint de stream é consultado, then retransmite o transcript ao vivo, incluindo o que já existia e o que chega depois. _(satisfies FR-4)_
- **AC-07** — Given uma execução sem etapa do Claude Code ativa no momento, when o endpoint de stream é consultado, then responde com erro claro, sem abrir um stream vazio ou travado. _(satisfies FR-4, NFR-2)_
- **AC-08** — Given uma etapa do Claude Code ativa, when uma instrução é enviada pelo endpoint, then ela chega ao mesmo mecanismo de entrega usado internamente pelo plugin. _(satisfies FR-5)_
- **AC-09** — Given nenhuma etapa do Claude Code ativa, when uma instrução é enviada pelo endpoint, then responde com erro claro. _(satisfies FR-5, NFR-2)_
- **AC-10** — Given uma execução disparada pelo terminal (não pela API), when os endpoints de ver/interagir são consultados através da API para essa execução, then funcionam exatamente igual a uma execução disparada pela própria API. _(satisfies NFR-1)_

## Edge Cases

- Instrução chegando depois que a sessão já terminou → sem efeito, sem erro (AC-05).
- Nenhuma etapa do Claude Code ativa → erro claro em vez de travar esperando (AC-07, AC-09).
- Execução do terminal sendo vista/interagida via API → funciona igual (AC-10).

## Out of Scope (Non-Goals)

- Cancelamento de uma sessão em streaming — reusa o endpoint já definido na feature `004`, não redefinido aqui.
- WebSocket ou qualquer canal único bidirecional — ver/interagir são dois mecanismos unidirecionais separados.
- Qualquer mudança no contrato externo do plugin (parâmetros, formato de saída, sinalização de erro) além da internals de invocação.

## Open Questions

Nenhuma pendente e bloqueante.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-04 | O que "interagir com o agente" precisa cobrir já na primeira versão? | Acompanhar ao vivo + mandar instrução em tempo real (não só cancelar) |
| 2026-09-04 | Mecanismo de stream? | Server-Sent Events (SSE) para ver; endpoint HTTP comum para mandar instrução — dois canais unidirecionais, não WebSocket |
| 2026-09-04 | `--json-schema` funciona igual com `--output-format stream-json`? | Verificado ao vivo: funciona, mas via mecanismo diferente do assumido — tool call interna `StructuredOutput`, resultado final traz um campo `structured_output` já parseado além do `result` (string) |
| 2026-09-04 | Uma instrução nova durante o processamento realmente chega ao agente? | Verificado ao vivo, duas vezes — uma vez direto na CLI, outra vez através do plugin reescrito de verdade: instrução "pare e responda X" mudou o resultado final para "X" |
