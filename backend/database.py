"""
SQLite Veritabanı Katmanı — aiosqlite ile asenkron I/O.

Tablolar:
  - matches       : Maç ana bilgileri
  - match_logs    : Her 30 sn'de bir yazılan zaman serisi kayıtları
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "anomaly_bot.db"


# ── Tablo Oluşturma ─────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    match_id       TEXT PRIMARY KEY,
    home_team      TEXT NOT NULL,
    away_team      TEXT NOT NULL,
    opening_total  REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS match_logs (
    log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id         TEXT    NOT NULL,
    timestamp        TEXT    NOT NULL DEFAULT (datetime('now')),
    played_minutes   REAL    NOT NULL,
    current_score    INTEGER NOT NULL,
    current_ppm      REAL    NOT NULL,
    live_projection  REAL    NOT NULL,
    live_total_odds  REAL    NOT NULL,
    fair_value       REAL    NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches(match_id)
);

CREATE INDEX IF NOT EXISTS idx_logs_match_ts
    ON match_logs (match_id, timestamp DESC);
"""


# ── Bağlantı Yönetimi ───────────────────────────────────────────────────────

_db: Optional[aiosqlite.Connection] = None


async def init_db() -> None:
    """Veritabanını aç ve tabloları oluştur."""
    global _db
    _db = await aiosqlite.connect(str(DB_PATH))
    _db.row_factory = aiosqlite.Row
    await _db.executescript(_SCHEMA_SQL)
    await _db.commit()
    logger.info("SQLite veritabanı hazır: %s", DB_PATH)


async def close_db() -> None:
    """Veritabanı bağlantısını kapat."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("SQLite bağlantısı kapatıldı.")


def _get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Veritabanı henüz başlatılmadı — init_db() çağrılmalı.")
    return _db


# ── matches Tablosu ──────────────────────────────────────────────────────────

async def upsert_match(
    match_id: str, home_team: str, away_team: str, opening_total: float
) -> None:
    """Maçı kaydet veya güncelle (INSERT OR REPLACE)."""
    db = _get_db()
    await db.execute(
        """
        INSERT INTO matches (match_id, home_team, away_team, opening_total)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(match_id) DO UPDATE SET
            home_team     = excluded.home_team,
            away_team     = excluded.away_team,
            opening_total = excluded.opening_total
        """,
        (match_id, home_team, away_team, opening_total),
    )
    await db.commit()


# ── match_logs Tablosu ───────────────────────────────────────────────────────

async def insert_log(
    match_id: str,
    played_minutes: float,
    current_score: int,
    current_ppm: float,
    live_projection: float,
    live_total_odds: float,
    fair_value: float,
) -> None:
    """Yeni bir zaman serisi kaydı ekler."""
    db = _get_db()
    await db.execute(
        """
        INSERT INTO match_logs
            (match_id, played_minutes, current_score, current_ppm,
             live_projection, live_total_odds, fair_value)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (match_id, played_minutes, current_score, current_ppm,
         live_projection, live_total_odds, fair_value),
    )
    await db.commit()


async def get_recent_ppm(match_id: str, limit: int = 3) -> List[float]:
    """
    Belirli bir maç için son N kaydın PPM değerlerini döndürür.
    En yeni kayıt listenin başında olur: [ppm_t, ppm_t-1, ppm_t-2, ...]
    """
    db = _get_db()
    cursor = await db.execute(
        """
        SELECT current_ppm
        FROM match_logs
        WHERE match_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (match_id, limit),
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def get_latest_logs() -> List[dict]:
    """
    Her maç için en son kaydı döndürür.
    Dashboard WebSocket yayını için kullanılır.
    """
    db = _get_db()
    cursor = await db.execute(
        """
        SELECT m.match_id, m.home_team, m.away_team, m.opening_total,
               l.played_minutes, l.current_score, l.current_ppm,
               l.live_projection, l.live_total_odds, l.fair_value,
               l.timestamp
        FROM matches m
        INNER JOIN match_logs l ON m.match_id = l.match_id
        WHERE l.log_id = (
            SELECT l2.log_id FROM match_logs l2
            WHERE l2.match_id = m.match_id
            ORDER BY l2.timestamp DESC
            LIMIT 1
        )
        ORDER BY m.match_id
        """
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
