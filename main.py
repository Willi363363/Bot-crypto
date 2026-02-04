"""
Bot de Trading - Avec gestion d'état
"""
from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators
from src.notifier import DiscordNotifier
from src.state_manager import StateManager
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

def analyze_market():
    """Analyse le marché et envoie des signaux (uniquement si changement)"""

    # Configuration
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    timeframe = os.getenv('TIMEFRAME', '1h')

    print(f"\n{'='*60}")
    print(f"🤖 Analyse - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Paire: {symbol} | Timeframe: {timeframe}")
    print(f"{'='*60}\n")

    # Initialisation
    fetcher = DataFetcher(symbol=symbol)
    state_manager = StateManager()

    # Récupération des données
    df = fetcher.get_ohlcv(timeframe=timeframe, limit=200)

    if df is None:
        print("❌ Impossible de récupérer les données")
        return

    # Calcul des indicateurs
    df = TechnicalIndicators.add_all_indicators(df)

    # Dernières valeurs
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Affichage de l'analyse
    print(f"📈 Situation actuelle :")
    print(f"   Prix      : ${last['close']:,.2f}")
    print(f"   EMA 20    : ${last['ema_20']:,.2f}")
    print(f"   EMA 50    : ${last['ema_50']:,.2f}")
    print(f"   EMA 200   : ${last['ema_200']:,.2f}")
    print(f"   RSI       : {last['rsi']:.2f}")
    print(f"   Tendance  : {last['trend']}")
    print(f"   Volume    : {last['volume']:,.2f}")

    # Affichage du dernier signal
    last_signal = state_manager.get_last_signal()
    print(f"\n🔔 Dernier signal envoyé : {last_signal if last_signal else 'Aucun'}")

    # Détermination du signal actuel
    current_signal = None

    # Logique ACHAT : Tendance haussière + RSI < 70 + Crossover EMA
    if (last['trend'] == 'BULLISH' and 
        last['rsi'] < 70 and 
        last['rsi'] > 30 and  # Pas en survente non plus
        prev['ema_20'] <= prev['ema_50'] and last['ema_20'] > last['ema_50']):
        current_signal = 'BUY'

    # Logique VENTE : Tendance baissière OU RSI surachat OU Crossover baissier
    elif (last['trend'] == 'BEARISH' or
          last['rsi'] > 75 or
          (prev['ema_20'] >= prev['ema_50'] and last['ema_20'] < last['ema_50'])):
        current_signal = 'SELL'

    else:
        current_signal = 'NEUTRAL'

    print(f"🎯 Signal détecté : {current_signal}")

    # Vérification si on doit envoyer le signal
    if current_signal != 'NEUTRAL':
        if state_manager.should_send_signal(current_signal):
            # ENVOI DU SIGNAL
            notifier = DiscordNotifier()

            if current_signal == 'BUY':
                print("\n🟢 ENVOI SIGNAL D'ACHAT")
                notifier.send_buy_signal(
                    symbol=symbol,
                    price=last['close'],
                    indicators={
                        'rsi': f"{last['rsi']:.2f}",
                        'trend': last['trend'],
                        'ema_20': f"${last['ema_20']:,.2f}",
                        'ema_50': f"${last['ema_50']:,.2f}"
                    }
                )
            elif current_signal == 'SELL':
                print("\n🔴 ENVOI SIGNAL DE VENTE")
                notifier.send_sell_signal(
                    symbol=symbol,
                    price=last['close'],
                    indicators={
                        'rsi': f"{last['rsi']:.2f}",
                        'trend': last['trend'],
                        'ema_20': f"${last['ema_20']:,.2f}",
                        'ema_50': f"${last['ema_50']:,.2f}"
                    }
                )

            # Mise à jour de l'état
            state_manager.update_signal(current_signal, last['close'])
        else:
            print(f"\n⚪ Signal {current_signal} déjà envoyé - Pas de nouveau message")
    else:
        print("\n⚪ Marché neutre - Aucun signal")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    analyze_market()