"""
Script de test en boucle - Exécute le bot toutes les X secondes
🧪 MODE TEST : Tous les messages Discord vont sur DISCORD_TEST_WEBHOOK_URL
ATTENTION : Seulement pour test local !
"""
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ⚠️ FORCER LE MODE TEST POUR CE SCRIPT
os.environ['TEST_MODE'] = 'true'

# Importer après avoir défini TEST_MODE
from main import analyze_market

def run_bot_loop(interval_seconds):
    """
    Exécute le bot en boucle

    Args:
        interval_seconds: Intervalle entre chaque analyse (60 = 1 minute)
    """
    print("="*70)
    print("🧪 MODE TEST ACTIVÉ")
    print("Tous les messages Discord seront envoyés sur le webhook de test")
    print("="*70)
    
    print("\n🚀 Démarrage du bot en mode TEST")
    print(f"⏱️  Fréquence: toutes les {interval_seconds} secondes")
    print("⚠️  Appuie sur Ctrl+C pour arrêter\n")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"🔄 Itération #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")

            try:
                analyze_market()
            except Exception as e:
                print(f"❌ Erreur lors de l'analyse: {e}")

            print(f"\n⏸️  Attente de {interval_seconds} secondes...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du bot demandé")
        print(f"✅ {iteration} itérations effectuées")

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 SCRIPT DE TEST - BOT DE TRADING")
    print("=" * 70)

    while True:
        try:
            interval = int(input("⏱️  Entre la fréquence de rafraîchissement (en secondes) : "))

            if interval <= 0:
                print("❌ La fréquence doit être un nombre STRICTEMENT positif.\n")
                continue

            break

        except ValueError:
            print("❌ Entrée invalide. Merci d'entrer un nombre entier.\n")

    print(f"\n✅ Fréquence définie : {interval} secondes\n")

    run_bot_loop(interval)
