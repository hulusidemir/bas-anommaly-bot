"""
Veri Çekme Modülü — SofaScore API'sinden canlı basketbol maç verisi çeker.

SofaScore TLS fingerprint doğrulaması yaptığı için curl_cffi kullanılır.
Bahis oranları (O/U) SofaScore'dan gelmediği için, canlı skora dayalı
sentetik opening_line ve live_line üretilir.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import List

from curl_cffi import requests as cffi_requests

from config import settings
from models import LeagueType, MatchRaw
from time_parser import parse_clock_string

logger = logging.getLogger(__name__)

# NBA olarak tanınacak turnuva anahtar kelimeleri
_NBA_KEYWORDS = {"nba", "national basketball association"}

# Çeyrek tespiti: status.description → quarter numarası
_QUARTER_MAP = {
    "1st quarter": 1,
    "2nd quarter": 2,
    "3rd quarter": 3,
    "4th quarter": 4,
    "overtime": 5,
}


class DataFetcher:
    """Canlı maç verilerini SofaScore API'sinden çeker (curl_cffi + Chrome impersonate)."""

    async def close(self) -> None:
        pass  # curl_cffi oturum yönetimi gerektirmez

    # ── Ana Giriş Noktası ────────────────────────────────────────────────

    async def fetch_live_matches(self) -> List[MatchRaw]:
        """SofaScore'dan canlı basketbol maçlarını çeker."""
        try:
            return await self._fetch_sofascore()
        except Exception:
            logger.exception("Canlı veri çekilemedi — boş liste dönüyor.")
            return []

    # ── SofaScore API ────────────────────────────────────────────────────

    async def _fetch_sofascore(self) -> List[MatchRaw]:
        url = f"{settings.sofascore_api_base}/sport/basketball/events/live"
        # curl_cffi sync call'ı asyncio thread pool'a delege et
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: cffi_requests.get(url, impersonate="chrome", timeout=15),
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_sofascore(data)

    def _parse_sofascore(self, data: dict) -> List[MatchRaw]:
        matches: List[MatchRaw] = []
        for event in data.get("events", []):
            try:
                match = self._parse_event(event)
                if match:
                    matches.append(match)
            except Exception:
                logger.debug("Maç parse hatası, atlanıyor", exc_info=True)
                continue
        logger.info("SofaScore'dan %d canlı maç çekildi.", len(matches))
        return matches

    @staticmethod
    def _parse_event(event: dict) -> MatchRaw | None:
        status = event.get("status", {})
        if status.get("type") != "inprogress":
            return None

        event_id = event.get("id")
        slug = event.get("slug", "")
        home = event.get("homeTeam", {}).get("name", "?")
        away = event.get("awayTeam", {}).get("name", "?")

        home_score = event.get("homeScore", {}).get("current", 0) or 0
        away_score = event.get("awayScore", {}).get("current", 0) or 0

        # Çeyrek
        description = status.get("description", "").lower()
        quarter = _QUARTER_MAP.get(description, 1)

        # ── Oynanan süre ────────────────────────────────────────────────
        time_info = event.get("time", {})
        played_seconds = time_info.get("played", 0) or 0
        elapsed_minutes = played_seconds / 60.0

        # Eğer API'den saat stringi ("2Ç - 05:30" vb.) gelirse parse et
        current_period_time = time_info.get("currentPeriodStartTimestamp")
        period_str = status.get("description", "")

        # Lig tipi: periodLength 720 → NBA, 600 → FIBA
        period_length = time_info.get("periodLength", 600)
        tournament_name = (
            event.get("tournament", {})
            .get("uniqueTournament", {})
            .get("name", "")
            .lower()
        )
        if period_length == 720 or any(kw in tournament_name for kw in _NBA_KEYWORDS):
            league_type = LeagueType.NBA
            q_duration = 12.0
            total_minutes = 48.0
        else:
            league_type = LeagueType.EUROPE
            q_duration = 10.0
            total_minutes = 40.0

        # time_parser ile string saat formatı varsa kullan
        clock_str = time_info.get("clock", "")
        if clock_str:
            parsed = parse_clock_string(clock_str, quarter_duration=q_duration)
            if parsed is not None:
                elapsed_minutes = parsed

        # SofaScore URL
        sofascore_url = f"https://www.sofascore.com/{slug}/{event_id}" if slug else ""

        # elapsed_minutes'ı en az 0.1 yap
        if elapsed_minutes < 0.1:
            elapsed_minutes = 0.1

        # ── Sentetik Odds (Bahis Baremi) Hesaplama ──────────────────────
        # SofaScore bahis verisi sağlamıyor. Maça dayalı makul bir açılış
        # ve canlı barem üretiyoruz.
        total_score = home_score + away_score
        opening_line, live_line = _estimate_odds(
            event_id, total_score, elapsed_minutes, total_minutes
        )

        return MatchRaw(
            match_id=str(event_id),
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            quarter=quarter,
            elapsed_minutes=round(elapsed_minutes, 2),
            league_type=league_type,
            opening_line=opening_line,
            live_line=live_line,
            sofascore_url=sofascore_url,
        )


# ── Sentetik Odds Üretici ────────────────────────────────────────────────────

# Maç bazında sabit opening_line cache'i (aynı maç her yenilemede aynı açılışı alsın)
_opening_cache: dict[int, float] = {}


def _estimate_odds(
    event_id: int, total_score: int, elapsed: float, total_minutes: float
) -> tuple[float, float]:
    """
    SofaScore odds verisi sağlamadığı için, mevcut skor ve tempoya dayalı
    sentetik opening_line ve live_line üretir.

    opening_line: lig ortalamasına ±küçük sapma (maç başına SABİT).
    live_line:    mevcut PPM projeksiyonuna ±küçük bahisçi marjı.
    """
    # Lig ortalaması bazlı opening_line
    if total_minutes >= 48:
        league_avg = 220.0
    else:
        league_avg = 155.0

    # Maç başına sabit opening_line (cache'den al veya üret)
    if event_id not in _opening_cache:
        rng = random.Random(event_id)  # deterministic seed per match
        _opening_cache[event_id] = round(league_avg + rng.uniform(-8.0, 8.0), 1)
    opening_line = _opening_cache[event_id]

    # Canlı barem: mevcut tempoya dayalı projeksiyon ± bahisçi marjı
    if elapsed > 1.0 and total_score > 0:
        ppm = total_score / elapsed
        projection = ppm * total_minutes
        # Bahisçi marjı: hafif deterministik offset (aynı skor aynı marj)
        rng_live = random.Random(event_id + total_score)
        margin = rng_live.uniform(-3.0, 3.0)
        live_line = round(projection + margin, 1)
    else:
        live_line = opening_line

    return opening_line, live_line
