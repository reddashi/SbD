import time
import random
import threading

MIN_TEMP = 24.0
MAX_TEMP = 28.0
TEMP_CHANGE_RATE = 0.1  # degrees per second

class TemperaturePLC:
    def __init__(self, sender=None):
        self.current_temp = 0.0
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False

        threading.Thread(target=self.live_loop, daemon=True).start()

    def live_loop(self):
        time.sleep(3)  # sensor warm-up
        self.current_temp = random.uniform(MIN_TEMP, MAX_TEMP)
        self.sensor_online = True

        while self.running:
            if self.sensor_online:
                # Apply actuator effects first
                if self.heater_pct > 0:
                    self.current_temp += TEMP_CHANGE_RATE * (self.heater_pct / 100)
                elif self.cooler_pct > 0:
                    self.current_temp -= TEMP_CHANGE_RATE * (self.cooler_pct / 100)
                else:
                    if self.direction is None:
                        self.direction = random.choice([0, 1])

                    if self.direction == 0:
                        self.current_temp -= TEMP_CHANGE_RATE
                    else:
                        self.current_temp += TEMP_CHANGE_RATE

                # Clamp temperature
                self.current_temp = max(MIN_TEMP - 5, min(MAX_TEMP + 5, self.current_temp))

                # Update actuators based on new temperature
                if self.current_temp < MIN_TEMP:
                    self.heater_pct = 100
                    self.cooler_pct = 0
                    self.direction = None
                elif self.current_temp > MAX_TEMP:
                    self.heater_pct = 0
                    self.cooler_pct = 100
                    self.direction = None
                else:
                    self.heater_pct = 0
                    self.cooler_pct = 0
                    if self.direction is None:
                        self.direction = random.choice([0, 1])

                # Send sensor & actuator data
                self.sender({
                    "temperature": round(self.current_temp, 2),
                    "heater_pct": self.heater_pct,
                    "cooler_pct": self.cooler_pct
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

__all__ = ['TemperaturePLC', 'MIN_TEMP', 'MAX_TEMP']
