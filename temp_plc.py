import time
import random

TEMP_LOWER = 22.0
TEMP_UPPER = 28.0
TEMP_CHANGE_RATE = 0.5  # degrees per second

class TemperaturePLC:
    def __init__(self, sender=None):
        self.current_temp = random.uniform(TEMP_LOWER, TEMP_UPPER)
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])  # 0 = cooling, 1 = heating
        self.sender = sender or (lambda data: None)

    def run(self, cycles=1):
        for _ in range(cycles):
            if self.heater_pct == 0 and self.cooler_pct == 0:
                # Random walk according to direction
                if self.direction == 0:
                    self.current_temp -= TEMP_CHANGE_RATE
                else:
                    self.current_temp += TEMP_CHANGE_RATE
            else:
                # Reset direction if actuators are working
                self.direction = random.choice([0, 1])

            # Automatic heater/cooler response
            if self.current_temp > TEMP_UPPER:
                self.heater_pct = 0
                self.cooler_pct = 100
            elif self.current_temp < TEMP_LOWER:
                self.heater_pct = 100
                self.cooler_pct = 0
            else:
                self.heater_pct = 0
                self.cooler_pct = 0

            # Send sensor and actuator values
            self.sender({
                "temperature": round(self.current_temp, 2),
                "heater_pct": self.heater_pct,
                "cooler_pct": self.cooler_pct
            })

            time.sleep(1)

__all__ = ['TemperaturePLC', 'TEMP_LOWER', 'TEMP_UPPER']
