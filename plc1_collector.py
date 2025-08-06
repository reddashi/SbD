import threading
import time
import json
from temp_plc import TemperaturePLC, MIN_TEMP, MAX_TEMP



# Use thresholds from gh.py to avoid duplication
THRESHOLDS = {
    'temp': (MIN_TEMP, MAX_TEMP),
    #'irrigation': (MIN_MOISTURE, MAX_MOISTURE),
   # 'light': (MIN_LIGHT, MAX_LIGHT),
   # 'co2': (MIN_CO2, MAX_CO2),
}

# Capture sensor values from each PLC
sensor_values = {
    "temp": None,
   # "irrigation": None,
   # "light": None,
   # "co2": None
}

# Output dictionary
result_data = {
    "sensors": {},
    "actuators": {},
    "alerts": {}
}

# --- Sender function to collect each PLC's output ---
def get_sender(key):
    def _send(msg):
        sensor_values[key] = msg
    return _send

def check_alerts():
    alerts = {}
    for key, val in sensor_values.items():
        if val is None:
            continue
        low, high = THRESHOLDS[key]

        if key == "temp":
            value = val.get("temperature")
        else:
            value = 0  # Default fallback for other sensor types if added later

        if not (low <= value <= high):
            alerts[key] = {
                "value": value,
                "status": "ALERT",
                "target": f"PLC for {key}"
            }
    return alerts

def run_once(plc):
    plc.run(cycles=1)

if __name__ == "__main__":
    workers = [
        TemperaturePLC(sender=get_sender("temp")),
        #IrrigationPLC(sender=get_sender("irrigation")),
        #LightPLC(sender=get_sender("light")),
        #CO2PLC(sender=get_sender("co2")),
    ]

    while True:
        threads = [threading.Thread(target=run_once, args=(w,)) for w in workers]
        for t in threads: t.start()
        for t in threads: t.join()

        output = {
            "sensors": {
            "temperature": sensor_values["temp"]["temperature"] if sensor_values["temp"] else 0.0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
            "actuators": {
            "heater_pct": sensor_values["temp"]["heater_pct"] if sensor_values["temp"] else 0,
            "cooler_pct": sensor_values["temp"]["cooler_pct"] if sensor_values["temp"] else 0,
        },
        "alerts": check_alerts()
        }


        print(json.dumps(output), flush=True)
        time.sleep(1)