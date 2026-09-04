---
id: adr-001-motor-workflow-plugins
title: "ADR-001: Motor de workflow local com plugins Python"
sidebar_label: ADR-001 — Motor de workflow
---

# ADR-001: Motor de workflow local com cadeia configurável de plugins Python

> Fonte completa: `adr/ADR-001-motor-workflow-plugins.md` neste repositório
> (ai-lup-workspace-automation). Reproduzido aqui como exemplo real de ADR consumível
> via MCP pela própria automação que esta documentação alimenta.

**Status**: Proposto · **Contexto**: motor-workflow

## Decisão

Motor de workflow em Python composto por: CLI, Chain Loader, Workflow Engine, Plugin
Registry, Plugin Interface (contrato), Retry Handler, State Store (SQLite) e Logger.
Workflows são declarados em arquivo de config (YAML/JSON) como uma cadeia ordenada de
etapas; cada etapa referencia um plugin descoberto automaticamente em um diretório
local.

**Contrato da Plugin Interface**: todo plugin implementa `run(context) -> output`.
`context` contém `input` (output da etapa anterior, ou `None`), `params` (dict da
config), `run_id` e `step_name`. Falha transitória (retriable): plugin levanta
`TransientError`; qualquer outra exceção é falha permanente.

## Componentes afetados

CLI, Chain Loader, Workflow Engine, Plugin Registry, Plugin Interface, Retry Handler,
State Store (SQLite), Logger.
