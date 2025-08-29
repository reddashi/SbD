SbD – Secure by Design Greenhouse Monitoring System
Project Overview
SbD (Secure by Design) is a cyber-physical greenhouse monitoring and security system that integrates IoT, data engineering, visualization, and machine learning.
This project was developed as part of the curriculum at the Singapore University of Technology and Design (SUTD) and was awarded a Distinction. It was a collaborative group effort that demonstrated both technical innovation and practical impact.
________________________________________
Motivation
Modern smart infrastructures such as greenhouses rely on automation driven by sensor networks. While efficient, these systems are vulnerable to:
•	Data manipulation attacks – falsifying sensor readings
•	Timing-based attacks – introducing delays or fake data
•	System faults – causing loss of control or inaccurate monitoring
Our project set out to answer:
How can we design such systems to be resilient against these risks?
We addressed this by combining real-time monitoring, secure data pipelines, and machine learning–based anomaly detection.
________________________________________
Key Features
•	Greenhouse PLC Simulations – temperature, light, CO₂, and irrigation
•	Time-Series Storage – InfluxDB backend for secure data collection
•	Visualization – PySide6 GUI + Grafana dashboards
•	Machine Learning – anomaly detection to flag attacks or faults
•	Attack Simulations – tested data injection & manipulation scenarios
________________________________________
System Architecture
1.	Sensors/PLCs simulate greenhouse conditions
2.	Python Collectors push data to InfluxDB
3.	PySide6 GUI provides local interactive monitoring
4.	Grafana Dashboards offer historical & real-time insights
5.	ML Detection Layer monitors for abnormal or malicious behaviour
________________________________________
Installation & Setup
This project uses Python, PySide, InfluxDB, and Grafana to visualize and secure our greenhouse PLC system.
Install Python dependencies
pip install PySide6 pyqtgraph
Install & Run InfluxDB (v2.7.xx)
PS C:> cd .\path\to\influxdb\
PS C:\path\to\influxdb> ./influxd
(Optional) Install & Run Grafana (for enhanced charts)
PS C:> cd "C:\path\to\Grafana\bin"
PS C:\path\to\Grafana\bin> .\grafana-server.exe
Configure Environment Variables
$env:INFLUXDB_URL="http://localhost:8086"
$env:INFLUXDB_ORG="your-org"
$env:INFLUXDB_BUCKET="your-bucket"
$env:INFLUXDB_TOKEN="your-token"
Run the GUI
python pyside.py
________________________________________
Attack Scenarios
We implemented two example attack vectors to demonstrate vulnerabilities:
1.	Override Attack – Triggered within pyside.py to simulate compromised logic.
2.	Database Injection Attack – Using influx_attack.py to push random/fake values directly into InfluxDB.
For more details, please refer to the project report and presentation slides included in this repository.
________________________________________
Project Highlights
•	PySide6 Monitoring Interface
•	Grafana Dashboard
•	Security/Anomaly Detection
________________________________________
Technical Stack
•	Programming: Python (PySide6, pyqtgraph, InfluxDB client)
•	Database: InfluxDB for time-series data
•	Visualization: Grafana, PySide6 GUI
•	Machine Learning: Supervised anomaly detection (scikit-learn)
•	Cybersecurity: Secure-by-design architecture, attack simulations
________________________________________
Recognition
This project was awarded a Distinction at SUTD for its integration of:
•	Cyber-physical system simulation
•	Secure data design principles
•	Practical machine learning applications
•	Effective teamwork and system integration
________________________________________
Future Enhancements
•	Deployment on Docker/Kubernetes for scalability
•	Integration with real greenhouse hardware
•	Stronger defences against advanced cyber attacks
•	Predictive ML models for plant growth and environment forecasting
________________________________________
Acknowledgements
This project was developed as a team effort at SUTD.
Special thanks to my teammates for their collaboration, innovation, and contributions.
________________________________________
License
This project is open-sourced under the MIT License – see the LICENSE file for details.
________________________________________
