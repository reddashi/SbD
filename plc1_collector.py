# plc1_collector.py
import threading
import time
import json
import sys
import os
import random
 
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
 
from temp_plc import TemperaturePLC, MIN_TEMP, MAX_TEMP
from light_plc import LightPLC, MIN_LIGHT, MAX_LIGHT
from irr_plc import IrrigationPLC, MIN_MOISTURE, MAX_MOISTURE
from co2_plc import CO2PLC, MIN_CO2, MAX_CO2
 
# --- InfluxDB setup ---
token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"
 
client    = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)
 
# --- Thresholds ---
THRESHOLDS = {
    "temperature": (MIN_TEMP, MAX_TEMP),
    "light":       (MIN_LIGHT, MAX_LIGHT),
    "moisture":    (MIN_MOISTURE, MAX_MOISTURE),
    "co2":         (MIN_CO2, MAX_CO2),
}
 
# Latest packets from each PLC
sensor_values = {"temp": None, "light": None, "irrigation": None, "co2": None}
 
# IMPORTANT: PLCs read this dict expecting NUMBERS. Keep it numeric.
overrides = {}            # e.g. {"temperature": 25.0}
range_overrides = {}      # e.g. {"temperature": (20.0, 25.0)}
_overrides_lock = threading.Lock()
 
# --- helpers ---
def _normalize_sensor_key(k: str) -> str:
    k = (k or "").lower()
    if k in ("temp", "temperature"):
        return "temperature"
    if k in ("moist", "moisture", "irrigation"):
        return "moisture"
    if k == "light":
        return "light"
    if k in ("co2", "carbon", "carbon_dioxide"):
        return "co2"
    return k
 
def _sender(slot_key):
    def send(packet: dict):
        sensor_values[slot_key] = packet
    return send
 
# --- stdin command listener (minimal change; adds override_range) ---
def stdin_listener():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except Exception as e:
            print(f"STDIN JSON error: {e}", file=sys.stderr, flush=True)
            continue
 
        ctype = cmd.get("type")
        s_key = _normalize_sensor_key(cmd.get("sensor"))
 
        with _overrides_lock:
            if ctype == "override":
                # constant override stays numeric; clear any existing range
                try:
                    overrides[s_key] = float(cmd["value"])
                    range_overrides.pop(s_key, None)
                except Exception as e:
                    print(f"override parse error for {s_key}: {e}", file=sys.stderr, flush=True)
 
            elif ctype == "override_range":
                # store the range and also set an initial numeric sample
                try:
                    vmin = float(cmd["min"])
                    vmax = float(cmd["max"])
                    if vmin > vmax:
                        vmin, vmax = vmax, vmin
                    range_overrides[s_key] = (vmin, vmax)
                    overrides[s_key] = random.uniform(vmin, vmax)  # numeric for PLCs
                except Exception as e:
                    print(f"override_range parse error for {s_key}: {e}", file=sys.stderr, flush=True)
 
            elif ctype == "clear_override":
                overrides.pop(s_key, None)
                range_overrides.pop(s_key, None)
            # else ignore unknown types
 
def check_alerts(sensors_payload: dict):
    alerts = {}
    for field, (low, high) in THRESHOLDS.items():
        val = sensors_payload.get(field)
        if val is None:
            continue
        try:
            fv = float(val)
        except Exception:
            continue
        if not (low <= fv <= high):
            alerts[field] = {"value": fv, "status": "ALERT", "target": f"PLC for {field}"}
    return alerts
 
def run_once(plc):
    plc.run(cycles=1)
 
def main():
    # Start command reader
    threading.Thread(target=stdin_listener, daemon=True).start()
 
    # Instantiate PLCs with the numeric 'overrides' dict (unchanged contract)
    workers = [
        TemperaturePLC(sender=_sender("temp"),        overrides=overrides),
        LightPLC(      sender=_sender("light"),       overrides=overrides),
        IrrigationPLC( sender=_sender("irrigation"),  overrides=overrides),
        CO2PLC(        sender=_sender("co2"),         overrides=overrides),
    ]
 
    while True:
        # --- NEW: for any range overrides, resample a numeric value BEFORE each cycle
        with _overrides_lock:
            for field, (vmin, vmax) in list(range_overrides.items()):
                overrides[field] = random.uniform(vmin, vmax)
 
        # Step each PLC once 
        threads = [threading.Thread(target=run_once, args=(w,)) for w in workers]
        for t in threads: t.start()
        for t in threads: t.join()
 
        # Build outgoing payload from latest PLC packets 
        sensors = {
            "temperature": sensor_values["temp"]["temperature"]         if sensor_values["temp"]        else 0.0,
            "light":       sensor_values["light"]["light"]               if sensor_values["light"]       else 0.0,
            "moisture":    sensor_values["irrigation"]["moisture"]       if sensor_values["irrigation"]  else 0.0,
            "co2":         sensor_values["co2"]["co2"]                   if sensor_values["co2"]         else 0.0,
            "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S"),
        }
 
        actuators = {
            "heater_pct":   sensor_values["temp"]["heater_pct"]          if sensor_values["temp"]        else 0,
            "cooler_pct":   sensor_values["temp"]["cooler_pct"]          if sensor_values["temp"]        else 0,
            "lamp_pct":     sensor_values["light"]["lamp_pct"]           if sensor_values["light"]       else 0,
            "shutter_pct":  sensor_values["light"]["shutter_pct"]        if sensor_values["light"]       else 0,
            "pump_pct":     sensor_values["irrigation"]["pump_pct"]      if sensor_values["irrigation"]  else 0,
            "drain_pct":    sensor_values["irrigation"]["drain_pct"]     if sensor_values["irrigation"]  else 0,
            "co2_pump_pct": sensor_values["co2"]["co2_pump_pct"]         if sensor_values["co2"]         else 0,
            "co2_vent_pct": sensor_values["co2"]["co2_vent_pct"]         if sensor_values["co2"]         else 0,
        }
 
        alerts = check_alerts(sensors)
 
        output = {"sensors": sensors, "actuators": actuators, "alerts": alerts}
        print(json.dumps(output), flush=True)
 
        # Influx write
        point = (
            Point("greenhouse")
            .tag("location", "greenhouse_room_1")
            .field("temperature",   float(sensors["temperature"]))
            .field("heater_pct",    float(actuators["heater_pct"]))
            .field("cooler_pct",    float(actuators["cooler_pct"]))
            .field("light",         float(sensors["light"]))
            .field("lamp_pct",      float(actuators["lamp_pct"]))
            .field("shutter_pct",   float(actuators["shutter_pct"]))
            .field("moisture",      float(sensors["moisture"]))
            .field("pump_pct",      float(actuators["pump_pct"]))
            .field("drain_pct",     float(actuators["drain_pct"]))
            .field("co2",           float(sensors["co2"]))
            .field("co2_pump_pct",  float(actuators["co2_pump_pct"]))
            .field("co2_vent_pct",  float(actuators["co2_vent_pct"]))
            .field("alerts_count",  int(len(alerts)))
            .time(time.time_ns(), WritePrecision.NS)
        )
        write_api.write(bucket=bucket, org=org, record=point)
 
        time.sleep(0.1)
 
if __name__ == "__main__":
    main()