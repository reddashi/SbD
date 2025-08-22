import time
import random
import threading

# Threshold range (target light levels in lux)
MIN_LIGHT = 400.0
MAX_LIGHT = 600.0

# Extended simulation range (can drift beyond)
MIN_LIGHT_EXT = 0.0
MAX_LIGHT_EXT = 1000.0

# Lux change per second
LIGHT_CHANGE_RATE = 25.0

class LightPLC:
    def __init__(self, sender=None, overrides=None):
        self.current_light = 500.0  # Start in the middle
        self.lamp_pct = 0           # 0–100% power for lamp
        self.shutter_pct = 0        # 0–100% for blocking light
        self.direction = random.choice([0, 1])  # 0 = down, 1 = up
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False
        self.overrides = overrides if overrides is not None else {}

        threading.Thread(target=self._live_loop, daemon=True).start()

    def _live_loop(self):
        time.sleep(0.1)  # Sensor warm-up
        self.sensor_online = True
        target_light = (MIN_LIGHT + MAX_LIGHT) / 2  # = 500 lux

        while self.running:
            if self.sensor_online:
                # Apply override if exists
                if "light" in self.overrides:
                    self.current_light = float(self.overrides["light"])
                else:
                    # ACTUATOR CONTROL: return to middle if out of range
                    if self.lamp_pct > 0:
                        self.current_light += LIGHT_CHANGE_RATE 
                        if self.current_light >= target_light:
                            self.lamp_pct = 0
                            self.direction = random.choice([0, 1])

                    elif self.shutter_pct > 0:
                        self.current_light -= LIGHT_CHANGE_RATE 
                        if self.current_light <= target_light:
                            self.shutter_pct = 0
                            self.direction = random.choice([0, 1])

                    else:
                        # No actuator: simulate environment drift
                        if self.direction == 0:
                            self.current_light -= LIGHT_CHANGE_RATE
                        else:
                            self.current_light += LIGHT_CHANGE_RATE
                        
                # OUT OF THRESHOLD: activate actuator
                if self.current_light < MIN_LIGHT - 25:
                    diff = (MIN_LIGHT - self.current_light)
                    self.lamp_pct = min(100, diff - 15)
                    self.shutter_pct = 0
                    self.direction = None
                elif self.current_light > MAX_LIGHT + 25:
                    diff = self.current_light - (MAX_LIGHT)
                    self.shutter_pct = min(100, diff - 15)
                    self.lamp_pct = 0
                    self.direction = None

                # Clamp to sim limits
                self.current_light = max(MIN_LIGHT_EXT, min(MAX_LIGHT_EXT, self.current_light))

                # Send updated sensor + actuator values
                self.sender({
                    "light": round(self.current_light, 0),
                    "lamp_pct": round(self.lamp_pct, 0),
                    "shutter_pct": round(self.shutter_pct, 0)
                })

            else:
                # If sensor offline
                self.sender({
                    "light": 0.0,
                    "lamp_pct": 0,
                    "shutter_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass  

__all__ = ['LightPLC', 'MIN_LIGHT', 'MAX_LIGHT', 'MIN_LIGHT_EXT', 'MAX_LIGHT_EXT']
