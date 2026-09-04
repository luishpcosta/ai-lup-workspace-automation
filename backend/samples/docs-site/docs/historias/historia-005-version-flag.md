---
id: historia-005-version-flag
title: "História: --version flag"
sidebar_label: "HIST-005 — --version (pendente)"
---

# HIST-005: flag `--version`

**Status: pendente de implementação** — usada para testar execuções paralelas
independentes (ADR-003), junto com HIST-006.

Como usuário do `lup-skills`, quero rodar `lup-skills --version` e ver a versão do
pacote (de `package.json`) impressa no terminal, para não precisar abrir o
`package.json` manualmente pra saber qual versão está instalada.

## Escopo

- Adicionar a opção `--version`/`-V` na definição do programa em `index.js`
  (`commander` já suporta isso nativamente via `.version(...)`).
- Só toca `index.js` — não deve alterar nenhum arquivo em `src/`.

## Critérios de Aceite

- **AC-1** — Dado `lup-skills --version` (ou `-V`), quando executado, então imprime a
  versão declarada em `package.json` e encerra sem rodar nenhum comando.
- **AC-2** — O comportamento dos comandos existentes (`add`/`list`/`remove`/`update`)
  não muda.
