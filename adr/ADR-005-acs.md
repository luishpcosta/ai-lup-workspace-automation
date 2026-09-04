# Atividades e Acceptance Criteria — ADR-005

> Referência: `ADR-005-stream-interacao-agente.md`. Componentes: Plugin Claude Code
> Runner (reescrita interna, ADR-002) e API HTTP (extensão, ADR-004).

## Componente: Plugin Claude Code Runner (reescrita interna)

### Atividade ADR-005-AT-01: Invocação via processo de longa duração (Popen + stream-json)

- **Descrição**: Substituir `subprocess.run(capture_output=True)` por `Popen` com
  stdin/stdout abertos, usando `--input-format stream-json --output-format
  stream-json --verbose`. O contrato externo do plugin (`params`/`output`) não muda
  em relação à ADR-002.
- **Depende de**: Claude Code Runner existente (ADR-002-AT-02/AT-03)

**AC ADR-005-AC-01**
```
Dado que a etapa executa em modo coding ou review
Quando o plugin invoca a CLI
Então usa Popen (não subprocess.run bloqueante) com --input-format stream-json --output-format stream-json --verbose, e o output final retornado ao Engine (status, summary, docs_referenced, session_log_path) é idêntico em forma ao contrato já documentado na ADR-002-AC-04/AC-06 — nenhuma mudança visível para quem chama o plugin
```

---

### Atividade ADR-005-AT-02: Escrita incremental de `session_log_path`

- **Descrição**: Cada linha recebida do processo `claude` é imediatamente
  acrescentada a `session_log_path`, não só escrita ao final — torna o arquivo
  "tailable" em tempo real.
- **Depende de**: AT-01

**AC ADR-005-AC-02**
```
Dado uma sessão em andamento
Quando o processo claude emite uma linha de output
Então essa linha já está em session_log_path antes de a sessão terminar (verificável lendo o arquivo enquanto o processo ainda roda — não só depois que ele encerra)
```

**AC ADR-005-AC-03** (reforça ADR-002-AC-08)
```
Dado que a sessão falha (qualquer motivo)
Quando a falha é propagada ao Engine
Então session_log_path contém todas as linhas recebidas até o momento da falha (mesma garantia da ADR-002-AC-08, agora por escrita incremental em vez de só no finally)
```

---

### Atividade ADR-005-AT-03: Repasse de instrução para o processo vivo

- **Descrição**: Uma thread do plugin observa `<step_name>.instrucoes.jsonl`
  (mesmo diretório de `session_log_path`); cada linha nova vira uma mensagem de
  usuário escrita no stdin do processo `claude`, repassada enquanto a sessão está
  ativa.
- **Depende de**: AT-01

**AC ADR-005-AC-04**
```
Dado uma sessão ativa e uma linha nova aparecendo em <step_name>.instrucoes.jsonl
Quando o plugin detecta essa linha
Então escreve {"type":"user","message":{"role":"user","content":"<linha>"}} no stdin do processo claude, e a resposta subsequente do agente reflete essa instrução (comportamento verificado ao vivo nesta sessão: instrução "pare de contar, responda X" mudou o curso da resposta)
```

**AC ADR-005-AC-05**
```
Dado que a sessão termina (processo encerrado)
Quando uma escrita posterior acontece em <step_name>.instrucoes.jsonl
Então essa escrita não tem efeito — o plugin já parou de observar o arquivo, não fica pendurado esperando um processo que não existe mais
```

---

## Componente: API HTTP (extensão da ADR-004)

### Atividade ADR-005-AT-04: Stream ao vivo (`GET /runs/{chain_name}/stream`)

- **Descrição**: Resolver `session_log_path` da etapa `claude_code_runner`
  atualmente ativa para aquele `chain_name` (via `workflow_runs.config_path` +
  `step_executions` + carry-forward de `workspace_path`) e retransmitir via SSE.
- **Depende de**: Monitoria (ADR-004-AT-03), escrita incremental (AT-02)

**AC ADR-005-AC-06**
```
Dado um chain_name com uma etapa claude_code_runner em status "running"
Quando GET /runs/{chain_name}/stream é chamado
Então abre um stream SSE que emite cada linha nova de session_log_path conforme ela é escrita, incluindo o que já existia no arquivo no momento da conexão
```

**AC ADR-005-AC-07**
```
Dado um chain_name sem nenhuma etapa claude_code_runner em status "running" no momento
Quando GET /runs/{chain_name}/stream é chamado
Então responde 409 com {"error": {"code": "not_streamable", ...}}, sem abrir um stream vazio ou travado
```

---

### Atividade ADR-005-AT-05: Envio de instrução (`POST /runs/{chain_name}/instrucoes`)

- **Descrição**: Resolver `instructions_path` da mesma forma que AT-04 e acrescentar
  a mensagem recebida.
- **Depende de**: Repasse de instrução (AT-03)

**AC ADR-005-AC-08** (contrato de payload)
```
Dado uma etapa claude_code_runner ativa para chain_name
Quando POST /runs/{chain_name}/instrucoes com corpo {"mensagem": "<texto>"} é chamado
Então a mensagem é acrescentada ao arquivo de instruções daquela etapa, e a resposta é 202 (aceito — não espera o agente processar a instrução)
```

**AC ADR-005-AC-09**
```
Dado nenhuma etapa claude_code_runner ativa para chain_name
Quando POST /runs/{chain_name}/instrucoes é chamado
Então responde 409 com {"error": {"code": "not_interactable", ...}}
```

**AC ADR-005-AC-10** (RNF-01 — funciona cross-processo)
```
Dado uma execução disparada por `workflow run` no terminal (não pelo processo `serve`)
Quando GET /runs/{chain_name}/stream ou POST /runs/{chain_name}/instrucoes são chamados através do `serve` para aquele chain_name
Então funcionam exatamente igual a uma execução disparada pelo próprio `serve` — a resolução de caminho e o mecanismo de arquivo não distinguem quem disparou a execução
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-005 | AT-01 | AC-01 | Plugin Claude Code Runner | Pendente |
| RF-02 | ADR-005 | AT-02 | AC-02, AC-03 | Plugin Claude Code Runner | Pendente |
| RF-03 | ADR-005 | AT-03 | AC-04, AC-05 | Plugin Claude Code Runner | Pendente |
| RF-04 | ADR-005 | AT-04 | AC-06, AC-07 | API HTTP | Pendente |
| RF-05 | ADR-005 | AT-05 | AC-08, AC-09 | API HTTP | Pendente |
| RNF-01 | ADR-005 | AT-04, AT-05 | AC-10 | API HTTP | Pendente |
| RNF-02 | ADR-005 | AT-04, AT-05 | AC-07, AC-09 | API HTTP | Pendente |
| RNF-03 (herdado) | ADR-001/ADR-002 | — | — | (ver ADR-001/ADR-002) | N/A |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
