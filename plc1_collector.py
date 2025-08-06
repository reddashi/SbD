import threading
import time
import json
from gh import (
    TemperaturePLC, IrrigationPLC, LightPLC, CO2PLC,
    MIN_TEMP, MAX_TEMP,
    MIN_MOISTURE, MAX_MOISTURE,
    MIN_LIGHT, MAX_LIGHT,
    MIN_CO2, MAX_CO2
)

# Use thresholds from gh.py to avoid duplication
THRESHOLDS = {
    'temp': (MIN_TEMP, MAX_TEMP),
    'irrigation': (MIN_MOISTURE, MAX_MOISTURE),
    'light': (MIN_LIGHT, MAX_LIGHT),
    'co2': (MIN_CO2, MAX_CO2),
}

# Capture sensor values from each PLC
sensor_values = {
    "temp": None,
    "irrigation": None,
    "light": None,
    "co2": None
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
        value = (
            val.get("temperature") if key == "temp" else
            val.get("moisture") if key == "irrigation" else
            val.get("light") if key == "light" else
            val.get("co2_ppm")
        )
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
        IrrigationPLC(sender=get_sender("irrigation")),
        LightPLC(sender=get_sender("light")),
        CO2PLC(sender=get_sender("co2")),
    ]

    while True:
        threads = [threading.Thread(target=run_once, args=(w,)) for w in workers]
        for t in threads: t.start()
        for t in threads: t.join()

        output = {
            "sensors": {
                "temperature": sensor_values["temp"]["temperature"],
                "humidity": sensor_values["irrigation"]["moisture"],
                "light": sensor_values["light"]["light"],
                "co2": sensor_values["co2"]["co2_ppm"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "actuators": {
                "heater_pct": sensor_values["temp"]["heater_pct"],
                "cooler_pct": sensor_values["temp"]["cooler_pct"],
                "pump_pct": sensor_values["irrigation"]["pump_pct"],
                "drain_pct": sensor_values["irrigation"]["drain_pct"],
                "grow_power_pct": sensor_values["light"]["grow_power_pct"],
                "co2_pump_pct": sensor_values["co2"]["pump_pct"],
                "co2_vent_pct": sensor_values["co2"]["vent_pct"]
            },
            "alerts": check_alerts()
        }

        print(json.dumps(output), flush=True)
        time.sleep(2)