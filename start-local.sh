#!/bin/bash
# Sobe o motor de workflow (backend, workflow serve) e o painel de controle
# (frontend, vite dev server) juntos, localmente. Ctrl+C encerra os dois.
#
# Uso:
#   ./start-local.sh
#   BACKEND_PORT=8010 FRONTEND_PORT=5183 ./start-local.sh
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
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
python -m workflow_engine.adapters.cli serve --port "$BACKEND_PORT" \
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
echo "Na primeira vez, configure no app (tela de Configuração):"
echo "  URL base do backend -> http://localhost:$BACKEND_PORT"
echo ""
echo "Ctrl+C para encerrar os dois processos."

wait
