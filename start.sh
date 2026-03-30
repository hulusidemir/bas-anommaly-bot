#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Basketbol Anomali Tespit Sistemi — Tek Komutla Başlatma
# Backend (FastAPI) + Frontend (Vite) aynı anda çalışır.
# ──────────────────────────────────────────────────────────────
set -e

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJ_DIR/venv"

# venv varsa aktive et
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

cleanup() {
    echo ""
    echo "🛑 Servisler durduruluyor..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo "Tamamlandı."
}
trap cleanup EXIT INT TERM

# Backend
echo "🚀 Backend başlatılıyor (port 8000)..."
cd "$PROJ_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend
echo "🚀 Frontend başlatılıyor (port 5173)..."
cd "$PROJ_DIR/frontend"
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Dashboard  →  http://localhost:5173"
echo "  API        →  http://localhost:8000/api/health"
echo "  WebSocket  →  ws://localhost:8000/ws"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Durdurmak için Ctrl+C"

wait
