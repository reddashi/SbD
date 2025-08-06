import time
import random
import threading

# Threshold range (target values to maintain)
MIN_TEMP = 24.0
MAX_TEMP = 28.0

# Extended simulation range (can drift beyond)
MIN_TEMP_EXT = 0.0
MAX_TEMP_EXT = 50.0

# Degrees per second
TEMP_CHANGE_RATE = 0.1

class TemperaturePLC:
    def __init__(self, sender=None):
        self.current_temp = 26.0  # ✅ Start in the middle
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])  # 0 = down, 1 = up
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False

        threading.Thread(target=self._live_loop, daemon=True).start()

    def _live_loop(self):
        time.sleep(3)  # Sensor warm-up
        self.sensor_online = True
        target_temp = (MIN_TEMP + MAX_TEMP) / 2  # = 26.0°C

        while self.running:
            if self.sensor_online:
                # ACTUATOR CONTROL: return to middle if out of range
                if self.heater_pct > 0:
                    self.current_temp += TEMP_CHANGE_RATE * (self.heater_pct / 100)
                    if self.current_temp >= target_temp:
                        self.heater_pct = 0
                        self.direction = random.choice([0, 1])

                elif self.cooler_pct > 0:
                    self.current_temp -= TEMP_CHANGE_RATE * (self.cooler_pct / 100)
                    if self.current_temp <= target_temp:
                        self.cooler_pct = 0
                        self.direction = random.choice([0, 1])

                else:
                    # No actuator: simulate environment drift
                    if self.direction == 0:
                        self.current_temp -= TEMP_CHANGE_RATE
                    else:
                        self.current_temp += TEMP_CHANGE_RATE

                # OUT OF THRESHOLD: activate actuator
                if self.current_temp < MIN_TEMP - 0.2 :
                    self.heater_pct = 100
                    self.cooler_pct = 0
                    self.direction = None
                elif self.current_temp > MAX_TEMP + 0.2 :
                    self.cooler_pct = 100
                    self.heater_pct = 0
                    self.direction = None

                # Clamp to sim limits
                self.current_temp = max(MIN_TEMP_EXT, min(MAX_TEMP_EXT, self.current_temp))

                # Send updated sensor + actuator values
                self.sender({
                    "temperature": round(self.current_temp, 2),
                    "heater_pct": self.heater_pct,
                    "cooler_pct": self.cooler_pct
                })

            else:
                # If sensor offline
                self.sender({
                    "temperature": 0.0,
                    "heater_pct": 0,
                    "cooler_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass  # Not used

__all__ = ['TemperaturePLC', 'MIN_TEMP', 'MAX_TEMP', 'MIN_TEMP_EXT', 'MAX_TEMP_EXT']
