import threading
import time
import json
import sys
import queue
import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from temp_plc import TemperaturePLC, MIN_TEMP, MAX_TEMP
from light_plc import LightPLC, MIN_LIGHT, MAX_LIGHT
from irr_plc import IrrigationPLC, MIN_MOISTURE, MAX_MOISTURE
from co2_plc import CO2PLC, MIN_CO2, MAX_CO2

# InfluxDB setup (token from env)
token = os.environ.get("INFLUXDB_TOKEN")
org = "SUTD"
bucket = "greenhouse"
url = "http://localhost:8086"

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Thresholds for all sensors
THRESHOLDS = {
    'temp': (MIN_TEMP, MAX_TEMP),
    'light': (MIN_LIGHT, MAX_LIGHT),
    'irrigation': (MIN_MOISTURE, MAX_MOISTURE),
    'co2': (MIN_CO2, MAX_CO2),
}

sensor_values = {
    "temp": None,
    "light": None,
    "irrigation": None,
    "co2": None,
}

overrides = {}
command_queue = queue.Queue()

def get_sender(key):
    def _send(msg):
        sensor_values[key] = msg
    return _send

def stdin_listener():
    for line in sys.stdin:
        try:
            cmd = json.loads(line.strip())
            if cmd["type"] == "override":
                overrides[cmd["sensor"]] = cmd["value"]
            elif cmd["type"] == "clear_override":
                overrides.pop(cmd["sensor"], None)
        except Exception as e:
            print(f"STDIN error: {e}", file=sys.stderr)

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
    plc.run(cycles=1)

if __name__ == "__main__":
    threading.Thread(target=stdin_listener, daemon=True).start()

    workers = [
        TemperaturePLC(sender=get_sender("temp"), overrides=overrides),
        LightPLC(sender=get_sender("light"), overrides=overrides),
        IrrigationPLC(sender=get_sender("irrigation"), overrides=overrides),
        CO2PLC(sender=get_sender("co2"), overrides=overrides),
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

        point = (
            Point("greenhouse")
            .tag("location", "greenhouse_room_1")
            .field("temperature", float(output["sensors"]["temperature"]))
            .field("heater_pct", float(output["actuators"]["heater_pct"]))
            .field("cooler_pct", float(output["actuators"]["cooler_pct"]))
            .field("light", float(output["sensors"]["light"]))
            .field("lamp_pct", float(output["actuators"]["lamp_pct"]))
            .field("shutter_pct", float(output["actuators"]["shutter_pct"]))
            .field("moisture", float(output["sensors"]["moisture"]))
            .field("pump_pct", float(output["actuators"]["pump_pct"]))
            .field("drain_pct", float(output["actuators"]["drain_pct"]))
            .field("co2", float(output["sensors"]["co2"]))
            .field("co2_pump_pct", float(output["actuators"]["co2_pump_pct"]))
            .field("co2_vent_pct", float(output["actuators"]["co2_vent_pct"]))
            .field("alerts_count", int(len(output["alerts"])))  # <--- as int
            .time(time.time_ns(), WritePrecision.NS)
        )

        write_api.write(bucket=bucket, org=org, record=point)

        print(json.dumps(output), flush=True)
        time.sleep(0.1)
