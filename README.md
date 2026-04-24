# MY-BOT

## App mobile-ready (Google Play via PWA/TWA)

Oui: l'app est connectée à Internet et récupère les prix/fluctuations directement depuis Hyperliquid.
Elle calcule ensuite seule les signaux BUY/SELL/WAIT.

### Comment elle récupère le prix en "temps réel" ?

- Le backend Flask interroge `https://api.hyperliquid.xyz/info` (endpoint candles).
- Le front appelle `/api/signals` toutes les ~30 secondes.
- À chaque refresh: nouveaux prix -> nouveaux indicateurs -> nouveau signal.

> C'est du **near real-time par polling** (pas tick-by-tick websocket).

---

## Fonctionnalités ajoutées

- Signaux BTC/ETH avec entrée, SL, TP et taille de position.
- Score de signal (`0..100`) pour prioriser les setups.
- Modes:
  - `conservative`
  - `aggressive`
- Quiet hours UTC (ex: `23-06`) pour couper les notifications.
- Historique local des signaux (CSV).
- Export CSV depuis l'interface.
- Notifications navigateur + Telegram (optionnel).
- App installable sur téléphone (PWA) puis publiable Google Play via TWA.

---

## Installation

```bash
pip install -r requirements.txt
```

## Variables d'environnement

```bash
export APP_INTERVAL=5m
export APP_CAPITAL=50
export APP_RISK_PER_TRADE=0.01
export APP_MODE=conservative
export APP_QUIET_HOURS_UTC=23-06
export APP_NOTIF_COOLDOWN_SEC=600
export APP_HISTORY_CSV=signals_history.csv
export TELEGRAM_BOT_TOKEN=
export TELEGRAM_CHAT_ID=
export PORT=8081
```

## Lancer

```bash
python signal_app.py
```

Puis ouvrir:

```text
http://localhost:8081
```

---

## Notifications mobile

### Option A — app web installée
- Ouvre l'app depuis Chrome Android
- Clique "Installer sur mobile" ou "Ajouter à l'écran d'accueil"
- Active les notifications

### Option B — Telegram (recommandé)
- Crée un bot via @BotFather
- Mets `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`
- Tu reçois les alertes BUY/SELL même hors navigateur

---

## Google Play (TWA)

1. Déployer l'app en HTTPS
2. Vérifier la PWA installable (manifest + service worker)
3. Emballer en app Android via Bubblewrap (Trusted Web Activity)
4. Publier sur Google Play Console

---

## Stratégie actuelle

- EMA 21/55 (tendance)
- RSI 14 (filtre)
- ATR 14 (SL/TP)
- sizing selon `capital * risk%`

⚠️ Aucune stratégie ne garantit des gains.
