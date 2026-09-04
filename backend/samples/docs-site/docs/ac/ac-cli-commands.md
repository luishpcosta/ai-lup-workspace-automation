---
id: ac-cli-commands
title: "AC: CLI — Comandos (add/list/remove)"
sidebar_label: AC — CLI Comandos
---

# AC: CLI — Comandos (add/list/remove)

> Reproduzido de `~/developer/ai-tools/ai-lup-skills/specs/001-cli-commands/spec.md`
> (feature `001-cli-commands`, reverse-engineered a partir do código e dos testes
> existentes em `cli/src/commands/{add,list,remove}.js`).

## Comando `add`

Fonte: `cli/src/commands/add.js` · Teste: `cli/test/add.test.js`

- **AC-1** — `addCommand` exibe erro quando a skill não existe.
- **AC-2** — `addCommand` não copia nada quando nenhum agente é selecionado.
- **AC-3** — `addCommand` copia a skill para os agentes selecionados.
- **AC-4** — `addCommand` encontra skill aninhada em categoria e instala de forma plana.

## Comando `list`

Fonte: `cli/src/commands/list.js` · Teste: `cli/test/list.test.js`

- **AC-5** — `listCommand` mostra "Nenhuma skill disponível." quando o diretório não existe.
- **AC-6** — `listCommand` agrupa por language seguindo o frontmatter, não as pastas.
- **AC-7** — `listCommand` filtra por `--language`.
- **AC-8** — `listCommand` filtra por `--tag`.
- **AC-9** — `listCommand` informa quando o filtro não retorna nada.
- **AC-10** — `listCommand` mostra "Nenhuma skill disponível." quando o diretório está vazio.

## Comando `remove`

Fonte: `cli/src/commands/remove.js` · Teste: `cli/test/remove.test.js`

- **AC-11** — `removeCommand` informa quando a skill não está instalada.
- **AC-12** — `removeCommand` não remove nada quando nenhum agente é selecionado.
- **AC-13** — `removeCommand` remove a skill dos agentes selecionados.
