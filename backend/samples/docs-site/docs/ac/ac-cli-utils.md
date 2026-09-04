---
id: ac-cli-utils
title: "AC: CLI — Utilitários (frontmatter/paths/skills)"
sidebar_label: AC — CLI Utilitários
---

# AC: CLI — Utilitários (frontmatter/paths/skills)

> Reproduzido de `~/developer/ai-tools/ai-lup-skills/specs/002-cli-utils/spec.md`
> (feature `002-cli-utils`, reverse-engineered).

## Leitura de frontmatter (`readSkillMetadata`)

Fonte: `cli/src/utils/frontmatter.js` · Teste: `cli/test/frontmatter.test.js`

- **AC-1** — lê `language` e `tags` inline aninhados sob `metadata`.
- **AC-2** — lê `language` com aspas e `tags` em bloco sob `metadata`.
- **AC-3** — também tolera `language` e `tags` no topo do frontmatter.
- **AC-4** — campos ausentes retornam valores neutros.
- **AC-5** — sem frontmatter retorna valores neutros.
- **AC-6** — sem arquivo `SKILL.md` retorna valores neutros.
- **AC-7** — tags em bloco param na primeira linha que não é item.
- **AC-8** — `language` vazio é tratado como ausente.

## Resolução de caminhos (`getSkillTargetPath`/`AGENT_TARGETS`)

Fonte: `cli/src/utils/paths.js` · Teste: `cli/test/paths.test.js`

- **AC-9** — `getSkillTargetPath` resolve o caminho para o agente Claude.
- **AC-10** — `getSkillTargetPath` resolve o caminho para o agente Devin.
- **AC-11** — `getSkillTargetPath` lança erro para agente desconhecido.
- **AC-12** — `AGENT_TARGETS` contém `claude` e `devin`.

## Descoberta de skills (`discoverSkills`/`findSkill`)

Fonte: `cli/src/utils/skills.js` · Teste: `cli/test/skills.test.js`

- **AC-13** — `discoverSkills` retorna `[]` quando o diretório não existe.
- **AC-14** — `discoverSkills` acha skills na raiz e aninhadas em categorias.
- **AC-15** — `discoverSkills` não desce dentro de uma skill (ignora `scripts/`).
- **AC-16** — `findSkill` encontra a skill pelo nome.
- **AC-17** — `findSkill` retorna `undefined` quando não existe.
- **AC-18** — `findSkill` lança erro em caso de nome ambíguo.
