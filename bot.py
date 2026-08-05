import requests
import time
from datetime import datetime


==== CONFIGURATION ====


TELEGRAM_TOKEN = "8701789147:AAGIbXhBOo5aoNYLr0VveVUVNq7cHC3htXI"
CHAT_ID = "TON_CHAT_ID_ICI"
TWELVEDATA_KEY = "9ea69f958d4e4b34abadbd12edcf7fd2"
SYMBOL = "XAU/USD"


==== ENVOI TELEGRAM ====


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)


==== RECUP DONNEES PRIX ====


def get_candles(interval="4h", outputsize=50):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_KEY
    }
    r = requests.get(url, params=params).json()
    if "values" not in r:
        return None
    values = r["values"]
    values.reverse()  # ordre chronologique
    closes = [float(v["close"]) for v in values]
    highs = [float(v["high"]) for v in values]
    lows = [float(v["low"]) for v in values]
    return closes, highs, lows


==== INDICATEURS ====


def ema(data, period):
    k = 2 / (period + 1)
    ema_vals = [data[0]]
    for price in data[1:]:
        ema_vals.append(price * k + ema_vals[-1] * (1 - k))
    return ema_vals


def rsi(data, period=14):
    gains, losses = [], []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


==== STRATEGIE SIMPLE (EMA crossover + RSI) ====


def analyze(interval):
    result = get_candles(interval)
    if result is None:
        return None
    closes, highs, lows = result


ema9 = ema(closes, 9)
ema21 = ema(closes, 21)
current_rsi = rsi(closes)

price = closes[-1]
signal = None

# Croisement haussier
if ema9[-2] < ema21[-2] and ema9[-1] > ema21[-1] and current_rsi < 70:
    signal = "ACHAT (BUY)"
# Croisement baissier
elif ema9[-2] > ema21[-2] and ema9[-1] < ema21[-1] and current_rsi > 30:
    signal = "VENTE (SELL)"

return {
    "signal": signal,
    "price": price,
    "rsi": round(current_rsi, 2),
    "ema9": round(ema9[-1], 2),
    "ema21": round(ema21[-1], 2)
}



==== GESTION DE RISQUE (calcul suggestion SL/TP) ====


def risk_management(price, signal, capital=50, risk_pct=1):
    risk_amount = capital * (risk_pct / 100)  # ex: 0.50€ risqué max
    # Pour XAUUSD, 0.01 lot = ~0.10$/pip approximativement (variable selon broker)
    pip_value = 0.10
    sl_pips = risk_amount / pip_value
    if signal == "ACHAT (BUY)":
        sl = round(price - sl_pips * 0.1, 2)
        tp = round(price + sl_pips * 0.2, 2)  # ratio 1:2
    else:
        sl = round(price + sl_pips * 0.1, 2)
        tp = round(price - sl_pips * 0.2, 2)
    return sl, tp


==== BOUCLE PRINCIPALE ====


last_signal_h4 = None
last_signal_m5 = None


def run():
    global last_signal_h4, last_signal_m5


send_telegram("🤖 Bot XAUUSD démarré. Surveillance H4 & M5 en cours...")

while True:
    try:
        # Analyse H4
        data_h4 = analyze("4h")
        if data_h4 and data_h4["signal"] and data_h4["signal"] != last_signal_h4:
            sl, tp = risk_management(data_h4["price"], data_h4["signal"])
            msg = (
                f"📊 *SIGNAL H4 — XAUUSD*\n\n"
                f"➡️ {data_h4['signal']}\n"
                f"💰 Prix actuel: {data_h4['price']}\n"
                f"📈 RSI: {data_h4['rsi']}\n"
                f"EMA9: {data_h4['ema9']} / EMA21: {data_h4['ema21']}\n\n"
                f"🎯 TP suggéré: {tp}\n"
                f"🛑 SL suggéré: {sl}\n\n"
                f"⚠️ Vérifie manuellement avant d'ouvrir sur MT5"
            )
            send_telegram(msg)
            last_signal_h4 = data_h4["signal"]

        # Analyse M5
        data_m5 = analyze("5min")
        if data_m5 and data_m5["signal"] and data_m5["signal"] != last_signal_m5:
            sl, tp = risk_management(data_m5["price"], data_m5["signal"])
            msg = (
                f"⚡ *SIGNAL M5 — XAUUSD*\n\n"
                f"➡️ {data_m5['signal']}\n"
                f"💰 Prix actuel: {data_m5['price']}\n"
                f"📈 RSI: {data_m5['rsi']}\n\n"
                f"🎯 TP suggéré: {tp}\n"
                f"🛑 SL suggéré: {sl}\n\n"
                f"⚠️ Signal court terme — sois prudent"
            )
            send_telegram(msg)
            last_signal_m5 = data_m5["signal"]

    except Exception as e:
        print(f"Erreur: {e}")

    time.sleep(60)  # vérifie toutes les 60 secondes



if name == "main":
    run()

