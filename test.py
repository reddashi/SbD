import os
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"

print(f"Token: {token}")
print(f"Org: {org}")
print(f"Bucket: {bucket}")

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

point = Point("test_measurement").tag("unit", "none").field("value", 1)

try:
    write_api.write(bucket=bucket, org=org, record=point)
    print("Write successful")
except Exception as e:
    print(f"Write failed: {e}")

#"export INFLUXDB_TOKEN=IlFwe-6RV4MhhKYaJh-zweHAvsXRCwo7cOHWI04BfFhEFhrsQB2l2hvsFDa8u7OsCZqWJ7cORiDlH100k12DbA==