# src/core.strategy/performance.py
from typing import List, Dict, Any, Optional, Tuple
import math
import time


def _safe_mean(arr: List[float]) -> Optional[float]:
    if not arr:
        return None
    return sum(arr) / len(arr)


def _safe_std(arr: List[float]) -> Optional[float]:
    n = len(arr)
    if n < 2:
        return None
    mean = _safe_mean(arr)
    if mean is None:
        return None
    s = math.sqrt(sum((x - mean) ** 2 for x in arr) / (n - 1))
    return s


def returns_from_equity(equity: List[float]) -> List[float]:
    """
    Compute simple returns from equity series but skip segments where previous equity < threshold.
    """
    out: List[float] = []
    min_equity = 1e-6  # threshold to avoid dividing by zero

    for i in range(1, len(equity)):
        prev = equity[i - 1]
        cur = equity[i]
        if prev < min_equity:
            continue
        out.append((cur / prev) - 1.0)
    return out


class PerformanceEngine:
    """
    Records equity points and derives performance metrics.
    Sampling modes:
      - 'fills'           : record every call (intended for fills)
      - 'on_position'     : record only when position_open=True is passed
      - 'every_n_seconds': record at most once per sample_interval seconds
      - 'all'             : record every call (same as 'fills')
    """

    def __init__(self,
                 starting_equity: float = 0.0,
                 sample_mode: str = "fills",
                 sample_interval: float = 10.0):    # <-- default 10s now | 0.2-1 HFT | 1-10s Swing trades | 10-60s LFT 
        self._points: List[Tuple[float, float]] = []
        self.starting_equity = float(starting_equity)
        self.sample_mode = sample_mode
        self.sample_interval = float(sample_interval)
        self._last_sample_ts: Optional[float] = None

        if self.starting_equity > 0:
            # record initial baseline
            self.record_point(self.starting_equity, ts=None, position_open=False, force=True)

    def record_point(self,
                     equity_value: float,
                     ts: Optional[float] = None,
                     position_open: bool = False,
                     force: bool = False):
        """
        Try to append an equity snapshot. Sampling rules determine whether it is stored.
        - position_open: hint from caller whether a position was open when this sample was taken.
        - force: bypass sampling rules (used to record starting equity).
        """
        if ts is None:
            ts = time.time()
        ts = float(ts)
        equity_value = float(equity_value)

        # Always allow force writes
        if not force:
            if self.sample_mode == "fills":
                # fills mode: recorder should be called at fills (we assume caller calls accordingly)
                pass  # accept the call (no extra checks)
            elif self.sample_mode == "all":
                pass
            elif self.sample_mode == "on_position":
                # only record if position was open when called
                if not position_open:
                    return
            elif self.sample_mode == "every_n_seconds":
                if self._last_sample_ts is None or (ts - self._last_sample_ts) >= self.sample_interval:
                    # ok
                    pass
                else:
                    return
            else:
                # unknown mode — default to conservative behavior: only record on fills/force
                return

        # Append the sample and update last sample time
        self._points.append((ts, equity_value))
        self._last_sample_ts = ts

    def equity_curve(self) -> List[Dict[str, float]]:
        """Return list of {'ts':..., 'equity': ...} sorted by time."""
        return [{"ts": t, "equity": e} for (t, e) in self._points]

    def _equity_list(self) -> List[float]:
        return [e for (_, e) in self._points]

    def _compute_drawdowns(self) -> Dict[str, Any]:
        eq = self._equity_list()
        if not eq:
            return {"current_drawdown": 0.0, "max_drawdown": 0.0, "peak_ts": None, "trough_ts": None}
        peak = eq[0]
        peak_ts = self._points[0][0]
        max_dd = 0.0
        max_peak_ts = peak_ts
        max_trough_ts = peak_ts
        current_dd = 0.0

        for (ts, val) in self._points:
            if val > peak:
                peak = val
                peak_ts = ts
            drawdown = (peak - val) / (peak if peak != 0 else 1e-12)
            if drawdown > max_dd:
                max_dd = drawdown
                max_peak_ts = peak_ts
                max_trough_ts = ts
            current_dd = (peak - val) / (peak if peak != 0 else 1e-12)

        return {
            "current_drawdown": current_dd,
            "max_drawdown": max_dd,
            "peak_ts": max_peak_ts,
            "trough_ts": max_trough_ts,
        }

    def _compute_return_stats(self, annualization: Optional[float] = None) -> Dict[str, Any]:
        eq = self._equity_list()
        rets = returns_from_equity(eq)

        if not rets:
            return {
                "returns_count": 0,
                "mean_return": None,
                "std_return": None,
                "sharpe": None,
                "sortino": None,
            }

        mean_r = _safe_mean(rets)
        std_r = _safe_std(rets)

        sharpe = None
        if mean_r is not None and std_r not in (None, 0):
            sharpe = mean_r / std_r
            if annualization:
                sharpe *= math.sqrt(annualization)

        downside = [r for r in rets if r < 0]
        std_down = _safe_std(downside) if downside else None
        sortino = None
        if mean_r is not None and std_down not in (None, 0):
            sortino = mean_r / std_down
            if annualization:
                sortino *= math.sqrt(annualization)

        return {
            "returns_count": len(rets),
            "mean_return": mean_r,
            "std_return": std_r,
            "sharpe": sharpe,
            "sortino": sortino,
        }

    def report(self, annualization: Optional[float] = None) -> Dict[str, Any]:
        eq = self._equity_list()
        draw = self._compute_drawdowns()
        stats = self._compute_return_stats(annualization=annualization)
        return {
            "equity_curve": self.equity_curve(),
            "last_equity": eq[-1] if eq else None,
            "drawdown": draw,
            "returns": stats,
        }
