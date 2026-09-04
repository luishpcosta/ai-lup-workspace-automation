---
id: historia-004-list-json
title: "História: list --json"
sidebar_label: "HIST-004 — list --json (pendente)"
---

# HIST-004: `list --json`

**Status: pendente de implementação** — este é o item real usado para testar a
automação (ADR-002) ponta a ponta contra `samples/target-cli`.

Como usuário do `lup-skills` que quer integrar a listagem de skills com outra
ferramenta (scripts, outra automação), quero rodar `lup-skills list --json` e receber
a lista de skills como um array JSON em vez do texto formatado, respeitando os mesmos
filtros `--language`/`--tag` que o `list` normal já aceita, para não precisar fazer
parsing de texto para consumir essa lista programaticamente.

## Escopo

- Nova flag `--json` no comando `list` existente (`cli/src/commands/list.js`).
- Quando `--json` é passado, a saída em stdout é um único array JSON (não o texto
  agrupado por linguagem) — um objeto por skill, com pelo menos `name`, `language` e
  `tags`.
- Os filtros `--language`/`--tag` já existentes continuam funcionando normalmente com
  `--json`.
- Sem `--json`, o comportamento atual (texto formatado, agrupado por linguagem) não
  muda.

## Fora de escopo

- Novos filtros além dos já existentes (`--language`, `--tag`).
- Formato JSON para os comandos `add`/`remove`/`update`.

## Critérios de Aceite

- **AC-1** — Dado que existem skills disponíveis, quando `lup-skills list --json` é
  executado sem outros filtros, então a saída em stdout é um array JSON válido, um
  item por skill, cada item com `name`, `language` e `tags`.
- **AC-2** — Dado `--json` combinado com `--language <x>`, então o array retornado
  contém só as skills daquela linguagem (mesmo filtro do `list` sem `--json`).
- **AC-3** — Dado `--json` combinado com `--tag <x>`, então o array retornado contém
  só as skills com aquela tag.
- **AC-4** — Dado que nenhuma skill está disponível (diretório vazio/inexistente),
  quando `--json` é passado, então a saída é um array JSON vazio (`[]`), não a
  mensagem de texto "Nenhuma skill disponível." (essa mensagem só faz sentido no modo
  texto).
- **AC-5** — Dado `--json` e um filtro que não retorna nenhuma skill, então a saída é
  `[]`, não a mensagem de texto "Nenhuma skill encontrada para o filtro informado.".
- **AC-6** — Sem a flag `--json`, o comportamento existente do `list` (texto agrupado
  por linguagem, mensagens de "nenhuma skill...") permanece inalterado — nenhuma AC de
  `AC — CLI Comandos` (AC-5 a AC-10) pode regredir.

PB relacionado: [PB — lup-skills CLI](/pb/pb-lup-skills) (item BL-04).
