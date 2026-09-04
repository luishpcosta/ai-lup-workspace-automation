# Project Constitution

Non-negotiable principles for this repository (contexto `frontend`, ver
`../CONTEXT-MAP.md`). Plans and code must comply; conflicts are escalated a um
humano, nunca contornados silenciosamente.

## Principles

1. **Spec before code** — Nenhuma implementação começa antes de a feature ter um
   spec aprovado e passar o gate de Tasks.
2. **Every behavior is traceable** — Cada critério de aceite mapeia para uma
   tarefa e para evidência de verificação.
3. **Verification is mandatory** — Uma feature só está pronta quando seus
   critérios de aceite são provados por checagem automatizada (ou evidência
   manual explicitamente registrada).
4. **Small, reversible steps** — Uma feature e uma tarefa por vez; manter o
   repositório reiniciável.
5. **Contrato REST é do backend, não do frontend** — Nenhuma mudança de payload,
   rota ou contrato de erro das ADRs do `motor-workflow` (ADR-004/ADR-005) é
   assumida ou proposta a partir daqui; qualquer necessidade de rota nova exige
   uma ADR própria, revisitando `afeta: [motor-workflow]` (ver ADR-006).
6. **Configuração é sempre em runtime, nunca no bundle** — URL base do backend e
   diretório-base de configs (ADR-006, RF-01) são valores configurados pelo
   usuário e persistidos em `localStorage`; nunca hardcoded no build.

## Technical Constraints

- **Language / stack**: React + Vite (ADR-006). Framework de teste, linter e uso
  de TypeScript ainda não decididos — a definir na atividade ADR-006-AT-01
  (scaffold), antes de `init.sh` ter comandos de verificação reais.
- **Test framework**: `<a definir no AT-01>`
- **Style / lint**: `<a definir no AT-01>`
- **Architecture boundaries**: SPA de processo único, sem estado compartilhado
  com o backend além de REST/SSE; nenhum dado sensível fora de `localStorage`
  (sem autenticação nesta versão, ADR-006 RNF-01).

## Quality Bar

- Verification command(s) que devem passar: `./init.sh` (hoje um placeholder —
  `echo "No package manifest detected..."` — até o scaffold do AT-01 existir).
- Coverage / review expectations: toda AC de
  `docs/specs/006-frontend-painel-controle/spec.md` precisa de evidência antes
  de a feature ser marcada `done` em `tasks.md`.

## Amendments

Mudar esta constituição exige uma decisão explícita registrada em
`progress.md` (data, motivo, quem aprovou).
