import time
import random
import threading

# Thresholds for soil moisture (in %)
MIN_MOISTURE = 30.0
MAX_MOISTURE = 70.0

# Extended moisture range (simulate drift)
MIN_MOISTURE_EXT = 0.0
MAX_MOISTURE_EXT = 100.0

MOISTURE_CHANGE_RATE = 1.0  # % per second

class IrrigationPLC:
    def __init__(self, sender=None):
        self.current_moisture = 50.0  # Start mid-range
        self.pump_pct = 0
        self.drain_pct = 0
        self.direction = random.choice([0, 1])  # 0 = drying, 1 = moistening
        self.sender = sender or (lambda data: None)
        self.running = True
        self.sensor_online = False

        threading.Thread(target=self.live_loop, daemon=True).start()

    def moisture_to_power_smooth(moisture, max_val, min_val):
        target = (min_val + max_val) / 2.0  # midpoint

        # Too wet -> drain
        if moisture > max_val:
            diff = moisture - target
            scale = max_val - target  # how far from target to max_val
            pct = 100 * math.exp(- (diff - scale) / scale)  # smooth drop
            return -min(100, max(0, round(pct)))

        # Too dry -> pump
        elif moisture < min_val:
            diff = target - moisture
            scale = target - min_val
            pct = 100 * math.exp(- (diff - scale) / scale)
            return min(100, max(0, round(pct)))

        # In range
        return 0

    def live_loop(self):
        time.sleep(0.1)
        self.sensor_online = True

        middle_moisture = (MIN_MOISTURE + MAX_MOISTURE) / 2  # Target middle

        while self.running:
            if self.sensor_online:
                # Apply actuator effects
                if self.pump_pct > 0:
                    self.current_moisture += MOISTURE_CHANGE_RATE 
                    if self.current_moisture >= middle_moisture:
                        self.pump_pct = 0
                        self.direction = random.choice([0, 1])
                elif self.drain_pct > 0:
                    self.current_moisture -= MOISTURE_CHANGE_RATE 
                    if self.current_moisture <= middle_moisture:
                        self.drain_pct = 0
                        self.direction = random.choice([0, 1])
                else:
                    # Drift naturally if no actuator active
                    if self.direction is None:
                        self.direction = random.choice([0, 1])
                    if self.direction == 0:
                        self.current_moisture -= MOISTURE_CHANGE_RATE
                    else:
                        self.current_moisture += MOISTURE_CHANGE_RATE

                # Actuator trigger logic
                if self.current_moisture < MIN_MOISTURE - 5:
                     # Calculate proportional power based on how far from MIN_MOISTURE
                    diff = (MIN_MOISTURE - self.current_moisture)
                    self.pump_pct = min(100, diff + 29)  # each 0.1 difference adds ~1% power
                    self.drain_pct = 0
                    self.direction = None
                elif self.current_moisture > MAX_MOISTURE + 5:
                     # Calculate proportional power based on how far from MAX_MOISTURE
                    diff = self.current_moisture - (MAX_MOISTURE)
                    self.pump_pct = 0
                    self.drain_pct = min(100, diff + 29)
                    self.direction = None

                # Clamp values
                self.current_moisture = max(MIN_MOISTURE_EXT, min(MAX_MOISTURE_EXT, self.current_moisture))

                # Send status
                self.sender({
                    "moisture": round(self.current_moisture, 2),
                    "pump_pct": self.pump_pct,
                    "drain_pct": self.drain_pct
                })
            else:
                # Sensor offline fallback
                self.sender({
                    "moisture": 0.0,
                    "pump_pct": 0,
                    "drain_pct": 0
                })

            time.sleep(1)

    def run(self, cycles=1):
        pass
