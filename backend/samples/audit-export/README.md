# Audit export — HIST-004 real run (2026-09-04)

Snapshot exportado de `workflow_state.db` (SQLite, gerado pelo motor — ADR-001, Data
Model) para o `run_id` `abddb3a1-1392-4acb-81e1-2cf058bf6618`, a execução real que
abriu https://github.com/luishpcosta/ai-lup-poc-target-cli/pull/1.

- `workflow_runs.csv` — 1 linha: a execução da cadeia `hist-004-list-json`.
- `step_executions.csv` — 5 linhas, uma por etapa (`preparar_ambiente`,
  `implementar_historia`, `abrir_pr`, `aguardar_checks`, `revisar_pr`), com `input`/
  `output` completos em JSON por célula (não truncados), `attempt_count`,
  `started_at`/`finished_at`, `error_message`.

É um snapshot pontual, não atualiza sozinho. Pra reexportar depois de uma nova
execução:

```python
import sqlite3, csv

conn = sqlite3.connect("workflow_state.db")
conn.row_factory = sqlite3.Row

for table in ("workflow_runs", "step_executions"):
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    with open(f"samples/audit-export/{table}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(list(r))
```
