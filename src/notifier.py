"""
Gestionnaire de notifications Discord
"""
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DiscordNotifier:
    def __init__(self, webhook_url=None, heartbeat_webhook_url=None):
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.heartbeat_webhook_url = heartbeat_webhook_url or os.getenv('DISCORD_HEARTBEAT_WEBHOOK_URL')

    def send_heartbeat(self, title, description, color=0x808080, fields=None):
        """Envoie un heartbeat sur le canal dédié"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Trading Bot 💓"}
        }

        if fields:
            embed["fields"] = fields

        data = {"embeds": [embed]}

        try:
            response = requests.post(self.heartbeat_webhook_url, json=data)
            if response.status_code == 204:
                print("✅ Heartbeat envoyé")
                return True
        except Exception as e:
            print(f"❌ Erreur heartbeat: {e}")
            return False

    def send_message(self, title, description, color=0x00ff00, fields=None):
        """
        Envoie un message embed sur Discord

        color: 0x00ff00 (vert), 0xff0000 (rouge), 0xffaa00 (orange)
        """
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Trading Bot 🤖"
            }
        }

        if fields:
            embed["fields"] = fields

        data = {
            "embeds": [embed]
        }

        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code == 204:
                print("✅ Message Discord envoyé")
                return True
            else:
                print(f"❌ Erreur Discord: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erreur envoi Discord: {e}")
            return False

    def send_buy_signal(self, symbol, price, indicators):
        """Signal d'achat"""
        fields = [
            {"name": "💰 Prix", "value": f"${price:,.2f}", "inline": True},
            {"name": "📊 RSI", "value": f"{indicators.get('rsi', 'N/A')}", "inline": True},
            {"name": "📈 Tendance", "value": indicators.get('trend', 'N/A'), "inline": True}
        ]

        self.send_message(
            title=f"🟢 SIGNAL ACHAT - {symbol}",
            description="Conditions d'achat remplies !",
            color=0x00ff00,
            fields=fields
        )

    def send_sell_signal(self, symbol, price, indicators):
        """Signal de vente"""
        fields = [
            {"name": "💰 Prix", "value": f"${price:,.2f}", "inline": True},
            {"name": "📊 RSI", "value": f"{indicators.get('rsi', 'N/A')}", "inline": True},
            {"name": "📉 Tendance", "value": indicators.get('trend', 'N/A'), "inline": True}
        ]

        self.send_message(
            title=f"🔴 SIGNAL VENTE - {symbol}",
            description="Conditions de vente remplies !",
            color=0xff0000,
            fields=fields
        )

# Test
if __name__ == "__main__":
    # Pour tester, crée un webhook Discord :
    # Discord → Paramètres serveur → Intégrations → Webhooks → Nouveau

    notifier = DiscordNotifier()

    # Test message simple
    notifier.send_message(
        title="🤖 Bot Trading Démarré",
        description="Test de connexion réussi !",
        color=0x00ff00
    )

    # Test signal d'achat
    notifier.send_buy_signal(
        symbol="BTC/USDT",
        price=45250.50,
        indicators={
            "rsi": 45.2,
            "trend": "Haussière"
        }
    )