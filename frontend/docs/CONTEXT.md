---
contexto: frontend
depende_de: [motor-workflow]
---

# Contexto: frontend

Painel de controle web (SPA, React + Vite) que consome a API HTTP/SSE do
motor-workflow (`workflow serve`, ADR-004/ADR-005) para disparar, visualizar,
acompanhar ao vivo e interagir com execuções — sem introduzir nenhuma rota de
negócio nova; ver `adr/ADR-006-*.md` para a decisão fundadora deste contexto.

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

**Config_path (do formulário de disparo)**:
Texto digitado pelo usuário no formulário de "novo run", repassado sem alteração para
`POST /runs`. O frontend não lista, valida antecipadamente nem navega arquivos de
configuração — quem valida é o backend (`ChainValidationError` -> 400 `invalid_config`).
_Evitar_: chain file, workflow config (usar o mesmo nome do campo do payload REST).
