"""
Test rapide de la nouvelle stratégie
Vérifie que tous les indicateurs sont calculés et qu'un signal est généré
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Forcer le mode test
os.environ['TEST_MODE'] = 'true'

from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators
from src.strategy import ImprovedStrategy
from src.notifier import DiscordNotifier

def test_strategy():
    print("="*70)
    print("🧪 TEST DE LA NOUVELLE STRATÉGIE")
    print("="*70)
    
    # Configuration
    symbol = 'BTC/USDT'
    timeframe = '1h'
    exchange_name = 'kraken'
    
    print(f"\n📊 Récupération des données {symbol} ({timeframe})...")
    
    # Récupération des données
    fetcher = DataFetcher(exchange_name=exchange_name, symbol=symbol)
    df = fetcher.get_ohlcv(timeframe=timeframe, limit=300)
    
    if df is None:
        print("❌ Impossible de récupérer les données")
        return
    
    print(f"✅ {len(df)} bougies récupérées")
    
    # Calcul des indicateurs
    print("\n📈 Calcul des indicateurs...")
    df = TechnicalIndicators.add_all_indicators(df)
    
    # Vérifier que tous les nouveaux indicateurs sont présents
    required_indicators = [
        'ema_20', 'ema_50', 'ema_200',
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'vwap', 'structure', 'atr', 'atr_ma',
        'volume_sma_20', 'bb_squeeze', 'bb_upper', 'bb_lower',
        'ema_gap', 'volume_ratio', 'atr_pct'
    ]
    
    missing = []
    for ind in required_indicators:
        if ind not in df.columns:
            missing.append(ind)
    
    if missing:
        print(f"❌ Indicateurs manquants : {missing}")
        return
    else:
        print(f"✅ Tous les indicateurs calculés ({len(required_indicators)} indicateurs)")
    
    # Afficher les dernières valeurs
    last = df.iloc[-2]  # Dernière bougie clôturée
    
    print(f"\n📊 Dernière analyse :")
    print(f"   Prix         : ${last['close']:,.2f}")
    print(f"   EMA 20/50/200: {last['ema_20']:,.0f} / {last['ema_50']:,.0f} / {last['ema_200']:,.0f}")
    print(f"   RSI          : {last['rsi']:.2f}")
    print(f"   MACD Hist    : {last['macd_hist']:.4f}")
    print(f"   VWAP         : ${last['vwap']:,.2f}")
    print(f"   Structure    : {last['structure']}")
    print(f"   ATR          : ${last['atr']:,.2f}")
    print(f"   Volume ratio : {last['volume_ratio']:.2f}x")
    print(f"   CHOP         : {last['chop']:.2f}")
    print(f"   BB Squeeze   : {'Oui' if last['bb_squeeze'] else 'Non'}")
    
    # Générer un signal
    print(f"\n🎯 Génération du signal...")
    signal = ImprovedStrategy.generate_signal(df)
    
    print(f"\n{'='*70}")
    print(f"SIGNAL : {signal.signal}")
    print(f"RAISON : {signal.reason}")
    print(f"{'='*70}")
    
    if signal.signal != 'NEUTRAL':
        print(f"\n💰 Détails du trade :")
        print(f"   Entry      : ${signal.context.get('entry', 0):,.2f}")
        if signal.stop_loss:
            print(f"   Stop Loss  : ${signal.stop_loss:,.2f}")
            print(f"   Take Profit 1 : ${signal.take_profit_1:,.2f}")
            print(f"   Take Profit 2 : ${signal.take_profit_2:,.2f}")
            
            risk = abs(signal.context.get('entry', 0) - signal.stop_loss)
            reward1 = abs(signal.take_profit_1 - signal.context.get('entry', 0))
            reward2 = abs(signal.take_profit_2 - signal.context.get('entry', 0))
            
            print(f"\n   Risk/Reward 1 : 1:{reward1/risk:.2f}")
            print(f"   Risk/Reward 2 : 1:{reward2/risk:.2f}")
    
    print(f"\n📋 Contexte :")
    for key, value in signal.context.items():
        if isinstance(value, float):
            print(f"   {key:15} : {value:.4f}")
        else:
            print(f"   {key:15} : {value}")
    
    # Test notification Discord
    print(f"\n📤 Test d'envoi Discord...")
    notifier = DiscordNotifier()
    
    if signal.signal == 'BUY':
        notifier.send_message(
            title="🧪 TEST - Signal BUY détecté",
            description=signal.reason,
            color=0x00ff00,
            fields=[
                {"name": "Prix", "value": f"${signal.context.get('entry', 0):,.2f}", "inline": True},
                {"name": "Stop Loss", "value": f"${signal.stop_loss:,.2f}" if signal.stop_loss else "N/A", "inline": True},
                {"name": "TP1", "value": f"${signal.take_profit_1:,.2f}" if signal.take_profit_1 else "N/A", "inline": True},
            ]
        )
    elif signal.signal == 'SELL':
        notifier.send_message(
            title="🧪 TEST - Signal SELL détecté",
            description=signal.reason,
            color=0xff0000,
            fields=[
                {"name": "Prix", "value": f"${signal.context.get('entry', 0):,.2f}", "inline": True},
                {"name": "Stop Loss", "value": f"${signal.stop_loss:,.2f}" if signal.stop_loss else "N/A", "inline": True},
                {"name": "TP1", "value": f"${signal.take_profit_1:,.2f}" if signal.take_profit_1 else "N/A", "inline": True},
            ]
        )
    else:
        notifier.send_message(
            title="🧪 TEST - Marché neutre",
            description=signal.reason,
            color=0x808080
        )
    
    print(f"\n✅ Test terminé ! Vérifie ton Discord.")
    print(f"\n{'='*70}")

if __name__ == "__main__":
    test_strategy()