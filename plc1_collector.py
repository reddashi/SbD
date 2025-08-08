import threading
import time
import json
from temp_plc import TemperaturePLC, MIN_TEMP, MAX_TEMP
from light_plc import LightPLC, MIN_LIGHT, MAX_LIGHT  

# Thresholds
THRESHOLDS = {
    'temp': (MIN_TEMP, MAX_TEMP),
    'light': (MIN_LIGHT, MAX_LIGHT),
}

# Store latest sensor values
sensor_values = {
    "temp": None,
    "light": None,
}

# --- Sender function to collect each PLC's output ---
def get_sender(key):
    def _send(msg):
        sensor_values[key] = msg
    return _send

# Check for alerts based on thresholds
def check_alerts():
    alerts = {}
    for key, val in sensor_values.items():
        if val is None:
            continue
        low, high = THRESHOLDS[key]

        if key == "temp":
            value = val.get("temperature")
        elif key == "light":
            value = val.get("light")
        else:
            value = 0  # Fallback if new sensor type added later

        if not (low <= value <= high):
            alerts[key] = {
                "value": value,
                "status": "ALERT",
                "target": f"PLC for {key}"
            }
    return alerts

def run_once(plc):
    plc.run(cycles=1)  # This does nothing but is kept for compatibility

if __name__ == "__main__":
    workers = [
        TemperaturePLC(sender=get_sender("temp")),
        LightPLC(sender=get_sender("light")),
    ]

    while True:
        # In case run() gets used in future
        threads = [threading.Thread(target=run_once, args=(w,)) for w in workers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        output = {
            "sensors": {
                "temperature": sensor_values["temp"]["temperature"] if sensor_values["temp"] else 0.0,
                "light": sensor_values["light"]["light"] if sensor_values["light"] else 0.0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "actuators": {
                "heater_pct": sensor_values["temp"]["heater_pct"] if sensor_values["temp"] else 0,
                "cooler_pct": sensor_values["temp"]["cooler_pct"] if sensor_values["temp"] else 0,
                "lamp_pct": sensor_values["light"]["lamp_pct"] if sensor_values["light"] else 0,
                "shutter_pct": sensor_values["light"]["shutter_pct"] if sensor_values["light"] else 0,
            },
            "alerts": check_alerts()
        }

        print(json.dumps(output), flush=True)
        time.sleep(1)
