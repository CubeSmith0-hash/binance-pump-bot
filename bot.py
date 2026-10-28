import ccxt
import time
import requests

# --- Telegram Ayarları ---
# BotFather'dan aldığın token ve Telegram Chat ID'ni buraya yazmalısın
TELEGRAM_BOT_TOKEN = "BURAYA_BOT_TOKENINIZI_YAZIN"
TELEGRAM_CHAT_ID = "BURAYA_CHAT_ID_YAZIN"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram mesaj hatası: {e}")

# --- Binance Bağlantısı ---
exchange = ccxt.binance({
    'enableRateLimit': True,
})

# Eşik Değerler (İstediğin gibi değiştirebilirsin)
VOLUME_MULTIPLIER = 5.0       # Hacim katı (Örn: Önceki ortalamanın 5 katı)
PRICE_CHANGE_THRESHOLD = 4.0  # Min % fiyat artışı (Örn: %4)

# Spam engellemek için daha önce uyarı gönderilen coin'leri tutacak sözlük
cooldown_dict = {}

def check_pump_signals():
    print(f"[{time.strftime('%H:%M:%S')}] Binance spot piyasası taranıyor...")
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = [symbol for symbol in tickers if symbol.endswith('/USDT')]
    except Exception as e:
        print(f"Ticker verileri alınamadı: {e}")
        return

    current_time = time.time()

    for symbol in usdt_pairs:
        try:
            # Aynı coin için son 30 dakika içinde tekrar bildirim gitmesin (Cooldonw)
            if symbol in cooldown_dict and (current_time - cooldown_dict[symbol]) < 1800:
                continue

            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=21)
            if len(ohlcv) < 21:
                continue

            last_candle = ohlcv[-1]
            open_p, close_p, current_vol = last_candle[1], last_candle[4], last_candle[5]

            # Sadece yeşil mumlar
            if close_p <= open_p:
                continue

            # Önceki 20 mumun ortalama hacmi
            previous_volumes = [c[5] for c in ohlcv[:-1]]
            avg_volume = sum(previous_volumes) / len(previous_volumes)

            if avg_volume == 0:
                continue

            vol_ratio = current_vol / avg_volume
            price_change = ((close_p - open_p) / open_p) * 100

            # Şartlar: Hacim >= 5x VE Fiyat Değişimi >= %4
            if vol_ratio >= VOLUME_MULTIPLIER and price_change >= PRICE_CHANGE_THRESHOLD:
                
                ticker_data = tickers[symbol]
                vol_24h_usdt = ticker_data.get('quoteVolume', 0)

                msg = (
                    f"🚨 *PUMP UYARISI / ANI HACİM ARTIŞI* 🚨\n\n"
                    f"📌 *Coin:* `{symbol}`\n"
                    f"💵 *Güncel Fiyat:* `{close_p}`\n"
                    f"📈 *15d Fiyat Artışı:* `%{price_change:.2f}`\n"
                    f"📊 *Hacim Katlaması:* `{vol_ratio:.1f}x` (20 Ort. Göre)\n"
                    f"💰 *24s Hacim:* `${vol_24h_usdt:,.0f} USDT`\n\n"
                    f"🔗 [Binance Grafiği](https://www.binance.com/en/trade/{symbol.replace('/', '_')})"
                )
                
                send_telegram_msg(msg)
                print(f"[YAKALANDI] {symbol} - Fiyat: %{price_change:.2f}, Hacim: {vol_ratio:.1f}x")
                
                # Cooldown süresini başlat (30 dakika boyunca tekrar bildirim atmaz)
                cooldown_dict[symbol] = current_time

        except Exception as e:
            continue

if __name__ == "__main__":
    print("Pump Takip Botu Başlatıldı...")
    while True:
        check_pump_signals()
        # Her 2 dakikada bir tarama döngüsünü çalıştırır
        time.sleep(120)
