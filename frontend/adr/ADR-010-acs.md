# Atividades e Acceptance Criteria — ADR-010

> Referência: `ADR-010-refinamentos-ux-knowledge-bases-stream-legivel.md`. Cada
> atividade pertence a um componente e tem 1+ AC vinculada. A AC de contrato
> (ADR-010-AC-06) descreve o contrato REST explicitamente — campos, tipos e regras.

## Componente: Frontend App

### Atividade ADR-010-AT-01: Reposicionar o alternador de tema na topbar

- **Descrição**: mover `ThemeToggle` para o último elemento de `topbar__actions`,
  separado visualmente do grupo de botões ("Atualizar"/"Configurações") por um
  espaçamento maior (ou divisor sutil), em vez de intercalado entre eles.
- **Depende de**: nada.

**AC ADR-010-AC-01**
```
Dado o painel com a listagem de execuções aberta
Quando a topbar é renderizada
Então o alternador de tema aparece à direita de todos os botões de ação (nunca entre
  dois botões), com separação visual clara do grupo
```

### Atividade ADR-010-AT-02: `KnowledgeBasePicker` sobre `react-select`

- **Descrição**: reescrever `SpecPicker.jsx` usando `react-select` (`isMulti`), mantendo
  `fetchSpecsIndex`/`specsClient.js` como fonte de dado (inalterados) e o contrato de
  props (`id`, `value: string[]`, `onChange(nextValue: string[])`) que
  `DynamicParamsForm.jsx` já usa. Renomear os textos visíveis do componente
  (carregando/vazio/erro) para "Knowledge Base(s)" em vez de "spec(s)".
- **Depende de**: nada.

**AC ADR-010-AC-02**
```
Dado o backend de specs remotas retornando uma lista de itens
Quando o campo "Knowledge Bases" é renderizado
Então ele aparece como um combobox em barra com busca (react-select), não como lista
  de checkboxes
E múltiplos itens podem ser selecionados, cada um removível individualmente
```

**AC ADR-010-AC-03**
```
Dado o valor atual do campo (array de ids já selecionados)
Quando o usuário seleciona ou remove um item pelo combobox
Então onChange é chamado com o novo array de ids, na mesma forma que o contrato
  anterior (compatível com DynamicParamsForm/TriggerForm, sem mudança no payload
  enviado ao motor)
```

### Atividade ADR-010-AT-03: Rótulo "Knowledge Bases" no template

- **Descrição**: alterar `docs_referenced.label` em
  `backend/config/workflow_templates/claude-implementar-local.yaml` de "Specs de
  referência" para "Knowledge Bases". `param.name`/`source` não mudam.
- **Depende de**: nada.

**AC ADR-010-AC-04**
```
Dado o template claude-implementar-local carregado pelo GET /workflows
Quando o formulário de disparo é renderizado
Então o rótulo do campo de referência de conhecimento é "Knowledge Bases"
```

### Atividade ADR-010-AT-04: `StreamPanel` — leitura formatada por padrão, log bruto por opção

- **Descrição**: `StreamPanel.jsx` recebe o `plugin` do step em execução (via
  `RunDetail.jsx`, que já tem `detail.steps`); escolhe um formatador por `plugin` a
  partir de um registro pequeno. Para `claude_code_runner`, usa
  `lib/claudeStream.js` (novo) para transformar as linhas `stream-json` em turnos
  (texto, rastro de ferramenta com status/detalhe expansível, resumo final). Sem
  formatador para o `plugin`, ou linha não reconhecida como JSON, cai no log bruto
  para aquele conteúdo. Um controle no cabeçalho do painel ("Ver log bruto"/"Ver
  leitura formatada") alterna entre os dois modos a qualquer momento.
- **Depende de**: ADR-010-AT-05 (precisa de `plugin` vindo da API).

**AC ADR-010-AC-05**
```
Dado um step em execução cujo plugin é claude_code_runner, emitindo linhas
  stream-json (system/user/assistant/result)
Quando o stream ao vivo é aberto
Então, por padrão, o painel mostra texto da IA como prosa e cada tool_use como um
  rastro rotulado com nome + status (executando/concluído/falhou) + detalhe
  expansível — não o JSON bruto por linha
```

**AC ADR-010-AC-06**
```
Dado o painel em modo de leitura formatada
Quando o usuário aciona "Ver log bruto"
Então o painel troca para a exibição linha-a-linha já existente (<pre>), preservando
  todas as linhas recebidas até o momento
E acionar "Ver leitura formatada" volta ao modo anterior sem perder linhas
```

**AC ADR-010-AC-07** (degradação segura)
```
Dado uma linha do stream que não é JSON válido, ou um plugin sem formatador
  dedicado no registro
Quando o painel tenta renderizar a leitura formatada
Então aquela linha (ou o step inteiro, se o plugin for desconhecido) aparece no modo
  bruto, sem lançar erro não tratado nem quebrar o restante do painel
```

---

## Componente: API HTTP (motor-workflow)

### Atividade ADR-010-AT-05: `GET /runs/{chain_name}` passa a incluir `plugin` por etapa

- **Descrição**: `get_run_detail` (`http_api.py`) resolve o `plugin` de cada
  `step_execution` a partir do `config_path` já persistido em `workflow_runs`, usando
  `YamlJsonChainLoader` (mesma técnica de `_resolve_active_claude_step`, ADR-005).
  Se o YAML não puder ser recarregado (removido, inválido), `plugin` vem como `null`
  para aquele step em vez de falhar a resposta inteira.
- **Depende de**: nada.

**AC ADR-010-AC-08** (contrato REST)
```
Dado que o Frontend App chama a API HTTP via GET /runs/{chain_name}
Nenhum parâmetro de consulta novo é introduzido por esta atividade
A resposta de sucesso é: 200 com o mesmo formato de hoje, e cada item de "steps"
  ganha o campo adicional "plugin": string | null
  - string -> nome do plugin declarado para aquele step no YAML da chain
    (ex.: "claude_code_runner", "git_pr")
  - null   -> config_path do run não pôde ser recarregado (arquivo ausente/inválido)
    ou o step_name não existe mais no YAML atual
Os erros são: nenhum status de erro novo — mesmos 404 (not_found) de hoje para
  chain_name desconhecido
A leitura é idempotente por ser GET; nenhum estado do servidor é alterado
```

**AC ADR-010-AC-09** (retrocompatibilidade)
```
Dado um cliente existente que ignora campos desconhecidos no JSON de resposta
Quando ele chama GET /runs/{chain_name} depois desta mudança
Então todo campo que já existia antes (chain_name, run_id, status, created_at,
  updated_at, steps[].step_name/status/attempt_count/started_at/finished_at/
  error_message, e input/output quando include=io) continua presente, com o mesmo
  nome e tipo de antes — só "plugin" é novo
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-010 | AT-01 | AC-01 | Frontend App | Concluído |
| RF-02 | ADR-010 | AT-02, AT-03 | AC-02, AC-03, AC-04 | Frontend App | Concluído |
| RF-03 | ADR-010 | AT-05 | AC-08 | API HTTP | Concluído |
| RF-04 | ADR-010 | AT-04 | AC-05 | Frontend App | Concluído |
| RF-05 | ADR-010 | AT-04 | AC-06 | Frontend App | Concluído |
| RNF-01 | ADR-010 | AT-05 | AC-08, AC-09 | API HTTP | Concluído |
| RNF-02 | ADR-010 | AT-04 | AC-07 | Frontend App | Concluído |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
