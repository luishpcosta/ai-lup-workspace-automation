# Atividades e Acceptance Criteria — ADR-009

> Referência: `ADR-009-config-boot-runtime-pasta-trabalho.md`. Cada atividade pertence
> a um componente e tem 1+ AC vinculada. A AC de contrato (ADR-009-AC-06) descreve o
> contrato REST explicitamente — campos, tipos e regras elicitados na Fase 3.5.

## Componente: Frontend App

### Atividade ADR-009-AT-01: Defaults de boot lidos de arquivo estático em runtime

- **Descrição**: criar `frontend/public/painel-config.json` com `baseUrl`,
  `specsBaseUrl` e `reposRoot`, e fazer a SPA lê-lo por `fetch` no boot. Precedência:
  `localStorage` > `painel-config.json` > vazio. O arquivo é servido como asset
  estático (não passa pelo bundler), preservando o princípio 6 da constitution.
- **Depende de**: nada.

**AC ADR-009-AC-01**
```
Dado um navegador sem nada salvo em localStorage
E um public/painel-config.json com baseUrl e specsBaseUrl preenchidos
Quando a SPA é carregada
Então o painel abre direto na listagem de execuções, sem passar pela tela de configuração
```

**AC ADR-009-AC-02**
```
Dado um valor de baseUrl salvo em localStorage diferente do que está no painel-config.json
Quando a SPA é carregada
Então o valor usado é o do localStorage (o arquivo é default, não sobrescrita)
```

**AC ADR-009-AC-03**
```
Dado que public/painel-config.json está ausente, é inválido, ou não tem os campos obrigatórios
Quando a SPA é carregada
Então a tela de configuração é exibida normalmente, sem erro não tratado no console
```

### Atividade ADR-009-AT-02: Tela de configuração — redesenho e pasta de trabalho

- **Descrição**: acrescentar o campo "pasta de trabalho" (raiz de repositórios),
  persistido em `localStorage` junto das duas URLs; remover os placeholders que imitam
  valor real, distinguindo visualmente valor efetivo de sugestão; deixar visível de
  onde veio cada valor (salvo pelo usuário vs. default do arquivo) e permitir voltar ao
  default.
- **Depende de**: ADR-009-AT-01.

**AC ADR-009-AC-04**
```
Dado que o usuário abre a tela de configuração
Quando um campo está usando o valor default vindo do painel-config.json
Então a tela indica explicitamente que aquele valor é o default do arquivo, e não algo digitado
```

**AC ADR-009-AC-05**
```
Dado que o usuário informa uma pasta de trabalho e salva
Quando o seletor de repositórios é carregado
Então ele lista as subpastas daquela raiz, sem que o backend tenha sido reiniciado
E a raiz escolhida continua valendo após recarregar a página
```

---

## Componente: API HTTP (motor-workflow)

### Atividade ADR-009-AT-03: `GET /workspace/repos` aceita raiz por parâmetro de consulta

- **Descrição**: acrescentar o parâmetro de consulta opcional `root` a
  `GET /workspace/repos`. Ausente, o comportamento é o atual (raiz do processo).
  Presente, lista as subpastas imediatas do caminho informado.
- **Depende de**: nada.

**AC ADR-009-AC-06** (contrato REST)
```
Dado que o Frontend App chama a API HTTP via GET /workspace/repos
O parâmetro de consulta é: root: string, opcional
  - ausente  -> usa a raiz configurada no processo (--local-repos-root / LOCAL_REPOS_ROOT)
  - presente -> usa o caminho informado, ignorando a raiz do processo
A resposta de sucesso é: 200 com uma lista de objetos {name: string, path: string},
  ordenada por nome, contendo apenas subdiretórios imediatos
Os erros são: nenhum status de erro novo -> raiz inexistente, não-diretório, ou
  não configurada respondem 200 com lista vazia (mesma semântica já definida na
  ADR-007-AC-03, preservada para o caminho novo)
A leitura é idempotente por ser GET; nenhum estado do servidor é alterado pelo parâmetro
```

**AC ADR-009-AC-07** (retrocompatibilidade)
```
Dado um cliente que chama GET /workspace/repos sem o parâmetro root
Quando o backend está configurado com --local-repos-root
Então a resposta é idêntica à de antes desta ADR (ADR-007-AC-02 continua passando)
```

---

## Componente: CLI (motor-workflow)

### Atividade ADR-009-AT-04: `LOCAL_REPOS_ROOT` como fonte de default da raiz

- **Descrição**: o default de `--local-repos-root` em `serve` passa a ser
  `os.environ.get("LOCAL_REPOS_ROOT")`. A flag explícita continua tendo precedência
  sobre a variável.
- **Depende de**: nada.

**AC ADR-009-AC-08**
```
Dado LOCAL_REPOS_ROOT definido no ambiente e nenhuma flag --local-repos-root
Quando `workflow serve` sobe
Então GET /workspace/repos lista as subpastas da raiz vinda da variável

Dado LOCAL_REPOS_ROOT definido no ambiente E a flag --local-repos-root informada
Quando `workflow serve` sobe
Então a raiz usada é a da flag (a flag vence a variável)
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-009 | AT-01 | AC-01, AC-02, AC-03 | Frontend App | Pendente |
| RF-02 | ADR-009 | AT-04 | AC-08 | CLI (motor-workflow) | Pendente |
| RF-03 | ADR-009 | AT-02, AT-03 | AC-05, AC-06 | Frontend App, API HTTP | Pendente |
| RF-04 | ADR-009 | AT-02 | AC-04 | Frontend App | Pendente |
| RNF-01 | ADR-009 | AT-01 | AC-01, AC-02 | Frontend App | Pendente |
| RNF-02 | ADR-009 | AT-03 | AC-07 | API HTTP | Pendente |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
