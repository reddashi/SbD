import time
import random
import threading

# Thresholds for temperature band
TEMP_LOWER = 22.0
TEMP_UPPER = 28.0
TEMP_CHANGE_RATE = 0.5  # degrees per second

class TemperaturePLC:
    def __init__(self):
        self.current_temp = random.uniform(TEMP_LOWER, TEMP_UPPER)
        self.heater_pct = 0
        self.cooler_pct = 0
        self.direction = random.choice([0, 1])  # 0 = cooling, 1 = heating
        self.running = True
        threading.Thread(target=self.simulate, daemon=True).start()

    def simulate(self):
        while self.running:
            if self.heater_pct == 0 and self.cooler_pct == 0:
                if self.direction == 0:
                    self.current_temp -= TEMP_CHANGE_RATE
                else:
                    self.current_temp += TEMP_CHANGE_RATE
            else:
                # Actuator is active; reset toss for next idle period
                self.direction = random.choice([0, 1])

            print(f"[TempPLC] Temp: {self.current_temp:.2f}°C | "
                  f"Dir: {'Cooling' if self.direction == 0 else 'Heating'} | "
                  f"Heater: {self.heater_pct}% | Cooler: {self.cooler_pct}%")
            time.sleep(1)

    def set_actuators(self, heater_pct=0, cooler_pct=0):
        self.heater_pct = heater_pct
        self.cooler_pct = cooler_pct

    def get_status(self):
        return {
            "temp": round(self.current_temp, 2),
            "heater_pct": self.heater_pct,
            "cooler_pct": self.cooler_pct
        }

# Exportable items for external use
__all__ = ['TemperaturePLC', 'TEMP_LOWER', 'TEMP_UPPER']
