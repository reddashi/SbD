import threading
import time
import json

from temp_plc import TemperaturePLC, MIN_TEMP, MAX_TEMP
from light_plc import LightPLC, MIN_LIGHT, MAX_LIGHT
from irr_plc import IrrigationPLC, MIN_MOISTURE, MAX_MOISTURE
from co2_plc import CO2PLC, MIN_CO2, MAX_CO2

# Thresholds for all sensors
THRESHOLDS = {
    'temp': (MIN_TEMP, MAX_TEMP),
    'light': (MIN_LIGHT, MAX_LIGHT),
    'irrigation': (MIN_MOISTURE, MAX_MOISTURE),
    'co2': (MIN_CO2, MAX_CO2),
}

# Store latest sensor values from each PLC
sensor_values = {
    "temp": None,
    "light": None,
    "irrigation": None,
    "co2": None,
}

# Sender factory for each PLC
def get_sender(key):
    def _send(msg):
        sensor_values[key] = msg
    return _send

# Check sensor values vs thresholds and generate alerts
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
        elif key == "irrigation":
            value = val.get("moisture")
        elif key == "co2":
            value = val.get("co2")
        else:
            value = 0

        if value is None:
            continue

        if not (low <= value <= high):
            alerts[key] = {
                "value": value,
                "status": "ALERT",
                "target": f"PLC for {key}"
            }
    return alerts

def run_once(plc):
    plc.run(cycles=1)  # For compatibility, no-op in current PLC classes

if __name__ == "__main__":
    workers = [
        TemperaturePLC(sender=get_sender("temp")),
        LightPLC(sender=get_sender("light")),
        IrrigationPLC(sender=get_sender("irrigation")),
        CO2PLC(sender=get_sender("co2")),
    ]

    while True:
        threads = [threading.Thread(target=run_once, args=(w,)) for w in workers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        output = {
            "sensors": {
                "temperature": sensor_values["temp"]["temperature"] if sensor_values["temp"] else 0.0,
                "light": sensor_values["light"]["light"] if sensor_values["light"] else 0.0,
                "moisture": sensor_values["irrigation"]["moisture"] if sensor_values["irrigation"] else 0.0,
                "co2": sensor_values["co2"]["co2"] if sensor_values["co2"] else 0.0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "actuators": {
                "heater_pct": sensor_values["temp"]["heater_pct"] if sensor_values["temp"] else 0,
                "cooler_pct": sensor_values["temp"]["cooler_pct"] if sensor_values["temp"] else 0,
                "lamp_pct": sensor_values["light"]["lamp_pct"] if sensor_values["light"] else 0,
                "shutter_pct": sensor_values["light"]["shutter_pct"] if sensor_values["light"] else 0,
                "pump_pct": sensor_values["irrigation"]["pump_pct"] if sensor_values["irrigation"] else 0,
                "drain_pct": sensor_values["irrigation"]["drain_pct"] if sensor_values["irrigation"] else 0,
                "co2_pump_pct": sensor_values["co2"]["co2_pump_pct"] if sensor_values["co2"] else 0,
                "co2_vent_pct": sensor_values["co2"]["co2_vent_pct"] if sensor_values["co2"] else 0,
            },
            "alerts": check_alerts()
        }

        print(json.dumps(output), flush=True)
        time.sleep(0.1)
