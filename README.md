this project uses python, pyside, influxdb and grafana to show our greenhouse plc system

install python
pip install PySide6 pyqtgraph
install influxdb 2.7.xx
PS C:> cd .\path\to\influxdb\
PS C:\path\to\influxdb> ./influxd
install grafana, to have a better view of the charts (optional)
PS C:> cd "C:\path\to\Grafana\bin"
PS C:\path\to\Grafana\bin> .\grafana-server.exe

$env:INFLUXDB_URL="http://localhost:8086"
$env:INFLUXDB_ORG="your-org"
$env:INFLUXDB_BUCKET="your-bucket"
$env:INFLUXDB_TOKEN="your-token"
then run the code  python pyside.py



