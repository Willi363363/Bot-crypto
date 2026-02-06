"""
Stratégie de trading 1h basée sur EMA, RSI, CHOP et supports/résistances.
Paramètres ajustables via variables d'environnement.
"""
from dataclasses import dataclass
import os


@dataclass
class StrategySignal:
	signal: str
	reason: str
	context: dict


class Strategy:
	@staticmethod
	def generate_signal(df):
		"""
		Génère un signal BUY / SELL / NEUTRAL à partir des données et indicateurs.
		"""
		if df is None or len(df) < 260:
			return StrategySignal(
				signal="NEUTRAL",
				reason="Pas assez de données pour la stratégie 1h",
				context={}
			)

		last = df.iloc[-2]
		prev = df.iloc[-3]

		ema_20 = last.get('ema_20')
		ema_50 = last.get('ema_50')
		ema_200 = last.get('ema_200')
		ema_200_slope = last.get('ema_200_slope')
		ema_50_slope = last.get('ema_50_slope')
		ema_200_slope_10 = last.get('ema_200_slope_10')
		ema_50_slope_10 = last.get('ema_50_slope_10')
		rsi = last.get('rsi')
		rsi_delta = last.get('rsi_delta')
		chop = last.get('chop')
		atr = last.get('atr')
		support = last.get('support')
		resistance = last.get('resistance')
		price = last.get('close')
		volume = last.get('volume')
		volume_sma_20 = last.get('volume_sma_20')
        
		prev_close = prev.get('close')

		trend_bull = ema_20 > ema_50 > ema_200
		trend_bear = ema_20 < ema_50 < ema_200

		has_resistance = resistance == resistance
		has_support = support == support

		volume_ok = volume_sma_20 is not None and volume is not None and volume > volume_sma_20

		tolerance = 0.005  # 0.5% autour des niveaux
		near_support = has_support and abs(price - support) / price <= tolerance
		near_resistance = has_resistance and abs(price - resistance) / price <= tolerance

		chop_trend_max = float(os.getenv('CHOP_TREND_MAX', '60'))
		chop_range_min = float(os.getenv('CHOP_RANGE_MIN', '65'))
		ema_gap_min = float(os.getenv('EMA_GAP_MIN', '0.0008'))
		atr_pct_min = float(os.getenv('ATR_PCT_MIN', '0.0015'))
		rsi_pullback_long_min = float(os.getenv('RSI_PULLBACK_LONG_MIN', '48'))
		rsi_pullback_short_max = float(os.getenv('RSI_PULLBACK_SHORT_MAX', '52'))
		use_range = os.getenv('USE_RANGE', 'false').lower() == 'true'

		trending_market = chop is not None and chop < chop_trend_max
		ranging_market = chop is not None and chop > chop_range_min
		no_trade_zone = chop is not None and chop_trend_max <= chop <= chop_range_min

		atr_pct = (atr / price) if atr is not None and price else None
		volatility_ok = atr_pct is not None and atr_pct >= atr_pct_min

		ema_gap = abs(ema_20 - ema_50) / price if price else None
		trend_strength = ema_gap is not None and ema_gap > ema_gap_min

		prev_rsi = prev.get('rsi')
		rsi_cross_up = prev_rsi is not None and rsi is not None and prev_rsi <= 50 and rsi > 50
		rsi_cross_down = prev_rsi is not None and rsi is not None and prev_rsi >= 50 and rsi < 50

		trend_long_ok = (
			trend_bull and
			price > ema_200 and
			ema_200_slope is not None and ema_200_slope > 0 and
			ema_200_slope_10 is not None and ema_200_slope_10 > 0 and
			trend_strength and
			trending_market and
			volatility_ok
		)

		trend_short_ok = (
			trend_bear and
			price < ema_200 and
			ema_200_slope is not None and ema_200_slope < 0 and
			ema_200_slope_10 is not None and ema_200_slope_10 < 0 and
			trend_strength and
			trending_market and
			volatility_ok
		)

		pullback_long = trend_bull and price >= ema_20 and rsi is not None and rsi >= rsi_pullback_long_min and rsi_delta is not None and rsi_delta > 0
		pullback_short = trend_bear and price <= ema_20 and rsi is not None and rsi <= rsi_pullback_short_max and rsi_delta is not None and rsi_delta < 0

		# Zone neutre => pas de trade
		if no_trade_zone:
			return StrategySignal(
				signal="NEUTRAL",
				reason="Marché indécis (CHOP moyen)",
				context={
					"price": price,
					"rsi": rsi,
					"chop": chop,
					"ema_20": ema_20,
					"ema_50": ema_50,
					"ema_200": ema_200,
					"ema_200_slope": ema_200_slope,
					"ema_50_slope": ema_50_slope,
					"support": support,
					"resistance": resistance,
					"trend": "BULLISH" if trend_bull else "BEARISH" if trend_bear else "NEUTRAL"
				}
			)

		# Trend-following (cross ou pullback)
		if trend_long_ok and (rsi_cross_up or pullback_long) and price > ema_20 and volume_ok:
			return StrategySignal(
				signal="BUY",
				reason="Tendance haussière + RSI (cross/pullback) + volume",
				context={
					"price": price,
					"rsi": rsi,
					"chop": chop,
					"ema_20": ema_20,
					"ema_50": ema_50,
					"ema_200": ema_200,
					"ema_200_slope": ema_200_slope,
					"ema_50_slope": ema_50_slope,
					"support": support,
					"resistance": resistance,
					"trend": "BULLISH"
				}
			)

		if trend_short_ok and (rsi_cross_down or pullback_short) and price < ema_20 and volume_ok:
			return StrategySignal(
				signal="SELL",
				reason="Tendance baissière + RSI (cross/pullback) + volume",
				context={
					"price": price,
					"rsi": rsi,
					"chop": chop,
					"ema_20": ema_20,
					"ema_50": ema_50,
					"ema_200": ema_200,
					"ema_200_slope": ema_200_slope,
					"ema_50_slope": ema_50_slope,
					"support": support,
					"resistance": resistance,
					"trend": "BEARISH"
				}
			)

		# Mean-reversion en range (optionnel)
		if use_range and ranging_market and volatility_ok and near_support and rsi is not None and rsi < 40 and rsi_delta is not None and rsi_delta > 0:
			return StrategySignal(
				signal="BUY",
				reason="Range: rebond support + RSI bas",
				context={
					"price": price,
					"rsi": rsi,
					"chop": chop,
					"support": support,
					"resistance": resistance,
					"trend": "RANGE"
				}
			)

		if use_range and ranging_market and volatility_ok and near_resistance and rsi is not None and rsi > 60 and rsi_delta is not None and rsi_delta < 0:
			return StrategySignal(
				signal="SELL",
				reason="Range: rejet résistance + RSI haut",
				context={
					"price": price,
					"rsi": rsi,
					"chop": chop,
					"support": support,
					"resistance": resistance,
					"trend": "RANGE"
				}
			)

		return StrategySignal(
			signal="NEUTRAL",
			reason="Aucun setup valide",
			context={
				"price": price,
				"rsi": rsi,
				"chop": chop,
				"ema_20": ema_20,
				"ema_50": ema_50,
				"ema_200": ema_200,
				"ema_200_slope": ema_200_slope,
				"ema_50_slope": ema_50_slope,
				"support": support,
				"resistance": resistance,
				"trend": "BULLISH" if trend_bull else "BEARISH" if trend_bear else "NEUTRAL"
			}
		)
