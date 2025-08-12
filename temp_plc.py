import time
import random
import threading

# Threshold range (target values to maintain)
MIN_TEMP = 24.0
MAX_TEMP = 28.0

# Extended simulation range
MIN_TEMP_EXT = 0.0
MAX_TEMP_EXT = 50.0

TEMP_CHANGE_RATE = 0.1

class TemperaturePLC:
    def __init__(self, sender=None, overrides=None):
        self.current_temp = 26.0
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False
        self.overrides = overrides if overrides is not None else {}

        threading.Thread(target=self._live_loop, daemon=True).start()

    def _live_loop(self):
        time.sleep(0.1)
        self.sensor_online = True
        target_temp = (MIN_TEMP + MAX_TEMP) / 2

        while self.running:
            if self.sensor_online:
                # Apply override if exists
                if "temperature" in self.overrides:
                    self.current_temp = float(self.overrides["temperature"])
                else:
                    # Normal actuator/environment logic
                    if self.heater_pct > 0:
                        self.current_temp += TEMP_CHANGE_RATE
                        if self.current_temp >= target_temp:
                            self.heater_pct = 0
                            self.direction = random.choice([0, 1])
                    elif self.cooler_pct > 0:
                        self.current_temp -= TEMP_CHANGE_RATE
                        if self.current_temp <= target_temp:
                            self.cooler_pct = 0
                            self.direction = random.choice([0, 1])
                    else:
                        if self.direction == 0:
                            self.current_temp -= TEMP_CHANGE_RATE
                        else:
                            self.current_temp += TEMP_CHANGE_RATE

                # Actuator logic still applies even if overridden
                if self.current_temp < MIN_TEMP - 0.5:
                    diff = (MIN_TEMP - self.current_temp)
                    self.heater_pct = min(100, diff + 34.5)
                    self.cooler_pct = 0
                    self.direction = None
                elif self.current_temp > MAX_TEMP + 0.5:
                    diff = self.current_temp - (MAX_TEMP)
                    self.cooler_pct = min(100, diff + 34.5)
                    self.heater_pct = 0
                    self.direction = None

                self.current_temp = max(MIN_TEMP_EXT, min(MAX_TEMP_EXT, self.current_temp))

                self.sender({
                    "temperature": round(self.current_temp, 2),
                    "heater_pct": round(self.heater_pct, 1),
                    "cooler_pct": round(self.cooler_pct, 1)
                })

            else:
                self.sender({
                    "temperature": 0.0,
                    "heater_pct": 0,
                    "cooler_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass
