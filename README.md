# Basketbol Anomali Tespit ve Dashboard Sistemi

Canlı basketbol maçlarının istatistiklerini analiz ederek **Adil Barem (Fair Value)** hesaplayan,
anomali tespit ettiğinde **Telegram** bildirimi gönderen ve tüm süreci bir **web Dashboard**
üzerinde anlık gösteren karar destek sistemi.

## Mimari

```
backend/
├── main.py               # FastAPI giriş noktası, HTTP + WS + arka plan döngüsü
├── config.py             # Çevre değişkenlerinden okunan konfigürasyon
├── models.py             # Pydantic veri modelleri
├── calculator.py         # Matematiksel hesaplama motoru (PPM, projeksiyon, adil barem)
├── anomaly.py            # Anomali tespit kuralları (3 kural)
├── telegram_notifier.py  # Telegram bildirim modülü
├── data_fetcher.py       # API veri çekme (+ mock data)
├── websocket_manager.py  # Dashboard WebSocket yayıncısı
└── requirements.txt
```

## Hızlı Başlangıç

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Çevre Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot API token |
| `TELEGRAM_CHAT_ID` | — | Bildirimlerin gönderileceği chat ID |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis bağlantı adresi |
| `DATA_FETCH_INTERVAL` | `30` | Veri çekme aralığı (saniye) |
| `PACE_DROP_THRESHOLD` | `15` | Kural 1 eşik değeri |
| `VALUE_DELTA_THRESHOLD` | `8.5` | Kural 2 eşik değeri |

## API Endpoint'leri

- **GET** `/api/matches` — Son hesaplanan tüm maç analizleri
- **GET** `/api/health` — Sistem durumu
- **WS** `/ws` — Dashboard için anlık güncelleme akışı
# bas-anommaly-bot
