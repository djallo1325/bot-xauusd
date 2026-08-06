import time
import requests
from datetime import datetime
import threading

# ⚙️ CONFIGURATION
TELEGRAM_TOKEN = "8701789147:AAGIbXhBOo5aoNYLr0VveVUVNq7cHC3htXI"
CHAT_ID = "8076604087"
TWELVEDATA_KEY = "9ea69f958d4e4b34abadbd12edcf7fd2"
CAPITAL = 50
RISK_PERCENT = 1
SYMBOL = "XAU/USD"
INTERVAL = "4h"

dernier_update_id = 0

def envoyer_message(texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texte, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi message: {e}")

def recuperer_prix():
    try:
        url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={TWELVEDATA_KEY}"
        r = requests.get(url, timeout=10).json()
        return float(r["price"])
    except Exception as e:
        print(f"Erreur prix: {e}")
        return None

def recuperer_rsi():
    try:
        url = f"https://api.twelvedata.com/rsi?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
        r = requests.get(url, timeout=10).json()
        return float(r["values"][0]["rsi"])
    except Exception as e:
        print(f"Erreur RSI: {e}")
        return None

def recuperer_ema(periode):
    try:
        url = f"https://api.twelvedata.com/ema?symbol={SYMBOL}&interval={INTERVAL}&time_period={periode}&apikey={TWELVEDATA_KEY}"
        r = requests.get(url, timeout=10).json()
        return float(r["values"][0]["ema"])
    except Exception as e:
        print(f"Erreur EMA{periode}: {e}")
        return None

def recuperer_macd():
    try:
        url = f"https://api.twelvedata.com/macd?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
        r = requests.get(url, timeout=10).json()
        macd = float(r["values"][0]["macd"])
        signal = float(r["values"][0]["macd_signal"])
        return macd, signal
    except Exception as e:
        print(f"Erreur MACD: {e}")
        return None, None

def recuperer_toutes_donnees():
    prix = recuperer_prix()
    rsi = recuperer_rsi()
    ema50 = recuperer_ema(50)
    ema200 = recuperer_ema(200)
    macd, macd_signal = recuperer_macd()
    return prix, rsi, ema50, ema200, macd, macd_signal

def calculer_taille_position(prix_entree, prix_sl):
    risque_euros = CAPITAL * (RISK_PERCENT / 100)
    distance_pips = abs(prix_entree - prix_sl) * 100
    if distance_pips == 0:
        return 0.01
    lot = risque_euros / (distance_pips * 1)
    return round(max(lot, 0.01), 2)

def analyser_signal(prix, rsi, ema50, ema200, macd, macd_signal):
    """Retourne 'BUY', 'SELL' ou None selon les 3 indicateurs"""
    if None in (prix, rsi, ema50, ema200, macd, macd_signal):
        return None

    tendance_haussiere = ema50 > ema200
    tendance_baissiere = ema50 < ema200

    macd_haussier = macd > macd_signal
    macd_baissier = macd < macd_signal

    # BUY : RSI en survente + tendance haussière + MACD haussier
    if rsi < 35 and tendance_haussiere and macd_haussier:
        return "BUY"

    # SELL : RSI en surachat + tendance baissière + MACD baissier
    if rsi > 65 and tendance_baissiere and macd_baissier:
        return "SELL"

    return None

def analyser_et_envoyer():
    prix, rsi, ema50, ema200, macd, macd_signal = recuperer_toutes_donnees()
    if prix is None:
        return

    action = analyser_signal(prix, rsi, ema50, ema200, macd, macd_signal)

    if action == "BUY":
        prix_sl = prix - 5
        prix_tp = prix + 10
    elif action == "SELL":
        prix_sl = prix + 5
        prix_tp = prix - 10
    else:
        print(f"Pas de signal - RSI:{rsi:.2f} EMA50:{ema50:.2f} EMA200:{ema200:.2f} MACD:{macd:.4f}")
        return

    lot = calculer_taille_position(prix, prix_sl)
    risque_euros = CAPITAL * (RISK_PERCENT / 100)
    gain_potentiel = risque_euros * 2

    tendance = "📈 Haussière" if ema50 > ema200 else "📉 Baissière"

    message = f"""
🚨 <b>SIGNAL {action}</b> 🚨

📊 XAUUSD | Tendance: {tendance}
📈 RSI: <b>{rsi:.2f}</b>
📊 MACD: <b>{macd:.4f}</b> / Signal: <b>{macd_signal:.4f}</b>

💰 Prix d'entrée: <b>{round(prix, 2)}</b>
📦 Taille lot: <b>{lot}</b>

🎯 Take Profit: <b>{round(prix_tp, 2)}</b>
🛑 Stop Loss: <b>{round(prix_sl, 2)}</b>

💵 Risque: <b>{risque_euros:.2f}€</b>
💎 Gain potentiel: <b>{gain_potentiel:.2f}€</b>

✅ Confirmé par 3 indicateurs (RSI + EMA + MACD)

👉 Ouvre Exness et passe l'ordre !
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
    envoyer_message(message)

def message_demarrage():
    message = """
🤖 <b>Bot Trading XAUUSD démarré !</b>

✅ Connecté à Telegram
✅ Analyse RSI + EMA50/200 + MACD
✅ Vérification toutes les 15 min

Tape /aide pour voir les commandes disponibles.
"""
    envoyer_message(message)

def traiter_commande(texte):
    texte = texte.strip().lower()

    if texte == "/prix":
        prix, rsi, ema50, ema200, macd, macd_signal = recuperer_toutes_donnees()
        if prix is None:
            envoyer_message("❌ Erreur lors de la récupération des données.")
            return

        tendance = "📈 Haussière" if ema50 > ema200 else "📉 Baissière"
        action = analyser_signal(prix, rsi, ema50, ema200, macd, macd_signal)
        statut = f"🟢 Signal {action} actif !" if action else "⚪ Aucun signal pour le moment"

        message = f"""
📊 <b>XAUUSD - État actuel</b>

💰 Prix: <b>{round(prix, 2)}</b>
📈 RSI ({INTERVAL}): <b>{rsi:.2f}</b>
📊 EMA50: <b>{ema50:.2f}</b> | EMA200: <b>{ema200:.2f}</b>
📉 Tendance: {tendance}
🔢 MACD: <b>{macd:.4f}</b> / Signal: <b>{macd_signal:.4f}</b>

{statut}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        envoyer_message(message)

    elif texte == "/status":
        envoyer_message(f"✅ Le bot tourne normalement !\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    elif texte == "/aide":
        message = """
📋 <b>Commandes disponibles :</b>

/prix - Voir le prix, RSI, EMA, MACD actuel
/status - Vérifier que le bot fonctionne
/aide - Afficher cette liste

📌 <b>Stratégie du bot :</b>
Signal envoyé seulement si 3 conditions réunies :
🟢 BUY: RSI < 35 + tendance haussière (EMA50>EMA200) + MACD haussier
🔴 SELL: RSI > 65 + tendance baissière (EMA50<EMA200) + MACD baissier
"""
        envoyer_message(message)

def ecouter_commandes():
    global dernier_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={dernier_update_id + 1}&timeout=30"
            r = requests.get(url, timeout=35).json()

            for update in r.get("result", []):
                dernier_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    texte = update["message"]["text"]
                    print(f"Commande reçue: {texte}")
                    traiter_commande(texte)

        except Exception as e:
            print(f"Erreur écoute commandes: {e}")
            time.sleep(5)

def boucle_analyse():
    while True:
        try:
            analyser_et_envoyer()
        except Exception as e:
            print(f"Erreur analyse: {e}")
        time.sleep(900)

# 🚀 DÉMARRAGE
if __name__ == "__main__":
    message_demarrage()
    print("Bot démarré ! Écoute des commandes + analyse en cours...")

    thread_commandes = threading.Thread(target=ecouter_commandes, daemon=True)
    thread_commandes.start()

    boucle_analyse()