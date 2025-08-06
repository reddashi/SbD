import time
import random
import threading

TEMP_LOWER = 22.0
TEMP_UPPER = 28.0
TEMP_CHANGE_RATE = 0.5

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
                # If actuator is active, reset direction for next cycle
                self.direction = random.choice([0, 1])
            print(f"[TempPLC] Temp: {self.current_temp:.2f}°C | Dir: {'Cooling' if self.direction == 0 else 'Heating'} | Heater: {self.heater_pct}% | Cooler: {self.cooler_pct}%")
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

if __name__ == "__main__":
    plc = TemperaturePLC()

    try:
        while True:
            # Example actuator trigger logic for test/demo:
            temp = plc.current_temp

            # simulate actuator commands
            if temp > TEMP_UPPER:
                plc.set_actuators(heater_pct=0, cooler_pct=100)
            elif temp < TEMP_LOWER:
                plc.set_actuators(heater_pct=100, cooler_pct=0)
            else:
                plc.set_actuators(heater_pct=0, cooler_pct=0)

            time.sleep(1)

    except KeyboardInterrupt:
        plc.running = False
        print("Temperature PLC stopped.")

__all__ = ['TemperaturePLC', 'TEMP_LOWER', 'TEMP_UPPER']