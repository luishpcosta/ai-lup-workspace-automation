---
id: ADR-006
titulo: Frontend v1 — painel de controle, visualização e interação com o motor via REST
status: proposto            # proposto | aceito | superado
contextos: [frontend]
afeta: [motor-workflow]
supera: []                  # [<ADR-id>] se substitui uma decisão anterior
depende_de: [ADR-004, ADR-005]
---

<!-- Front matter de relação: metadado que alimenta o grafo de dependências mantido
pela skill `blueprintfy` (scripts/graph_query.py). Use os nomes exatos das entradas do
CONTEXT-MAP.md em `contextos`/`afeta`. `supera` vai na ADR NOVA (a antiga é marcada
como superada pela ferramenta, não à mão). Mantenha os campos mesmo com lista vazia. -->

# ADR-006: Frontend v1 — painel de controle, visualização e interação com o motor via REST

- **Status**: Proposto
- **Data**: 2026-09-04
- **Autor**: Gerado a partir de demanda informal (elicitação via skill issue-to-adr)
- **PRD relacionado**: Nenhum — origem é uma demanda informal descrita em conversa, não um documento formal.

## Contexto

A ADR-004 abriu a porta HTTP (`workflow serve`) e a ADR-005 acrescentou stream ao vivo
e interação com o Claude Code Runner — mas ambas só têm cliente via `curl`/HTTP direto.
O usuário pediu explicitamente uma primeira versão de **frontend** para controlar
(disparar/cancelar runs), visualizar (listar runs, ver detalhe por etapa) e interagir
(mandar instrução, ver stream ao vivo) com o motor, tudo consumindo a API REST/SSE já
implementada — sem propor nenhuma rota nova de negócio.

Este é o primeiro trabalho real no contexto `frontend/`, que até aqui era só uma pasta
reservada (ver `CONTEXT-MAP.md`, monorepo dividido em `backend/`+`frontend/`).

**Assunções registradas (elicitação, 2 rodadas):**
- Uso local/individual, sem autenticação nesta versão — mesma postura do backend hoje.
- `config_path` (para disparar um run novo) é digitado pelo usuário, não escolhido de
  uma lista — o backend não expõe (e esta ADR não propõe) um endpoint de
  navegação/listagem de arquivos de configuração.
- O conteúdo transmitido por `GET /runs/{chain_name}/stream` é mostrado como texto cru
  (linhas do transcript stream-json), sem parsing do schema de eventos do Claude Code —
  fica para uma versão futura.
- Volume baixo (um usuário, poucos runs simultâneos) — já é o cenário do backend
  (ADR-003/004, pool pequeno e fixo).

## Requisitos atendidos

| ID | Requisito | Tipo |
|----|-----------|------|
| RF-01 | Tela de configuração: usuário informa a URL base do backend (`host:porta` de `workflow serve`); persistida no navegador (localStorage), usada em toda chamada REST/SSE subsequente | Funcional |
| RF-02 | Listagem de runs (`GET /runs`) e detalhe por etapa (`GET /runs/{chain_name}`) | Funcional |
| RF-03 | Disparo de novo run via formulário (`POST /runs`, campo `config_path`) | Funcional |
| RF-04 | Stream ao vivo da etapa Claude Code Runner ativa (`GET /runs/{chain_name}/stream`, SSE) e envio de instrução (`POST /runs/{chain_name}/instrucoes`) | Funcional |
| RF-05 | Cancelamento de run (`POST /runs/{chain_name}/cancelar`) | Funcional |
| RNF-01 | Sem autenticação nesta versão | Não-funcional |
| RNF-02 | Frontend e backend são processos independentes (dev server Vite + `workflow serve`), comunicação só via REST/SSE — backend precisa de CORS habilitado | Não-funcional |
| RNF-03 | Erros de conexão (backend fora do ar, URL mal configurada) e erros de contrato (4xx/409) sempre exibidos de forma clara — nunca uma tela travada esperando indefinidamente | Não-funcional |

## Decisão

**Novo componente**: SPA em `frontend/` (React + Vite), processo próprio (dev server,
porta própria), sem build/estado compartilhado com o backend. **Extensão pequena** no
componente existente API HTTP (`backend/src/workflow_engine/adapters/http_api.py`):
adicionar `CORSMiddleware`, única mudança no backend — nenhuma rota nova, nenhum
payload existente muda.

```mermaid
flowchart LR
    subgraph Frontend["frontend/ (React + Vite, :5173)"]
        Config["Tela de Configuração\n(base URL -> localStorage)"]
        Lista["Lista de Runs\nGET /runs"]
        Detalhe["Detalhe por etapa\nGET /runs/{chain_name}"]
        Form["Disparar novo run\nPOST /runs"]
        Stream["Stream ao vivo + instrução\nGET /stream (SSE) + POST /instrucoes"]
        Cancelar["Cancelar\nPOST /runs/{chain_name}/cancelar"]
    end
    Config -.fornece base URL.-> Lista & Detalhe & Form & Stream & Cancelar
    Lista --> Detalhe
    Backend["workflow serve (FastAPI, :8000)\nCORSMiddleware novo (ADR-006)\nADR-004/ADR-005, inalteradas"]
    Lista -- "REST" --> Backend
    Detalhe -- "REST" --> Backend
    Form -- "REST" --> Backend
    Stream -- "REST + SSE" --> Backend
    Cancelar -- "REST" --> Backend
```

- **Configuração pelo app (RF-01)**: sem URL configurada, a SPA força a tela de
  configuração antes de qualquer outra tela; a URL fica em `localStorage` do
  navegador (por viewer, não compartilhada) — decisão simétrica ao restante do
  motor: sem estado novo no backend, sem banco novo no frontend.
- **Cliente REST único**: todas as chamadas passam por um client HTTP fino que lê a
  base URL configurada; se a chamada falhar (rede, 4xx, 5xx), a tela correspondente
  mostra o erro (RNF-03) — nunca um spinner infinito.
- **Reaproveitamento total do contrato existente**: nenhum payload novo. `POST /runs`
  continua só `{"config_path": str}`; `POST /runs/{chain_name}/instrucoes` continua só
  `{"mensagem": str}`; as respostas de erro continuam `{"error": {"code", "message"}}`
  (ADR-004) — a SPA lê `error.code` para decidir a mensagem exibida (`invalid_config`,
  `already_running`, `not_streamable`, `not_interactable`, `not_found`).
- **Stream (RF-04)**: a SPA abre `EventSource`/fetch-stream em
  `GET /runs/{chain_name}/stream` só quando a tela de detalhe mostra uma etapa
  `claude_code_runner` "running"; em 409 (`not_streamable`), mostra "sem sessão ativa
  no momento" em vez de tentar reconectar em loop.
- **CORS (única mudança de backend)**: `CORSMiddleware` adicionado em `build_app()`,
  permitindo os métodos usados (`GET`, `POST`) e o header `Content-Type`, sem exigir
  credenciais — coerente com "sem autenticação" (RNF-01). Ver Riscos.

## Alternativas consideradas

| Alternativa | Por que não foi escolhida |
|-------------|---------------------------|
| Build estático da SPA servido pelo próprio FastAPI (sem CORS, um processo só) | Acopla o deploy do frontend ao do backend; o motor é pensado como processo standalone (ADR-001/004) — usuário escolheu explicitamente manter os dois processos independentes. |
| Autenticação simples (token fixo) já nesta versão | Fora de escopo confirmado na elicitação — uso local/individual, mesma postura do backend hoje; revisitar se o backend passar a ser exposto além de localhost. |
| Backend expõe endpoint para listar/navegar `config_path`s disponíveis | Fora de escopo desta versão — usuário confirmou que digitar o caminho é aceitável para v1; evita introduzir uma rota nova de negócio só para conveniência de formulário. |
| Parsing do schema de eventos stream-json no frontend (renderização "bonita" do que o agente está fazendo) | Fora de escopo desta versão — v1 mostra o transcript cru; parsing fica para uma iteração futura, quando houver clareza de quais eventos vale a pena destacar. |

## Consequências

- **Positivas**: nenhuma mudança de contrato REST existente (ADR-004/005 continuam
  válidas como estão); permite trocar de backend (outra máquina/porta) sem rebuild,
  só reconfigurando a URL na tela; reaproveita 100% dos endpoints já implementados e
  testados.
- **Negativas / trade-offs**: sem lista de configs disponíveis, o usuário precisa
  saber/copiar o `config_path` manualmente; CORS sem allowlist restrita (permissivo)
  é uma simplificação deliberada para v1.
- **Riscos**: CORS aberto sem autenticação é aceitável apenas enquanto o backend
  roda só em `localhost`/rede de confiança — se `workflow serve` for exposto além
  disso no futuro, esta combinação (CORS aberto + sem auth) vira um risco real de
  segurança e precisa ser revisitada explicitamente, não apenas herdada desta ADR.

## Componentes afetados

- **Novo**: Frontend App (`frontend/`, React + Vite) — implementação completa nova
  neste contexto.
- API HTTP (`backend/src/workflow_engine/adapters/http_api.py`, ADR-004/ADR-005) —
  adiciona `CORSMiddleware`; nenhuma rota ou payload existente muda.

> Atividades e Acceptance Criteria detalhadas estão em `ADR-006-acs.md`.
