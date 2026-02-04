"""
Gestionnaire d'état pour éviter les signaux dupliqués
"""
import json
import os
from datetime import datetime

class StateManager:
    def __init__(self, state_file='state.json'):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        """Charge l'état précédent"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                return self._get_default_state()
        return self._get_default_state()

    def _get_default_state(self):
        """État par défaut"""
        return {
            'last_signal': None,  # 'BUY', 'SELL', ou None
            'last_signal_time': None,
            'last_price': None
        }

    def save_state(self):
        """Sauvegarde l'état"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def should_send_signal(self, new_signal):
        """
        Détermine si on doit envoyer le signal
        Retourne True seulement si le signal a CHANGÉ
        """
        last_signal = self.state.get('last_signal')

        # Cas 1 : Premier signal
        if last_signal is None:
            return True

        # Cas 2 : Le signal a changé (BUY → SELL ou inversement)
        if last_signal != new_signal:
            return True

        # Cas 3 : Même signal = on ne renvoie pas
        return False

    def update_signal(self, signal, price):
        """Met à jour l'état après envoi d'un signal"""
        self.state['last_signal'] = signal
        self.state['last_signal_time'] = datetime.now().isoformat()
        self.state['last_price'] = price
        self.save_state()

    def get_last_signal(self):
        """Récupère le dernier signal envoyé"""
        return self.state.get('last_signal')