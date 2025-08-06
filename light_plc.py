import time, random, datetime
from typing import Callable

# --- comfort band (lux, PPFD, etc.) ---
MIN_LIGHT       = 200
MAX_LIGHT       = 350
LIGHT_MIN_BOUND = 0
LIGHT_MAX_BOUND = 1000
LIGHT_INTERVAL  = 7           # seconds between PLC ticks

# --- photoperiod configuration ---
DARK_START_HR  = 22           # 22:00 local (lights forced OFF)
DARK_END_HR    = 6            # 06:00 local
LONG_DAY_HOURS = 16           # desired total lit hours per 24 h
# ----------------------------------

class LightPLC:
    """Grow-light controller with night-shutdown and long-day tracking."""
    def __init__(self,
                 sender: Callable[[dict], None],
                 *,
                 initial_light: float = (MIN_LIGHT + MAX_LIGHT) / 2,
                 natural_drift: float = 15.0,
                 lamp_gain_100: float = 60.0):
        self.light  = initial_light
        self.drift  = natural_drift
        self.gain   = lamp_gain_100
        self.send   = sender
        self._lit_seconds_today   = 0
        self._midnight_day_index  = datetime.date.today()

    # ─── helpers ──────────────────────────────────────────────────────
    def _clock_now(self):
        return datetime.datetime.now()

    def _is_dark_window(self) -> bool:
        hr = self._clock_now().hour
        if DARK_START_HR < DARK_END_HR:             # same-day window
            return DARK_START_HR <= hr < DARK_END_HR
        else:                                       # window crosses midnight
            return hr >= DARK_START_HR or hr < DARK_END_HR

    def _reset_midnight_counter(self):
        today = datetime.date.today()
        if today != self._midnight_day_index:
            self._midnight_day_index = today
            self._lit_seconds_today  = 0

    # ─── physics each tick ───────────────────────────────────────────
    def _ambient_variation(self):
        self.light += random.uniform(-self.drift, self.drift)

    def _apply_lamp_effect(self, pct: float):
        self.light += (pct / 100) * self.gain
        if pct > 0:
            self._lit_seconds_today += LIGHT_INTERVAL

    # ─── controller ──────────────────────────────────────────────────
    def _compute_power_pct(self) -> float:
        # 1) Absolute OFF inside dark window
        if self._is_dark_window():
            return 0.0

        # 2) Long-day achieved? → keep lamps off unless dangerously dim
        lit_hours = self._lit_seconds_today / 3600
        if lit_hours >= LONG_DAY_HOURS and self.light >= MIN_LIGHT:
            return 0.0

        # 3) Standard proportional top-up
        if self.light < MIN_LIGHT:
            deficit = MIN_LIGHT - self.light
            span    = MIN_LIGHT - LIGHT_MIN_BOUND or 1
            return min((deficit / span) * 100, 100)

        return 0.0

    # ─── main loop ───────────────────────────────────────────────────
    def run(self, cycles: int | None = None):
        prev_power = 0.0
        tick = 0
        while cycles is None or tick < cycles:
            self._reset_midnight_counter()
            self._ambient_variation()
            self._apply_lamp_effect(prev_power)

            # clamp
            self.light = max(LIGHT_MIN_BOUND,
                             min(LIGHT_MAX_BOUND, self.light))

            power_pct = self._compute_power_pct()
            self.send({
                "light":          round(self.light, 2),
                "grow_power_pct": round(power_pct, 2),
            })

            prev_power = power_pct
            tick += 1
            time.sleep(LIGHT_INTERVAL)
