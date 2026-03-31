"""
Matematiksel Hesaplama Motoru — Adil Barem, PPM, Projeksiyon, Hedef Tempo.

Her 30 saniyede bir her maç için çağrılır.
Hesaplanan veriler SQLite match_logs tablosuna yazılır.
"""

from __future__ import annotations

import database as db
from models import LeagueType, MatchAnalysis, MatchRaw, OpportunitySignal
from config import settings


class Calculator:
    """Tek bir maçın anlık verisinden tüm türev metrikleri hesaplar ve DB'ye yazar."""

    # ── Yardımcılar ──────────────────────────────────────────────────────

    @staticmethod
    def _total_minutes(league: LeagueType) -> float:
        if league == LeagueType.NBA:
            return float(settings.league_total_minutes.get("NBA", 48))
        return float(settings.league_total_minutes.get("DEFAULT", 40))

    # ── Ana Hesaplama ────────────────────────────────────────────────────

    async def analyze(self, raw: MatchRaw) -> MatchAnalysis:
        total_minutes = self._total_minutes(raw.league_type)
        elapsed = max(raw.elapsed_minutes, 0.1)          # 0-a bölme koruması
        remaining = max(total_minutes - elapsed, 0.0)
        total_score = raw.home_score + raw.away_score

        # ── Güvenlik Duvarı 1: İlk 1 dakika koruması ────────────────────
        # İlk 1 dakikada PPM projeksiyonu istatistiksel olarak geçersizdir.
        if elapsed <= 1.0:
            ppm = 0.0
            live_projection = 0.0
            fair_value = 0.0
            target_ppm = 0.0
            delta = 0.0
        else:
            # 1) PPM — Dakika Başına Sayı
            ppm = total_score / elapsed

            # 2) Canlı Projeksiyon (Normal Süre)
            live_projection = ppm * total_minutes

            # ── Crunch Time (Taktik Faul) Eklentisi ──
            # Son çeyrekte ve maçın son 3 dakikasında serbest atışlardan dolayı skor ağırlığı artar.
            if raw.quarter >= 4 and remaining <= 3.0 and remaining > 0:
                crunch_inflation = remaining * 1.5  # Kalan her dakika için ekstra 1.5 sayı bekliyoruz
                live_projection += crunch_inflation

            # ── Güvenlik Duvarı 2: Eksik barem koruması ─────────────────
            # opening_line veya live_line 0 ise barem hesaplaması yapılamaz.
            has_opening = raw.opening_line > 0.0
            has_live = raw.live_line > 0.0

            # 3) Adil Barem (Fair Value)
            #    Time-Decay: Geride kalan süreye göre ağırlıklar dinamik değişir (Maç sonuna doğru canlı veriye daha çok güvenilir).
            if has_opening:
                weight_live = elapsed / total_minutes
                weight_open = 1.0 - weight_live
                fair_value = (live_projection * weight_live) + (raw.opening_line * weight_open)
            else:
                fair_value = live_projection  # Açılış baremi yoksa sadece proj kullan

            # 4) Hedef PPM — Kalan dakikalarda atılması gereken sayı hızı
            #    Kalan ≤ 0.5 dk ise hesaplama anlamsız → 0
            if has_live and remaining > 0.5:
                target_ppm = (raw.live_line - total_score) / remaining
            else:
                target_ppm = 0.0

            # 5) Delta — Adil barem ile canlı barem farkı
            if has_live:
                delta = fair_value - raw.live_line
            else:
                delta = 0.0

        # Çeyrek gösterimi
        quarter_display = self._format_quarter(raw.quarter, elapsed, total_minutes)

        analysis = MatchAnalysis(
            match_id=raw.match_id,
            match_name=f"{raw.home_team} vs {raw.away_team}",
            quarter_display=quarter_display,
            home_score=raw.home_score,
            away_score=raw.away_score,
            total_score=total_score,
            opening_line=raw.opening_line,
            live_line=raw.live_line,
            fair_value=round(fair_value, 1),
            live_projection=round(live_projection, 1),
            ppm=round(ppm, 2),
            target_ppm=round(target_ppm, 2),
            delta=round(delta, 1),
            signal=OpportunitySignal.NONE,
            signal_message="",
            elapsed_minutes=elapsed,
            remaining_minutes=remaining,
            total_minutes=total_minutes,
            sofascore_url=raw.sofascore_url,
        )

        # ── SQLite'a yaz ────────────────────────────────────────────────
        await db.upsert_match(
            raw.match_id, raw.home_team, raw.away_team, raw.opening_line
        )
        await db.insert_log(
            match_id=raw.match_id,
            played_minutes=elapsed,
            current_score=total_score,
            current_ppm=analysis.ppm,
            live_projection=analysis.live_projection,
            live_total_odds=raw.live_line,
            fair_value=analysis.fair_value,
        )

        return analysis

    # ── Çeyrek Formatı ───────────────────────────────────────────────────

    @staticmethod
    def _format_quarter(quarter: int, elapsed: float, total: float) -> str:
        q_duration = total / 4
        minutes_in_q = elapsed - (quarter - 1) * q_duration
        minutes_in_q = max(minutes_in_q, 0)
        mins = int(minutes_in_q)
        secs = int((minutes_in_q - mins) * 60)
        return f"{quarter}Ç - {mins:02d}:{secs:02d}"
