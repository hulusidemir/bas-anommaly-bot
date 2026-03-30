"""
WebSocket Yöneticisi — Dashboard istemcilerine anlık veri yayını yapar.

Bağlı tüm istemcilere DashboardFrame gönderir.
Veritabanından her maçın en son kaydını çekerek yayınlayabilir.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Set

from fastapi import WebSocket

import database as db

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Bağlı WebSocket istemcilerini yönetir ve broadcast yapar."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket bağlantısı açıldı. Aktif: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket bağlantısı kapandı. Aktif: %d", len(self._connections))

    async def broadcast_json(self, payload: dict) -> None:
        """Tüm bağlı istemcilere JSON mesaj gönderir."""
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)

    async def broadcast_from_db(self) -> None:
        """
        SQLite'tan her maç için son kaydı çeker ve
        tüm istemcilere JSON olarak yayınlar.
        """
        rows = await db.get_latest_logs()
        payload = {
            "matches_from_db": rows,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast_json(payload)

    @property
    def active_count(self) -> int:
        return len(self._connections)
