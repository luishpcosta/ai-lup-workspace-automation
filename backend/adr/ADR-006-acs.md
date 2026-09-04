# Atividades e Acceptance Criteria — ADR-006

> Referência: `ADR-006-frontend-painel-controle.md`. Componentes: Frontend App
> (novo, `frontend/`) e API HTTP (extensão pequena, `backend/src/workflow_engine/
> adapters/http_api.py`, ADR-004/ADR-005).

## Componente: Frontend App (novo)

### Atividade ADR-006-AT-01: Scaffold da SPA + configuração da URL base do backend

- **Descrição**: Estrutura inicial React + Vite em `frontend/`; tela de configuração
  onde o usuário informa `host:porta` do backend; valor persistido em `localStorage`;
  cliente HTTP único que lê essa URL para toda chamada REST/SSE subsequente.
- **Depende de**: Nenhuma (primeira atividade do componente)

**AC ADR-006-AC-01**
```
Dado que o app abre pela primeira vez, sem nenhuma URL configurada
Quando o usuário acessa a tela de configuração e informa a URL base do backend
Então essa URL é persistida em localStorage e usada em toda chamada REST/SSE subsequente, sem precisar reconfigurar a cada sessão
```

**AC ADR-006-AC-02**
```
Dado que uma URL já foi configurada em uma sessão anterior
Quando o app é recarregado
Então ele volta a usar essa URL automaticamente, sem forçar a tela de configuração de novo
```

**AC ADR-006-AC-03**
```
Dado que a URL configurada não responde (backend fora do ar ou endereço incorreto)
Quando qualquer tela tenta uma chamada REST
Então exibe um erro claro de conexão, nunca uma tela travada esperando indefinidamente
```

---

### Atividade ADR-006-AT-02: Listagem de runs e detalhe por etapa

- **Descrição**: Tela lista todos os `chain_name` conhecidos pelo backend
  (`GET /runs`); ao selecionar um, mostra o detalhe por etapa (`GET /runs/{chain_name}`).
- **Depende de**: AT-01

**AC ADR-006-AC-04** (contrato REST, consumo)
```
Dado que existem N runs registrados no backend
Quando a tela de listagem carrega
Então chama GET /runs e mostra, para cada item: chain_name, run_id, workflow_name, status, created_at, updated_at (campos exatamente como devolvidos pelo endpoint, ADR-004)
```

**AC ADR-006-AC-05** (contrato REST, consumo)
```
Dado um chain_name selecionado na lista
Quando o usuário abre o detalhe
Então chama GET /runs/{chain_name} e mostra, por etapa: step_name, status, attempt_count, started_at, finished_at, error_message (campos exatamente como devolvidos pelo endpoint, ADR-004); se o chain_name não existir, trata o 404 (not_found) exibindo mensagem clara
```

---

### Atividade ADR-006-AT-03: Disparo de novo run

- **Descrição**: Formulário com um campo de texto para `config_path`; ao enviar,
  chama `POST /runs`.
- **Depende de**: AT-01

**AC ADR-006-AC-06** (contrato REST)
```
Dado que o usuário preenche um config_path no formulário e envia
Quando a SPA chama POST /runs com corpo {"config_path": "<texto>"}
Então em caso de sucesso (202, {"chain_name", "status": "started"}) leva o usuário para a tela de detalhe daquele chain_name; em caso de erro 400 (invalid_config) ou 409 (already_running) exibe a mensagem de erro correspondente (error.code/error.message, ADR-004) sem travar a tela
```

---

### Atividade ADR-006-AT-04: Stream ao vivo e envio de instrução

- **Descrição**: Na tela de detalhe, quando há uma etapa `claude_code_runner` ativa,
  abre o stream (`GET /runs/{chain_name}/stream`, SSE) e mostra uma caixa de texto
  para enviar instrução (`POST /runs/{chain_name}/instrucoes`).
- **Depende de**: AT-02

**AC ADR-006-AC-07**
```
Dado um chain_name com etapa claude_code_runner em status "running"
Quando o usuário está na tela de detalhe
Então a SPA abre uma conexão SSE em GET /runs/{chain_name}/stream e mostra cada linha recebida como texto cru, na ordem de chegada, incluindo o que já existia no momento da conexão
```

**AC ADR-006-AC-08**
```
Dado um chain_name sem etapa claude_code_runner ativa no momento (409, not_streamable)
Quando a tela de detalhe tenta abrir o stream
Então mostra um estado "sem sessão ativa no momento", sem tentar reconectar em loop
```

**AC ADR-006-AC-09** (contrato REST)
```
Dado uma etapa claude_code_runner ativa para chain_name
Quando o usuário envia uma instrução pela caixa de texto
Então a SPA chama POST /runs/{chain_name}/instrucoes com corpo {"mensagem": "<texto>"}; 202 confirma o envio; 409 (not_interactable) exibe mensagem de erro sem travar a tela
```

---

### Atividade ADR-006-AT-05: Cancelamento de run

- **Descrição**: Botão de cancelar na tela de detalhe, chamando
  `POST /runs/{chain_name}/cancelar`.
- **Depende de**: AT-02

**AC ADR-006-AC-10**
```
Dado um run em andamento na tela de detalhe
Quando o usuário clica em cancelar
Então a SPA chama POST /runs/{chain_name}/cancelar e reflete na tela um dos resultados já documentados na ADR-004: cancelado, já rodando/não cancelável (etapa em execução não pode ser interrompida, só o que ainda não começou), ou não encontrado
```

---

## Componente: API HTTP (extensão da ADR-004/ADR-005)

### Atividade ADR-006-AT-06: Habilitar CORS em `build_app()`

- **Descrição**: Adicionar `CORSMiddleware` ao app FastAPI, permitindo requisições de
  origem diferente (dev server do frontend), sem exigir credenciais (sem
  autenticação, RNF-01).
- **Depende de**: Nenhuma (mudança isolada no backend, paralela ao frontend)

**AC ADR-006-AC-11** (contrato)
```
Dado que build_app() é construído
Quando uma requisição chega de uma origem diferente da do backend (ex.: http://localhost:5173)
Então o CORSMiddleware permite os métodos GET e POST e o header Content-Type, sem exigir credenciais; nenhuma rota, payload ou contrato de erro existente (ADR-004/ADR-005) muda
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-006 | AT-01 | AC-01, AC-02, AC-03 | Frontend App | Pendente |
| RF-02 | ADR-006 | AT-02 | AC-04, AC-05 | Frontend App | Pendente |
| RF-03 | ADR-006 | AT-03 | AC-06 | Frontend App | Pendente |
| RF-04 | ADR-006 | AT-04 | AC-07, AC-08, AC-09 | Frontend App | Pendente |
| RF-05 | ADR-006 | AT-05 | AC-10 | Frontend App | Pendente |
| RNF-01 | ADR-006 | AT-06 | AC-11 | API HTTP | Pendente |
| RNF-02 | ADR-006 | AT-06 | AC-11 | API HTTP | Pendente |
| RNF-03 | ADR-006 | AT-01, AT-02, AT-03, AT-04, AT-05 | AC-03, AC-05, AC-06, AC-08, AC-09, AC-10 | Frontend App | Pendente |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
