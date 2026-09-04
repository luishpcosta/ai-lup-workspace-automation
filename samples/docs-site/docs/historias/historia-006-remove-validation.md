---
id: historia-006-remove-validation
title: "História: validação no remove"
sidebar_label: "HIST-006 — validação remove (pendente)"
---

# HIST-006: validação de nome vazio no `remove`

**Status: pendente de implementação** — usada para testar execuções paralelas
independentes (ADR-003), junto com HIST-005. Independente dela: só toca
`src/commands/remove.js`, HIST-005 só toca `index.js`.

Como usuário do `lup-skills`, quero que `lup-skills remove ""` (nome de skill vazio)
mostre uma mensagem de erro clara em vez de um comportamento confuso, para entender
imediatamente que preciso informar um nome de skill.

## Escopo

- Em `removeCommand` (`src/commands/remove.js`), se o nome da skill recebido for uma
  string vazia (ou só espaços), imprimir uma mensagem de erro clara (ex.: "Informe o
  nome da skill a remover.") e encerrar sem perguntar agentes nem tentar remover nada.
- Não altera o comportamento existente para um nome de skill válido (existente ou
  inexistente) — só o caso de nome vazio.

## Critérios de Aceite

- **AC-1** — Dado `lup-skills remove ""` (ou só espaços), quando executado, então
  imprime uma mensagem de erro clara e não pergunta agentes nem tenta remover nada.
- **AC-2** — O comportamento existente para nome de skill não-vazio (instalada ou não)
  não muda.
