import math, threading, pprint, time
from gh import CO2PLC, CO2_INTERVAL, CO2_MIN_BOUND, CO2_MAX_BOUND

class QuickSweepCO2PLC(CO2PLC):
    """
    Drives the CO₂ reading through one full sine-wave sweep
    (300 ppm → 2000 ppm → 300 ppm) over `sweep_cycles` iterations.
    Actuator effects are disabled so ppm follows the preset curve.
    """
    def __init__(self, *a, sweep_cycles: int = 40, **kw):
        super().__init__(*a, **kw)
        self._sweep_cycles = max(sweep_cycles, 2)

    # --- override physics -----------------------------------
    def _apply_plant_effect(self):
        # phase ∈ [0, 2π] over one sweep
        phi = 2 * math.pi * (self._cycle % self._sweep_cycles) / self._sweep_cycles
        self.ppm = ((math.sin(phi) + 1) / 2) * (CO2_MAX_BOUND - CO2_MIN_BOUND) \
                   + CO2_MIN_BOUND

    def _apply_actuator_effect(self):
        pass   # disable feedback so curve is deterministic
    # ---------------------------------------------------------

# ------------ channel to observe outputs -------------------
def print_sender(msg): pprint.pprint(msg)

# ----- OPTIONAL: speed up the demo (e.g. 0.2-second ticks) --
import gh
gh.CO2_INTERVAL = 0.2     # comment this line out to keep 7-s cadence
# ------------------------------------------------------------

plc       = QuickSweepCO2PLC(sender=print_sender, sweep_cycles=40)
demo_thr  = threading.Thread(target=plc.run, kwargs={'cycles': 40})
demo_thr.start(); demo_thr.join()
print("Quick-sweep CO₂ PLC demo finished.")

