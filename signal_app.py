import csv
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import List

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template

INFO_URL = "https://api.hyperliquid.xyz/info"


@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float


def ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return [50.0] * len(values)

    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0.0))
        losses.append(abs(min(d, 0.0)))

    out = [50.0] * len(values)
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    out[period] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

    return out


def atr(candles: List[Candle], period: int = 14) -> List[float]:
    if not candles:
        return []
    tr = [candles[0].high - candles[0].low]
    for i in range(1, len(candles)):
        h_l = candles[i].high - candles[i].low
        h_pc = abs(candles[i].high - candles[i - 1].close)
        l_pc = abs(candles[i].low - candles[i - 1].close)
        tr.append(max(h_l, h_pc, l_pc))
    return ema(tr, period)


class HyperliquidDataClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def get_candles(self, coin: str, interval: str, lookback_minutes: int = 900) -> List[Candle]:
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - lookback_minutes * 60_000
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_ms,
                "endTime": now_ms,
            },
        }
        r = requests.post(INFO_URL, json=payload, timeout=self.timeout)
        r.raise_for_status()

        candles: List[Candle] = []
        for c in r.json():
            candles.append(
                Candle(
                    ts=int(c.get("t") or c.get("T") or c.get("time") or 0),
                    open=float(c.get("o") or c.get("open")),
                    high=float(c.get("h") or c.get("high")),
                    low=float(c.get("l") or c.get("low")),
                    close=float(c.get("c") or c.get("close")),
                )
            )
        candles.sort(key=lambda x: x.ts)
        return candles


class SignalEngine:
    def __init__(self, risk_pct: float, mode: str = "conservative"):
        self.risk_pct = risk_pct
        self.mode = mode

    def _params(self) -> dict:
        if self.mode == "aggressive":
            return {
                "rsi_long": (45, 66),
                "rsi_short": (34, 55),
                "sl_atr": 1.4,
                "tp_atr": 2.0,
            }
        return {
            "rsi_long": (50, 60),
            "rsi_short": (40, 50),
            "sl_atr": 1.1,
            "tp_atr": 1.8,
        }

    def compute_signal(self, candles: List[Candle], capital: float) -> dict:
        if len(candles) < 120:
            return {"action": "WAIT", "reason": "Pas assez de données.", "score": 0}

        p = self._params()
        closes = [c.close for c in candles]
        ef = ema(closes, 21)
        es = ema(closes, 55)
        rr = rsi(closes, 14)
        aa = atr(candles, 14)
        last = candles[-1]

        action = "WAIT"
        reason = "Aucun setup clair"
        entry = last.close
        stop = None
        tp = None

        if ef[-1] > es[-1] and p["rsi_long"][0] <= rr[-1] <= p["rsi_long"][1]:
            action = "BUY"
            reason = f"Trend up + RSI ({self.mode})"
            stop = entry - p["sl_atr"] * aa[-1]
            tp = entry + p["tp_atr"] * aa[-1]
        elif ef[-1] < es[-1] and p["rsi_short"][0] <= rr[-1] <= p["rsi_short"][1]:
            action = "SELL"
            reason = f"Trend down + RSI ({self.mode})"
            stop = entry + p["sl_atr"] * aa[-1]
            tp = entry - p["tp_atr"] * aa[-1]

        risk_usd = capital * self.risk_pct
        size_coin = 0.0
        if action in {"BUY", "SELL"} and stop is not None:
            per_coin_risk = abs(entry - stop)
            if per_coin_risk > 0:
                size_coin = risk_usd / per_coin_risk

        ema_gap_pct = abs(ef[-1] - es[-1]) / entry * 100 if entry > 0 else 0
        trend_score = min(40, ema_gap_pct * 800)
        rsi_center = 55 if action == "BUY" else (45 if action == "SELL" else 50)
        rsi_score = max(0, 35 - abs(rr[-1] - rsi_center) * 2)
        action_bonus = 25 if action in {"BUY", "SELL"} else 0
        score = int(max(0, min(100, trend_score + rsi_score + action_bonus)))

        return {
            "action": action,
            "reason": reason,
            "entry": round(entry, 2),
            "stop_loss": round(stop, 2) if stop is not None else None,
            "take_profit": round(tp, 2) if tp is not None else None,
            "qty_coin": round(size_coin, 6),
            "risk_usd": round(risk_usd, 2),
            "rsi": round(rr[-1], 2),
            "score": score,
            "last_ts": last.ts,
        }


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, message: str) -> None:
        if not self.token or not self.chat_id:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        requests.post(url, json={"chat_id": self.chat_id, "text": message}, timeout=10)


class SignalRecorder:
    def __init__(self, path: str):
        self.path = path
        self.lock = Lock()
        self.headers = [
            "created_at_utc",
            "coin",
            "action",
            "score",
            "entry",
            "stop_loss",
            "take_profit",
            "qty_coin",
            "risk_usd",
            "interval",
            "mode",
            "reason",
        ]
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.headers)

    def append(self, row: dict) -> None:
        with self.lock:
            with open(self.path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writerow(row)

    def tail(self, limit: int = 80) -> list[dict]:
        with self.lock:
            with open(self.path, "r", newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                return rows[-limit:]

    def csv_text(self) -> str:
        with self.lock:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()


def is_quiet_hours(spec: str) -> bool:
    # spec ex: "23-06" (UTC)
    if not spec or "-" not in spec:
        return False
    now_h = datetime.now(timezone.utc).hour
    start, end = [int(x.strip()) for x in spec.split("-", 1)]
    if start == end:
        return True
    if start < end:
        return start <= now_h < end
    return now_h >= start or now_h < end


load_dotenv()
app = Flask(__name__)
client = HyperliquidDataClient(timeout=12)
APP_MODE = os.getenv("APP_MODE", "conservative").lower()
engine = SignalEngine(risk_pct=float(os.getenv("APP_RISK_PER_TRADE", "0.01")), mode=APP_MODE)

APP_INTERVAL = os.getenv("APP_INTERVAL", "5m")
APP_CAPITAL = float(os.getenv("APP_CAPITAL", "50"))
APP_QUIET_HOURS_UTC = os.getenv("APP_QUIET_HOURS_UTC", "")
NOTIF_COOLDOWN_SEC = int(os.getenv("APP_NOTIF_COOLDOWN_SEC", "600"))
notifier = TelegramNotifier(os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", ""))
recorder = SignalRecorder(os.getenv("APP_HISTORY_CSV", "signals_history.csv"))
last_notified: dict[str, int] = {}


@app.route("/")
def index():
    return render_template(
        "signal_dashboard.html",
        interval=APP_INTERVAL,
        capital=APP_CAPITAL,
        mode=APP_MODE,
        quiet_hours=APP_QUIET_HOURS_UTC or "off",
    )


@app.route("/api/history")
def api_history():
    return jsonify({"history": recorder.tail(100)})


@app.route("/api/export.csv")
def api_export_csv():
    return Response(
        recorder.csv_text(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=signals_history.csv"},
    )


@app.route("/api/signals")
def api_signals():
    out = {"interval": APP_INTERVAL, "capital": APP_CAPITAL, "mode": APP_MODE, "pairs": []}
    now = int(time.time())

    for coin in ("BTC", "ETH"):
        try:
            candles = client.get_candles(coin=coin, interval=APP_INTERVAL)
            sig = engine.compute_signal(candles, APP_CAPITAL)
            sig["coin"] = coin
            out["pairs"].append(sig)

            if sig["action"] in {"BUY", "SELL"}:
                signal_key = f"{coin}:{sig['action']}:{sig.get('last_ts', 0)}"

                recorder.append(
                    {
                        "created_at_utc": datetime.now(timezone.utc).isoformat(),
                        "coin": coin,
                        "action": sig["action"],
                        "score": sig["score"],
                        "entry": sig["entry"],
                        "stop_loss": sig["stop_loss"],
                        "take_profit": sig["take_profit"],
                        "qty_coin": sig["qty_coin"],
                        "risk_usd": sig["risk_usd"],
                        "interval": APP_INTERVAL,
                        "mode": APP_MODE,
                        "reason": sig["reason"],
                    }
                )

                if not is_quiet_hours(APP_QUIET_HOURS_UTC) and now - last_notified.get(signal_key, 0) >= NOTIF_COOLDOWN_SEC:
                    msg = (
                        f"{coin} {sig['action']} (score {sig['score']}/100)\n"
                        f"Entrée: {sig['entry']}\n"
                        f"SL: {sig['stop_loss']} | TP: {sig['take_profit']}\n"
                        f"Qty: {sig['qty_coin']} | Risque: ${sig['risk_usd']}\n"
                        f"TF: {APP_INTERVAL} | Mode: {APP_MODE}"
                    )
                    notifier.send(msg)
                    last_notified[signal_key] = now
        except Exception as e:
            out["pairs"].append({"coin": coin, "action": "ERROR", "reason": str(e)})

    out["internet_source"] = INFO_URL
    out["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return jsonify(out)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    app.run(host="0.0.0.0", port=port, debug=False)
