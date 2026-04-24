import os
import time
import math
import json
import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

import requests
from dotenv import load_dotenv


INFO_URL = "https://api.hyperliquid.xyz/info"


@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Position:
    side: str  # "long" or "short"
    entry: float
    size: float
    stop: float
    take_profit: float
    opened_at: int


class HyperliquidDataClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _post(self, payload: dict):
        r = requests.post(INFO_URL, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_candles(self, coin: str, interval: str, lookback_minutes: int = 600) -> List[Candle]:
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
        raw = self._post(payload)
        candles: List[Candle] = []

        # Hyperliquid renvoie des clés qui peuvent varier selon endpoint/version,
        # on parse donc de manière robuste.
        for c in raw:
            ts = int(c.get("t") or c.get("T") or c.get("time") or 0)
            o = float(c.get("o") or c.get("open"))
            h = float(c.get("h") or c.get("high"))
            l = float(c.get("l") or c.get("low"))
            cl = float(c.get("c") or c.get("close"))
            v = float(c.get("v") or c.get("volume") or 0)
            candles.append(Candle(ts=ts, open=o, high=h, low=l, close=cl, volume=v))

        candles.sort(key=lambda x: x.ts)
        return candles


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

    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - (100 / (1 + rs))

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


class PaperTrader:
    def __init__(self, starting_balance: float, risk_per_trade: float, fee_rate: float):
        self.balance = starting_balance
        self.risk_per_trade = risk_per_trade
        self.fee_rate = fee_rate
        self.position: Optional[Position] = None
        self.day_start_balance = starting_balance
        self.day_key = dt.datetime.utcnow().strftime("%Y-%m-%d")
        self.consecutive_losses = 0

    def _roll_day(self):
        k = dt.datetime.utcnow().strftime("%Y-%m-%d")
        if k != self.day_key:
            self.day_key = k
            self.day_start_balance = self.balance
            self.consecutive_losses = 0

    def daily_drawdown_pct(self) -> float:
        if self.day_start_balance <= 0:
            return 0.0
        return (self.day_start_balance - self.balance) / self.day_start_balance * 100

    def can_trade(self, max_daily_dd: float, max_consecutive_losses: int) -> bool:
        self._roll_day()
        if self.daily_drawdown_pct() >= max_daily_dd:
            return False
        if self.consecutive_losses >= max_consecutive_losses:
            return False
        return True

    def open_position(self, side: str, price: float, stop: float, take_profit: float):
        risk_usd = self.balance * self.risk_per_trade
        per_unit_risk = abs(price - stop)
        if per_unit_risk <= 0:
            return
        size = risk_usd / per_unit_risk

        notional = size * price
        fee = notional * self.fee_rate
        self.balance -= fee

        self.position = Position(
            side=side,
            entry=price,
            size=size,
            stop=stop,
            take_profit=take_profit,
            opened_at=int(time.time() * 1000),
        )
        print(
            f"[OPEN] {side.upper()} entry={price:.2f} size={size:.6f} stop={stop:.2f} tp={take_profit:.2f} fee={fee:.4f} bal={self.balance:.2f}"
        )

    def update(self, candle: Candle):
        if not self.position:
            return

        p = self.position
        exit_price = None
        reason = None

        if p.side == "long":
            if candle.low <= p.stop:
                exit_price = p.stop
                reason = "SL"
            elif candle.high >= p.take_profit:
                exit_price = p.take_profit
                reason = "TP"
        else:
            if candle.high >= p.stop:
                exit_price = p.stop
                reason = "SL"
            elif candle.low <= p.take_profit:
                exit_price = p.take_profit
                reason = "TP"

        if exit_price is None:
            return

        pnl = (exit_price - p.entry) * p.size if p.side == "long" else (p.entry - exit_price) * p.size
        close_fee = (p.size * exit_price) * self.fee_rate
        pnl_after_fees = pnl - close_fee
        self.balance += pnl_after_fees

        if pnl_after_fees < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        print(
            f"[CLOSE] {reason} {p.side.upper()} exit={exit_price:.2f} pnl={pnl_after_fees:.4f} bal={self.balance:.2f} losses={self.consecutive_losses}"
        )
        self.position = None


class Strategy:
    def __init__(self, ema_fast: int, ema_slow: int, rsi_period: int, atr_period: int):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.atr_period = atr_period

    def signal(self, candles: List[Candle]) -> Optional[dict]:
        if len(candles) < max(self.ema_slow, self.rsi_period, self.atr_period) + 5:
            return None

        closes = [c.close for c in candles]
        ef = ema(closes, self.ema_fast)
        es = ema(closes, self.ema_slow)
        rr = rsi(closes, self.rsi_period)
        aa = atr(candles, self.atr_period)

        c = candles[-1]
        trend_up = ef[-1] > es[-1]
        trend_down = ef[-1] < es[-1]

        # Petite timeframe: on filtre avec RSI pour éviter de chase.
        if trend_up and 48 <= rr[-1] <= 62:
            stop = c.close - 1.2 * aa[-1]
            tp = c.close + 1.8 * aa[-1]
            return {"side": "long", "entry": c.close, "stop": stop, "tp": tp}

        if trend_down and 38 <= rr[-1] <= 52:
            stop = c.close + 1.2 * aa[-1]
            tp = c.close - 1.8 * aa[-1]
            return {"side": "short", "entry": c.close, "stop": stop, "tp": tp}

        return None


def pick_interval(user_interval: str) -> str:
    allowed = {"1m", "3m", "5m", "15m", "30m", "1h"}
    if user_interval not in allowed:
        print(f"[WARN] interval '{user_interval}' invalide, fallback 5m")
        return "5m"
    return user_interval


def main():
    load_dotenv()

    coin = os.getenv("BOT_COIN", "BTC").upper()
    if coin not in {"BTC", "ETH"}:
        raise ValueError("BOT_COIN doit être BTC ou ETH")

    interval = pick_interval(os.getenv("BOT_INTERVAL", "5m"))
    poll_seconds = int(os.getenv("BOT_POLL_SECONDS", "20"))

    starting_balance = float(os.getenv("BOT_START_BALANCE", "50"))
    risk_per_trade = float(os.getenv("BOT_RISK_PER_TRADE", "0.01"))
    fee_rate = float(os.getenv("BOT_FEE_RATE", "0.00035"))

    max_daily_dd = float(os.getenv("BOT_MAX_DAILY_DD_PCT", "3.0"))
    max_losses = int(os.getenv("BOT_MAX_CONSEC_LOSSES", "3"))

    print("=" * 72)
    print("Hyperliquid BTC/ETH Paper Bot (petites timeframes)")
    print("Objectif: discipline + gestion du risque. Pas de garantie de gain.")
    print(f"Coin={coin} interval={interval} balance={starting_balance}$ risk/trade={risk_per_trade*100:.2f}%")
    print("=" * 72)

    data = HyperliquidDataClient(timeout=10)
    strat = Strategy(ema_fast=21, ema_slow=55, rsi_period=14, atr_period=14)
    trader = PaperTrader(starting_balance, risk_per_trade, fee_rate)

    last_candle_ts = None

    while True:
        try:
            candles = data.get_candles(coin=coin, interval=interval, lookback_minutes=900)
            if len(candles) < 100:
                print("[INFO] Pas assez de candles, on attend...")
                time.sleep(poll_seconds)
                continue

            latest = candles[-1]
            if last_candle_ts == latest.ts:
                time.sleep(poll_seconds)
                continue
            last_candle_ts = latest.ts

            trader.update(latest)

            if trader.position is None and trader.can_trade(max_daily_dd=max_daily_dd, max_consecutive_losses=max_losses):
                sig = strat.signal(candles[:-1])  # on utilise la dernière bougie clôturée
                if sig:
                    trader.open_position(
                        side=sig["side"],
                        price=sig["entry"],
                        stop=sig["stop"],
                        take_profit=sig["tp"],
                    )
                else:
                    print(f"[{coin} {interval}] pas de setup | bal={trader.balance:.2f}")
            else:
                if trader.position is not None:
                    print(f"[{coin} {interval}] position ouverte | bal={trader.balance:.2f}")
                else:
                    print(
                        f"[{coin} {interval}] kill-switch actif (dd={trader.daily_drawdown_pct():.2f}% losses={trader.consecutive_losses})"
                    )

        except KeyboardInterrupt:
            print("\nArrêt demandé.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(max(5, poll_seconds))


if __name__ == "__main__":
    main()
