"""
Debug de la stratégie : identifier quel filtre bloque
"""
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators

def debug_filters():
    print("="*80)
    print("🔍 DEBUG DES FILTRES DE LA STRATÉGIE")
    print("="*80)
    
    # Récupération des données
    fetcher = DataFetcher(exchange_name='binance', symbol='BTC/USDT')
    df = fetcher.get_ohlcv(timeframe='1h', limit=500)
    
    if df is None:
        print("❌ Impossible de récupérer les données")
        return
    
    print(f"\n✅ {len(df)} bougies récupérées")
    
    # Calcul des indicateurs
    df = TechnicalIndicators.add_all_indicators(df)
    
    # Paramètres (via .env)
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in ("1", "true", "yes", "y", "on")

    atr_extreme_mult = float(os.getenv('ATR_EXTREME_MULT', '3'))
    volume_ratio_min = float(os.getenv('VOLUME_RATIO_MIN', '0.3'))
    chop_no_trade_max = float(os.getenv('CHOP_NO_TRADE_MAX', '70'))
    chop_trend_max = float(os.getenv('CHOP_TREND_MAX', '60'))
    ema_gap_min = float(os.getenv('EMA_GAP_MIN', '0.002'))
    rsi_pullback_long_min = float(os.getenv('RSI_PULLBACK_LONG_MIN', '35'))
    rsi_pullback_long_max = float(os.getenv('RSI_PULLBACK_LONG_MAX', '60'))
    volume_spike_min = float(os.getenv('VOLUME_SPIKE_MIN', '1.1'))

    require_structure = _env_bool('REQUIRE_STRUCTURE', False)
    require_vwap = _env_bool('REQUIRE_VWAP', False)
    require_macd = _env_bool('REQUIRE_MACD', False)
    require_volume_spike = _env_bool('REQUIRE_VOLUME_SPIKE', False)

    # Statistiques sur chaque filtre
    print(f"\n{'='*80}")
    print("📊 STATISTIQUES DES FILTRES (sur les 500 dernières bougies)")
    print(f"{'='*80}\n")
    
    # Couche 1 : Filtres macro
    print("🔴 COUCHE 1 : FILTRES MACRO (NO-TRADE ZONES)")
    print("-" * 80)
    
    df['atr_ma'] = df['atr'].rolling(20).mean()
    extreme_volatility = df['atr'] > atr_extreme_mult * df['atr_ma']
    print(f"Volatilité extrême (ATR > {atr_extreme_mult}x moyenne)    : {extreme_volatility.sum():4d} / {len(df)} ({extreme_volatility.mean()*100:.1f}%)")
    
    df['volume_ratio'] = df['volume'] / df['volume_sma_20']
    low_volume = df['volume_ratio'] < volume_ratio_min
    print(f"Volume mort (< {volume_ratio_min}x moyenne)             : {low_volume.sum():4d} / {len(df)} ({low_volume.mean()*100:.1f}%)")
    
    choppy_market = df['chop'] > chop_no_trade_max
    print(f"Marché choppy (CHOP > {chop_no_trade_max})              : {choppy_market.sum():4d} / {len(df)} ({choppy_market.mean()*100:.1f}%)")
    
    # Bougies qui passent la couche 1
    pass_layer1 = ~extreme_volatility & ~low_volume & ~choppy_market
    print(f"\n✅ PASSENT LA COUCHE 1                     : {pass_layer1.sum():4d} / {len(df)} ({pass_layer1.mean()*100:.1f}%)")
    
    # Couche 2 : Filtre de tendance
    print(f"\n🟡 COUCHE 2 : FILTRE DE TENDANCE")
    print("-" * 80)
    
    df['ema_gap'] = abs(df['ema_20'] - df['ema_50']) / df['close']
    
    # Tendance bullish
    trend_bull_ema = df['close'] > df['ema_50']
    trend_bull_ema2 = df['ema_50'] > df['ema_200']
    trend_bull_slope200 = df['ema_200_slope'] > 0
    trend_bull_slope200_10 = df['ema_200_slope_10'] > 0
    trend_bull_structure = df['structure'] == 'BULLISH' if require_structure else df['structure'] != 'BEARISH'
    trend_bull_vwap = df['close'] > df['vwap'] if require_vwap else pd.Series([True] * len(df), index=df.index)
    trend_bull_gap = df['ema_gap'] > ema_gap_min
    trend_bull_chop = df['chop'] < chop_trend_max
    
    print(f"Close > EMA 50                           : {trend_bull_ema.sum():4d} / {len(df)} ({trend_bull_ema.mean()*100:.1f}%)")
    print(f"EMA 50 > EMA 200                         : {trend_bull_ema2.sum():4d} / {len(df)} ({trend_bull_ema2.mean()*100:.1f}%)")
    print(f"EMA 200 slope > 0                        : {trend_bull_slope200.sum():4d} / {len(df)} ({trend_bull_slope200.mean()*100:.1f}%)")
    print(f"EMA 200 slope 10 bars > 0                : {trend_bull_slope200_10.sum():4d} / {len(df)} ({trend_bull_slope200_10.mean()*100:.1f}%)")
    print(f"Structure == BULLISH                     : {trend_bull_structure.sum():4d} / {len(df)} ({trend_bull_structure.mean()*100:.1f}%)")
    print(f"Close > VWAP                             : {trend_bull_vwap.sum():4d} / {len(df)} ({trend_bull_vwap.mean()*100:.1f}%)")
    print(f"EMA gap > {ema_gap_min*100:.2f}%                           : {trend_bull_gap.sum():4d} / {len(df)} ({trend_bull_gap.mean()*100:.1f}%)")
    print(f"CHOP < {chop_trend_max}                                : {trend_bull_chop.sum():4d} / {len(df)} ({trend_bull_chop.mean()*100:.1f}%)")
    
    trend_bullish = (
        trend_bull_ema & trend_bull_ema2 & 
        trend_bull_slope200 & trend_bull_slope200_10 &
        trend_bull_structure & trend_bull_vwap &
        trend_bull_gap & trend_bull_chop
    )
    
    print(f"\n✅ TENDANCE BULLISH COMPLÈTE               : {trend_bullish.sum():4d} / {len(df)} ({trend_bullish.mean()*100:.1f}%)")
    
    # Tendance bearish
    trend_bear_ema = df['close'] < df['ema_50']
    trend_bear_ema2 = df['ema_50'] < df['ema_200']
    trend_bear_slope200 = df['ema_200_slope'] < 0
    trend_bear_slope200_10 = df['ema_200_slope_10'] < 0
    trend_bear_structure = df['structure'] == 'BEARISH' if require_structure else df['structure'] != 'BULLISH'
    trend_bear_vwap = df['close'] < df['vwap'] if require_vwap else pd.Series([True] * len(df), index=df.index)
    trend_bear_gap = df['ema_gap'] > ema_gap_min
    trend_bear_chop = df['chop'] < chop_trend_max
    
    trend_bearish = (
        trend_bear_ema & trend_bear_ema2 &
        trend_bear_slope200 & trend_bear_slope200_10 &
        trend_bear_structure & trend_bear_vwap &
        trend_bear_gap & trend_bear_chop
    )
    
    print(f"✅ TENDANCE BEARISH COMPLÈTE              : {trend_bearish.sum():4d} / {len(df)} ({trend_bearish.mean()*100:.1f}%)")
    
    any_trend = trend_bullish | trend_bearish
    print(f"\n✅ AU MOINS UNE TENDANCE CLAIRE           : {any_trend.sum():4d} / {len(df)} ({any_trend.mean()*100:.1f}%)")
    
    # Bougies qui passent couche 1 ET 2
    pass_layer2 = pass_layer1 & any_trend
    print(f"\n✅ PASSENT COUCHES 1 + 2                   : {pass_layer2.sum():4d} / {len(df)} ({pass_layer2.mean()*100:.1f}%)")
    
    # Couche 3 : Setup
    print(f"\n🟢 COUCHE 3 : SETUP (PULLBACK)")
    print("-" * 80)
    
    df['rsi_prev'] = df['rsi'].shift(1)
    df['rsi_prev2'] = df['rsi'].shift(2)
    
    rsi_pullback_long = (
        (df['rsi'] > rsi_pullback_long_min) & (df['rsi'] < rsi_pullback_long_max) &
        (df['rsi'] > df['rsi_prev']) &
        (df['rsi_prev'] < df['rsi_prev2'])
    )
    
    print(f"RSI pullback LONG ({rsi_pullback_long_min}-{rsi_pullback_long_max}, remonte)       : {rsi_pullback_long.sum():4d} / {len(df)} ({rsi_pullback_long.mean()*100:.1f}%)")
    
    # Couche 4 : Trigger
    print(f"\n🔵 COUCHE 4 : TRIGGER (VOLUME)")
    print("-" * 80)
    
    volume_spike = df['volume_ratio'] > volume_spike_min
    print(f"Volume spike (> {volume_spike_min}x moyenne)            : {volume_spike.sum():4d} / {len(df)} ({volume_spike.mean()*100:.1f}%)")
    
    # RÉSUMÉ
    print(f"\n{'='*80}")
    print("📈 RÉSUMÉ DU PARCOURS (ENTONNOIR)")
    print(f"{'='*80}\n")
    
    print(f"Total bougies                            : {len(df):4d}")
    print(f"↓")
    print(f"Passent Couche 1 (macro)                 : {pass_layer1.sum():4d} ({pass_layer1.mean()*100:.1f}%)")
    print(f"↓")
    print(f"Passent Couche 2 (tendance)              : {pass_layer2.sum():4d} ({pass_layer2.mean()*100:.1f}%)")
    
    # DIAGNOSTIC
    print(f"\n{'='*80}")
    print("💡 DIAGNOSTIC")
    print(f"{'='*80}\n")
    
    if pass_layer1.mean() < 0.1:
        print("🚨 PROBLÈME IDENTIFIÉ : Couche 1 (filtres macro) trop restrictive !")
        print("   → Moins de 10% des bougies passent les filtres de base")
        print()
        if low_volume.mean() > 0.5:
            print("   🔴 Volume trop faible est le problème principal")
            print("   → SOLUTION : Baisser le seuil de volume de 0.5 à 0.3")
            print("   → Dans ImprovedStrategy, ligne ~90 : if volume_ratio < 0.3:")
        if choppy_market.mean() > 0.5:
            print("   🔴 Marché choppy est le problème principal")
            print("   → SOLUTION : Augmenter le seuil CHOP de 61.8 à 70")
    
    elif pass_layer2.mean() < 0.01:
        print("🚨 PROBLÈME IDENTIFIÉ : Couche 2 (tendance) trop restrictive !")
        print("   → Moins de 1% des bougies ont une tendance claire")
        print()
        if trend_bull_structure.mean() < 0.2:
            print("   🔴 Structure BULLISH/BEARISH rarement détectée")
            print("   → SOLUTION : Vérifier la fonction detect_market_structure()")
        if trend_bull_gap.mean() < 0.3:
            print("   🔴 Gap EMA trop strict (> 0.5%)")
            print("   → SOLUTION : Baisser à 0.3% dans la stratégie")
        if trend_bull_chop.mean() < 0.4:
            print("   🔴 CHOP < 55 trop strict")
            print("   → SOLUTION : Augmenter à CHOP < 60")
    
    else:
        print("✅ Les filtres macro et tendance semblent OK")
        print("   → Le problème vient probablement des couches 3 ou 4")
        print("   → Ou il n'y a vraiment pas eu de bons setups (rare)")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    debug_filters()