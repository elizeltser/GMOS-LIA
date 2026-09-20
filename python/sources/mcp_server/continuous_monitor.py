"""
Background continuous R/theta monitoring with live drift-fit estimation.

Runs as a daemon thread so MCP tool calls (which are one-shot request/response
and can't block indefinitely) can start it, poll its status, and stop it via
separate tool calls. Mirrors ``DifferentialCalibration._sample_for``'s live
``np.polyfit`` slope tracking, but on R instead of X, and persists every
sample to CSV as it arrives.
"""

import csv
import logging
import threading
import time

import numpy as np
from setups.setup_base import SetupSnapshot

logger = logging.getLogger(__name__)


class ContinuousMonitor:
    """Continuously snaps LIA R/theta, appends to CSV, and tracks drift.

    ``read_sample`` is a zero-argument callable returning ``(r, theta)``; the
    caller (``OperatingPointSession``) supplies one that snaps under its own
    lock so the monitor thread never races a synchronous tool call against
    the instrument.
    """

    def __init__(
        self,
        read_sample,
        csv_path: str,
        snapshot: SetupSnapshot,
        sample_interval: float = 1.0,
        drift_window_s: float = 60.0,
    ) -> None:
        self._read_sample = read_sample
        self.csv_path = csv_path
        self.snapshot = snapshot
        self.sample_interval = sample_interval
        self.drift_window_s = drift_window_s

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._data_lock = threading.Lock()
        self._t: list[float] = []
        self._r: list[float] = []
        self._theta: list[float] = []
        self._events: list[tuple[int, str]] = []
        self._pending_event: str | None = None
        self._t0: float | None = None
        self._error: str | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            raise RuntimeError("monitor already running")
        self._stop_event.clear()
        self._t0 = time.time()
        self._csv_file = open(self.csv_path, "w", newline="")
        writer = csv.writer(self._csv_file)
        writer.writerows(self.snapshot.as_rows(width=5))
        writer.writerow(["index", "time_s", "R_v", "theta_deg", "event"])
        self._writer = writer
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def add_event(self, note: str) -> int:
        """Attach ``note`` to the next row written; returns that row's index."""
        with self._data_lock:
            self._pending_event = (
                f"{self._pending_event} | {note}" if self._pending_event else note
            )
            return len(self._t)

    def _run(self) -> None:
        assert self._t0 is not None
        index = 0
        try:
            while not self._stop_event.is_set():
                r, theta = self._read_sample()
                elapsed = time.time() - self._t0
                with self._data_lock:
                    note = self._pending_event or ""
                    self._pending_event = None
                    self._t.append(elapsed)
                    self._r.append(r)
                    self._theta.append(theta)
                    if note:
                        self._events.append((index, note))
                self._writer.writerow([index, elapsed, r, theta, note])
                self._csv_file.flush()
                index += 1
                self._stop_event.wait(self.sample_interval)
        except Exception as exc:  # instrument I/O failure inside the loop
            logger.exception("continuous monitor sample loop failed")
            with self._data_lock:
                self._error = str(exc)
            self._running = False
        finally:
            self._csv_file.close()

    def _drift_slope(self, t: list[float], r: list[float]) -> float | None:
        if len(t) < 2:
            return None
        return float(np.polyfit(t, r, 1)[0])

    def status(self) -> dict:
        with self._data_lock:
            t = list(self._t)
            r = list(self._r)
            theta = list(self._theta)
            error = self._error
        elapsed = t[-1] if t else 0.0
        window_start_idx = 0
        for i in range(len(t) - 1, -1, -1):
            if t[-1] - t[i] > self.drift_window_s:
                window_start_idx = i + 1
                break
        return {
            "running": self._running,
            "n_samples": len(t),
            "elapsed_s": elapsed,
            "latest_r_v": r[-1] if r else None,
            "latest_theta_deg": theta[-1] if theta else None,
            "drift_slope_v_per_s": self._drift_slope(t, r),
            "windowed_drift_slope_v_per_s": self._drift_slope(
                t[window_start_idx:], r[window_start_idx:]
            ),
            "error": error,
        }

    def stop(self) -> dict:
        if not self._running and self._thread is None:
            raise RuntimeError("monitor is not running")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.sample_interval + 10.0)
        self._running = False
        result = self.status()
        result["csv_path"] = self.csv_path
        return result

    def buffer(
        self,
    ) -> tuple[list[float], list[float], list[float], list[tuple[int, str]]]:
        with self._data_lock:
            return list(self._t), list(self._r), list(self._theta), list(self._events)
