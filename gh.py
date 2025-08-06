# ─────────────────────── PLC-1 (Coordinator) ───────────────────────
import threading, queue, time

class PLC1:
    """
    • Receives sensor/control payloads from PLC2-PLC5 via per-PLC queues
    • Evaluates whether each value lies inside its threshold band
    • When a PLC drifts out of band, logs a "request" (real system would
      send a command; here we just print)
    • When all PLCs are healthy simultaneously, increments ack_count
    """
    def __init__(self):
        self.queues  = {            # inbound channels
            "temp":        queue.Queue(),
            "irrigation":  queue.Queue(),
            "light":       queue.Queue(),
            "co2":         queue.Queue(),
        }
        self.ok_flags = {k: False for k in self.queues}
        self.ack_count = 0

    # ---------- helper handed to each PLC so it can publish ----------
    def sender_for(self, key: str):
        q = self.queues[key]
        def _sender(msg: dict):
            q.put(msg)
        return _sender
    # -----------------------------------------------------------------

    # ---------- threshold tests for every PLC type ----------
    def _within_band(self, key: str, msg: dict) -> bool:
        match key:
            case "temp":
                return MIN_TEMP <= msg["temperature"] <= MAX_TEMP
            case "irrigation":
                return MIN_MOISTURE <= msg["moisture"] <= MAX_MOISTURE
            case "light":
                return MIN_LIGHT <= msg["light"] <= MAX_LIGHT
            case "co2":
                return MIN_CO2 <= msg["co2_ppm"] <= MAX_CO2
        return False
    # --------------------------------------------------------

    def run(self):
        while True:
            # non-blocking scan of each queue
            for key, q in self.queues.items():
                try:
                    msg = q.get_nowait()
                except queue.Empty:
                    continue

                in_band = self._within_band(key, msg)

                # transition → out of band  ➔  "send request"
                if not in_band and self.ok_flags[key]:
                    self.ok_flags[key] = False
                    print(f"[PLC1] {key} out-of-range – asking PLC to correct")

                # transition → back in band  ➔  acknowledgement
                elif in_band and not self.ok_flags[key]:
                    self.ok_flags[key] = True
                    print(f"[PLC1] {key} back in range")

            # all healthy?  ➔  increment ack counter once per full set
            if all(self.ok_flags.values()):
                self.ack_count += 1
                print(f"[PLC1] ✅  all sensors nominal (ack_count = {self.ack_count})")
                # reset flags so next disturbance must be fixed again
                self.ok_flags = {k: False for k in self.ok_flags}

            time.sleep(0.1)   # light CPU touch

# ──────────────── Temperature PLC ────────────────
import random
import time
from typing import Callable

# ---------- configurable thresholds ----------
MIN_TEMP = 25          # °C – lower bound of comfort band
MAX_TEMP = 27          # °C – upper bound of comfort band
TEMP_MIN_BOUND = 0     # absolute physical lower limit
TEMP_MAX_BOUND = 50    # absolute physical upper limit
TEMP_INTERVAL = 7      # seconds between sensor updates
# ---------------------------------------------

class TemperaturePLC:
    """
    Simulates a temperature-control PLC that:
      • updates an internal temperature every `INTERVAL` seconds,
      • calculates proportional heater / cooler power (%) to re-enter
        the [MIN_TEMP, MAX_TEMP] band,
      • sends a payload dict upstream via a user-provided `sender`.
    """

    def __init__(self,
                 sender: Callable[[dict], None],
                 initial_temp: float = (MIN_TEMP + MAX_TEMP) / 2,
                 drift: float = 2.0):
        self.temp = initial_temp
        self.drift = drift
        self.send = sender

    # ---- internal helpers --------------------------------------------------
    def _tick_environment(self) -> None:
        """Randomly drifts temperature within physical bounds."""
        self.temp += random.uniform(-self.drift, self.drift)
        self.temp = max(TEMP_MIN_BOUND, min(TEMP_MAX_BOUND, self.temp))

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

    def run(self, cycles: int | None = None) -> None:
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
                "heater_pct": round(heat, 2),
                "cooler_pct": round(cool, 2),
            })
            count += 1
            time.sleep(TEMP_INTERVAL)

# ──────────────── Irrigation / Water-Pump PLC ────────────────

#  • Simulates soil-moisture regulation in a greenhouse.
#  • TWO actuators:
#        1) pump_pct  – watering valve (adds moisture)
#        2) drain_pct – drain valve  (removes excess water)
#  • Control policy
#        moisture < 40 %   → pump   proportional to deficit
#        40 %–60 %         → both   0 %  (comfort band)
#        moisture > 60 %   → drain  proportional to surplus
#  • Each loop step (default 7 s) applies:
#        – natural evaporation (dry_drift)
#        – previous pump & drain effects
#        – new control decision
#  • Publishes a payload dict via the user-supplied `sender`
#        { "moisture": %, "pump_pct": %, "drain_pct": % }
# ──────────────────────────────────────────────────────────────

import time
from typing import Callable

# ── user-tunable thresholds & physics constants ──────────────
MIN_MOISTURE        = 40      # %  – lower comfort limit
MAX_MOISTURE        = 60      # %  – upper comfort limit
MOISTURE_MIN_BOUND  = 0       # absolute dry
MOISTURE_MAX_BOUND  = 100     # fully saturated
IRRIGATION_INTERVAL    = 7       # seconds between PLC ticks
# ──────────────────────────────────────────────────────────────

class IrrigationPLC:
    def __init__(self,
                 sender: Callable[[dict], None],
                 *,
                 initial_moisture: float = 50,
                 dry_drift: float = 1.0,       # % lost naturally each tick
                 irrigation_rate: float = 3.0, # % gained at 100 % pump duty
                 drain_rate: float = 4.0):     # % lost at 100 % drain duty
        self.moisture = initial_moisture
        self.dry_drift = dry_drift
        self.irrigation_rate = irrigation_rate
        self.drain_rate = drain_rate
        self.send = sender

    # ─────── environment physics per tick ────────────────────
    def _evaporate(self) -> None:
        """Natural water loss from soil (always subtracts)."""
        self.moisture -= abs(self.dry_drift)

    def _apply_irrigation(self, pct: float) -> None:
        """Add water based on pump duty cycle."""
        self.moisture += (pct / 100) * self.irrigation_rate

    def _apply_drain(self, pct: float) -> None:
        """Remove water based on drain duty cycle."""
        self.moisture -= (pct / 100) * self.drain_rate

    # ─────── controller (decides actuator set-points) ────────
    def _compute_actuators(self) -> tuple[float, float]:
        """
        Returns (pump_pct, drain_pct), each 0-100 %.
        Only one actuator is active at a time.
        """
        if self.moisture < MIN_MOISTURE:             # too dry
            deficit = MIN_MOISTURE - self.moisture
            span = MIN_MOISTURE - MOISTURE_MIN_BOUND or 1
            pump_pct = min((deficit / span) * 100, 100)
            return pump_pct, 0.0

        if self.moisture > MAX_MOISTURE:             # too wet
            surplus = self.moisture - MAX_MOISTURE
            span = MOISTURE_MAX_BOUND - MAX_MOISTURE or 1
            drain_pct = min((surplus / span) * 100, 100)
            return 0.0, drain_pct

        return 0.0, 0.0                              # in comfort band

    # ─────── public run loop ─────────────────────────────────
    def run(self, cycles: int | None = None) -> None:
        """
        Start the PLC loop.
        • cycles=None  → run forever
        • cycles=int   → run exactly that many iterations
        """
        count = 0
        while cycles is None or count < cycles:
            # 1. environment update
            self._evaporate()

            # 2. control decision
            pump_pct, drain_pct = self._compute_actuators()

            # 3. apply actuator effects *for next tick*
            self._apply_irrigation(pump_pct)
            self._apply_drain(drain_pct)

            # 4. clamp to physical limits for realism
            self.moisture = max(MOISTURE_MIN_BOUND,
                                min(MOISTURE_MAX_BOUND, self.moisture))

            # 5. publish reading upstream (e.g., to PLC-1)
            self.send({
                "moisture":  round(self.moisture, 2),
                "pump_pct":  round(pump_pct, 2),
                "drain_pct": round(drain_pct, 2),
            })

            count += 1
            time.sleep(IRRIGATION_INTERVAL)


# ──────────────── Light-Intensity / Grow-Light PLC (v2) ────────────────
# Key additions
#   • Configurable DARK_START_HR / DARK_END_HR  → lights locked OFF inside
#   • Optional LONG_DAY_HOURS target            → ensure total light ≥ target
#       (simplest implementation: if daytime so far today < target hours,
#        allow lights outside comfort band; else treat like dark window)

import time, random, datetime
from typing import Callable

# --- comfort band (lux, PPFD, etc.) ---
MIN_LIGHT         = 200         # grow lights top-up below this
MAX_LIGHT         = 350         # fine once above this
LIGHT_MIN_BOUND   = 0
LIGHT_MAX_BOUND   = 1000
LIGHT_INTERVAL          = 7           # seconds between PLC ticks

# --- photoperiod configuration ------------
DARK_START_HR     = 22          # 22:00 local  (lights forced OFF)
DARK_END_HR       = 6           # 06:00 local
LONG_DAY_HOURS    = 16          # desired total lit hours per 24 h
# ------------------------------------------

class LightPLC:
    """
    Grow-light controller with night-shutdown and long-day tracking.
    """

    def __init__(self,
                 sender: Callable[[dict], None],
                 *,
                 initial_light: float = (MIN_LIGHT + MAX_LIGHT) / 2,
                 natural_drift: float = 15.0,       # ±lux each tick
                 lamp_gain_100: float = 60.0):      # added lux per 100 % duty
        self.light = initial_light
        self.drift = natural_drift
        self.gain  = lamp_gain_100
        self.send  = sender

        # photoperiod bookkeeping
        self._lit_seconds_today = 0
        self._midnight_day_index = datetime.date.today()

    # ── helpers --------------------------------------------------------
    def _clock_now(self):
        return datetime.datetime.now()

    def _is_dark_window(self) -> bool:
        hr = self._clock_now().hour
        if DARK_START_HR < DARK_END_HR:            # same-day window
            return DARK_START_HR <= hr < DARK_END_HR
        else:                                      # window crosses midnight
            return hr >= DARK_START_HR or hr < DARK_END_HR

    def _reset_midnight_counter(self):
        today = datetime.date.today()
        if today != self._midnight_day_index:
            self._midnight_day_index = today
            self._lit_seconds_today = 0

    # ── physics each tick ---------------------------------------------
    def _ambient_variation(self):
        self.light += random.uniform(-self.drift, self.drift)

    def _apply_lamp_effect(self, pct: float):
        self.light += (pct / 100) * self.gain
        if pct > 0:                                # accumulate photoperiod
#            self._lit_seconds_today += INTERVAL
            self._lit_seconds_today += 3600
            
    # ── controller -----------------------------------------------------
    def _compute_power_pct(self) -> float:
        """Return grow-lamp duty cycle (0-100)."""

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
            span = MIN_LIGHT - LIGHT_MIN_BOUND or 1
            return min((deficit / span) * 100, 100)

        return 0.0

    # ── main loop ------------------------------------------------------
    def run(self, cycles: int | None = None):
        prev_power = 0.0
        tick = 0
        while cycles is None or tick < cycles:
            self._reset_midnight_counter()            # reset at midnight

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


# ──────────────── CO₂ Management PLC ────────────────
# Place below the other PLC classes in the same Python file.

import time, random, datetime
from typing import Callable

# ---------- configuration ----------
MIN_CO2          = 800          # ppm – dose CO₂ when below this (day-time)
MAX_CO2          = 1200         # ppm – vent when above this (any time)
CO2_MIN_BOUND    = 300          # outdoor ambient
CO2_MAX_BOUND    = 2000         # safety ceiling
CO2_INTERVAL     = 7            # seconds per control loop
DOSING_PERIOD    = 1            # dose check every N cycles (~35 s here)
DAY_START_HR     = 6            # 06:00 local
DAY_END_HR       = 18           # 18:00 local
# -----------------------------------

class CO2PLC:
    """
    Simulates a CO₂-dosing and vent-control PLC.

      • Every 7 s:
          - Natural plant effect: daytime photosynthesis ↓ CO₂,
                                   nighttime respiration ↑ CO₂
          - Adds previous pump dosing (raises ppm)
          - Removes previous vent opening (lowers ppm)
      • Doses only during daylight and only once each DOSING_PERIOD cycles.
      • Control payload:

          {
              "co2_ppm":   <float>,
              "pump_pct":  <float>,   # 0-100; dosing valve duty
              "vent_pct":  <float>,   # 0-100; vent opening
          }
    """

    def __init__(self,
                 sender: Callable[[dict], None],
                 initial_ppm: float = 900,
                 plant_day_sink: float = 8.0,     # ppm consumed each tick
                 plant_night_source: float = 15.0, # ppm produced each tick
                 pump_gain_100: float = 40.0,     # ppm added at 100 % duty
                 vent_loss_100: float = 60.0,     # ppm removed at 100 % duty
                 dosing_period: int = DOSING_PERIOD):
        self.ppm = initial_ppm
        self.day_sink = plant_day_sink
        self.night_src = plant_night_source
        self.pump_gain = pump_gain_100
        self.vent_loss = vent_loss_100
        self.send = sender
        self.dosing_period = max(dosing_period, 1)
        self._cycle = 0
        self._prev_pump = 0.0
        self._prev_vent = 0.0

    # ── helpers ──────────────────────────────────────────
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
        """Returns (pump_pct, vent_pct)."""
        pump_pct = vent_pct = 0.0

        # Venting priority if CO₂ too high
        if self.ppm > MAX_CO2:
            excess = self.ppm - MAX_CO2
            span   = CO2_MAX_BOUND - MAX_CO2 or 1
            vent_pct = min((excess / span) * 100, 100)
            return 0.0, vent_pct

        # Dosing allowed only during daylight & on dosing period ticks
        if self._is_daytime() and self._cycle % self.dosing_period == 0 \
                               and self.ppm < MIN_CO2:
            deficit = MIN_CO2 - self.ppm
            span    = MIN_CO2 - CO2_MIN_BOUND or 1
            pump_pct = min((deficit / span) * 100, 100)

        return pump_pct, 0.0
    # -----------------------------------------------------

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


# ───────────────────── demo harness (optional) ─────────────────────
if __name__ == "__main__":
    CYCLES = 40                        # how long each worker PLC runs

    plc1 = PLC1()
    workers = [
        TemperaturePLC(sender=plc1.sender_for("temp")),
        IrrigationPLC(sender=plc1.sender_for("irrigation")),
        LightPLC(sender=plc1.sender_for("light")),
        CO2PLC(sender=plc1.sender_for("co2")),
    ]

    threads = [
        threading.Thread(target=w.run, kwargs={"cycles": CYCLES})
        for w in workers
    ] + [threading.Thread(target=plc1.run, daemon=True)]

    try:
        for t in threads: t.start()
        for t in threads[:-1]: t.join()    # wait only for the worker PLCs
        print("Simulation finished.")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up threads...")
    except Exception as e:
        print(f"Error occurred: {e}. Cleaning up threads...")
    finally:
        # Ensure threads are cleaned up
        for t in threads:
            if t.is_alive():
                try:
                    t.join(timeout=1.0)
                except:
                    pass