# collect_labeled_data.py
import pandas as pd
import time
import os
from influxdb_client import InfluxDBClient

# ==== USER SETTINGS ====
token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"

# ==== INPUT LABEL ====
label = int(input("Enter label (0 = normal, 1 = attack): "))
filename = "plc_labeled_data.csv"

# ==== CONNECT ====
client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

print(f"📡 Collecting data with label {label}... Press Ctrl+C to stop.")

try:
    while True:
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -5s)
          |> filter(fn: (r) => r["_measurement"] == "greenhouse")
          |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
        '''
        result = query_api.query_data_frame(query)

        # Handle if result is a list of DataFrames
        if isinstance(result, list):
            if len(result) == 0:
                time.sleep(1)
                continue
            df = pd.concat(result)
        else:
            df = result

        # Ensure it's not empty
        if not df.empty:
            # Only keep sensor columns that exist
            cols = [c for c in ["temperature", "moisture", "co2", "light"] if c in df.columns]
            if cols:
                df = df[cols].dropna()
                df["label"] = label
                df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
                print(f"💾 Saved {len(df)} rows with label {label}")

        time.sleep(1)

except KeyboardInterrupt:
    print(f"✅ Data collection stopped. Saved to {filename}")
