import time
import random
import threading

# Thresholds for actuator logic (target range)
MIN_TEMP = 24.0
MAX_TEMP = 28.0

# Extended temperature simulation range (drift can go up to these)
MIN_TEMP_EXT = 0.0
MAX_TEMP_EXT = 50.0

TEMP_CHANGE_RATE = 0.5  # Degrees per second

class TemperaturePLC:
    def __init__(self, sender=None):
        self.current_temp = 0.0
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])  # 0 = down, 1 = up
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False

        threading.Thread(target=self.live_loop, daemon=True).start()

    def live_loop(self):
        # Sensor warm-up
        time.sleep(3)
        self.current_temp = random.uniform(MIN_TEMP, MAX_TEMP)
        self.sensor_online = True

        middle_temp = (MIN_TEMP + MAX_TEMP) / 2  # Target: 26.0°C

        while self.running:
            if self.sensor_online:
                # Step 1: Apply actuator effects
                if self.heater_pct > 0:
                    self.current_temp += TEMP_CHANGE_RATE * (self.heater_pct / 100)
                    if self.current_temp >= middle_temp:
                        self.heater_pct = 0
                        self.direction = random.choice([0, 1])

                elif self.cooler_pct > 0:
                    self.current_temp -= TEMP_CHANGE_RATE * (self.cooler_pct / 100)
                    if self.current_temp <= middle_temp:
                        self.cooler_pct = 0
                        self.direction = random.choice([0, 1])

                else:
                    # Step 2: Drift if no actuator is active
                    if self.direction is None:
                        self.direction = random.choice([0, 1])
                    if self.direction == 0:
                        self.current_temp -= TEMP_CHANGE_RATE
                    else:
                        self.current_temp += TEMP_CHANGE_RATE

                # Step 3: Trigger actuators if out of threshold
                if self.current_temp < MIN_TEMP:
                    self.heater_pct = 100
                    self.cooler_pct = 0
                    self.direction = None
                elif self.current_temp > MAX_TEMP:
                    self.heater_pct = 0
                    self.cooler_pct = 100
                    self.direction = None

                # Step 4: Clamp to simulation limits
                self.current_temp = max(MIN_TEMP_EXT, min(MAX_TEMP_EXT, self.current_temp))

                # Step 5: Send values
                self.sender({
                    "temperature": round(self.current_temp, 2),
                    "heater_pct": self.heater_pct,
                    "cooler_pct": self.cooler_pct
                })
            else:
                # Sensor offline
                self.sender({
                    "temperature": 0.0,
                    "heater_pct": 0,
                    "cooler_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass  # Compatibility; not used in live simulation

# For import
__all__ = ['TemperaturePLC', 'MIN_TEMP', 'MAX_TEMP', 'MIN_TEMP_EXT', 'MAX_TEMP_EXT']
