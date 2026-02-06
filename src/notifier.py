"""
Gestionnaire de notifications Discord
"""
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DiscordNotifier:
    def __init__(self, webhook_url=None, heartbeat_webhook_url=None, test_mode=None):
        # Détection du mode test
        if test_mode is None:
            test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
        self.test_mode = test_mode
        
        # En mode test, utiliser le webhook de test pour TOUT
        if self.test_mode:
            test_webhook = os.getenv('DISCORD_TEST_WEBHOOK_URL')
            if test_webhook:
                print("🧪 MODE TEST ACTIVÉ - Tous les messages vont sur le webhook de test")
                self.webhook_url = test_webhook
                self.heartbeat_webhook_url = test_webhook
            else:
                print("⚠️ ATTENTION: TEST_MODE=true mais DISCORD_TEST_WEBHOOK_URL non défini!")
                self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
                self.heartbeat_webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        else:
            # Mode production normal
            self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
            if heartbeat_webhook_url:
                self.heartbeat_webhook_url = heartbeat_webhook_url
            else:
                env_heartbeat = os.getenv('DISCORD_HEARTBEAT_WEBHOOK_URL')
                if env_heartbeat and env_heartbeat.strip():
                    self.heartbeat_webhook_url = env_heartbeat
                else:
                    self.heartbeat_webhook_url = self.webhook_url

        # Debug
        mode_label = "🧪 TEST" if self.test_mode else "🚀 PRODUCTION"
        print(f"\n{mode_label}")
        print(f"🔗 Webhook signaux  : {self.webhook_url[:50] if self.webhook_url else '❌ Non défini'}...")
        print(f"🔗 Webhook heartbeat: {self.heartbeat_webhook_url[:50] if self.heartbeat_webhook_url else '❌ Non défini'}...")
        if self.webhook_url == self.heartbeat_webhook_url:
            print(f"⚠️  Même webhook utilisé pour signaux et heartbeat")
        print()

    def send_heartbeat(self, title, description, color=0x808080, fields=None):
        """Envoie un heartbeat sur le canal dédié"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Trading Bot 💓" + (" [TEST]" if self.test_mode else "")}
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
                "text": "Trading Bot 🤖" + (" [TEST]" if self.test_mode else "")
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

        extra_fields = [
            ("EMA 20", indicators.get('ema_20')),
            ("EMA 50", indicators.get('ema_50')),
            ("EMA 200", indicators.get('ema_200')),
            ("CHOP", indicators.get('chop')),
            ("Support", indicators.get('support')),
            ("Résistance", indicators.get('resistance'))
        ]

        for name, value in extra_fields:
            if value not in (None, "N/A"):
                fields.append({"name": name, "value": f"{value}", "inline": True})

        self.send_message(
            title=f"🟢 SIGNAL ACHAT - {symbol}" + (" [TEST]" if self.test_mode else ""),
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

        extra_fields = [
            ("EMA 20", indicators.get('ema_20')),
            ("EMA 50", indicators.get('ema_50')),
            ("EMA 200", indicators.get('ema_200')),
            ("CHOP", indicators.get('chop')),
            ("Support", indicators.get('support')),
            ("Résistance", indicators.get('resistance'))
        ]

        for name, value in extra_fields:
            if value not in (None, "N/A"):
                fields.append({"name": name, "value": f"{value}", "inline": True})

        self.send_message(
            title=f"🔴 SIGNAL VENTE - {symbol}" + (" [TEST]" if self.test_mode else ""),
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