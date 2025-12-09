from collections import deque

class RollingWindow:
    def __init__(self, size):
        self.size = size
        self._dq = deque(maxlen=size)

    def append(self, v):
        self._dq.append(v)

    def all(self):
        return list(self._dq)

    def last(self, n=1):
        return list(self._dq)[-n:]

    def mean(self):
        vals = [x for x in self._dq if x is not None]
        return sum(vals)/len(vals) if vals else None

# --- Simple indicators ---
def sma(values):
    return sum(values) / len(values) if values else None

def ema(values, period):
    if not values:
        return None
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = e * (1 - k) + v * k
    return e

def rsi(values, period=14):
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        diff = values[i] - values[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1)+gains[i])/period
        avg_loss = (avg_loss*(period-1)+losses[i])/period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

def vwap(bars):
    total_vp = 0
    total_vol = 0
    for b in bars:
        p = float(b.get("price") or 0)
        v = float(b.get("volume") or 0)
        total_vp += p * v
        total_vol += v
    return total_vp / total_vol if total_vol else None
