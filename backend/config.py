"""
Uygulama konfigürasyonu — çevre değişkenlerinden okunur.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # --- Telegram ---
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- Veritabanı ---
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "anomaly_bot.db")

    # --- Veri Kaynağı ---
    sofascore_api_base: str = os.getenv(
        "SOFASCORE_API_BASE", "https://api.sofascore.com/api/v1"
    )
    aiscore_api_base: str = os.getenv("AISCORE_API_BASE", "")
    data_fetch_interval_sec: int = int(os.getenv("DATA_FETCH_INTERVAL", "30"))

    # --- Anomali Eşik Değerleri ---
    pace_drop_threshold: float = float(os.getenv("PACE_DROP_THRESHOLD", "15"))
    value_delta_threshold: float = float(os.getenv("VALUE_DELTA_THRESHOLD", "8.5"))
    drought_points_threshold: int = int(os.getenv("DROUGHT_POINTS_THRESHOLD", "4"))
    drought_minutes_window: int = int(os.getenv("DROUGHT_MINUTES_WINDOW", "3"))
    drought_ppm_ratio: float = float(os.getenv("DROUGHT_PPM_RATIO", "1.4"))

    # --- Lig Toplam Süreleri (dakika) ---
    league_total_minutes: dict = field(default_factory=lambda: {
        "NBA": 48,
        "DEFAULT": 40,  # Avrupa / FIBA
    })


settings = Settings()
