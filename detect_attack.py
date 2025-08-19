import pandas as pd
import time
import joblib
from influxdb_client import InfluxDBClient
import os

# Load trained model
clf = joblib.load("plc_detector.pkl")

# InfluxDB environment
token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"

client = InfluxDBClient(url=url, token=token, org=org, bucket=bucket)
query_api = client.query_api()

WINDOW = 10      # seconds for Influx query
BATCH_SIZE = 5   # batch prediction

print("[ALERT] Real-time PLC Attack Detector Running...")

last_seen = None  # track most recent timestamp

while True:
    try:
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -{WINDOW}s)
          |> filter(fn: (r) => r["_measurement"] == "greenhouse")
          |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
        '''
        result = query_api.query_data_frame(query)

        # Flatten result
        if isinstance(result, list):
            dfs = [r.dropna(axis=1, how="all") for r in result if isinstance(r, pd.DataFrame) and not r.empty]
            if len(dfs) == 0:
                time.sleep(1)
                continue
            df = pd.concat(dfs, ignore_index=True)
        else:
            if result.empty:
                time.sleep(1)
                continue
            df = result.dropna(axis=1, how="all")

        # Ensure required features exist
        required_cols = ["temperature", "moisture", "co2", "light"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0  

        # Only keep rows with timestamp > last_seen
        if last_seen is not None:
            df = df[df["_time"] > last_seen]

        if df.empty:
            time.sleep(1)
            continue

        # Update last_seen
        last_seen = df["_time"].max()

        X_live = df[required_cols]
        times = df["_time"].tolist()

        # Batch prediction
        for i in range(0, len(X_live), BATCH_SIZE):
            batch = X_live.iloc[i:i+BATCH_SIZE]
            batch_times = times[i:i+BATCH_SIZE]
            preds = clf.predict(batch)

            for t, p in zip(batch_times, preds):
                if p == 1:
                    print(f"[ATTACK] Detected at {t}")
                else:
                    print(f"[NORMAL] at {t}")

        time.sleep(0.5)

    except Exception as e:
        print(f"[ERROR] {e}")
        time.sleep(2)
