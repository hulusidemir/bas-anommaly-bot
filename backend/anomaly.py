"""
Anomali Tespit Kuralları — Üç kural seti ile fırsat / uyarı sinyalleri üretir.

Calculator tarafından üretilen MatchAnalysis üzerinde çalışır,
signal ve signal_message alanlarını doldurur.

Kural 1 ve 2 için **trend doğrulaması** yapılır:
  SQLite match_logs tablosundaki son 3 kaydın PPM değerine bakılır.
  Yalnızca PPM istikrarlı düşüyorsa (negatif ivme) sinyal onaylanır;
  aksi halde gürültü kabul edilip yoksayılır.
"""

from __future__ import annotations

import logging
from typing import List

import database as db
from models import MatchAnalysis, MatchRaw, OpportunitySignal
from config import settings

logger = logging.getLogger(__name__)


class AnomalyDetector:

    # ── Genel Giriş Noktası ─────────────────────────────────────────────

    async def evaluate(self, analysis: MatchAnalysis, raw: MatchRaw) -> MatchAnalysis:
        """Tüm kuralları sırayla değerlendirir; ilk tetiklenen sinyali yazar."""

        # Kural 1 — Ortalamaya Dönüş (Pace Drop)
        result = await self._rule_pace_drop(analysis, raw)
        if result:
            return result

        # Kural 2 — Değer Fırsatı (Value Gap)
        result = await self._rule_value_gap(analysis)
        if result:
            return result

        # Kural 3 — Kilitlenme (Scoring Drought)
        result = self._rule_scoring_drought(analysis, raw)
        if result:
            return result

        return analysis

    # ── Trend Doğrulaması (Gürültü Engelleme) ───────────────────────────

    @staticmethod
    async def _confirm_declining_ppm(match_id: str) -> bool:
        """
        Son 3 kayıttaki PPM'in istikrarlı düştüğünü doğrular.
        ppm_t < ppm_t-1 < ppm_t-2  ise True döner.
        Yeterli veri yoksa False döner (bildirim engellenir).
        """
        # Eskiden 3 (90 saniye) olan limit, daha sağlam bir trend için 6'ya (3 dakika) çıkarıldı
        ppm_values: List[float] = await db.get_recent_ppm(match_id, limit=6)

        if len(ppm_values) < 6:
            return False

        # İstikrarlı düşüş trendi: en_yeni < ... < en_eski
        return all(ppm_values[i] < ppm_values[i+1] for i in range(len(ppm_values) - 1))

    # ── Kural 1: Pace Drop Anomaly ───────────────────────────────────────

    async def _rule_pace_drop(
        self, a: MatchAnalysis, raw: MatchRaw
    ) -> MatchAnalysis | None:
        """
        Eğer canlı projeksiyon, açılış bareminden ≥ threshold fazla ise Pace Drop hesaplanır.
        Açılış baremi çekilememişse kural iptal edilir.
        """
        if a.opening_line <= 0.0:
            return None

        threshold = settings.pace_drop_threshold
        overshoot = a.live_projection - a.opening_line

        # Çeyrek bitim zorunluluğunu (is_q_end) tamamen kaldırıyoruz, trend hareketli pencere (rolling window) ile maç genelinde de yakalanabilir.
        if overshoot >= threshold:
            if not await self._confirm_declining_ppm(a.match_id):
                logger.info(
                    "Kural 1 tetiklendi ama PPM trendi doğrulanamadı → gürültü: %s",
                    a.match_id,
                )
                return None

            a.signal = OpportunitySignal.PACE_DROP
            a.signal_message = (
                f"🚨 Aşırı Hız Tespit Edildi. Ritmin düşmesi bekleniyor. "
                f"Adil Barem: {a.fair_value}, Güncel Canlı Barem: {a.live_line}. "
                f"Değerli Senaryo: ALT."
            )
            return a
        return None

    # ── Kural 2: Value Gap ───────────────────────────────────────────────

    async def _rule_value_gap(self, a: MatchAnalysis) -> MatchAnalysis | None:
        """
        Adil barem ile şirket canlı baremi arasındaki fark threshold'u aşarsa.
        Canlı barem çekilememişse işlem iptal edilir.
        """
        if a.live_line <= 0.0:
            return None

        threshold = settings.value_delta_threshold
        gap = abs(a.fair_value - a.live_line)

        if gap > threshold:
            if not await self._confirm_declining_ppm(a.match_id):
                logger.info(
                    "Kural 2 tetiklendi ama PPM trendi doğrulanamadı → gürültü: %s",
                    a.match_id,
                )
                return None

            a.signal = OpportunitySignal.VALUE_GAP
            a.signal_message = (
                f"📊 Barem Uyuşmazlığı. Şirket baremi matematikten saptı. "
                f"Adil Değer: {a.fair_value}, Sistem Değeri: {a.live_line}."
            )
            return a
        return None

    # ── Kural 3: Scoring Drought ─────────────────────────────────────────

    def _rule_scoring_drought(
        self, a: MatchAnalysis, raw: MatchRaw
    ) -> MatchAnalysis | None:
        """
        Son 3 dakikada toplam sayı < 4
        VE hedef PPM, mevcut PPM'in %40 üzerine çıktıysa → SCORING_DROUGHT.
        """
        if raw.last_3min_points is None:
            return None

        pts_threshold = settings.drought_points_threshold
        ppm_ratio = settings.drought_ppm_ratio

        drought = raw.last_3min_points < pts_threshold
        ppm_impossible = a.ppm > 0 and a.target_ppm > (a.ppm * ppm_ratio)

        if drought and ppm_impossible:
            a.signal = OpportunitySignal.SCORING_DROUGHT
            a.signal_message = (
                f"🛑 Maç Kilitlendi. Hedef barem için imkansız tempo gerekiyor. "
                f"Değerli Senaryo: ALT."
            )
            return a
        return None

    # ── Yardımcı ─────────────────────────────────────────────────────────

    @staticmethod
    def _near_quarter_end(
        elapsed: float, quarter: int, q_duration: float, tolerance: float = 1.0
    ) -> bool:
        """Çeyrek bitişine ±tolerance dakika kala olup olmadığını döndürür."""
        q_end_time = quarter * q_duration
        return abs(elapsed - q_end_time) <= tolerance
