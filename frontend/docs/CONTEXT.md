---
contexto: frontend
depende_de: [motor-workflow]
---

# Contexto: frontend

Painel de controle web (SPA, React + Vite) que consome a API HTTP/SSE do
motor-workflow (`workflow serve`, ADR-004/ADR-005) para disparar, visualizar,
acompanhar ao vivo e interagir com execuções — sem introduzir nenhuma rota de
negócio nova; ver `../adr/ADR-006-*.md` para a decisão fundadora deste contexto.

## Linguagem

**Base URL (do backend)**:
Endereço (`host:porta`) de um processo `workflow serve` configurado pelo usuário na
tela de configuração do app e persistido em `localStorage` do navegador — não existe
valor padrão nem descoberta automática.
_Evitar_: API endpoint, server address.

**chain_name**:
Mesmo termo do contexto [motor-workflow](../../backend/docs/motor-workflow/CONTEXT.md)
— identifica de forma única um run na listagem e no detalhe. O frontend nunca gera
ou deriva esse valor: ele vem sempre de uma resposta do backend.

**Stream ao vivo**:
Conexão SSE aberta em `GET /runs/{chain_name}/stream` enquanto uma etapa Claude Code
Runner está `running`; v1 mostra o transcript cru (texto), sem parsing do schema de
eventos do Claude Code.
_Evitar_: live log, tail (usar sempre "stream ao vivo", para distinguir da leitura
única de detalhe).

**ID de documento de referência**:
O que o usuário efetivamente digita/cola no formulário de disparo (um ou vários) —
não é um `config_path` nem uma "história de usuário": é o ID de um documento inicial
no servidor MCP, que pode ter outros documentos vinculados por frontmatter (achado da
entrevista de UX, ADR-006). A SPA resolve cada ID para `config_path` por convenção
exata de nome de arquivo (`<diretório-base configurado>/<id>.yaml`), antes de chamar
`POST /runs` — sem navegar ou listar arquivos no backend.
_Evitar_: historia_id (nome usado em ADR-001/002, mais estreito que o conceito real;
rename pendente, ver ADR-006, Consequências — não decida usar esse nome em código novo
do frontend sem checar se o rename já aconteceu).

**config_path (payload REST)**:
Campo que o `POST /runs` do backend espera (`{"config_path": str}`, ADR-004) — no
frontend, é sempre um valor **derivado** (ID de documento de referência + convenção de
nome de arquivo), nunca digitado diretamente pelo usuário. Quem valida sua existência é
o backend (`ChainValidationError` -> 400 `invalid_config`).
