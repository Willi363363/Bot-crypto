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
    def calculate_choppiness(df, period=14):
        """Choppiness Index (CHOP)"""
        high = df['high']
        low = df['low']
        close = df['close']

        prev_close = close.shift(1)
        true_range = pd.concat(
            [
                (high - low),
                (high - prev_close).abs(),
                (low - prev_close).abs()
            ],
            axis=1
        ).max(axis=1)

        atr_sum = true_range.rolling(window=period).sum()
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        price_range = (highest_high - lowest_low)
        chop = 100 * np.log10(atr_sum / price_range) / np.log10(period)
        chop = chop.replace([np.inf, -np.inf], np.nan)

        return chop

    @staticmethod
    def calculate_atr(df, period=14):
        """Average True Range (ATR)"""
        high = df['high']
        low = df['low']
        close = df['close']

        prev_close = close.shift(1)
        true_range = pd.concat(
            [
                (high - low),
                (high - prev_close).abs(),
                (low - prev_close).abs()
            ],
            axis=1
        ).max(axis=1)

        atr = true_range.rolling(window=period).mean()
        return atr

    @staticmethod
    def add_support_resistance(df, lookback=50):
        """Ajoute des niveaux simples de support / résistance (rolling)"""
        df['support'] = df['low'].rolling(window=lookback, min_periods=lookback).min().shift(1)
        df['resistance'] = df['high'].rolling(window=lookback, min_periods=lookback).max().shift(1)
        return df

    @staticmethod
    def add_all_indicators(df, chop_period=14, sr_lookback=50, atr_period=14):
        """Ajoute tous les indicateurs au DataFrame"""
        # EMAs
        df['ema_20'] = TechnicalIndicators.calculate_ema(df, 20)
        df['ema_50'] = TechnicalIndicators.calculate_ema(df, 50)
        df['ema_200'] = TechnicalIndicators.calculate_ema(df, 200)

        # Pente EMA200
        df['ema_200_slope'] = df['ema_200'].diff()
        df['ema_50_slope'] = df['ema_50'].diff()
        df['ema_200_slope_10'] = df['ema_200'].diff(10)
        df['ema_50_slope_10'] = df['ema_50'].diff(10)

        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, 14)
        df['rsi_delta'] = df['rsi'].diff()

        # Volume
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()

        # Choppiness Index
        df['chop'] = TechnicalIndicators.calculate_choppiness(df, chop_period)

        # ATR
        df['atr'] = TechnicalIndicators.calculate_atr(df, atr_period)

        # Supports / résistances
        df = TechnicalIndicators.add_support_resistance(df, lookback=sr_lookback)

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