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
    def calculate_macd(df, fast=12, slow=26, signal=9):
        """MACD classique"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df

    @staticmethod
    def calculate_daily_vwap(df):
        """VWAP resetté quotidiennement"""
        df = df.copy()
        df['date'] = df.index.normalize()  # Garde seulement la date
        
        df['pv'] = df['close'] * df['volume']
        df['cum_pv'] = df.groupby('date')['pv'].cumsum()
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        df['vwap'] = df['cum_pv'] / df['cum_vol']
        
        df.drop(['pv', 'cum_pv', 'cum_vol'], axis=1, inplace=True)
        
        return df

    @staticmethod
    def detect_market_structure(df, lookback=20):
        """Détecte HH/HL (bullish) ou LH/LL (bearish)"""
        df = df.copy()
        
        # Swing highs/lows sur période de lookback
        df['swing_high'] = df['high'].rolling(lookback, center=True).max()
        df['swing_low'] = df['low'].rolling(lookback, center=True).min()
        
        # HH : nouveau swing high > précédent
        df['hh'] = df['swing_high'] > df['swing_high'].shift(lookback)
        # HL : nouveau swing low > précédent
        df['hl'] = df['swing_low'] > df['swing_low'].shift(lookback)
        
        # LH : nouveau swing high < précédent
        df['lh'] = df['swing_high'] < df['swing_high'].shift(lookback)
        # LL : nouveau swing low < précédent
        df['ll'] = df['swing_low'] < df['swing_low'].shift(lookback)
        
        # Structure de marché
        df['structure'] = 'NEUTRAL'
        df.loc[df['hh'] & df['hl'], 'structure'] = 'BULLISH'
        df.loc[df['lh'] & df['ll'], 'structure'] = 'BEARISH'
        
        # Forward fill pour avoir une valeur à chaque ligne
        df['structure'] = df['structure'].replace('NEUTRAL', pd.NA).ffill().fillna('NEUTRAL')
        
        return df

    @staticmethod
    def calculate_bollinger_squeeze(df, period=20, std_dev=2):
        """Détecte compression Bollinger Bands"""
        df = df.copy()
        
        df['bb_mid'] = df['close'].rolling(period).mean()
        df['bb_std'] = df['close'].rolling(period).std()
        df['bb_upper'] = df['bb_mid'] + (std_dev * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (std_dev * df['bb_std'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        df['bb_width_ma'] = df['bb_width'].rolling(50).mean()
        
        # Squeeze = largeur < 70% de la moyenne
        df['bb_squeeze'] = df['bb_width'] < (df['bb_width_ma'] * 0.7)
        
        return df

    # Modifier add_all_indicators
    @staticmethod
    def add_all_indicators(df, chop_period=14, sr_lookback=50, atr_period=14):
        """Ajoute TOUS les indicateurs"""
        # Existants
        df['ema_20'] = TechnicalIndicators.calculate_ema(df, 20)
        df['ema_50'] = TechnicalIndicators.calculate_ema(df, 50)
        df['ema_200'] = TechnicalIndicators.calculate_ema(df, 200)
        df['ema_200_slope'] = df['ema_200'].diff()
        df['ema_50_slope'] = df['ema_50'].diff()
        df['ema_200_slope_10'] = df['ema_200'].diff(10)
        df['ema_50_slope_10'] = df['ema_50'].diff(10)
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, 14)
        df['rsi_delta'] = df['rsi'].diff()
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['chop'] = TechnicalIndicators.calculate_choppiness(df, chop_period)
        df['atr'] = TechnicalIndicators.calculate_atr(df, atr_period)
        df['atr_ma'] = df['atr'].rolling(20).mean()
        df = TechnicalIndicators.add_support_resistance(df, lookback=sr_lookback)
        df['trend'] = np.where(df['ema_20'] > df['ema_50'], 'BULLISH', 'BEARISH')
        
        # NOUVEAUX
        df = TechnicalIndicators.calculate_macd(df)
        df = TechnicalIndicators.calculate_daily_vwap(df)
        df = TechnicalIndicators.detect_market_structure(df, lookback=20)
        df = TechnicalIndicators.calculate_bollinger_squeeze(df)
        
        # Métriques supplémentaires
        df['ema_gap'] = abs(df['ema_20'] - df['ema_50']) / df['close']
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        df['atr_pct'] = df['atr'] / df['close']
        df['atr_pct_sma_20'] = df['atr_pct'].rolling(20).mean()

        # HTF (4H) trend filter: EMA200 on 4H closes forward-filled to 1H
        try:
            h4_close = df['close'].resample('4h').last()
            h4_ema200 = h4_close.ewm(span=200, adjust=False).mean()
            df['ema_200_4h'] = h4_ema200.reindex(df.index, method='ffill')
            df['ema_200_4h_slope'] = df['ema_200_4h'].diff()
        except Exception:
            df['ema_200_4h'] = np.nan
            df['ema_200_4h_slope'] = np.nan

        # Daily regime filter (SMA200 daily forward-filled to 1h)
        try:
            d1_close = df['close'].resample('1d').last()
            d1_sma200 = d1_close.rolling(200).mean()
            df['sma_200_1d'] = d1_sma200.reindex(df.index, method='ffill')
        except Exception:
            df['sma_200_1d'] = np.nan
        
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