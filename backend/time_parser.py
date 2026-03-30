"""
Zaman Ayrıştırıcı — API/string formatlarından oynanan dakika hesaplar.

Desteklenen formatlar:
  "1Ç - 05:30", "2Ç - 08:00", "Q2 08:00", "3rd quarter 04:30"

FIBA çeyrek süreleri: 10 dk, NBA: 12 dk.
Saat yönüne göre otomatik algılama: eğer süre >= çeyrek süresi ise
geriye sayım kabul edilir.
"""

from __future__ import annotations

import re
from typing import Optional

# ── Regex: Çeyrek numarası + Zaman ──────────────────────────────────────────
# Grup 1: Çeyrek tanımlayıcı (ör. "3rd", "2Ç", "Q4", "overtime")
# Grup 2: Dakika
# Grup 3: Saniye
_PATTERN = re.compile(
    r"(?:"
    r"(?P<num>\d)\s*(?:st|nd|rd|th|ç)"        # "3rd", "2Ç"  vb.
    r"|Q\s*(?P<qnum>\d)"                       # "Q2"  vb.
    r"|(?P<ot>overtime|üz)"                     # "overtime" / "üz"
    r")"
    r"(?:\s*(?:quarter|çeyrek))?"               # opsiyonel "quarter"/"çeyrek"
    r"\s*[-–\s]*\s*"                            # ayırıcı
    r"(?P<mm>\d{1,2}):(?P<ss>\d{2})",
    re.IGNORECASE,
)


def parse_clock_string(
    clock_str: str,
    quarter_duration: float = 10.0,
    countdown: bool | None = None,
) -> Optional[float]:
    """
    Saat stringinden toplam oynanan dakikayı döndürür.

    Parameters
    ----------
    clock_str : str
        API'den gelen zaman stringi, ör. "2Ç - 05:30"
    quarter_duration : float
        Bir çeyrek süresi (FIBA=10, NBA=12).
    countdown : bool | None
        True  → süre geriye sayıyor (kalan süre verilmiş).
        False → süre ileriye sayıyor (geçen süre verilmiş).
        None  → otomatik algıla: clock_minutes < quarter_duration ise geriye sayım.

    Returns
    -------
    float | None
        Oynanan toplam dakika. Parse edilemezse None.
    """
    match = _PATTERN.search(clock_str)
    if not match:
        return None

    # Çeyrek numarası
    if match.group("ot"):
        quarter = 5
    elif match.group("qnum"):
        quarter = int(match.group("qnum"))
    else:
        quarter = int(match.group("num"))

    mm = int(match.group("mm"))
    ss = int(match.group("ss"))
    clock_minutes = mm + ss / 60.0

    # Otomatik yön algılama
    if countdown is None:
        countdown = clock_minutes < quarter_duration

    quarter_base = (quarter - 1) * quarter_duration

    if countdown:
        # Geriye sayım → kalan süre verilmiş, geçen süreyi bul
        elapsed_in_quarter = quarter_duration - clock_minutes
    else:
        # İleri sayım → geçen süre doğrudan verilmiş
        elapsed_in_quarter = clock_minutes

    # Negatif süre koruması
    elapsed_in_quarter = max(elapsed_in_quarter, 0.0)

    return round(quarter_base + elapsed_in_quarter, 2)
