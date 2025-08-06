import time, datetime
from typing import Callable

# ---------- configuration ----------
MIN_CO2       = 800      # ppm – dose CO₂ when below this (day-time)
MAX_CO2       = 1200     # ppm – vent when above this (any time)
CO2_MIN_BOUND = 300
CO2_MAX_BOUND = 2000
CO2_INTERVAL  = 7        # seconds per control loop
DOSING_PERIOD = 1        # dose check every N cycles (~35 s here)
DAY_START_HR  = 6
DAY_END_HR    = 18
# -----------------------------------

class CO2PLC:
    """
    Simulates a CO₂-dosing and vent-control PLC.
    Publishes {co2_ppm, pump_pct, vent_pct}.
    """
    def __init__(self,
                 sender: Callable[[dict], None],
                 initial_ppm: float = 900,
                 plant_day_sink: float = 8.0,
                 plant_night_source: float = 15.0,
                 pump_gain_100: float = 40.0,
                 vent_loss_100: float = 60.0,
                 dosing_period: int = DOSING_PERIOD):
        self.ppm        = initial_ppm
        self.day_sink   = plant_day_sink
        self.night_src  = plant_night_source
        self.pump_gain  = pump_gain_100
        self.vent_loss  = vent_loss_100
        self.send       = sender
        self.dosing_period = max(dosing_period, 1)
        self._cycle        = 0
        self._prev_pump    = 0.0
        self._prev_vent    = 0.0

    # ─── helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _is_daytime() -> bool:
        hr = datetime.datetime.now().hour
        return DAY_START_HR <= hr < DAY_END_HR

    def _apply_plant_effect(self):
        if self._is_daytime():
            self.ppm -= self.day_sink
        else:
            self.ppm += self.night_src

    def _apply_actuator_effect(self):
        self.ppm += (self._prev_pump / 100) * self.pump_gain
        self.ppm -= (self._prev_vent / 100) * self.vent_loss

    def _compute_control(self) -> tuple[float, float]:
        pump_pct = vent_pct = 0.0

        # Venting priority if CO₂ too high
        if self.ppm > MAX_CO2:
            excess   = self.ppm - MAX_CO2
            span     = CO2_MAX_BOUND - MAX_CO2 or 1
            vent_pct = min((excess / span) * 100, 100)
            return 0.0, vent_pct

        # Dosing allowed only during daylight & on dosing-period ticks
        if self._is_daytime() and self._cycle % self.dosing_period == 0 \
                               and self.ppm < MIN_CO2:
            deficit  = MIN_CO2 - self.ppm
            span     = MIN_CO2 - CO2_MIN_BOUND or 1
            pump_pct = min((deficit / span) * 100, 100)

        return pump_pct, 0.0
    # -----------------------------------------------------------------

    def run(self, cycles: int | None = None):
        while cycles is None or self._cycle < cycles:
            # 1. environment dynamics
            self._apply_plant_effect()
            self._apply_actuator_effect()

            # keep within physical bounds
            self.ppm = max(CO2_MIN_BOUND, min(CO2_MAX_BOUND, self.ppm))

            # 2. control decision
            pump_pct, vent_pct = self._compute_control()

            # 3. publish reading
            self.send({
                "co2_ppm":   round(self.ppm, 1),
                "pump_pct":  round(pump_pct, 2),
                "vent_pct":  round(vent_pct, 2),
            })

            # 4. remember actuators for next tick
            self._prev_pump = pump_pct
            self._prev_vent = vent_pct

            self._cycle += 1
            time.sleep(CO2_INTERVAL)
