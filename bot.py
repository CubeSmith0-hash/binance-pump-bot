import ccxt
import time
import requests

# --- Telegram Ayarları ---
TELEGRAM_BOT_TOKEN = 9173946791:AAGY3wveS05TECs-nEMbVA-1G55K0j-Izv8
TELEGRAM_CHAT_ID = -1004318579434  # Grubun eksi(-) ID'si

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram mesaj hatası: {e}")

# --- Binance Futures Bağlantısı ---
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # USDⓈ-M Futures piyasası
    }
})

# Eşik Değerler
VOLUME_MULTIPLIER = 5.0       # Hacim katı (Örn: Önceki 20 mumun ortalamasının 5 katı)
PRICE_CHANGE_THRESHOLD = 3.0  # Min % fiyat artışı (Örn: %3)

# Aynı coin'in üst üste spam atmasını önlemek için cooldown sözlüğü
cooldown_dict = {}

def check_pump_signals():
    print(f"[{time.strftime('%H:%M:%S')}] Binance USDⓈ-M Futures (Tüm Kriptolar) taranıyor...")
    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers()
        
        # USDⓈ-M Futures piyasasındaki BÜTÜN USDT paritelerini filtrele
        usdt_futures_pairs = [
            symbol for symbol, market in exchange.markets.items() 
            if symbol.endswith('/USDT') and market.get('linear', True) and market.get('active', True)
        ]
    except Exception as e:
        print(f"Piyasa verileri alınamadı: {e}")
        return

    current_time = time.time()

    for symbol in usdt_futures_pairs:
        try:
            # Aynı coin için 30 dakika içinde tekrar bildirim gitmesin
            if symbol in cooldown_dict and (current_time - cooldown_dict[symbol]) < 1800:
                continue

            # 15 dakikalık mumları çek
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

            # Şartlar: Hacim katı ve fiyat artışı
            if vol_ratio >= VOLUME_MULTIPLIER and price_change >= PRICE_CHANGE_THRESHOLD:
                
                ticker_data = tickers.get(symbol, {})
                vol_24h_usdt = ticker_data.get('quoteVolume', 0)

                formatted_symbol = symbol.replace('/', '')
                msg = (
                    f"🚨 *FUTURES PUMP UYARISI* 🚨\n\n"
                    f"📌 *Coin:* `{symbol}`\n"
                    f"💵 *Güncel Fiyat:* `{close_p}`\n"
                    f"📈 *15d Fiyat Artışı:* `%{price_change:.2f}`\n"
                    f"📊 *Hacim Katlaması:* `{vol_ratio:.1f}x` (20 Ort. Göre)\n"
                    f"💰 *24s Hacim:* `${vol_24h_usdt:,.0f} USDT`\n\n"
                    f"🔗 [Binance Futures](https://www.binance.com/en/futures/{formatted_symbol})"
                )
                
                send_telegram_msg(msg)
                print(f"[YAKALANDI] {symbol} - Fiyat: %{price_change:.2f}, Hacim: {vol_ratio:.1f}x")
                
                cooldown_dict[symbol] = current_time

        except Exception as e:
            continue

if __name__ == "__main__":
    print("Binance Futures Tüm Kriptolar Takip Botu Başlatıldı...")
    while True:
        check_pump_signals()
        time.sleep(120)
