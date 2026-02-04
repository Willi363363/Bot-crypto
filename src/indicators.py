"""
Calcul des indicateurs techniques
"""
import pandas as pd
import numpy as np

class TechnicalIndicators:

    @staticmethod
    def calculate_ema(df, period):
        """Moyenne Mobile Exponentielle"""
        return df['close'].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(df, period=14):
        """RSI (Relative Strength Index)"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def add_all_indicators(df):
        """Ajoute tous les indicateurs au DataFrame"""
        # EMAs
        df['ema_20'] = TechnicalIndicators.calculate_ema(df, 20)
        df['ema_50'] = TechnicalIndicators.calculate_ema(df, 50)
        df['ema_200'] = TechnicalIndicators.calculate_ema(df, 200)

        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, 14)

        # Tendance simple (EMA 20 > 50)
        df['trend'] = np.where(df['ema_20'] > df['ema_50'], 'BULLISH', 'BEARISH')

        return df

# Test
if __name__ == "__main__":
    from data_fetcher import DataFetcher

    fetcher = DataFetcher()
    df = fetcher.get_ohlcv(timeframe='1h', limit=200)

    if df is not None:
        df = TechnicalIndicators.add_all_indicators(df)

        print("📊 Indicateurs calculés :")
        print(df[['close', 'ema_20', 'ema_50', 'rsi', 'trend']].tail(10))

        # Dernières valeurs
        last = df.iloc[-1]
        print(f"\n📈 Dernières valeurs :")
        print(f"   Prix    : ${last['close']:,.2f}")
        print(f"   EMA 20  : ${last['ema_20']:,.2f}")
        print(f"   EMA 50  : ${last['ema_50']:,.2f}")
        print(f"   RSI     : {last['rsi']:.2f}")
        print(f"   Tendance: {last['trend']}")