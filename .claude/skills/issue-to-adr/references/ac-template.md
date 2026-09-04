# Atividades e Acceptance Criteria — ADR-XXX

> Referência: `ADR-XXX-titulo.md`. Cada atividade pertence a um componente e
> tem 1+ AC vinculada. ACs de contrato (API/evento/schema) devem descrever o
> contrato explicitamente — campos, tipos e regras elicitados na Fase 3.5
> (ver `contrato-payload.md`), não apenas "deve funcionar".

## Componente: <nome-do-componente>

### Atividade ADR-XXX-AT-01: <título da atividade>

- **Descrição**: <o que precisa ser feito, objetivamente>
- **Depende de**: <outra atividade ou componente, se houver>

**AC ADR-XXX-AC-01**
```
Dado <contexto/pré-condição>
Quando <ação>
Então <resultado esperado, verificável objetivamente>
```

**AC ADR-XXX-AC-02** (se houver contrato REST entre componentes)
```
Dado que <componente A> chama <componente B> via <método> <endpoint>
O payload de request tem os campos: <campo: tipo, obrigatório/opcional>
A resposta de sucesso é: <status code> com os campos: <campo: tipo>
Os erros são: <status code> -> <formato do corpo de erro> quando <cenário>
A escrita é idempotente via: <chave de idempotência ou semântica do método>
```

**AC ADR-XXX-AC-03** (se houver contrato de mensageria/evento)
```
Dado que <componente A> publica o evento <nome> no tópico/fila <id>
Consumidores conhecidos (informados pelo usuário): <lista, ou "nenhum informado">
O schema é versionado por: <campo de versão / convenção>
Campos novos em relação à versão anterior são opcionais: <sim, quais>
O consumidor trata duplicidade via: <chave de deduplicação>
Após <N> falhas a mensagem vai para a DLQ <nome>, reprocessada por: <quem>
```

---

## Componente: <próximo-componente>

### Atividade ADR-XXX-AT-02: <título>
...

---

## Tabela de rastreabilidade

| Requisito (PRD) | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-XXX | AT-01 | AC-01, AC-02 | <componente> | Pendente |
| RNF-01 | ADR-XXX | AT-02 | AC-03 | <componente> | Pendente |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado). Isso é o que permite a uma IA (ou a
> outro humano) auditar depois se o PRD foi de fato atendido ponta a ponta.
