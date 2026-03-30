"""
Pydantic veri modelleri — API yanıtları, iç veri akışı ve WebSocket payload'ları.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class LeagueType(str, Enum):
    NBA = "NBA"
    EUROPE = "EUROPE"


class Quarter(int, Enum):
    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4
    OT = 5


class OpportunitySignal(str, Enum):
    NONE = "NONE"
    PACE_DROP = "PACE_DROP"          # Kural 1
    VALUE_GAP = "VALUE_GAP"          # Kural 2
    SCORING_DROUGHT = "SCORING_DROUGHT"  # Kural 3


# ── Giriş: Ham Maç Verisi ───────────────────────────────────────────────────

class MatchRaw(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    home_score: int = 0
    away_score: int = 0
    quarter: int = 1
    elapsed_minutes: float = 0.0       # Oynanan dakika
    league_type: LeagueType = LeagueType.EUROPE
    opening_line: float = 0.0          # Maç önü açılış baremi (Toplam O/U)
    live_line: float = 0.0             # Canlıda sunulan barem
    last_3min_points: Optional[int] = None  # Son 3 dk'da atılan toplam sayı
    sofascore_url: str = ""             # SofaScore maç sayfası linki


# ── Çıkış: Hesaplanmış Maç Analizi ──────────────────────────────────────────

class MatchAnalysis(BaseModel):
    match_id: str
    match_name: str                     # "Fenerbahçe vs Olympiacos"
    quarter_display: str                # "3Ç - 04:12"
    home_score: int
    away_score: int
    total_score: int

    # Barem / Projeksiyon
    opening_line: float
    live_line: float
    fair_value: float = Field(..., description="Sistem Adil Baremi")
    live_projection: float

    # Tempo
    ppm: float = Field(..., description="Dakika Başına Sayı")
    target_ppm: float = Field(..., description="Hedefe ulaşmak için gereken PPM")

    # Fırsat
    delta: float = Field(..., description="Adil barem − canlı barem farkı")
    signal: OpportunitySignal = OpportunitySignal.NONE
    signal_message: str = ""

    elapsed_minutes: float
    remaining_minutes: float
    total_minutes: float
    sofascore_url: str = ""


# ── WebSocket Frame ──────────────────────────────────────────────────────────

class DashboardFrame(BaseModel):
    """Dashboard'a WebSocket üzerinden gönderilen toplu güncelleme."""
    matches: list[MatchAnalysis] = []
    updated_at: str  # ISO-8601
