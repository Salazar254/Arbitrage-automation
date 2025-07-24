
import requests
import time

# APIs
BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT"
KONWEX_API = "https://api.konwex.com/markets/bnbusdt/ticker"

# Telegram config
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
ARBITRAGE_THRESHOLD = 1.0  # %

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

def get_binance_price():
    try:
        res = requests.get(BINANCE_API).json()
        return float(res['price'])
    except:
        return None

def get_konwex_price():
    try:
        res = requests.get(KONWEX_API).json()
        return float(res['ticker']['last'])  # Adjust this if needed
    except:
        return None

print("Bot started...")

while True:
    binance = get_binance_price()
    konwex = get_konwex_price()

    if binance and konwex:
        spread = ((konwex - binance) / binance) * 100
        print(f"Binance: {binance} | Konwex: {konwex} | Spread: {spread:.2f}%")

        if spread >= ARBITRAGE_THRESHOLD:
            message = f"🔥 Arbitrage Opportunity!\nBuy on Binance @ ${binance:.2f}\nSell on Konwex @ ${konwex:.2f}\nSpread: {spread:.2f}%"
            send_telegram_alert(message)

    time.sleep(15)
