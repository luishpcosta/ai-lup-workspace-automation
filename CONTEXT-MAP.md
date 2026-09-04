# Context Map

## Contextos

- [motor-workflow](./docs/motor-workflow/CONTEXT.md) — motor de workflow local com
  plugins Python, mais seus pontos de entrada (CLI, HTTP) e observabilidade
  (execuções paralelas, monitoria, streaming)

## Relacionamentos

Repositório de contexto único — sem relacionamentos entre contextos ainda.

## Decisões (ADR)

- [Registro de decisões](./adr/) — ADR-001 a ADR-005, todas em `contextos:
  [motor-workflow]`. Ver `adr/ADR-00N-*.md` para o front matter de relação
  (`depende_de`/`afeta`/`supera`) de cada uma.

## Planejamento (to-be)

- **motor-workflow**: [specs](./specs/) — spec/plan/tasks por feature (harness SDD,
  `AGENTS.md`), uma pasta por feature numerada (`001-...` a `003-...` implementadas;
  `004-...`/`005-...` — API HTTP e streaming — ainda não especificadas em `specs/`,
  só decididas em ADR).
