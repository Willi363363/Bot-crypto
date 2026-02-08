# """
# Stratégie 1h améliorée : Trend-following multi-confirmation
# """
# from dataclasses import dataclass
# import os
# import numpy as np


# @dataclass
# class StrategySignal:
#     signal: str
#     reason: str
#     context: dict
#     stop_loss: float = None
#     take_profit_1: float = None
#     take_profit_2: float = None


# class ImprovedStrategy:
    
#     @staticmethod
#     def generate_signal(df):
#         """Génère un signal BUY/SELL/NEUTRAL."""
#         if df is None or len(df) < 220:
#             return StrategySignal(signal="NEUTRAL", reason="Données insuffisantes", context={})

#         last = df.iloc[-2]
#         prev = df.iloc[-3]
#         prev2 = df.iloc[-4]

#         def _env_bool(name: str, default: bool) -> bool:
#             value = os.getenv(name)
#             if value is None:
#                 return default
#             return value.strip().lower() in ("1", "true", "yes", "y", "on")

#         vol_floor = float(os.getenv('VOLUME_RATIO_MIN', '0.95'))
#         vol_spike = float(os.getenv('VOLUME_SPIKE_MIN', '1.3'))
#         chop_block = float(os.getenv('CHOP_NO_TRADE_MAX', '70'))
#         atr_silence = float(os.getenv('ATR_PCT_MIN', '0.005'))
#         atr_expansion_mult = float(os.getenv('ATR_EXPANSION_MULT', '1.05'))
#         atr_stop_mult = float(os.getenv('ATR_STOP_MULT', '1.0'))
#         tp1_mult = float(os.getenv('TP1_MULT', '1.4'))
#         tp2_mult = float(os.getenv('TP2_MULT', '2.8'))
#         require_structure = _env_bool('REQUIRE_STRUCTURE', True)
#         require_vwap = _env_bool('REQUIRE_VWAP', False)

#         close = last['close']
#         ema_50 = last['ema_50']
#         ema_200 = last['ema_200']
#         ema_200_slope = last['ema_200_slope']
#         ema_200_4h = last.get('ema_200_4h', np.nan)
#         sma_200_1d = last.get('sma_200_1d', np.nan)
#         structure = last['structure']
#         vwap = last['vwap']
#         chop = last['chop']

#         rsi = last['rsi']
#         rsi_prev = prev['rsi']
#         rsi_prev2 = prev2['rsi']

#         macd_hist = last['macd_hist']
#         macd_hist_prev = prev['macd_hist']

#         atr = last['atr']
#         atr_pct = last['atr_pct']
#         atr_pct_sma_20 = last.get('atr_pct_sma_20', np.nan)

#         volume = last['volume']
#         volume_ratio = last['volume_ratio']

#         recent_highs = df.iloc[-6:-2]['high'].values
#         recent_lows = df.iloc[-6:-2]['low'].values

#         bb_squeeze = last.get('bb_squeeze', False)
#         bb_upper = last.get('bb_upper', np.nan)
#         bb_lower = last.get('bb_lower', np.nan)

#         if volume_ratio < vol_floor:
#             return StrategySignal(signal="NEUTRAL", reason="Volume trop faible", context={"volume_ratio": volume_ratio})
#         if chop > chop_block:
#             return StrategySignal(signal="NEUTRAL", reason="Marché trop choppy", context={"chop": chop})
#         if atr_pct < atr_silence:
#             return StrategySignal(signal="NEUTRAL", reason="Volatilité trop compressée", context={"atr_pct": atr_pct})

#         htf_up = (np.isnan(ema_200_4h) or close > ema_200_4h) and (np.isnan(sma_200_1d) or close > sma_200_1d)
#         htf_down = (np.isnan(ema_200_4h) or close < ema_200_4h) and (np.isnan(sma_200_1d) or close < sma_200_1d)

#         trend_bullish = (
#             close > ema_200 and ema_50 > ema_200 and ema_200_slope > 0 and htf_up and
#             (structure == 'BULLISH' if require_structure else structure != 'BEARISH') and
#             (close > vwap if require_vwap else True)
#         )
#         trend_bearish = (
#             close < ema_200 and ema_50 < ema_200 and ema_200_slope < 0 and htf_down and
#             (structure == 'BEARISH' if require_structure else structure != 'BULLISH') and
#             (close < vwap if require_vwap else True)
#         )
#         if not (trend_bullish or trend_bearish):
#             return StrategySignal(signal="NEUTRAL", reason="Pas de tendance claire", context={"structure": structure})

#         rsi_pullback_long = (rsi_prev < 50 <= rsi) or (rsi_prev < rsi and rsi > 48)
#         rsi_pullback_short = (rsi_prev > 50 >= rsi) or (rsi_prev > rsi and rsi < 52)
#         macd_turn_long = macd_hist_prev < 0 <= macd_hist
#         macd_turn_short = macd_hist_prev > 0 >= macd_hist
#         pullback_long = rsi_pullback_long or macd_turn_long
#         pullback_short = rsi_pullback_short or macd_turn_short

#         atr_expanded = True if np.isnan(atr_pct_sma_20) else atr_pct >= atr_expansion_mult * atr_pct_sma_20
#         breakout_high = close > max(recent_highs) + 0.03 * atr
#         breakout_low = close < min(recent_lows) - 0.03 * atr
#         reject_short = last['high'] > ema_50 and close < ema_50 and close < last['open']
#         reject_long = last['low'] < ema_50 and close > ema_50 and close > last['open']
#         squeeze_break_long = bb_squeeze and close > bb_upper
#         squeeze_break_short = bb_squeeze and close < bb_lower
#         vol_confirm = volume_ratio >= vol_spike and atr_expanded

#         trigger_long = trend_bullish and pullback_long and vol_confirm and (squeeze_break_long or breakout_high)
#         trigger_short = trend_bearish and pullback_short and vol_confirm and (squeeze_break_short or breakout_low or reject_short)

#         if trigger_long:
#             stop_loss = min(last['low'], close - atr_stop_mult * atr)
#             tp1 = close + tp1_mult * atr
#             tp2 = close + tp2_mult * atr
#             return StrategySignal(
#                 signal="BUY",
#                 reason="Tendance haussière + pullback momentum + breakout/squeeze + volume",
#                 context={"entry": close, "rsi": rsi, "macd_hist": macd_hist, "volume_ratio": volume_ratio, "structure": structure, "trend": "BULLISH"},
#                 stop_loss=stop_loss,
#                 take_profit_1=tp1,
#                 take_profit_2=tp2
#             )

#         if trigger_short:
#             stop_loss = max(last['high'], close + atr_stop_mult * atr)
#             tp1 = close - tp1_mult * atr
#             tp2 = close - tp2_mult * atr
#             return StrategySignal(
#                 signal="SELL",
#                 reason="Tendance baissière + pullback momentum + breakout/squeeze + volume",
#                 context={"entry": close, "rsi": rsi, "macd_hist": macd_hist, "volume_ratio": volume_ratio, "structure": structure, "trend": "BEARISH"},
#                 stop_loss=stop_loss,
#                 take_profit_1=tp1,
#                 take_profit_2=tp2
#             )

#         return StrategySignal(
#             signal="NEUTRAL",
#             reason="Conditions partielles mais trigger manquant",
#             context={"trend_bullish": trend_bullish, "trend_bearish": trend_bearish, "pullback_long": pullback_long, "pullback_short": pullback_short, "volume_ratio": volume_ratio}
#         )


"""
Stratégie V2 OPTIMISÉE - Simple & Robuste
================================

PHILOSOPHIE :
- Moins de filtres (6 vs 13)
- Seuils réalistes
- Trend-following pur
- Objectif : 15-50 trades/an, Win rate 45-55%, R:R 1:2+

CHANGEMENTS MAJEURS vs V1 :
1. Volume : 0.5x vs 0.95x (accepte volume plus faible)
2. RSI : Zone 35-65 vs franchissement exact de 50
3. CHOP : 65 vs 48 (accepte plus de range léger)
4. Suppression : Structure de marché (trop rare)
5. Suppression : VWAP obligatoire
6. Suppression : EMA 200 4H (1 seul HTF suffit)
7. Volume spike : 1.1x vs 1.4x (spike léger suffit)
8. ATR min : 0.2% vs 0.5% (accepte volatilité plus faible)

PERFORMANCE ATTENDUE :
- Trades/an : 15-50
- Win rate : 45-55%
- Profit factor : 1.5-2.5
- Max drawdown : 15-25%
"""
from dataclasses import dataclass
import os
import numpy as np


@dataclass
class StrategySignal:
    signal: str
    reason: str
    context: dict
    stop_loss: float = None
    take_profit_1: float = None
    take_profit_2: float = None


class ImprovedStrategy:
    """
    Stratégie simplifiée et robuste pour BTC 1H
    
    LONG :
    1. Volume > 0.5x moyenne
    2. CHOP < 65
    3. ATR 0.2-3% 
    4. Prix > EMA 200 + Prix > SMA 200 daily
    5. RSI 35-65 OU MACD > 0
    6. Prix > EMA 50 + Volume > 1.1x
    
    SHORT : inverse
    """
    
    @staticmethod
    def generate_signal(df):
        """Génère signal BUY/SELL/NEUTRAL."""
        
        if df is None or len(df) < 220:
            return StrategySignal(
                signal="NEUTRAL",
                reason="Données insuffisantes (< 220 bougies)",
                context={}
            )
        
        # Dernières bougies
        last = df.iloc[-2]  # Bougie clôturée
        
        # ═══════════════════════════════════════════════════════════
        # PARAMÈTRES (valeurs par défaut OPTIMISÉES)
        # ═══════════════════════════════════════════════════════════
        
        # Filtres macro
        vol_min = float(os.getenv('VOLUME_RATIO_MIN', '0.5'))        # 0.5x vs 0.95x
        vol_spike = float(os.getenv('VOLUME_SPIKE_MIN', '1.1'))      # 1.1x vs 1.4x
        chop_max = float(os.getenv('CHOP_NO_TRADE_MAX', '65'))       # 65 vs 48
        atr_min_pct = float(os.getenv('ATR_PCT_MIN', '0.002'))       # 0.2% vs 0.65%
        atr_max_mult = float(os.getenv('ATR_EXTREME_MULT', '3.0'))
        
        # RSI (zone LARGE)
        rsi_min = float(os.getenv('RSI_MIN', '35'))                  # 35 vs 48
        rsi_max = float(os.getenv('RSI_MAX', '65'))                  # 65 vs 52
        
        # Stops & TPs
        atr_stop_mult = float(os.getenv('ATR_STOP_MULT', '2.0'))     # 2.0 vs 0.95
        tp1_mult = float(os.getenv('TP1_MULT', '1.5'))
        tp2_mult = float(os.getenv('TP2_MULT', '3.0'))
        
        # ═══════════════════════════════════════════════════════════
        # EXTRACTION INDICATEURS
        # ═══════════════════════════════════════════════════════════
        
        close = last['close']
        ema_50 = last['ema_50']
        ema_200 = last['ema_200']
        ema_200_slope = last['ema_200_slope']
        
        # HTF : Seulement 1 filtre (daily)
        sma_200_1d = last.get('sma_200_1d', np.nan)
        
        rsi = last['rsi']
        macd_hist = last['macd_hist']
        
        atr = last['atr']
        atr_pct = last['atr_pct']
        atr_ma = last.get('atr_ma', atr)
        
        volume_ratio = last['volume_ratio']
        chop = last['chop']
        
        # ═══════════════════════════════════════════════════════════
        # COUCHE 1 : FILTRES MACRO (NO-TRADE)
        # ═══════════════════════════════════════════════════════════
        
        # Volume trop faible
        if volume_ratio < vol_min:
            return StrategySignal(
                signal="NEUTRAL",
                reason=f"Volume trop faible ({volume_ratio:.2f}x < {vol_min}x)",
                context={"volume_ratio": volume_ratio}
            )
        
        # Marché choppy
        if chop > chop_max:
            return StrategySignal(
                signal="NEUTRAL",
                reason=f"Marché en range (CHOP {chop:.1f} > {chop_max})",
                context={"chop": chop}
            )
        
        # Volatilité trop faible
        if atr_pct < atr_min_pct:
            return StrategySignal(
                signal="NEUTRAL",
                reason=f"Volatilité trop faible (ATR {atr_pct*100:.2f}% < {atr_min_pct*100:.2f}%)",
                context={"atr_pct": atr_pct}
            )
        
        # Volatilité extrême
        if atr > atr_max_mult * atr_ma:
            return StrategySignal(
                signal="NEUTRAL",
                reason=f"Volatilité extrême (ATR > {atr_max_mult}x moyenne)",
                context={"atr": atr, "atr_ma": atr_ma}
            )
        
        # ═══════════════════════════════════════════════════════════
        # COUCHE 2 : TENDANCE (SIMPLIFIÉ - 2 CONDITIONS)
        # ═══════════════════════════════════════════════════════════
        
        # HTF trend (daily uniquement)
        htf_bullish = (np.isnan(sma_200_1d) or close > sma_200_1d)
        htf_bearish = (np.isnan(sma_200_1d) or close < sma_200_1d)
        
        # Tendance 1H
        trend_bullish = (
            close > ema_200 and
            ema_200_slope > 0 and
            htf_bullish
        )
        
        trend_bearish = (
            close < ema_200 and
            ema_200_slope < 0 and
            htf_bearish
        )
        
        if not (trend_bullish or trend_bearish):
            return StrategySignal(
                signal="NEUTRAL",
                reason="Pas de tendance claire (prix vs EMA 200)",
                context={
                    "close": close,
                    "ema_200": ema_200,
                    "ema_200_slope": ema_200_slope
                }
            )
        
        # ═══════════════════════════════════════════════════════════
        # COUCHE 3 : MOMENTUM (SIMPLIFIÉ - 1 CONDITION)
        # ═══════════════════════════════════════════════════════════
        
        # RSI dans zone LARGE (pas de franchissement exact)
        rsi_ok_long = (rsi_min < rsi < rsi_max)
        rsi_ok_short = (100 - rsi_max < rsi < 100 - rsi_min)  # 35-65 inversé
        
        # MACD positif/négatif
        macd_ok_long = macd_hist > 0
        macd_ok_short = macd_hist < 0
        
        # Au moins 1 des 2
        momentum_long = rsi_ok_long or macd_ok_long
        momentum_short = rsi_ok_short or macd_ok_short
        
        # ═══════════════════════════════════════════════════════════
        # COUCHE 4 : CONFIRMATION (SIMPLIFIÉ - 2 CONDITIONS)
        # ═══════════════════════════════════════════════════════════
        
        # Prix au-dessus EMA 50
        price_confirm_long = close > ema_50
        price_confirm_short = close < ema_50
        
        # Volume spike LÉGER
        volume_confirm = volume_ratio > vol_spike
        
        # ═══════════════════════════════════════════════════════════
        # GÉNÉRATION SIGNAL LONG
        # ═══════════════════════════════════════════════════════════
        
        if trend_bullish and momentum_long and price_confirm_long and volume_confirm:
            
            # Stop Loss : 2 ATR sous swing low récent
            recent_lows = df.iloc[-10:-1]['low'].min()
            stop_loss = min(recent_lows, close - atr_stop_mult * atr)
            
            # Take Profits
            tp1 = close + tp1_mult * atr
            tp2 = close + tp2_mult * atr
            
            # Raison
            reason_parts = []
            if rsi_ok_long:
                reason_parts.append(f"RSI {rsi:.1f}")
            if macd_ok_long:
                reason_parts.append("MACD+")
            reason = "Tendance haussière + " + " + ".join(reason_parts) + f" + volume {volume_ratio:.2f}x"
            
            return StrategySignal(
                signal="BUY",
                reason=reason,
                context={
                    "entry": close,
                    "rsi": rsi,
                    "macd_hist": macd_hist,
                    "volume_ratio": volume_ratio,
                    "ema_50": ema_50,
                    "ema_200": ema_200,
                    "chop": chop,
                    "atr": atr,
                    "trend": "BULLISH"
                },
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2
            )
        
        # ═══════════════════════════════════════════════════════════
        # GÉNÉRATION SIGNAL SHORT
        # ═══════════════════════════════════════════════════════════
        
        if trend_bearish and momentum_short and price_confirm_short and volume_confirm:
            
            # Stop Loss : 2 ATR au-dessus swing high récent
            recent_highs = df.iloc[-10:-1]['high'].max()
            stop_loss = max(recent_highs, close + atr_stop_mult * atr)
            
            # Take Profits
            tp1 = close - tp1_mult * atr
            tp2 = close - tp2_mult * atr
            
            # Raison
            reason_parts = []
            if rsi_ok_short:
                reason_parts.append(f"RSI {rsi:.1f}")
            if macd_ok_short:
                reason_parts.append("MACD-")
            reason = "Tendance baissière + " + " + ".join(reason_parts) + f" + volume {volume_ratio:.2f}x"
            
            return StrategySignal(
                signal="SELL",
                reason=reason,
                context={
                    "entry": close,
                    "rsi": rsi,
                    "macd_hist": macd_hist,
                    "volume_ratio": volume_ratio,
                    "ema_50": ema_50,
                    "ema_200": ema_200,
                    "chop": chop,
                    "atr": atr,
                    "trend": "BEARISH"
                },
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2
            )
        
        # ═══════════════════════════════════════════════════════════
        # AUCUN TRIGGER VALIDÉ
        # ═══════════════════════════════════════════════════════════
        
        reasons = []
        if trend_bullish:
            reasons.append("Tendance haussière OK")
            if not momentum_long:
                reasons.append(f"mais momentum faible (RSI {rsi:.1f}, MACD {macd_hist:.2f})")
            if not price_confirm_long:
                reasons.append(f"prix sous EMA 50")
            if not volume_confirm:
                reasons.append(f"volume {volume_ratio:.2f}x < {vol_spike}x")
        elif trend_bearish:
            reasons.append("Tendance baissière OK")
            if not momentum_short:
                reasons.append(f"mais momentum faible (RSI {rsi:.1f}, MACD {macd_hist:.2f})")
            if not price_confirm_short:
                reasons.append(f"prix sur EMA 50")
            if not volume_confirm:
                reasons.append(f"volume {volume_ratio:.2f}x < {vol_spike}x")
        
        return StrategySignal(
            signal="NEUTRAL",
            reason=" | ".join(reasons) if reasons else "Conditions incomplètes",
            context={
                "trend_bullish": trend_bullish,
                "trend_bearish": trend_bearish,
                "rsi": rsi,
                "macd_hist": macd_hist,
                "volume_ratio": volume_ratio
            }
        )