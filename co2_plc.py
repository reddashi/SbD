import time
import random
import threading

# Thresholds for CO2 (in ppm)
MIN_CO2 = 400
MAX_CO2 = 700

# Extended CO2 range (simulate drift)
MIN_CO2_EXT = 0
MAX_CO2_EXT = 1000

CO2_CHANGE_RATE = 30  # ppm per second

class CO2PLC:
    def __init__(self, sender=None, overrides=None):
        self.current_co2 = 550  # Start mid-range
        self.co2_pump_pct = 0
        self.co2_vent_pct = 0
        self.direction = random.choice([0, 1])  # 0 = dropping CO2, 1 = increasing CO2
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False
        self.overrides = overrides if overrides is not None else {}

        threading.Thread(target=self.live_loop, daemon=True).start()

    def live_loop(self):
        time.sleep(0.1)
        self.sensor_online = True

        middle_co2 = (MIN_CO2 + MAX_CO2) / 2  # Target mid CO2

        while self.running:
            if self.sensor_online:
                # Apply override if exists
                if "co2" in self.overrides:
                    self.current_co2 = float(self.overrides["co2"])
                else:
                    # Actuator effects
                    if self.co2_pump_pct > 0:
                        self.current_co2 += CO2_CHANGE_RATE 
                        if self.current_co2 >= middle_co2:
                            self.co2_pump_pct = 0
                            self.direction = random.choice([0, 1])
                    elif self.co2_vent_pct > 0:
                        self.current_co2 -= CO2_CHANGE_RATE
                        if self.current_co2 <= middle_co2:
                            self.co2_vent_pct = 0
                            self.direction = random.choice([0, 1])
                    else:
                        # Natural drift
                        if self.direction is None:
                            self.direction = random.choice([0, 1])
                        if self.direction == 0:
                            self.current_co2 -= CO2_CHANGE_RATE
                        else:
                            self.current_co2 += CO2_CHANGE_RATE

                # Actuator trigger
                if self.current_co2 < MIN_CO2 - 30:
                    diff = (MIN_CO2 - self.current_co2)
                    self.co2_pump_pct = min(100, diff - 25)
                    self.co2_vent_pct = 0
                    self.direction = None
                elif self.current_co2 > MAX_CO2 + 30:
                    diff = self.current_co2 - (MAX_CO2)
                    self.co2_pump_pct = 0
                    self.co2_vent_pct = min(100, diff - 25)
                    self.direction = None

                # Clamp
                self.current_co2 = max(MIN_CO2_EXT, min(MAX_CO2_EXT, self.current_co2))

                self.sender({
                    "co2": round(self.current_co2, 2),
                    "co2_pump_pct": self.co2_pump_pct,
                    "co2_vent_pct": self.co2_vent_pct
                })
            else:
                self.sender({
                    "co2": 0.0,
                    "co2_pump_pct": 0,
                    "co2_vent_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass
