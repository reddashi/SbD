this the project python for our greenhouse plc 


npm install electron --save-dev

$env:INFLUXDB_URL="http://localhost:8086"
$env:INFLUXDB_ORG="SUTD"
$env:INFLUXDB_BUCKET="greenhouse"
$env:INFLUXDB_TOKEN="IlFwe-6RV4MhhKYaJh-zweHAvsXRCwo7cOHWI04BfFhEFhrsQB2l2hvsFDa8u7OsCZqWJ7cORiDlH100k12DbA=="
then  python pysidenew.py

PS C:\Users\redda> cd .\Downloads\
PS C:\Users\redda\Downloads> cd .\influxdb\
PS C:\Users\redda\Downloads\influxdb> ./influxd

PS C:\Users\redda> cd "C:\Grafana\bin"
PS C:\Grafana\bin> .\grafana-server.exe