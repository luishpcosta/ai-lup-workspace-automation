---
id: ac-cli-update
title: "AC: CLI — Comando update"
sidebar_label: AC — CLI Update
---

# AC: CLI — Comando `update`

> Reproduzido de `~/developer/ai-tools/ai-lup-skills/specs/003-cli-update/spec.md`
> (feature `003-cli-update`, fase `verified`, spec-first).
> Fonte: `cli/src/commands/update.js` · Teste: `cli/test/update.test.js`

- **AC-1** — `updateCommand` exibe erro e encerra com `exitCode 1` quando a skill não
  existe no repositório central (e não pergunta agentes).
- **AC-2** — `updateCommand` oferece todos os agentes suportados na seleção, estejam a
  skill instalada neles ou não.
- **AC-3** — `updateCommand` não altera nada quando nenhum agente é selecionado.
- **AC-4** — `updateCommand` substitui a versão antiga pela nova nos agentes onde a
  skill já existe, removendo arquivos obsoletos.
- **AC-5** — `updateCommand` instala a skill no agente selecionado que ainda não a
  possui.

PRD relacionado: [PRD — comando update](/prd/prd-cli-update).
