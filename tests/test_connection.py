"""
Test de connexion à l'API Kraken et récupération des données
"""
import ccxt
from datetime import datetime

def test_kraken_connection():
    print("🔄 Connexion à Kraken...")

    try:
        # Initialisation de l'exchange (pas besoin d'API key pour données publiques)
        exchange = ccxt.kraken({
            'enableRateLimit': True,  # Respecte les limites de l'API
        })

        # Récupération du prix actuel de BTC/USDT
        ticker = exchange.fetch_ticker('BTC/USDT')

        print(f"✅ Connexion réussie !")
        print(f"\n📊 Bitcoin (BTC/USDT)")
        print(f"   Prix actuel : ${ticker['last']:,.2f}")
        print(f"   24h High    : ${ticker['high']:,.2f}")
        print(f"   24h Low     : ${ticker['low']:,.2f}")
        print(f"   Volume 24h  : {ticker['baseVolume']:,.2f} BTC")

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

        return True

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

if __name__ == "__main__":
    test_kraken_connection()
