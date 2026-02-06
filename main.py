"""
Bot de Trading - Avec heartbeat corrigé
"""
from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators
from src.notifier import DiscordNotifier
from src.state_manager import StateManager
from src.strategy import Strategy
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

def analyze_market():
    """Analyse le marché et envoie des signaux (uniquement si changement)"""

    # Configuration
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    timeframe = os.getenv('TIMEFRAME', '1h')
    exchange_name = os.getenv('EXCHANGE', 'kraken')
    send_heartbeat = os.getenv('SEND_HEARTBEAT', 'false').lower() == 'true'
    data_limit = int(os.getenv('DATA_LIMIT', '500'))

    print(f"\n{'='*60}")
    print(f"🤖 BOT ACTIF - Analyse en cours...")
    print(f"🕐 Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Exchange: {exchange_name}")
    print(f"📊 Paire: {symbol}")
    print(f"📊 Timeframe: {timeframe}")
    print(f"{'='*60}\n")

    # Initialisation
    fetcher = DataFetcher(exchange_name=exchange_name, symbol=symbol)
    state_manager = StateManager()
    notifier = DiscordNotifier()

    # Récupération des données
    df = fetcher.get_ohlcv(timeframe=timeframe, limit=max(260, data_limit))

    if df is None:
        print("❌ Impossible de récupérer les données")
        if send_heartbeat:
            notifier.send_message(
                title="❌ Erreur Bot Trading",
                description="Impossible de récupérer les données du marché",
                color=0xff0000
            )
        return

    # Calcul des indicateurs
    df = TechnicalIndicators.add_all_indicators(df)

    # Dernière bougie clôturée (évite la bougie en cours)
    last = df.iloc[-2]

    # Affichage de l'analyse
    print(f"📈 Situation actuelle :")
    print(f"   Prix      : ${last['close']:,.2f}")
    print(f"   EMA 20    : ${last['ema_20']:,.2f}")
    print(f"   EMA 50    : ${last['ema_50']:,.2f}")
    print(f"   EMA 200   : ${last['ema_200']:,.2f}")
    print(f"   RSI       : {last['rsi']:.2f}")
    print(f"   CHOP      : {last['chop']:.2f}")
    print(f"   Support   : {last['support']:.2f}" if last['support'] == last['support'] else "   Support   : N/A")
    print(f"   Résistance: {last['resistance']:.2f}" if last['resistance'] == last['resistance'] else "   Résistance: N/A")
    print(f"   Tendance  : {last['trend']}")
    print(f"   Volume    : {last['volume']:,.2f}")

    # Affichage du dernier signal
    last_signal = state_manager.get_last_signal()
    print(f"\n🔔 Dernier signal envoyé : {last_signal if last_signal else 'Aucun'}")

    # Détermination du signal actuel via la stratégie 1h
    strategy_signal = Strategy.generate_signal(df)
    current_signal = strategy_signal.signal

    print(f"🎯 Signal détecté : {current_signal}")
    print(f"🧠 Raison         : {strategy_signal.reason}")

    # ═══════════════════════════════════════════════════════════
    # INITIALISATION DES VARIABLES (IMPORTANT !)
    # ═══════════════════════════════════════════════════════════
    signal_sent = False
    status = "⚪ Marché neutre - En surveillance"
    heartbeat_color = 0x808080  # Gris par défaut

    # Vérification si on doit envoyer le signal
    if current_signal != 'NEUTRAL':
        if state_manager.should_send_signal(current_signal):
            # NOUVEAU SIGNAL À ENVOYER
            if current_signal == 'BUY':
                print("\n🟢 ENVOI SIGNAL D'ACHAT")
                notifier.send_buy_signal(
                    symbol=symbol,
                    price=last['close'],
                    indicators={
                        'rsi': f"{last['rsi']:.2f}",
                        'trend': strategy_signal.context.get('trend', last['trend']),
                        'ema_20': f"${last['ema_20']:,.2f}",
                        'ema_50': f"${last['ema_50']:,.2f}",
                        'ema_200': f"${last['ema_200']:,.2f}",
                        'chop': f"{last['chop']:.2f}",
                        'support': f"${last['support']:,.2f}" if last['support'] == last['support'] else "N/A",
                        'resistance': f"${last['resistance']:,.2f}" if last['resistance'] == last['resistance'] else "N/A"
                    }
                )
                status = "🟢 Nouveau signal BUY envoyé"
                heartbeat_color = 0x00ff00

            elif current_signal == 'SELL':
                print("\n🔴 ENVOI SIGNAL DE VENTE")
                notifier.send_sell_signal(
                    symbol=symbol,
                    price=last['close'],
                    indicators={
                        'rsi': f"{last['rsi']:.2f}",
                        'trend': strategy_signal.context.get('trend', last['trend']),
                        'ema_20': f"${last['ema_20']:,.2f}",
                        'ema_50': f"${last['ema_50']:,.2f}",
                        'ema_200': f"${last['ema_200']:,.2f}",
                        'chop': f"{last['chop']:.2f}",
                        'support': f"${last['support']:,.2f}" if last['support'] == last['support'] else "N/A",
                        'resistance': f"${last['resistance']:,.2f}" if last['resistance'] == last['resistance'] else "N/A"
                    }
                )
                status = "🔴 Nouveau signal SELL envoyé"
                heartbeat_color = 0xff0000

            state_manager.update_signal(current_signal, last['close'])
            signal_sent = True

        else:
            # SIGNAL DÉJÀ ACTIF
            print(f"\n⚪ Signal {current_signal} déjà envoyé - Pas de nouveau message")

            if current_signal == 'BUY':
                status = "🟢 Signal BUY actif (déjà envoyé)"
                heartbeat_color = 0x90EE90  # Vert clair
            elif current_signal == 'SELL':
                status = "🔴 Signal SELL actif (déjà envoyé)"
                heartbeat_color = 0xFFB6C1  # Rouge clair

    # ═══════════════════════════════════════════════════════════
    # HEARTBEAT : Notification de santé du bot
    # ═══════════════════════════════════════════════════════════
    if send_heartbeat and not signal_sent:
        # Détermination de l'emoji selon la tendance
        if last['trend'] == 'BULLISH':
            trend_emoji = "📈"  # Graphique qui monte
            trend_display = f"{trend_emoji} BULLISH"
        elif last['trend'] == 'BEARISH':
            trend_emoji = "📉"  # Graphique qui descend
            trend_display = f"{trend_emoji} BEARISH"
        else:
            trend_emoji = "➡️"  # Flèche horizontale pour neutre
            trend_display = f"{trend_emoji} NEUTRAL"

        import time
        current_timestamp = int(time.time())
        discord_time = f"<t:{current_timestamp}:T>"

        notifier.send_heartbeat(
            title=f"💓 Bot actif - {symbol}",
            description=status,
            color=heartbeat_color,
            fields=[
                {"name": "💰 Prix", "value": f"${last['close']:,.2f}", "inline": True},
                {"name": "📊 RSI", "value": f"{last['rsi']:.2f}", "inline": True},
                {"name": "🧭 CHOP", "value": f"{last['chop']:.2f}", "inline": True},
                {"name": "Tendance", "value": trend_display, "inline": True},
                {"name": "Support", "value": f"${last['support']:,.2f}" if last['support'] == last['support'] else "N/A", "inline": True},
                {"name": "Résistance", "value": f"${last['resistance']:,.2f}" if last['resistance'] == last['resistance'] else "N/A", "inline": True},
                {"name": "🕐 Heure", "value": discord_time, "inline": False}
            ]
        )

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    analyze_market()