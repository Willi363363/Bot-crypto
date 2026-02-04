"""
Récupération des données de marché
"""
import ccxt
import pandas as pd
from datetime import datetime

class DataFetcher:
    def __init__(self, exchange_name='binance', symbol='BTC/USDT'):
        self.exchange = getattr(ccxt, exchange_name)({
            'enableRateLimit': True
        })
        self.symbol = symbol

    def get_ohlcv(self, timeframe='1h', limit=100):
        """Récupère les données OHLCV"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)

            # Conversion en DataFrame pandas
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            return df
        except Exception as e:
            print(f"❌ Erreur récupération données: {e}")
            return None

    def get_current_price(self):
        """Prix actuel"""
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker['last']
        except Exception as e:
            print(f"❌ Erreur prix actuel: {e}")
            return None

# Test
if __name__ == "__main__":
    fetcher = DataFetcher()

    print("📊 Récupération des données BTC/USDT...")
    df = fetcher.get_ohlcv(timeframe='1h', limit=100)

    if df is not None:
        print(f"\n✅ {len(df)} bougies récupérées")
        print(f"\n{df.tail()}")

        price = fetcher.get_current_price()
        print(f"\n💰 Prix actuel: ${price:,.2f}")