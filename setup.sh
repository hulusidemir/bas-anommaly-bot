#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Basketbol Anomali Tespit Sistemi — Linux/Mac Kurulum Scripti
# ──────────────────────────────────────────────────────────────
set -e

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJ_DIR/venv"

echo "📦 Sanal ortam oluşturuluyor..."
python3 -m venv "$VENV_DIR"

echo "🔧 Sanal ortam aktif ediliyor..."
source "$VENV_DIR/bin/activate"

echo "⬆️  pip güncelleniyor..."
pip install --upgrade pip

echo "📥 Backend bağımlılıkları yükleniyor..."
pip install -r "$PROJ_DIR/backend/requirements.txt"

echo "📥 Frontend bağımlılıkları yükleniyor..."
cd "$PROJ_DIR/frontend" && npm install

cd "$PROJ_DIR"
echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo "Kullanım:"
echo "  source venv/bin/activate"
echo "  cd backend"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
