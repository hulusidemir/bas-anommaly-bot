"""
FastAPI Ana Uygulama — HTTP endpoint'leri, WebSocket, arka plan görevi.

Çalıştırma:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from calculator import Calculator
from anomaly import AnomalyDetector
from config import settings
import database as db
from data_fetcher import DataFetcher
from models import DashboardFrame, MatchAnalysis, MatchRaw
from telegram_notifier import TelegramNotifier
from websocket_manager import WebSocketManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Servisler ────────────────────────────────────────────────────────────────

calculator = Calculator()
detector = AnomalyDetector()
notifier = TelegramNotifier()
fetcher = DataFetcher()
ws_manager = WebSocketManager()

# Son hesaplanan analizler (bellek önbelleği)
_latest_analyses: List[MatchAnalysis] = []


# ── Arka Plan Döngüsü ───────────────────────────────────────────────────────

async def _tick() -> None:
    """Tek bir döngü adımı: veri çek → hesapla → DB'ye yaz → anomali değerlendir → yayınla."""
    global _latest_analyses

    raw_matches: List[MatchRaw] = await fetcher.fetch_live_matches()
    analyses: List[MatchAnalysis] = []

    for raw in raw_matches:
        analysis = await calculator.analyze(raw)
        analysis = await detector.evaluate(analysis, raw)
        await notifier.notify_if_needed(analysis)
        analyses.append(analysis)

    _latest_analyses = analyses

    frame = DashboardFrame(
        matches=analyses,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    await ws_manager.broadcast_json(frame.model_dump())
    logger.info(
        "Döngü tamamlandı — %d maç işlendi, %d WS istemcisi.",
        len(analyses),
        ws_manager.active_count,
    )


async def _background_loop() -> None:
    """Her DATA_FETCH_INTERVAL saniyede bir _tick çalıştıran sonsuz döngü."""
    interval = settings.data_fetch_interval_sec
    logger.info("Arka plan döngüsü başladı (her %d saniye).", interval)
    while True:
        try:
            await _tick()
        except Exception:
            logger.exception("Döngü hatası")
        await asyncio.sleep(interval)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    task = asyncio.create_task(_background_loop())
    yield
    task.cancel()
    await fetcher.close()
    await db.close_db()


# ── FastAPI Uygulaması ───────────────────────────────────────────────────────

app = FastAPI(
    title="Basketbol Anomali Tespit Sistemi",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HTTP Endpoint'leri ───────────────────────────────────────────────────────

@app.get("/api/matches", response_model=List[MatchAnalysis])
async def get_matches():
    """Son hesaplanan maç analizlerini döndürür."""
    return _latest_analyses


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "active_ws": ws_manager.active_count,
        "tracked_matches": len(_latest_analyses),
    }


@app.get("/api/matches/db")
async def get_matches_from_db():
    """SQLite'tan her maç için son kaydı döndürür."""
    return await db.get_latest_logs()


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # İlk bağlantıda mevcut veriyi gönder
        if _latest_analyses:
            frame = DashboardFrame(
                matches=_latest_analyses,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            await ws.send_json(frame.model_dump())
        # Bağlantı açık kaldığı sürece bekle
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)
