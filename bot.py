import time
import requests
from datetime import datetime

# ⚙️ CONFIGURATION
TELEGRAM_TOKEN = "8701789147:AAGIbXhBOo5aoNYLr0VveVUVNq7cHC3htXI"
CHAT_ID = "8701789147"
TWELVEDATA_KEY = "9ea69f958d4e4b34abadbd12edcf7fd2"
CAPITAL = 50
RISK_PERCENT = 1
SYMBOL = "XAU/USD"
INTERVAL = "4h"  # H4 comme convenu

def envoyer_message(texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texte, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi message: {e}")

def recuperer_donnees():
    """Récupère prix + RSI réel via TwelveData"""
    try:
        # Prix actuel
        url_prix = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={TWELVEDATA_KEY}"
        r_prix = requests.get(url_prix, timeout=10).json()
        prix = float(r_prix["price"])

        # RSI
        url_rsi = f"https://api.twelvedata.com/rsi?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
        r_rsi = requests.get(url_rsi, timeout=10).json()
        rsi = float(r_rsi["values"][0]["rsi"])

        return prix, rsi
    except Exception as e:
        print(f"Erreur récupération données: {e}")
        return None, None

def calculer_taille_position(prix_entree, prix_sl):
    risque_euros = CAPITAL * (RISK_PERCENT / 100)
    distance_pips = abs(prix_entree - prix_sl)
    if distance_pips == 0:
        distance_pips = 1
    taille_lot = round(risque_euros / (distance_pips * 100), 2)
    taille_lot = max(0.01, min(taille_lot, 0.10))
    return taille_lot, risque_euros

def analyser_et_envoyer():
    prix, rsi = recuperer_donnees()

    if prix is None or rsi is None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Erreur données, on réessaie au prochain cycle")
        return

    signal = None
    if rsi < 30:
        signal = "BUY"
    elif rsi > 70:
        signal = "SELL"

    if signal is None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pas de signal (RSI: {rsi:.2f}, Prix: {prix})")
        return

    distance_sl = 3
    distance_tp = 9

    if signal == "BUY":
        prix_sl = prix - distance_sl
        prix_tp = prix + distance_tp
        emoji = "🟢"
        action = "ACHAT (BUY)"
    else:
        prix_sl = prix + distance_sl
        prix_tp = prix - distance_tp
        emoji = "🔴"
        action = "VENTE (SELL)"

    taille_lot, risque_euros = calculer_taille_position(prix, prix_sl)
    gain_potentiel = risque_euros * 3

    message = f"""
{emoji} <b>SIGNAL {INTERVAL.upper()} — XAUUSD</b>

➡️ <b>{action}</b>
💰 Prix d'entrée: <b>{prix}</b>
📊 RSI: {rsi:.2f}

📦 Taille recommandée: <b>{taille_lot} lot</b>
🎯 Take Profit: <b>{round(prix_tp, 2)}</b>
🛑 Stop Loss: <b>{round(prix_sl, 2)}</b>

💵 Risque: <b>{risque_euros:.2f}€</b>
💎 Gain potentiel: <b>{gain_potentiel:.2f}€</b>

👉 Ouvre Exness et passe l'ordre avec ces valeurs !
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    envoyer_message(message)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Signal envoyé: {action} à {prix} (RSI: {rsi:.2f})")

def message_demarrage():
    texte = f"""
🤖 <b>Bot de trading démarré !</b>

📊 Paire: XAUUSD
⏱️ Timeframe: {INTERVAL.upper()}
💰 Capital: {CAPITAL}€
⚠️ Risque par trade: {RISK_PERCENT}% ({CAPITAL * RISK_PERCENT / 100:.2f}€)

✅ RSI en temps réel activé (TwelveData)

Le bot va analyser le marché et t'envoyer des signaux fiables.
Bon trade ! 🚀
"""
    envoyer_message(texte)

# 🚀 BOUCLE PRINCIPALE
if __name__ == "__main__":
    message_demarrage()
    print("Bot démarré ! Analyse en cours avec vraies données...")

    while True:
        try:
            analyser_et_envoyer()
        except Exception as e:
            print(f"Erreur: {e}")

        time.sleep(900)  # Vérifie toutes les 15 min (mais RSI reste basé sur H4)