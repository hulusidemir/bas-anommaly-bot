"""
Telegram Bildirim Modülü — Anomali tespit edildiğinde mesaj gönderir.

Aynı maç + aynı sinyal için tekrar bildirim göndermemek adına
basit bir cooldown mekanizması içerir.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Tuple

from telegram import Bot
from telegram.constants import ParseMode

from config import settings
from models import MatchAnalysis, OpportunitySignal

logger = logging.getLogger(__name__)

# (match_id, signal) → son bildirim zamanı
_cooldown_map: Dict[Tuple[str, OpportunitySignal], float] = {}

COOLDOWN_SECONDS = 300  # Aynı sinyal için 5 dakika bekleme


class TelegramNotifier:

    def __init__(self) -> None:
        token = settings.telegram_bot_token
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN tanımlı değil — bildirimler devre dışı.")
            self._bot = None
        else:
            self._bot = Bot(token=token)
        self._chat_id = settings.telegram_chat_id

    async def notify_if_needed(self, analysis: MatchAnalysis) -> None:
        """Sinyal varsa ve cooldown geçmişse Telegram mesajı gönderir."""
        if self._bot is None:
            return
        if analysis.signal == OpportunitySignal.NONE:
            return

        key = (analysis.match_id, analysis.signal)
        now = time.time()

        last_sent = _cooldown_map.get(key, 0.0)
        if now - last_sent < COOLDOWN_SECONDS:
            return

        text = self._build_message(analysis)
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            _cooldown_map[key] = now
            logger.info("Telegram bildirimi gönderildi: %s → %s", key, analysis.signal)
        except Exception:
            logger.exception("Telegram mesaj gönderimi başarısız: %s", key)

    @staticmethod
    def _build_message(a: MatchAnalysis) -> str:
        header = f"<b>{a.match_name}</b>  |  {a.quarter_display}"
        score = f"Skor: {a.home_score} - {a.away_score} (Toplam: {a.total_score})"
        lines = [
            header,
            score,
            "",
            a.signal_message,
            "",
            f"PPM: {a.ppm}  |  Hedef PPM: {a.target_ppm}",
            f"Açılış: {a.opening_line}  |  Canlı: {a.live_line}  |  Adil: {a.fair_value}",
        ]
        return "\n".join(lines)
