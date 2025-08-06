import random, time
from typing import Callable

# ---------- configurable thresholds ----------
MIN_TEMP = 25          # °C – lower bound of comfort band
MAX_TEMP = 27          # °C – upper bound of comfort band
TEMP_MIN_BOUND = 0     # absolute physical lower limit
TEMP_MAX_BOUND = 50    # absolute physical upper limit
TEMP_INTERVAL  = 7     # seconds between sensor updates
# ---------------------------------------------

class TemperaturePLC:
    """
    Simulates a temperature-control PLC that:
      • updates an internal temperature every `TEMP_INTERVAL` seconds,
      • calculates proportional heater / cooler power (%) to re-enter
        the [MIN_TEMP, MAX_TEMP] band,
      • sends a payload dict upstream via a user-provided `sender`.
    """
    def __init__(self,
                 sender: Callable[[dict], None],
                 initial_temp: float = (MIN_TEMP + MAX_TEMP) / 2,
                 drift: float = 2.0):
        self.temp  = initial_temp
        self.drift = drift
        self.send  = sender

    # ---- internal helpers --------------------------------------------------
    def _tick_environment(self):
        """Randomly drifts temperature within physical bounds."""
        self.temp += random.uniform(-self.drift, self.drift)
        self.temp  = max(TEMP_MIN_BOUND, min(TEMP_MAX_BOUND, self.temp))

    def _control_signal(self) -> tuple[float, float]:
        """
        Returns (heater_pct, cooler_pct); only one is non-zero.
        Heater (+%) when below MIN_TEMP, Cooler (+%) when above MAX_TEMP.
        """
        if self.temp < MIN_TEMP:
            pct = ((MIN_TEMP - self.temp) / (MIN_TEMP - TEMP_MIN_BOUND)) * 100
            return min(pct, 100), 0.0
        elif self.temp > MAX_TEMP:
            pct = ((self.temp - MAX_TEMP) / (TEMP_MAX_BOUND - MAX_TEMP)) * 100
            return 0.0, min(pct, 100)
        return 0.0, 0.0
    # ------------------------------------------------------------------------

    def run(self, cycles: int | None = None):
        """
        Starts the 7-second loop.
        • cycles=None → run indefinitely.
        • cycles=int  → run exactly that many iterations.
        """
        count = 0
        while cycles is None or count < cycles:
            self._tick_environment()
            heat, cool = self._control_signal()
            self.send({
                "temperature": round(self.temp, 2),
                "heater_pct":  round(heat, 2),
                "cooler_pct":  round(cool, 2),
            })
            count += 1
            time.sleep(TEMP_INTERVAL)
