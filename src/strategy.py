"""
Stratégie 1h améliorée : Trend-following multi-confirmation
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
    
    @staticmethod
    def generate_signal(df):
        """Génère un signal BUY/SELL/NEUTRAL."""
        if df is None or len(df) < 220:
            return StrategySignal(signal="NEUTRAL", reason="Données insuffisantes", context={})

        last = df.iloc[-2]
        prev = df.iloc[-3]
        prev2 = df.iloc[-4]

        def _env_bool(name: str, default: bool) -> bool:
            value = os.getenv(name)
            if value is None:
                return default
            return value.strip().lower() in ("1", "true", "yes", "y", "on")

        vol_floor = float(os.getenv('VOLUME_RATIO_MIN', '0.95'))
        vol_spike = float(os.getenv('VOLUME_SPIKE_MIN', '1.3'))
        chop_block = float(os.getenv('CHOP_NO_TRADE_MAX', '70'))
        atr_silence = float(os.getenv('ATR_PCT_MIN', '0.005'))
        atr_expansion_mult = float(os.getenv('ATR_EXPANSION_MULT', '1.05'))
        atr_stop_mult = float(os.getenv('ATR_STOP_MULT', '1.0'))
        tp1_mult = float(os.getenv('TP1_MULT', '1.4'))
        tp2_mult = float(os.getenv('TP2_MULT', '2.8'))
        require_structure = _env_bool('REQUIRE_STRUCTURE', True)
        require_vwap = _env_bool('REQUIRE_VWAP', False)

        close = last['close']
        ema_50 = last['ema_50']
        ema_200 = last['ema_200']
        ema_200_slope = last['ema_200_slope']
        ema_200_4h = last.get('ema_200_4h', np.nan)
        sma_200_1d = last.get('sma_200_1d', np.nan)
        structure = last['structure']
        vwap = last['vwap']
        chop = last['chop']

        rsi = last['rsi']
        rsi_prev = prev['rsi']
        rsi_prev2 = prev2['rsi']

        macd_hist = last['macd_hist']
        macd_hist_prev = prev['macd_hist']

        atr = last['atr']
        atr_pct = last['atr_pct']
        atr_pct_sma_20 = last.get('atr_pct_sma_20', np.nan)

        volume = last['volume']
        volume_ratio = last['volume_ratio']

        recent_highs = df.iloc[-6:-2]['high'].values
        recent_lows = df.iloc[-6:-2]['low'].values

        bb_squeeze = last.get('bb_squeeze', False)
        bb_upper = last.get('bb_upper', np.nan)
        bb_lower = last.get('bb_lower', np.nan)

        if volume_ratio < vol_floor:
            return StrategySignal(signal="NEUTRAL", reason="Volume trop faible", context={"volume_ratio": volume_ratio})
        if chop > chop_block:
            return StrategySignal(signal="NEUTRAL", reason="Marché trop choppy", context={"chop": chop})
        if atr_pct < atr_silence:
            return StrategySignal(signal="NEUTRAL", reason="Volatilité trop compressée", context={"atr_pct": atr_pct})

        htf_up = (np.isnan(ema_200_4h) or close > ema_200_4h) and (np.isnan(sma_200_1d) or close > sma_200_1d)
        htf_down = (np.isnan(ema_200_4h) or close < ema_200_4h) and (np.isnan(sma_200_1d) or close < sma_200_1d)

        trend_bullish = (
            close > ema_200 and ema_50 > ema_200 and ema_200_slope > 0 and htf_up and
            (structure == 'BULLISH' if require_structure else structure != 'BEARISH') and
            (close > vwap if require_vwap else True)
        )
        trend_bearish = (
            close < ema_200 and ema_50 < ema_200 and ema_200_slope < 0 and htf_down and
            (structure == 'BEARISH' if require_structure else structure != 'BULLISH') and
            (close < vwap if require_vwap else True)
        )
        if not (trend_bullish or trend_bearish):
            return StrategySignal(signal="NEUTRAL", reason="Pas de tendance claire", context={"structure": structure})

        rsi_pullback_long = (rsi_prev < 50 <= rsi) or (rsi_prev < rsi and rsi > 48)
        rsi_pullback_short = (rsi_prev > 50 >= rsi) or (rsi_prev > rsi and rsi < 52)
        macd_turn_long = macd_hist_prev < 0 <= macd_hist
        macd_turn_short = macd_hist_prev > 0 >= macd_hist
        pullback_long = rsi_pullback_long or macd_turn_long
        pullback_short = rsi_pullback_short or macd_turn_short

        atr_expanded = True if np.isnan(atr_pct_sma_20) else atr_pct >= atr_expansion_mult * atr_pct_sma_20
        breakout_high = close > max(recent_highs) + 0.03 * atr
        breakout_low = close < min(recent_lows) - 0.03 * atr
        reject_short = last['high'] > ema_50 and close < ema_50 and close < last['open']
        reject_long = last['low'] < ema_50 and close > ema_50 and close > last['open']
        squeeze_break_long = bb_squeeze and close > bb_upper
        squeeze_break_short = bb_squeeze and close < bb_lower
        vol_confirm = volume_ratio >= vol_spike and atr_expanded

        trigger_long = trend_bullish and pullback_long and vol_confirm and (squeeze_break_long or breakout_high)
        trigger_short = trend_bearish and pullback_short and vol_confirm and (squeeze_break_short or breakout_low or reject_short)

        if trigger_long:
            stop_loss = min(last['low'], close - atr_stop_mult * atr)
            tp1 = close + tp1_mult * atr
            tp2 = close + tp2_mult * atr
            return StrategySignal(
                signal="BUY",
                reason="Tendance haussière + pullback momentum + breakout/squeeze + volume",
                context={"entry": close, "rsi": rsi, "macd_hist": macd_hist, "volume_ratio": volume_ratio, "structure": structure, "trend": "BULLISH"},
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2
            )

        if trigger_short:
            stop_loss = max(last['high'], close + atr_stop_mult * atr)
            tp1 = close - tp1_mult * atr
            tp2 = close - tp2_mult * atr
            return StrategySignal(
                signal="SELL",
                reason="Tendance baissière + pullback momentum + breakout/squeeze + volume",
                context={"entry": close, "rsi": rsi, "macd_hist": macd_hist, "volume_ratio": volume_ratio, "structure": structure, "trend": "BEARISH"},
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2
            )

        return StrategySignal(
            signal="NEUTRAL",
            reason="Conditions partielles mais trigger manquant",
            context={"trend_bullish": trend_bullish, "trend_bearish": trend_bearish, "pullback_long": pullback_long, "pullback_short": pullback_short, "volume_ratio": volume_ratio}
        )