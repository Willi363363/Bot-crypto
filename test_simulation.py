"""
Script de test en boucle - Exécute le bot toutes les X secondes
ATTENTION : Seulement pour test local !
"""
import time
from main import analyze_market
from datetime import datetime

def run_bot_loop(interval_seconds):
    """
    Exécute le bot en boucle

    Args:
        interval_seconds: Intervalle entre chaque analyse (60 = 1 minute)
    """
    print("🚀 Démarrage du bot en mode TEST")
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
    # Change cette valeur pour tester différentes fréquences
    INTERVAL = 1  # 60 secondes = 1 minute

    run_bot_loop(INTERVAL)