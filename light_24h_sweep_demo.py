# light_24h_sweep_demo.py
# ------------------------------------------------------------
# Runs the upgraded LightPLC through all 24 local hours in < 30 s.
# Requires your updated LightPLC in gh.py.

import threading, datetime, itertools
from gh import LightPLC, LIGHT_MIN_BOUND, LIGHT_MAX_BOUND

# ---------- fast cadence ----------
SIM_INTERVAL = 0.2     # seconds per simulated hour  (24 h ≈ 4.8 s)
# ----------------------------------

# ---------- synthetic ambient profile ----------
# Bright midday, dim dawn/dusk, very dark night
AMB_MAP = {
    0:  10,  1:  10,  2:  10,  3:  20,
    4:  50,  5:  80,  6: 120,  7: 180,
    8: 220,  9: 260, 10: 300, 11: 340,
   12: 380, 13: 360, 14: 320, 15: 280,
   16: 240, 17: 200, 18: 150, 19: 100,
   20:  60, 21:  30, 22:  10, 23:  10
}
# -----------------------------------------------

class SimClockLightPLC(LightPLC):
    """
    Overrides _clock_now() so each call returns a simulated datetime
    that advances exactly one hour per PLC tick.
    """
    def __init__(self, *a, sim_start: datetime.datetime, **kw):
        super().__init__(*a, **kw)
        self._sim_time = sim_start

    def _clock_now(self):
        return self._sim_time

    def _advance_hour(self):
        self._sim_time += datetime.timedelta(hours=1)

    def run(self, cycles=24):
        tick = 0
        prev_power = 0.0
        while tick < cycles:
            hour = self._sim_time.hour
            # overwrite ambient reading with deterministic map
            self.light = AMB_MAP[hour]

            # apply previous lamp effect & accumulate lit hours
            self._apply_lamp_effect(prev_power)

            # decide new lamp power
            power_pct = self._compute_power_pct()

            # display
            print(f"{self._sim_time:%H:%M}  amb={self.light:3}  "
                  f"pwr={power_pct:5.1f}%  lit_h={self._lit_seconds_today/3600:4.1f}")

            prev_power = power_pct
            tick += 1
            self._advance_hour()
            threading.Event().wait(SIM_INTERVAL)

# ---------- run the sweep ----------
if __name__ == "__main__":
    start = datetime.datetime.combine(datetime.date.today(),
                                      datetime.time(hour=0, minute=0))
    plc = SimClockLightPLC(sender=lambda *_: None,        # no external sink
                           sim_start=start,
                           natural_drift=0,               # we override ambient
                           lamp_gain_100=200)             # brisk gain for demo

    plc.run(cycles=24)
