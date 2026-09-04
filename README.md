# ai-lup-workspace-automation

Motor de workflow local que orquestra uma cadeia configurável de etapas via
plugins Python (ex.: chamar o Claude Code, `git`/`gh`, um script), mais um
painel de controle web para disparar, visualizar e interagir com essas
execuções. Monorepo com dois contextos independentes, cada um com seu próprio
harness de desenvolvimento (SDD — spec-driven development).

## Estrutura do repositório

```
.
├── backend/                  # motor de workflow (Python) — o "server"
│   ├── src/workflow_engine/  # domain/ (entidades+ports) -> application/ -> adapters/ (CLI, HTTP, plugins)
│   ├── plugins/               # plugins descobertos em runtime (workspace_setup, claude_code_runner, git_pr, ...)
│   ├── tests/                 # pytest
│   ├── adr/                   # decisões de arquitetura deste contexto (ADR-001 a ADR-005)
│   ├── docs/
│   │   ├── motor-workflow/CONTEXT.md   # glossário/vocabulário do contexto
│   │   └── specs/NNN-slug/             # spec/plan/tasks por feature (harness SDD)
│   ├── samples/, examples/    # configs de chain (.yaml) de exemplo/teste real
│   ├── AGENTS.md, constitution.md, init.sh, progress.md  # harness SDD deste contexto
│   └── pyproject.toml
│
├── frontend/                  # painel de controle web (React + Vite) — o "client"
│   ├── src/
│   │   ├── lib/                # config.js, apiClient.js, resolveConfigPath.js
│   │   └── components/         # SettingsScreen, RunsList, RunDetail, TriggerForm, StreamPanel, InstructionBox
│   ├── adr/                    # decisões de arquitetura deste contexto (ADR-006)
│   ├── docs/
│   │   ├── CONTEXT.md
│   │   └── specs/006-frontend-painel-controle/
│   ├── AGENTS.md, constitution.md, init.sh, progress.md  # harness SDD deste contexto
│   └── package.json
│
├── CONTEXT-MAP.md             # mapa dos dois contextos, suas relações e onde estão as ADRs
├── start-local.sh             # sobe backend + frontend juntos, localmente
└── .gitignore
```

Cada pasta (`backend/`, `frontend/`) é dona da sua própria stack, testes e
decisões — a numeração das ADRs é global e sequencial entre as duas (ver
`CONTEXT-MAP.md`), mas o resto é independente.

## Pré-requisitos

- **Backend**: Python >= 3.10
- **Frontend**: Node.js >= 20.9 e npm

## Como rodar

### Opção rápida: os dois juntos

```bash
./start-local.sh
```

Sobe `workflow serve` (porta 8000) e o dev server do Vite (porta 5173),
imprime as duas URLs e encerra os dois com `Ctrl+C`. Instala dependências
automaticamente na primeira vez se ainda não existirem (`pip install -e
".[dev]"` dentro de `backend/`, `npm install` dentro de `frontend/`). Portas
configuráveis:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5183 ./start-local.sh
```

Depois de subir, abra `http://localhost:5173` e, na tela de Configuração,
informe a URL base do backend (`http://localhost:8000`) e um diretório-base
de configs (ver "Disparando uma execução" abaixo).

### Manual — backend

```bash
cd backend
python -m pip install -e ".[dev]"   # uma vez
./init.sh                            # verificação: pytest + ruff

# rodar uma cadeia até o fim
python -m workflow_engine.adapters.cli run examples/implementar-historia-sdd.yaml

# rodar várias cadeias independentes em paralelo
python -m workflow_engine.adapters.cli run-many chain-a.yaml chain-b.yaml

# subir a API HTTP (consumida pelo frontend)
python -m workflow_engine.adapters.cli serve --port 8000
```

(O pacote também instala o script `workflow` no seu ambiente Python — se
estiver no PATH, `workflow run ...` funciona igual a
`python -m workflow_engine.adapters.cli run ...`.)

### Manual — frontend

```bash
cd frontend
npm install       # uma vez
npm run dev       # http://localhost:5173
./init.sh         # verificação: vitest + build + lint
```

### Disparando uma execução pelo painel

O formulário de disparo pede o **ID de um documento de referência**, não um
caminho de arquivo. A SPA resolve isso sozinha por convenção exata de nome:
`<diretório-base configurado>/<id>.yaml` — o arquivo precisa já existir nesse
caminho (ver `backend/samples/*.yaml` para exemplos reais de chain config).

## Onde encontrar mais

- **Decisões de arquitetura**: `backend/adr/` (motor-workflow, ADR-001 a
  ADR-005) e `frontend/adr/` (frontend, ADR-006) — ver `CONTEXT-MAP.md` para o
  mapa completo e as relações entre os dois contextos.
- **Specs por feature** (o que foi implementado e como foi verificado):
  `backend/docs/specs/` e `frontend/docs/specs/`.
- **Como este repositório é trabalhado** (harness SDD — spec antes de código,
  gates entre fases): `backend/AGENTS.md` e `frontend/AGENTS.md`.
