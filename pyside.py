# pyside.py
import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QByteArray, Signal, Slot, QTimer, QProcess
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QPushButton, QLineEdit, QTextEdit, QGridLayout, QMessageBox,
    QMainWindow, QTabWidget, QTableWidget, QTableWidgetItem
)

APP_TITLE = "Greenhouse PLC Dashboard (Python GUI)"
ROOT = Path(__file__).resolve().parent
COLLECTOR = str(ROOT / "plc1_collector.py")   # must exist next to this file


# ---------- small helpers ----------
def pct_bar(max_val, value):
    if max_val <= 0:
        return 0
    try:
        return max(0, min(100, int((float(value) / float(max_val)) * 100)))
    except Exception:
        return 0


# ---------- Influx duplication (no extra port) ----------
class InfluxDuplicator(QWidget):
    """
    Thin wrapper around influxdb_client that:
      - starts a timed 'capture window'
      - on each new data packet, writes a duplicate row to greenhouse_room_2
    Reads env vars: INFLUXDB_URL, INFLUXDB_ORG, INFLUXDB_BUCKET, INFLUXDB_TOKEN
    """
    statusChanged = Signal(dict)  # {active:bool, remaining:int, reason:str, written:int, label:str}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._deadline = 0.0
        self._label = ""
        self._reason = ""
        self._written = 0

        self._client = None
        self._write_api = None
        self._bucket = None
        self._org = None
        self.Point = None
        self._load_influx()

        # status ticker (for countdown + surfacing errors)
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)
        self._ticker.start()

    def _load_influx(self):
        try:
            from influxdb_client import InfluxDBClient, Point
            from influxdb_client.client.write_api import SYNCHRONOUS
            self.Point = Point
        except Exception:
            self._reason = "influxdb_client not installed (pip install influxdb-client)"
            return

        token  = os.environ.get("INFLUXDB_TOKEN") or os.environ.get("INFLUX_TOKEN")
        org    = os.environ.get("INFLUXDB_ORG") or os.environ.get("INFLUX_ORG") or "SUTD"
        bucket = os.environ.get("INFLUXDB_BUCKET") or os.environ.get("INFLUX_BUCKET") or "greenhouse"
        url    = os.environ.get("INFLUXDB_URL") or os.environ.get("INFLUX_URL") or "http://localhost:8086"

        if not (url and org and bucket and token):
            self._reason = "Influx env vars missing (INFLUXDB_URL/ORG/BUCKET/TOKEN)"
            return

        try:
            self._client = InfluxDBClient(url=url, token=token, org=org)
            # Synchronous -> no buffering; points appear immediately
            self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
            self._bucket = bucket
            self._org = org
            self._reason = ""
        except Exception as e:
            self._reason = f"Influx init failed: {e}"

    def start(self, duration_sec: int, label: str = ""):
        if self._client is None or self._write_api is None:
            # lazy retry if env added later
            self._load_influx()
        if self._client is None or self._write_api is None:
            self._active = False
            self._deadline = 0
            self._label = ""
            self._emit_status()
            return

        self._active = True
        self._deadline = time.time() + int(duration_sec)
        self._label = label or ""
        self._written = 0
        self._emit_status()

    def stop(self):
        self._active = False
        self._deadline = 0
        self._label = ""
        try:
            if self._write_api is not None and hasattr(self._write_api, "flush"):
                self._write_api.flush()  # just in case
        except Exception as e:
            self._reason = f"flush failed: {e}"
        self._emit_status()

    def _tick(self):
        if not self._active:
            self._emit_status()
            return
        remaining = int(max(0, self._deadline - time.time()))
        if remaining == 0:
            self.stop()
        else:
            self._emit_status()

    def _emit_status(self):
        remaining = int(max(0, self._deadline - time.time())) if self._active else 0
        self.statusChanged.emit({
            "active": self._active,
            "remaining": remaining,
            "label": self._label,
            "reason": self._reason,
            "written": self._written,
        })

    def write_duplicate(self, sensors: dict, actuators: dict):
        """Call this on every new packet while active."""
        if not self._active or self._write_api is None or self.Point is None:
            return

        try:
            p = (
                self.Point("greenhouse")  # keep single measurement; separate by tag
                .tag("location", "greenhouse_room_2")
                .field("temperature", float(sensors.get("temperature", 0.0)))
                .field("light", float(sensors.get("light", 0.0)))
                .field("moisture", float(sensors.get("moisture", 0.0)))
                .field("co2", float(sensors.get("co2", 0.0)))
            )
            # mirror actuators to match schema
            for k, v in (actuators or {}).items():
                try:
                    p = p.field(k, float(v))
                except Exception:
                    pass

            if self._label:
                p = p.tag("label", self._label).tag("source", "duplicate")

            # pass org explicitly for robustness
            self._write_api.write(bucket=self._bucket, org=self._org, record=p)
            self._written += 1
        except Exception as e:
            self._reason = f"write failed: {e}"


# ---------- PLC panels & dashboard ----------
class PlcPanel(QGroupBox):
    # sensor_key, payload ({"type":"range","min":...,"max":...} or {"type":"constant","value":...})
    applyOverride = Signal(str, dict)
    clearOverride = Signal(str)

    def __init__(self, title, sensor_key, value_unit, gauge_max,
                 actuator_specs, parent=None):
        super().__init__(title, parent)
        self.sensor_key = sensor_key
        self.value_unit = value_unit
        self.gauge_max = gauge_max
        self.actuator_specs = actuator_specs  # [('Heater','heater_pct'), ...]

        self.value_lbl = QLabel("--")
        self.gauge = QProgressBar()
        self.gauge.setRange(0, 100)
        self.gauge.setFormat("")

        grid = QGridLayout()
        row = 0

        grid.addWidget(QLabel(f"{sensor_key.capitalize()}: "), row, 0, Qt.AlignLeft)
        grid.addWidget(self.value_lbl, row, 1, Qt.AlignLeft)
        grid.addWidget(QLabel(self.value_unit), row, 2, Qt.AlignLeft)
        row += 1
        grid.addWidget(self.gauge, row, 0, 1, 3)
        row += 1

        self.act_rows = []
        for label_text, key in self.actuator_specs:
            name_lbl = QLabel(f"{label_text}:")
            val_lbl = QLabel("--%")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setFormat("")
            grid.addWidget(name_lbl, row, 0, Qt.AlignLeft)
            grid.addWidget(val_lbl, row, 1, Qt.AlignLeft)
            row += 1
            grid.addWidget(bar, row, 0, 1, 3)
            row += 1
            self.act_rows.append((key, val_lbl, bar))

        # --- override inputs: range (min, max) OR constant (min only) ---
        self.override_min = QLineEdit()
        self.override_min.setPlaceholderText("Min (or constant)")
        self.override_max = QLineEdit()
        self.override_max.setPlaceholderText("Max (optional)")

        self.apply_btn = QPushButton("Apply")
        self.reset_btn = QPushButton("Reset")

        o_row = QHBoxLayout()
        o_row.addWidget(QLabel("Attack:"))
        o_row.addWidget(self.override_min)
        o_row.addWidget(self.override_max)
        o_row.addWidget(self.apply_btn)
        o_row.addWidget(self.reset_btn)

        v = QVBoxLayout()
        v.addLayout(grid)
        v.addLayout(o_row)
        self.setLayout(v)

        self.apply_btn.clicked.connect(self._apply_clicked)
        self.reset_btn.clicked.connect(self._reset_clicked)

    @Slot()
    def _apply_clicked(self):
        try:
            vmin = float(self.override_min.text()) if self.override_min.text() else None
            vmax = float(self.override_max.text()) if self.override_max.text() else None
        except ValueError:
            QMessageBox.warning(self, "Invalid override", "Enter numeric values.")
            return

        if vmin is not None and vmax is not None:
            if vmin > vmax:
                QMessageBox.warning(self, "Invalid range", "Min cannot be greater than Max.")
                return
            payload = {"type": "range", "min": vmin, "max": vmax}
        elif vmin is not None:
            payload = {"type": "constant", "value": vmin}
        else:
            QMessageBox.warning(self, "No value", "Enter at least a Min value.")
            return

        self.applyOverride.emit(self.sensor_key, payload)

    @Slot()
    def _reset_clicked(self):
        self.clearOverride.emit(self.sensor_key)

    def update_view(self, sensors: dict, actuators: dict):
        sv = sensors.get(self.sensor_key)
        if sv is not None:
            try:
                self.value_lbl.setText(f"{float(sv):.2f}")
            except Exception:
                self.value_lbl.setText(str(sv))
            self.gauge.setValue(pct_bar(self.gauge_max, sv))

        for key, val_lbl, bar in self.act_rows:
            try:
                p = float(actuators.get(key, 0))
            except Exception:
                p = 0.0
            val_lbl.setText(f"{p:.0f}%")
            bar.setValue(int(max(0, min(100, p))))


class DashboardWidget(QWidget):
    """
    Dashboard tab:
      - spawns plc1_collector.py
      - emits 'newPacket' with parsed JSON
    """
    newPacket = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc = QProcess(self)
        self.proc.setProgram(sys.executable)
        self.proc.setArguments(["-u", COLLECTOR])
        self.proc.setProcessChannelMode(QProcess.MergedChannels)

        # forward parent env (so Influx creds reach the collector)
        env = self.proc.processEnvironment()
        for k in ("INFLUXDB_URL", "INFLUXDB_ORG", "INFLUXDB_BUCKET", "INFLUXDB_TOKEN",
                  "INFLUX_URL", "INFLUX_ORG", "INFLUX_BUCKET", "INFLUX_TOKEN"):
            v = os.environ.get(k)
            if v:
                env.insert(k, v)
        self.proc.setProcessEnvironment(env)

        self.temp_panel = PlcPanel("🌡️ Temp PLC", "temperature", "°C", 50.0,
                                   [("Heater", "heater_pct"), ("Cooler", "cooler_pct")])
        self.moist_panel = PlcPanel("💧 Irrigation PLC", "moisture", "%", 100.0,
                                    [("Pump", "pump_pct"), ("Drain", "drain_pct")])
        self.light_panel = PlcPanel("💡 Light PLC", "light", "lux", 1000.0,
                                    [("Lamp", "lamp_pct"), ("Shutter", "shutter_pct")])
        self.co2_panel = PlcPanel("🫧 CO₂ PLC", "co2", "ppm", 1000.0,
                                  [("CO₂ Pump", "co2_pump_pct"), ("Vent", "co2_vent_pct")])

        for panel in (self.temp_panel, self.moist_panel, self.light_panel, self.co2_panel):
            panel.applyOverride.connect(self.send_override)
            panel.clearOverride.connect(self.clear_override)

        self.timestamp_lbl = QLabel("Timestamp: --")
        self.alerts_txt = QTextEdit()
        self.alerts_txt.setReadOnly(True)
        self.alerts_txt.setMinimumHeight(140)

        grid = QGridLayout()
        grid.addWidget(self.temp_panel, 0, 0)
        grid.addWidget(self.moist_panel, 0, 1)
        grid.addWidget(self.light_panel, 1, 0)
        grid.addWidget(self.co2_panel, 1, 1)

        info = QVBoxLayout()
        info.addWidget(self.timestamp_lbl)
        info.addWidget(self.alerts_txt)

        root = QVBoxLayout()
        root.addLayout(grid)
        root.addLayout(info)
        self.setLayout(root)

        self.proc.readyReadStandardOutput.connect(self.read_proc)
        self.proc.finished.connect(self.proc_finished)
        self.proc.errorOccurred.connect(self.proc_error)
        self.proc.start()

        if os.environ.get("INFLUXDB_TOKEN") in (None, "") and os.environ.get("INFLUX_TOKEN") in (None, ""):
            self.alerts_txt.append("⚠️ INFLUX token not set; collector may log auth errors.")

    @Slot()
    def read_proc(self):
        while self.proc.canReadLine():
            line: QByteArray = self.proc.readLine()
            text = bytes(line).decode(errors="ignore").strip()
            if not text:
                continue
            try:
                data = json.loads(text)
                self.update_dashboard(data)
                self.newPacket.emit(data)  # give to other tabs (e.g., duplicator)
            except json.JSONDecodeError:
                self.alerts_txt.append(text)

    @Slot(int, QProcess.ExitStatus)
    def proc_finished(self, code, status):
        self.alerts_txt.append(f"Collector exited (code={code}, status={int(status)}).")

    @Slot("QProcess::ProcessError")
    def proc_error(self, err):
        self.alerts_txt.append(f"Process error: {err}")

    def update_dashboard(self, data: dict):
        sensors = data.get("sensors", {})
        actuators = data.get("actuators", {})
        alerts = data.get("alerts", {})
        ts = sensors.get("timestamp", "--")
        self.timestamp_lbl.setText(f"Timestamp: {ts}")

        self.temp_panel.update_view(sensors, actuators)
        self.moist_panel.update_view(sensors, actuators)
        self.light_panel.update_view(sensors, actuators)
        self.co2_panel.update_view(sensors, actuators)

        if not alerts:
            self.alerts_txt.setPlainText("✅ All normal")
        else:
            out_lines = ["⚠️ Alerts:"]
            for k, info in alerts.items():
                out_lines.append(f"- {k.upper()}: {info.get('value')} → {info.get('status')}")
            self.alerts_txt.setPlainText("\n".join(out_lines))

    @Slot(str, dict)
    def send_override(self, sensor_key: str, payload: dict):
        # Normalize to collector message shapes
        if payload.get("type") == "range":
            cmd = {"type": "override_range", "sensor": sensor_key,
                   "min": payload["min"], "max": payload["max"]}
        else:
            cmd = {"type": "override", "sensor": sensor_key,
                   "value": payload["value"]}
        self._write_cmd(cmd)

    @Slot(str)
    def clear_override(self, sensor_key: str):
        cmd = {"type": "clear_override", "sensor": sensor_key}
        self._write_cmd(cmd)

    def _write_cmd(self, obj: dict):
        if self.proc.state() != QProcess.Running:
            QMessageBox.warning(self, "Not running", "Collector process is not running.")
            return
        payload = (json.dumps(obj) + "\n").encode()
        written = self.proc.write(payload)
        if written == -1:
            self.alerts_txt.append("Failed to write to collector stdin.")
            return
        if not self.proc.waitForBytesWritten(500):
            self.alerts_txt.append("Timed out waiting for command to be written.")

    def shutdown(self):
        if self.proc and self.proc.state() == QProcess.Running:
            self.proc.kill()
            self.proc.waitForFinished(2000)


# ---------- Local Subscribe / Duplicate tab (no HTTP) ----------
class LocalSubscribeTab(QWidget):
    """
    Mirrors the 'Subscribe/Duplicate' page but uses the local InfluxDuplicator
    and the live packets from DashboardWidget.newPacket (no network, no ports).
    """
    def __init__(self, duplicator: InfluxDuplicator, parent=None):
        super().__init__(parent)
        self.dupe = duplicator

        title = QLabel("PLC Live + Capture (Local)")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)  # portable across PySide6 versions
        title.setFont(f)
        title.setAlignment(Qt.AlignHCenter)

        self.btn5 = QPushButton("Start 5-min Capture")
        self.btn10 = QPushButton("Start 10-min Capture")
        self.btnStop = QPushButton("Stop Capture")

        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(self.btn5)
        top.addWidget(self.btn10)
        top.addWidget(self.btnStop)
        top.addStretch(1)

        self.capStatus = QLabel("capture: idle")
        self.capStatus.setAlignment(Qt.AlignHCenter)

        gbox = QGroupBox("Live Gauges")
        grid = QGridLayout(gbox)

        self.pbTemp = self._mk_bar(0, 50)
        self.pbLight = self._mk_bar(0, 1000)
        self.pbMoist = self._mk_bar(0, 100)
        self.pbCO2 = self._mk_bar(0, 1000)

        self.lblTemp = QLabel("0.00")
        self.lblLight = QLabel("0.00")
        self.lblMoist = QLabel("0.00")
        self.lblCO2 = QLabel("0.00")

        r = 0
        grid.addWidget(QLabel("Temperature (°C)"), r, 0); grid.addWidget(self.pbTemp, r, 1); grid.addWidget(self.lblTemp, r, 2); r += 1
        grid.addWidget(QLabel("Light"),           r, 0); grid.addWidget(self.pbLight, r, 1); grid.addWidget(self.lblLight, r, 2); r += 1
        grid.addWidget(QLabel("Moisture (%)"),    r, 0); grid.addWidget(self.pbMoist, r, 1); grid.addWidget(self.lblMoist, r, 2); r += 1
        grid.addWidget(QLabel("CO₂ (ppm)"),       r, 0); grid.addWidget(self.pbCO2,   r, 1); grid.addWidget(self.lblCO2,   r, 2); r += 1

        self.tbl = QTableWidget(5, 3)
        self.tbl.setHorizontalHeaderLabels(["Metric", "Value", "Timestamp"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        for i, name in enumerate(["Temperature", "Light", "Moisture", "CO₂", "Alerts"]):
            self.tbl.setItem(i, 0, QTableWidgetItem(name))
            self.tbl.setItem(i, 1, QTableWidgetItem("—"))
            self.tbl.setItem(i, 2, QTableWidgetItem("—"))

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addLayout(top)
        root.addWidget(self.capStatus)
        root.addWidget(gbox)
        root.addWidget(self.tbl)
        root.addStretch(1)

        # wire buttons
        self.btn5.clicked.connect(lambda: self.dupe.start(300, "block-5min"))
        self.btn10.clicked.connect(lambda: self.dupe.start(600, "block-10min"))
        self.btnStop.clicked.connect(self.dupe.stop)
        self.dupe.statusChanged.connect(self._on_status)

    def _mk_bar(self, lo, hi):
        bar = QProgressBar()
        bar.setRange(lo, hi)
        bar.setTextVisible(False)
        bar.setFixedHeight(18)
        return bar

    @Slot(dict)
    def _on_status(self, j):
        # Show errors or live countdown + written counter
        if j.get("reason"):
            self.capStatus.setText(f"capture: {('ACTIVE' if j.get('active') else 'idle')} — {j['reason']}")
            return
        w = j.get("written", 0)
        if j.get("active"):
            rem = j.get("remaining", 0)
            label = j.get("label") or ""
            self.capStatus.setText(f"capture: ACTIVE{f' (label={label})' if label else ''} — remaining {rem}s — written {w}")
        else:
            self.capStatus.setText(f"capture: idle — written {w}")

    # called by MainWindow when new packets arrive
    def update_live(self, sensors: dict, alerts_count: int, ts: str):
        temp = float(sensors.get("temperature") or 0.0)
        light = float(sensors.get("light") or 0.0)
        moist = float(sensors.get("moisture") or 0.0)
        co2  = float(sensors.get("co2") or 0.0)

        self.pbTemp.setValue(int(temp))
        self.pbLight.setValue(int(light))
        self.pbMoist.setValue(int(moist))
        self.pbCO2.setValue(int(co2))

        self.lblTemp.setText(f"{temp:.2f}")
        self.lblLight.setText(f"{light:.2f}")
        self.lblMoist.setText(f"{moist:.2f}")
        self.lblCO2.setText(f"{co2:.2f}")

        rows = [
            ("Temperature", temp, ts),
            ("Light",       light, ts),
            ("Moisture",    moist, ts),
            ("CO₂",         co2,   ts),
            ("Alerts",      alerts_count, ts),
        ]
        for i, (_, val, t) in enumerate(rows):
            self.tbl.setItem(i, 1, QTableWidgetItem(f"{val}"))
            self.tbl.setItem(i, 2, QTableWidgetItem(t))


# ---------- Main window ----------
class MainWindow(QMainWindow):
    """Hosts tabs: Dashboard and Local Subscribe/Duplicate."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)

        self.tabs = QTabWidget()
        self.dashboard = DashboardWidget()
        self.duplicator = InfluxDuplicator()
        self.subscribe = LocalSubscribeTab(self.duplicator)

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.subscribe, "Subscribe / Duplicate")

        self.setCentralWidget(self.tabs)
        self.resize(1200, 800)

        # bridge dashboard packets -> duplicator + local tab
        self.dashboard.newPacket.connect(self._on_packet)

    @Slot(dict)
    def _on_packet(self, data: dict):
        sensors = data.get("sensors", {}) or {}
        actuators = data.get("actuators", {}) or {}
        alerts = data.get("alerts", {}) or {}
        ts = sensors.get("timestamp", "")
        # feed duplicator (only writes when active)
        self.duplicator.write_duplicate(sensors, actuators)
        # update the local subscribe UI
        self.subscribe.update_live(sensors, len(alerts), ts)

    def closeEvent(self, event: QCloseEvent):
        if hasattr(self, "dashboard") and isinstance(self.dashboard, DashboardWidget):
            self.dashboard.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
