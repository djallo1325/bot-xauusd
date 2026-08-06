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

def recuperer_donnees():
    try:
        url_prix = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={TWELVEDATA_KEY}"
        r_prix = requests.get(url_prix, timeout=10).json()
        prix = float(r_prix["price"])

        url_rsi = f"https://api.twelvedata.com/rsi?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
        r_rsi = requests.get(url_rsi, timeout=10).json()
        rsi = float(r_rsi["values"][0]["rsi"])

        return prix, rsi
    except Exception as e:
        print(f"Erreur récupération données: {e}")
        return None, None

def calculer_taille_position(prix_entree, prix_sl):
    risque_euros = CAPITAL * (RISK_PERCENT / 100)
    distance_pips = abs(prix_entree - prix_sl) * 100
    if distance_pips == 0:
        return 0.01
    lot = risque_euros / (distance_pips * 1)
    return round(max(lot, 0.01), 2)

def analyser_et_envoyer():
    prix, rsi = recuperer_donnees()
    if prix is None or rsi is None:
        return

    action = None
    if rsi < 30:
        action = "BUY"
        prix_sl = prix - 5
        prix_tp = prix + 10
    elif rsi > 70:
        action = "SELL"
        prix_sl = prix + 5
        prix_tp = prix - 10

    if action:
        lot = calculer_taille_position(prix, prix_sl)
        risque_euros = CAPITAL * (RISK_PERCENT / 100)
        gain_potentiel = risque_euros * 2

        message = f"""
🚨 <b>SIGNAL {action}</b> 🚨

📊 XAUUSD | RSI: {rsi:.2f}
💰 Prix d'entrée: <b>{round(prix, 2)}</b>
📦 Taille lot: <b>{lot}</b>

🎯 Take Profit: <b>{round(prix_tp, 2)}</b>
🛑 Stop Loss: <b>{round(prix_sl, 2)}</b>

💵 Risque: <b>{risque_euros:.2f}€</b>
💎 Gain potentiel: <b>{gain_potentiel:.2f}€</b>

👉 Ouvre Exness et passe l'ordre avec ces valeurs !
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        envoyer_message(message)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Signal envoyé: {action} à {prix} (RSI: {rsi:.2f})")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pas de signal - RSI: {rsi:.2f} (prix: {prix})")

def message_demarrage():
    texte = f"""
🤖 <b>Bot de trading démarré !</b>

📊 Paire: XAUUSD
⏱️ Timeframe: {INTERVAL.upper()}
💰 Capital: {CAPITAL}€
⚠️ Risque par trade: {RISK_PERCENT}% ({CAPITAL * RISK_PERCENT / 100:.2f}€)

✅ RSI en temps réel activé (TwelveData)

<b>Commandes disponibles :</b>
/prix - Voir le prix et RSI actuel
/status - Vérifier que le bot tourne
/aide - Liste des commandes

Le bot va analyser le marché et t'envoyer des signaux fiables.
Bon trade ! 🚀
"""
    envoyer_message(texte)

def traiter_commande(texte):
    texte = texte.strip().lower()

    if texte == "/start":
        message_demarrage()

    elif texte == "/prix":
        prix, rsi = recuperer_donnees()
        if prix is None:
            envoyer_message("❌ Erreur lors de la récupération des données. Réessaie dans un instant.")
            return

        if rsi < 30:
            statut = "🟢 Zone de SURVENTE (achat possible)"
        elif rsi > 70:
            statut = "🔴 Zone de SURACHAT (vente possible)"
        else:
            statut = "⚪ Zone neutre (pas de signal)"

        message = f"""
📊 <b>XAUUSD - État actuel</b>

💰 Prix: <b>{round(prix, 2)}</b>
📈 RSI ({INTERVAL}): <b>{rsi:.2f}</b>

{statut}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        envoyer_message(message)

    elif texte == "/status":
        envoyer_message(f"✅ Le bot tourne normalement !\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    elif texte == "/aide":
        message = """
📋 <b>Commandes disponibles :</b>

/prix - Voir le prix et RSI actuel de XAUUSD
/status - Vérifier que le bot fonctionne
/aide - Afficher cette liste

Le bot t'envoie automatiquement un signal quand :
🟢 RSI < 30 (survente → BUY)
🔴 RSI > 70 (surachat → SELL)
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