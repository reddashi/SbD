import time
from typing import Callable

# ─── user-tunable thresholds & physics constants ───
MIN_MOISTURE        = 40     # % – lower comfort limit
MAX_MOISTURE        = 60     # % – upper comfort limit
MOISTURE_MIN_BOUND  = 0
MOISTURE_MAX_BOUND  = 100
IRRIGATION_INTERVAL = 7      # seconds between PLC ticks
# ──────────────────────────────────────────────────

class IrrigationPLC:
    """
    Simulates soil-moisture regulation with a pump (+) and drain (−).
    Publishes {moisture, pump_pct, drain_pct}.
    """
    def __init__(self,
                 sender: Callable[[dict], None],
                 *,
                 initial_moisture: float = 50,
                 dry_drift: float = 1.0,        # % lost naturally each tick
                 irrigation_rate: float = 3.0,  # % gained at 100 % pump duty
                 drain_rate: float = 4.0):      # % lost at 100 % drain duty
        self.moisture       = initial_moisture
        self.dry_drift      = dry_drift
        self.irrigation_rate = irrigation_rate
        self.drain_rate     = drain_rate
        self.send           = sender

    # ─── environment physics per tick ─────────────────────────────────
    def _evaporate(self):
        self.moisture -= abs(self.dry_drift)

    def _apply_irrigation(self, pct: float):
        self.moisture += (pct / 100) * self.irrigation_rate

    def _apply_drain(self, pct: float):
        self.moisture -= (pct / 100) * self.drain_rate

    # ─── controller (decides actuator set-points) ─────────────────────
    def _compute_actuators(self) -> tuple[float, float]:
        if self.moisture < MIN_MOISTURE:             # too dry
            deficit = MIN_MOISTURE - self.moisture
            span    = MIN_MOISTURE - MOISTURE_MIN_BOUND or 1
            pump_pct = min((deficit / span) * 100, 100)
            return pump_pct, 0.0

        if self.moisture > MAX_MOISTURE:             # too wet
            surplus = self.moisture - MAX_MOISTURE
            span    = MOISTURE_MAX_BOUND - MAX_MOISTURE or 1
            drain_pct = min((surplus / span) * 100, 100)
            return 0.0, drain_pct

        return 0.0, 0.0                              # in comfort band

    # ─── public run loop ──────────────────────────────────────────────
    def run(self, cycles: int | None = None):
        count = 0
        while cycles is None or count < cycles:
            # 1. environment update
            self._evaporate()

            # 2. control decision
            pump_pct, drain_pct = self._compute_actuators()

            # 3. apply actuator effects *for next tick*
            self._apply_irrigation(pump_pct)
            self._apply_drain(drain_pct)

            # 4. clamp to physical limits
            self.moisture = max(MOISTURE_MIN_BOUND,
                                min(MOISTURE_MAX_BOUND, self.moisture))

            # 5. publish reading upstream
            self.send({
                "moisture":  round(self.moisture, 2),
                "pump_pct":  round(pump_pct, 2),
                "drain_pct": round(drain_pct, 2),
            })

            count += 1
            time.sleep(IRRIGATION_INTERVAL)
