#!/bin/bash
# Sobe o motor de workflow (backend, workflow serve) e o painel de controle
# (frontend, vite dev server) juntos, localmente. Ctrl+C encerra os dois.
#
# Uso:
#   ./start-local.sh
#   BACKEND_PORT=8010 FRONTEND_PORT=5183 ./start-local.sh
#   LOCAL_REPOS_ROOT=/caminho/com/varios/repos ./start-local.sh   (ADR-007: GET /workspace/repos)
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
# ADR-009 (AC-08): sem nada configurado, a raiz de repositórios é o diretório que
# contém este repo — na prática `local-workflow-pipeline`, onde ficam os repos-alvo.
# Derivado do caminho do próprio script, então não depende da máquina.
LOCAL_REPOS_ROOT="${LOCAL_REPOS_ROOT:-$(dirname "$ROOT_DIR")}"
LOG_DIR="$ROOT_DIR/.local-logs"
mkdir -p "$LOG_DIR"

BACKEND_PID=""
FRONTEND_PID=""
CLEANED_UP=""

cleanup() {
  [ -n "$CLEANED_UP" ] && return
  CLEANED_UP=1
  echo ""
  echo "Encerrando..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
  wait 2>/dev/null
  echo "Parado."
}
trap cleanup EXIT INT TERM

echo "=== Backend (workflow serve) ==="
cd "$ROOT_DIR/backend"
if ! python -c "import workflow_engine" 2>/dev/null; then
  echo "Pacote workflow_engine não encontrado — instalando (pip install -e .[dev])..."
  python -m pip install -e ".[dev]"
fi
SERVE_ARGS=(--port "$BACKEND_PORT")
[ -n "$LOCAL_REPOS_ROOT" ] && SERVE_ARGS+=(--local-repos-root "$LOCAL_REPOS_ROOT")
echo "  Raiz de repositórios: $LOCAL_REPOS_ROOT"
python -m workflow_engine.adapters.cli serve "${SERVE_ARGS[@]}" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  PID $BACKEND_PID — log em $LOG_DIR/backend.log"

echo "=== Frontend (vite dev server) ==="
cd "$ROOT_DIR/frontend"
if [ ! -d node_modules ]; then
  echo "node_modules ausente — rodando npm install..."
  npm install
fi
npm run dev -- --port "$FRONTEND_PORT" \
  > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  PID $FRONTEND_PID — log em $LOG_DIR/frontend.log"

sleep 2
echo ""
echo "Backend:  http://localhost:$BACKEND_PORT"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo ""
echo "Defaults do painel (ADR-009): frontend/public/painel-config.json — editável sem"
echo "rebuild; o painel sobe já configurado e a tela de Configuração só é forçada se"
echo "faltar algum campo obrigatório. A pasta de trabalho também pode ser trocada por lá."
echo ""
if [ ! -d "$LOCAL_REPOS_ROOT" ]; then
  echo "Aviso: '$LOCAL_REPOS_ROOT' não é um diretório — GET /workspace/repos vai retornar"
  echo "vazio. Ajuste com LOCAL_REPOS_ROOT=/caminho ./start-local.sh"
  echo ""
fi
echo "Ctrl+C para encerrar os dois processos."

wait
