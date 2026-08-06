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
dernier_signal_envoye = None


# ============ TELEGRAM ============

def envoyer_message(texte):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texte, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print(f"Erreur envoi message ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"Erreur envoi message: {e}")


# ============ RÉCUPÉRATION DONNÉES (avec robustesse) ============

def requete_api(url, cle_valeur, nom_indicateur):
    """Fait une requête API et gère toutes les erreurs possibles."""
    try:
        r = requests.get(url, timeout=15).json()

        # Vérifie si l'API renvoie une erreur explicite
        if "status" in r and r["status"] == "error":
            print(f"Erreur API {nom_indicateur}: {r.get('message', 'inconnue')}")
            return None

        if "code" in r and r["code"] != 200:
            print(f"Erreur API {nom_indicateur} (code {r['code']}): {r.get('message', '')}")
            return None

        if cle_valeur == "price":
            return float(r["price"])
        elif cle_valeur == "rsi":
            return float(r["values"][0]["rsi"])
        elif cle_valeur == "ema":
            return float(r["values"][0]["ema"])
        elif cle_valeur == "macd":
            return (float(r["values"][0]["macd"]), float(r["values"][0]["macd_signal"]))

    except requests.exceptions.Timeout:
        print(f"Timeout API {nom_indicateur}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau API {nom_indicateur}: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Erreur parsing API {nom_indicateur}: {e} | Réponse: {r}")
        return None
    except Exception as e:
        print(f"Erreur inconnue API {nom_indicateur}: {e}")
        return None


def recuperer_prix():
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={TWELVEDATA_KEY}"
    return requete_api(url, "price", "PRIX")


def recuperer_rsi():
    url = f"https://api.twelvedata.com/rsi?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
    return requete_api(url, "rsi", "RSI")


def recuperer_ema(periode):
    url = f"https://api.twelvedata.com/ema?symbol={SYMBOL}&interval={INTERVAL}&time_period={periode}&apikey={TWELVEDATA_KEY}"
    return requete_api(url, "ema", f"EMA{periode}")


def recuperer_macd():
    url = f"https://api.twelvedata.com/macd?symbol={SYMBOL}&interval={INTERVAL}&apikey={TWELVEDATA_KEY}"
    resultat = requete_api(url, "macd", "MACD")
    if resultat is None:
        return None, None
    return resultat


def recuperer_toutes_donnees():
    """Récupère tout, avec des pauses pour éviter la limite API (8 req/min)."""
    prix = recuperer_prix()
    time.sleep(1)
    rsi = recuperer_rsi()
    time.sleep(1)
    ema50 = recuperer_ema(50)
    time.sleep(1)
    ema200 = recuperer_ema(200)
    time.sleep(1)
    macd, macd_signal = recuperer_macd()

    return prix, rsi, ema50, ema200, macd, macd_signal


# ============ ANALYSE / STRATÉGIE ============

def analyser_signal(prix, rsi, ema50, ema200, macd, macd_signal):
    """Retourne 'BUY', 'SELL' ou None selon la stratégie."""
    if None in (prix, rsi, ema50, ema200, macd, macd_signal):
        return None

    tendance_haussiere = ema50 > ema200
    tendance_baissiere = ema50 < ema200
    macd_haussier = macd > macd_signal
    macd_baissier = macd < macd_signal

    if rsi < 35 and tendance_haussiere and macd_haussier:
        return "BUY"
    elif rsi > 65 and tendance_baissiere and macd_baissier:
        return "SELL"

    return None


def calculer_sl_tp(prix, action):
    """Calcule Stop Loss et Take Profit basiques (exemple simple)."""
    if action == "BUY":
        sl = prix * 0.995
        tp = prix * 1.01
    elif action == "SELL":
        sl = prix * 1.005
        tp = prix * 0.99
    else:
        return None, None
    return round(sl, 2), round(tp, 2)


def analyser_et_envoyer():
    global dernier_signal_envoye

    prix, rsi, ema50, ema200, macd, macd_signal = recuperer_toutes_donnees()

    if None in (prix, rsi, ema50, ema200, macd, macd_signal):
        print("⚠️ Analyse automatique annulée : données incomplètes.")
        return

    action = analyser_signal(prix, rsi, ema50, ema200, macd, macd_signal)

    if action and action != dernier_signal_envoye:
        sl, tp = calculer_sl_tp(prix, action)
        emoji = "🟢" if action == "BUY" else "🔴"

        message = f"""
{emoji} <b>SIGNAL {action} - XAUUSD</b>

💰 Prix d'entrée: <b>{round(prix, 2)}</b>
🛑 Stop Loss: <b>{sl}</b>
🎯 Take Profit: <b>{tp}</b>

📈 RSI: {rsi:.2f}
📊 EMA50: {ema50:.2f} | EMA200: {ema200:.2f}
🔢 MACD: {macd:.4f} / Signal: {macd_signal:.4f}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        envoyer_message(message)
        dernier_signal_envoye = action

    elif action is None:
        dernier_signal_envoye = None


# ============ MESSAGES / COMMANDES ============

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

    # Retire les mentions type /prix@NomDuBot
    if "@" in texte:
        texte = texte.split("@")[0]

    try:
        if texte == "/start":
            message_demarrage()

        elif texte == "/prix":
            prix, rsi, ema50, ema200, macd, macd_signal = recuperer_toutes_donnees()

            if None in (prix, rsi, ema50, ema200, macd, macd_signal):
                envoyer_message(
                    "❌ Erreur lors de la récupération des données.\n"
                    "Cause probable : limite API atteinte (max 8 req/min sur le plan gratuit TwelveData).\n"
                    "⏳ Réessaie dans 1 minute."
                )
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
            message = (
                "📋 <b>Commandes disponibles :</b>\n\n"
                "/start - Redémarrer / message de bienvenue\n"
                "/prix - Voir le prix, RSI, EMA, MACD actuel\n"
                "/status - Vérifier que le bot fonctionne\n"
                "/aide - Afficher cette liste\n\n"
                "📌 <b>Stratégie du bot :</b>\n"
                "🟢 BUY: RSI < 35 + tendance haussière (EMA50>EMA200) + MACD haussier\n"
                "🔴 SELL: RSI > 65 + tendance baissière (EMA50<EMA200) + MACD baissier\n\n"
                f"💼 Capital: {CAPITAL}$ | Risque: {RISK_PERCENT}%"
            )
            envoyer_message(message)

        else:
            envoyer_message("❓ Commande inconnue. Tape /aide pour voir les commandes disponibles.")

    except Exception as e:
        print(f"Erreur dans traiter_commande('{texte}'): {e}")
        envoyer_message(f"❌ Erreur interne lors du traitement de la commande.\n{e}")


# ============ BOUCLES PRINCIPALES ============

def ecouter_commandes():
    global dernier_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={dernier_update_id + 1}&timeout=30"
            r = requests.get(url, timeout=35).json()

            if not r.get("ok", False):
                print(f"Erreur getUpdates: {r}")
                time.sleep(5)
                continue

            for update in r.get("result", []):
                dernier_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    texte = update["message"]["text"]
                    print(f"Commande reçue: {texte}")
                    traiter_commande(texte)

        except requests.exceptions.Timeout:
            # Normal avec le long polling, on continue
            continue
        except requests.exceptions.RequestException as e:
            print(f"Erreur réseau écoute commandes: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"Erreur écoute commandes: {e}")
            time.sleep(5)


def boucle_analyse():
    while True:
        try:
            analyser_et_envoyer()
        except Exception as e:
            print(f"Erreur analyse: {e}")
        time.sleep(900)  # 15 minutes


# ============ DÉMARRAGE ============

if __name__ == "__main__":
    print("Bot démarré ! Écoute des commandes + analyse en cours...")
    message_demarrage()

    thread_commandes = threading.Thread(target=ecouter_commandes, daemon=True)
    thread_commandes.start()

    boucle_analyse()