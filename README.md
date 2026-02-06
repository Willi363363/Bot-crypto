# Crypto Trading Bot - BTCUSDT Signals

Un bot de trading automatisé qui analyse le marché **BTCUSDT** et envoie des signaux d'achat/vente via un webhook Discord. Les données de prix sont récupérées en temps réel depuis l'**API Kraken**.

---

## 📌 Description

Ce projet est un bot Python conçu pour surveiller le marché **BTCUSDT** (Bitcoin/USDT) sur Kraken. Il génère des signaux d'achat ou de vente en fonction d'indicateurs techniques ou de règles personnalisées. Les signaux sont envoyés en temps réel via un **webhook Discord**, ce qui permet une intégration facile avec des serveurs Discord pour une notification instantanée.

---

## 🔧 Fonctionnalités

- **Analyse de marché en temps réel** : Récupération des prix depuis l'API Kraken.
- **Indicateurs techniques** : Utilisation d'indicateurs personnalisés pour la prise de décision.
- **Notifications Discord** : Envoi automatique des signaux via un webhook Discord.
- **Gestion d'état** : Suivi de l'état du bot et des positions ouvertes/fermées.
- **Tests automatisés** : Scripts de test pour vérifier la connexion à l'API Kraken et simuler des scénarios.

---

## 📦 Structure du projet

| Fichier | Description |
|---------|-------------|
| `main.py` | Point d'entrée principal du bot. |
| `src/data_fetcher.py` | Récupère les données de marché depuis l'API Kraken. |
| `src/indicators.py` | Contient les indicateurs techniques utilisés pour générer les signaux. |
| `src/notifier.py` | Gère l'envoi des notifications via le webhook Discord. |
| `src/state_manager.py` | Suivi de l'état du bot et des positions. |
| `src/strategy.py` | Logique de stratégie de trading. |
| `config/config.py` | Configuration de base de l'application. |
| `test_connection.py` | Teste la connexion à l'API Kraken. |
| `test_simulation.py` | Simule des scénarios de trading pour valider la logique du bot. |
| `requirements.txt` | Liste des dépendances Python nécessaires. |

---

## ⚙️ Prérequis

- Python 3.8 ou supérieur
- Un compte Discord avec les permissions pour créer un webhook
- Un compte Kraken et une clé API pour récupérer les données de marché

---

## 🛠️ Installation

1. **Cloner le dépôt** :
     ```bash
     git clone https://github.com/votre-utilisateur/crypto-trading-bot.git
     cd crypto-trading-bot
     ```

2. **Installer les dépendances** :
     ```bash
     pip install -r requirements.txt
     ```

3. **Configurer le webhook Discord** :
     - Créez un webhook Discord dans votre serveur (Paramètres du serveur > Intégrations > Webhooks).
     - Copiez l'URL du webhook et ajoutez-la dans le fichier `src/notifier.py` :
         ```python
         WEBHOOK_URL = "votre_url_de_webhook"
         ```

4. **Configurer l'API Kraken** :
     - Créez une clé API sur votre compte Kraken (Paramètres > API).
     - Ajoutez vos clés API dans un fichier `.env` à la racine du projet :
         ```bash
         KRAKEN_API_KEY=votre_cle_api_kraken
         KRAKEN_API_SECRET=votre_secret_api_kraken
         ```

## 🚀 Utilisation

1. **Lancer le bot** :
     ```bash
     python main.py
     ```

2. **Vérifier les logs** :

Le bot affichera les signaux générés dans la console et les enverra également via le webhook Discord.

3. **Exécuter les tests** :

- Pour tester la connexion à l'API Kraken :
    ```bash
    python test_connection.py
    ```

- Pour simuler des scénarios de trading :
    ```bash
    python test_simulation.py
    ```

## 📊 Exemple de signal Discord

Voici un exemple de message envoyé via le webhook Discord :
```text
🔍 Nouveau signal BTCUSDT
📈 Acheter à 50000 USDT
⏰ Heure : 2026-02-06 14:30:00 UTC
📊 Indicateur : RSI > 70 (Surachat)
```

## 📝 Personnalisation

- **Ajouter des indicateurs** : Modifiez le fichier `src/indicators.py` pour ajouter vos propres indicateurs techniques.
- **Changer la stratégie** : Adaptez la logique dans `main.py` pour modifier la stratégie de trading.
- **Personnaliser les notifications** : Modifiez le format des messages dans `src/notifier.py`.

## ⚠️ Avertissements

Ce bot est fourni à titre éducatif. Ne tradez pas avec de l'argent réel sans avoir testé et validé la stratégie.
Les marchés cryptographiques sont volatils. Utilisez ce bot à vos propres risques.

## 🤝 Contributions

Les contributions sont les bienvenues ! Ouvrez une issue ou une pull request pour proposer des améliorations.

## 📜 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
