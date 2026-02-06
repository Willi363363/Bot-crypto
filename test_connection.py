"""
Test de connexion à l'API Kraken et récupération des données
🧪 MODE TEST : Tous les messages Discord vont sur DISCORD_TEST_WEBHOOK_URL
"""
import ccxt
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ⚠️ FORCER LE MODE TEST POUR CE SCRIPT
os.environ['TEST_MODE'] = 'true'

# Importer après avoir défini TEST_MODE
from src.notifier import DiscordNotifier

def test_kraken_connection():
    print("="*70)
    print("🧪 MODE TEST ACTIVÉ")
    print("Tous les messages Discord seront envoyés sur le webhook de test")
    print("="*70)
    
    # Initialiser le notifier (détectera automatiquement le mode test)
    notifier = DiscordNotifier()
    
    # Message de démarrage
    notifier.send_message(
        title="🧪 Test de connexion démarré",
        description="Vérification de la connexion à Kraken",
        color=0x0099ff
    )
    
    print("\n🔄 Connexion à Kraken...")

    try:
        # Initialisation de l'exchange
        exchange = ccxt.kraken({
            'enableRateLimit': True,
        })

        # Récupération du prix actuel de BTC/USDT
        ticker = exchange.fetch_ticker('BTC/USDT')

        print(f"✅ Connexion réussie !")
        print(f"\n📊 Bitcoin (BTC/USDT)")
        print(f"   Prix actuel : ${ticker['last']:,.2f}")
        print(f"   24h High    : ${ticker['high']:,.2f}")
        print(f"   24h Low     : ${ticker['low']:,.2f}")
        print(f"   Volume 24h  : {ticker['baseVolume']:,.2f} BTC")

        # Message Discord de succès
        notifier.send_message(
            title="✅ Connexion Kraken réussie",
            description=f"Prix BTC/USDT: ${ticker['last']:,.2f}",
            color=0x00ff00,
            fields=[
                {"name": "💰 Prix", "value": f"${ticker['last']:,.2f}", "inline": True},
                {"name": "📈 24h High", "value": f"${ticker['high']:,.2f}", "inline": True},
                {"name": "📉 24h Low", "value": f"${ticker['low']:,.2f}", "inline": True},
                {"name": "📊 Volume", "value": f"{ticker['baseVolume']:,.2f} BTC", "inline": False}
            ]
        )

        # Test récupération données historiques
        print(f"\n🔄 Récupération données historiques (100 dernières bougies 1h)...")
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)

        print(f"✅ {len(ohlcv)} bougies récupérées")
        print(f"\nDernière bougie :")
        last_candle = ohlcv[-1]
        print(f"   Timestamp : {datetime.fromtimestamp(last_candle[0]/1000)}")
        print(f"   Open      : ${last_candle[1]:,.2f}")
        print(f"   High      : ${last_candle[2]:,.2f}")
        print(f"   Low       : ${last_candle[3]:,.2f}")
        print(f"   Close     : ${last_candle[4]:,.2f}")
        print(f"   Volume    : {last_candle[5]:,.2f} BTC")

        # Message Discord avec les données historiques
        notifier.send_message(
            title="📊 Données historiques récupérées",
            description=f"{len(ohlcv)} bougies de 1h récupérées avec succès",
            color=0x00ff00,
            fields=[
                {"name": "🕐 Timestamp", "value": datetime.fromtimestamp(last_candle[0]/1000).strftime('%Y-%m-%d %H:%M'), "inline": False},
                {"name": "📊 Open", "value": f"${last_candle[1]:,.2f}", "inline": True},
                {"name": "📈 High", "value": f"${last_candle[2]:,.2f}", "inline": True},
                {"name": "📉 Low", "value": f"${last_candle[3]:,.2f}", "inline": True},
                {"name": "💰 Close", "value": f"${last_candle[4]:,.2f}", "inline": True},
                {"name": "📊 Volume", "value": f"{last_candle[5]:,.2f} BTC", "inline": True}
            ]
        )
        
        # Message final de succès
        notifier.send_message(
            title="🎉 Test terminé avec succès",
            description="Toutes les vérifications sont passées ✅",
            color=0x00ff00
        )

        return True

    except Exception as e:
        print(f"❌ Erreur : {e}")
        
        # Message Discord d'erreur
        notifier.send_message(
            title="❌ Erreur de test",
            description=f"Une erreur s'est produite : {str(e)}",
            color=0xff0000
        )
        
        return False

if __name__ == "__main__":
    test_kraken_connection()