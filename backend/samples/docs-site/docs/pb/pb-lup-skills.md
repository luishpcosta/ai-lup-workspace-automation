---
id: pb-lup-skills
title: "PB: lup-skills CLI"
sidebar_label: PB — lup-skills CLI
---

# Product Backlog: lup-skills CLI

> Fonte real: `~/developer/ai-tools/ai-lup-skills` (repositório central de skills de IA).
> Este PB agrega os itens já entregues (documentados em PRD/AC/Histórias) e os itens
> ainda pendentes de implementação.

## Visão do produto

O `lup-skills` é um CLI (Node.js + commander) que instala, lista, remove e atualiza
skills de IA em projetos locais, a partir de um repositório central de skills.
Suporta múltiplos agentes de destino (Claude, Devin, ...).

## Itens do backlog

| ID | Item | Status | Doc relacionado |
|----|------|--------|------------------|
| BL-01 | Comandos `add`/`list`/`remove` | Entregue (reverse-engineered) | [AC — CLI Comandos](/ac/ac-cli-commands) |
| BL-02 | Camada de utilitários (frontmatter/paths/skills) | Entregue (reverse-engineered) | [AC — CLI Utilitários](/ac/ac-cli-utils) |
| BL-03 | Comando `update` | Entregue (spec-first, verified) | [AC — CLI Update](/ac/ac-cli-update) |
| BL-04 | `list --json` (saída em JSON, para consumo por automação) | **Pendente** | [História HIST-004](/historias/historia-004-list-json) |

## Fora de escopo (conhecido)

- `update --all` (atualizar todas as skills de uma vez) — não planejado ainda.
- Comparação de versões / detecção de "já está atualizado" no `update`.
