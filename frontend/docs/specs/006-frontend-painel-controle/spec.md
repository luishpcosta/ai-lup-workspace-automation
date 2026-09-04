# Spec: Painel de Controle Frontend v1 (REST/SSE)

**Feature ID:** 006-frontend-painel-controle
**Phase:** Verify
**Owner:** <who>
**Last updated:** 2026-09-04

> WHAT and WHY only — no implementation details (no tech, no file names, no APIs). Save those para `plan.md`.

## Problem / Motivation

O motor de workflow (`backend/`) só é acessível via CLI (`workflow run`/`run-many`/`serve`).
O usuário pediu explicitamente uma primeira versão de frontend para controlar
(disparar/cancelar runs), visualizar (listar, ver detalhe por etapa) e interagir
(mandar instrução, ver stream ao vivo) com o motor, consumindo 100% a API REST/SSE já
implementada (ADR-004/ADR-005) — sem propor nenhuma rota de negócio nova no backend.

Origem: demanda informal elicitada via skill `issue-to-adr`, aprofundada por uma
entrevista de descoberta UX (skill `ux-discovery-interviewer`), ambas registradas em
`adr/ADR-006-frontend-painel-controle.md` (depende de ADR-004 e ADR-005 do contexto
`motor-workflow`).

## User Stories

- Como usuário que acabou de sair de uma sessão de refinamento com um ou mais
  documentos de referência prontos, quero disparar todos de uma vez pelo app, para
  não precisar abrir um terminal por execução.
- Como usuário acompanhando várias execuções, quero ver rapidamente quais falharam sem
  precisar abrir cada uma, para não fazer troubleshooting manual de log/terminal.
- Como usuário vendo o Claude Code Runner ativo numa etapa, quero acompanhar ao vivo e
  poder mandar uma instrução, para corrigir o rumo sem esperar a etapa terminar.
- Como usuário, quero cancelar um run que ainda não deveria ter sido disparado, sabendo
  que só o que ainda não começou a rodar pode ser efetivamente interrompido.
- Como usuário, quero configurar pelo próprio app a que backend ele se conecta e onde
  ficam os arquivos de configuração das execuções, para não depender de valores fixos
  no código.

## Functional Requirements

- FR-1: Uma tela de configuração permite informar a URL base do backend (`workflow
  serve`) e um diretório-base de configs; os dois valores são persistidos no navegador
  e usados em toda chamada subsequente.
- FR-2: Uma tela lista todas as execuções conhecidas pelo backend, destacando
  visualmente (sem notificação ativa) as que estão com falha; uma segunda tela mostra o
  detalhe de uma execução por etapa.
- FR-3: Um formulário aceita um ou mais IDs de documento de referência e dispara uma
  execução por ID, resolvendo cada ID para o caminho de configuração correspondente por
  convenção de nome de arquivo (usando o diretório-base configurado); erro em um item
  não impede os demais do lote.
- FR-4: Quando uma execução tem uma etapa do Claude Code Runner ativa, o app retransmite
  ao vivo o que está acontecendo e permite enviar uma instrução nova para ela.
- FR-5: O app permite cancelar uma execução, refletindo os mesmos estados já suportados
  pelo motor (cancelado, não cancelável, não encontrado).

## Non-Functional Requirements

- NFR-1: Sem autenticação nesta versão — uso local/individual, mesma postura do backend.
- NFR-2: O app e o backend são processos independentes; nenhum estado é compartilhado
  além de chamadas REST/SSE.
- NFR-3: Toda falha (conexão, erro de contrato, item de lote inválido) é exibida de
  forma clara — nenhuma tela trava esperando indefinidamente.

## Acceptance Criteria

IDs mantidos alinhados com `adr/ADR-006-acs.md` para rastreabilidade cruzada.

- **AC-01** — Given que o app abre sem nenhuma configuração salva, when o usuário informa URL base do backend e diretório-base de configs na tela de configuração, then os dois valores são persistidos e usados em toda chamada subsequente sem precisar reconfigurar a cada sessão. _(FR-1)_
- **AC-02** — Given que URL e diretório já foram configurados antes, when o app é recarregado, then ele volta a usá-los automaticamente, sem forçar a tela de configuração de novo. _(FR-1)_
- **AC-03** — Given que a URL configurada não responde, when qualquer tela tenta uma chamada REST, then exibe um erro claro de conexão, nunca uma tela travada. _(FR-1, NFR-3)_
- **AC-04** — Given N execuções registradas no backend, when a tela de listagem carrega, then mostra chain_name, run_id, workflow_name, status, created_at, updated_at para cada uma. _(FR-2)_
- **AC-05** — Given um chain_name selecionado, when o usuário abre o detalhe, then mostra status por etapa (step_name, status, attempt_count, started_at, finished_at, error_message); chain_name inexistente exibe erro claro. _(FR-2, NFR-3)_
- **AC-12** — Given um run cujo status mais recente indica falha, when a listagem exibe esse item, then a linha recebe destaque visual passivo (sem notificação ativa). _(FR-2)_
- **AC-06** — Given um ou mais IDs de documento de referência informados, when o usuário dispara, then cada ID é resolvido para um caminho de configuração e disparado individualmente; sucesso atualiza a listagem com o chain_name daquele item, erro de um item não cancela os demais do lote. _(FR-3)_
- **AC-13** — Given um ID cujo arquivo de configuração correspondente não existe no backend, when o disparo daquele item é tentado, then o erro é exibido associado especificamente àquele ID, sem abortar os demais. _(FR-3, NFR-3)_
- **AC-07** — Given uma execução com etapa do Claude Code Runner ativa, when o usuário está no detalhe, then o app retransmite ao vivo o transcript daquela etapa, incluindo o que já existia. _(FR-4)_
- **AC-08** — Given uma execução sem etapa ativa no momento, when o detalhe tenta abrir o acompanhamento ao vivo, then mostra "sem sessão ativa", sem tentar reconectar em loop. _(FR-4, NFR-3)_
- **AC-09** — Given uma etapa ativa, when o usuário envia uma instrução, then ela é entregue ao mesmo mecanismo usado pelo motor; sem etapa ativa, exibe erro claro. _(FR-4, NFR-3)_
- **AC-10** — Given um run em andamento, when o usuário cancela, then reflete um dos três estados já suportados pelo motor (cancelado / não cancelável / não encontrado). _(FR-5)_
- **AC-11** — Given que o app e o backend rodam em origens diferentes, when qualquer chamada é feita, then é aceita pelo backend (CORS habilitado) sem exigir credenciais. _(NFR-2)_

## Edge Cases

- Backend fora do ar ou URL mal configurada → erro claro, nunca tela travada (AC-03).
- Disparo em lote com um ID inválido no meio → só aquele item falha, os demais seguem (AC-06, AC-13).
- Etapa ativa termina enquanto o usuário está acompanhando o stream → app para de tailar, sem erro (mesma garantia da ADR-005, AC-05 herdada).
- Instrução enviada depois que a etapa já terminou → sem efeito (herdado de ADR-005, não redefinido aqui).

## Out of Scope (Non-Goals)

- Autenticação/login nesta versão.
- Geração automática de arquivo de configuração a partir só do ID (o arquivo já precisa existir).
- Navegação/listagem de arquivos de configuração pelo backend (nenhuma rota nova de negócio).
- Parsing do schema de eventos stream-json (v1 mostra o transcript cru).
- Notificação ativa de erro (som, push do navegador) — só destaque visual passivo.
- Renomear `historia_id` no backend (decisão pendente, registrada na ADR-006, fora do escopo desta feature).

## Open Questions

Nenhuma pendente e bloqueante — todas resolvidas na elicitação (skill `issue-to-adr`) e na entrevista de UX (skill `ux-discovery-interviewer`), registradas em `adr/ADR-006-frontend-painel-controle.md`.

## Clarifications Log

| Date | Question | Resolution |
|---|---|---|
| 2026-09-04 | Stack? | React + Vite |
| 2026-09-04 | Como o app se conecta ao backend? | Dev server separado, CORS habilitado no backend |
| 2026-09-04 | Escopo v1? | Todas as 4 capacidades (listar/detalhe, disparar, stream+instrução, cancelar) |
| 2026-09-04 | Autenticação? | Nenhuma nesta versão |
| 2026-09-04 | Configuração pelo app? | URL base do backend, persistida em localStorage |
| 2026-09-04 (entrevista UX) | Gatilho real de uso? | Pós-planejamento — disparo é o ponto de entrada, e é feito em lote |
| 2026-09-04 (entrevista UX) | Forma do "alerta" de erro? | Só destaque visual passivo, sem notificação ativa |
| 2026-09-04 (entrevista UX) | O que se digita para disparar? | ID de documento de referência no MCP, não um `config_path` bruto |
| 2026-09-04 (entrevista UX) | Como resolver ID → config_path? | Convenção exata de nome de arquivo (`<diretório-base>/<id>.yaml`), configurável no app |
