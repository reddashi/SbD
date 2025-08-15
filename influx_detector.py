# influx_detector.py
from influxdb_client import InfluxDBClient
import time

url = "http://localhost:8086"
token ="IlFwe-6RV4MhhKYaJh-zweHAvsXRCwo7cOHWI04BfFhEFhrsQB2l2hvsFDa8u7OsCZqWJ7cORiDlH100k12DbA=="  # Attacker uses same token as PLC
org = "SUTD"
bucket = "greenhouse"

MIN_TEMP, MAX_TEMP = 20.0, 35.0
MIN_HUM, MAX_HUM = 30.0, 70.0

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

print("Detection system checking InfluxDB for anomalies...")

while True:
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -10s)
      |> filter(fn: (r) => r["_measurement"] == "greenhouse")
    '''
    tables = query_api.query(query)

    for table in tables:
        for record in table.records:
            field = record.get_field()
            value = record.get_value()
            if field == "temperature" and (value < MIN_TEMP or value > MAX_TEMP):
                print(f"🚨 ALERT: Abnormal temperature {value}°C detected")
            if field == "moisture" and (value < MIN_HUM or value > MAX_HUM):
                print(f"🚨 ALERT: Abnormal moisture {value}% detected")

    time.sleep(5)
