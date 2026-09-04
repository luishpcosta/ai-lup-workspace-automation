---
id: adr-002-plugins-poc-pipeline-sdd
title: "ADR-002: Plugins de POC — pipeline SDD ponta a ponta"
sidebar_label: ADR-002 — Plugins POC
---

# ADR-002: Plugins de prova de conceito — pipeline SDD ponta a ponta

> Fonte completa: `adr/ADR-002-plugins-poc-pipeline-sdd.md` neste repositório
> (ai-lup-workspace-automation). Depende de [ADR-001](/adr/adr-001-motor-workflow-plugins).

**Status**: Proposto · **Contexto**: motor-workflow

## Decisão

Quatro plugins novos, todos implementando o contrato `run(context) -> output` da
ADR-001: **Workspace Setup** (prepara repo/branch/infra), **Claude Code Runner**
(invoca o Claude Code CLI em modo `coding` ou `review`, com MCP apontando para esta
própria documentação), **Shell/Script Runner** (executa scripts de polling) e
**Git/PR** (cria/atualiza PR via `gh`, com validação obrigatória de rastreabilidade
antes de abrir a PR).

Este site de documentação (com `docusaurus-plugin-mcp-server`) é exatamente o servidor
MCP que o Claude Code Runner usa para buscar História/ADR/AC/PRD ao implementar uma
história — é a origem de dados descrita nesta ADR.

## Componentes afetados

Plugin Workspace Setup, Plugin Claude Code Runner, Plugin Shell/Script Runner, Plugin
Git/PR, Logger (estendido), Chain Loader (estendido — bloco `vars:`).
