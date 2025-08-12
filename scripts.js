// Shared references for inputs and labels
const simInputs = {
  temperature: document.getElementById('simTemp'),
  moisture: document.getElementById('simHum'),
  light: document.getElementById('simLight'),
  co2: document.getElementById('simCO2')
};
const simLabels = {
  temperature: document.getElementById('simTempVal'),
  moisture: document.getElementById('simHumVal'),
  light: document.getElementById('simLightVal'),
  co2: document.getElementById('simCO2Val')
};

if (simInputs.temperature) {
  Object.keys(simInputs).forEach(key => {
    simInputs[key].addEventListener('input', () => {
      simLabels[key].innerText = simInputs[key].value;
    });
  });
}

// Dashboard update functions
function updateDashboard(data) {
  const s = data.sensors;
  const a = data.actuators;
  const alerts = data.alerts || {};

  // Sensors
  document.getElementById('tempVal').innerText = s.temperature;
  document.getElementById('humVal').innerText = s.moisture;
  document.getElementById('co2Val').innerText = s.co2;
  document.getElementById('lightVal').innerText = s.light;
  document.getElementById('timestamp').innerText = "Timestamp: " + s.timestamp;

  // Gauges
  document.getElementById('tempBar').style.width = (s.temperature / 50 * 100) + "%";
  document.getElementById('humBar').style.width = (s.moisture / 100 * 100) + "%";
  document.getElementById('co2Bar').style.width = (s.co2 / 1200 * 100) + "%";
  document.getElementById('lightBar').style.width = (s.light / 1000 * 100) + "%";

  // Actuator values
  document.getElementById('heaterPct').innerText = a.heater_pct;
  document.getElementById('coolerPct').innerText = a.cooler_pct;
  document.getElementById('pumpPct').innerText = a.pump_pct;
  document.getElementById('drainPct').innerText = a.drain_pct;
  document.getElementById('lampPct').innerText = a.lamp_pct;
  document.getElementById('shutterPct').innerText = a.shutter_pct;
  document.getElementById('co2PumpPct').innerText = a.co2_pump_pct;
  document.getElementById('co2VentPct').innerText = a.co2_vent_pct;

  // Set actuator bars and status
  setActuator("heater", a.heater_pct);
  setActuator("cooler", a.cooler_pct);
  setActuator("pump", a.pump_pct);
  setActuator("drain", a.drain_pct);
  setActuator("lamp", a.lamp_pct);
  setActuator("shutter", a.shutter_pct);
  setActuator("co2Pump", a.co2_pump_pct);
  setActuator("co2Vent", a.co2_vent_pct);

  // Alerts
  const alertEl = document.getElementById('alerts');
  if (alertEl) {
    if (Object.keys(alerts).length === 0) {
      alertEl.innerHTML = `<span style="color:green;">✅ All normal</span>`;
    } else {
      let log = `<strong>Alerts:</strong><ul>`;
      for (const [type, info] of Object.entries(alerts)) {
        log += `<li><strong>${type.toUpperCase()}</strong>: ${info.value} → ${info.status}</li>`;
      }
      log += "</ul>";
      alertEl.innerHTML = log;
    }
  }
}

function setActuator(id, value) {
  const status = document.getElementById(id + 'Status');
  const gauge = document.getElementById(id + 'Gauge');

  if (!status || !gauge) return;

  if (typeof value === 'string') {
    status.innerText = value === "HIGH" ? "⚙️ HIGH POWER" : (value === "LOW" ? "⚙️ LOW POWER" : "✅");
    status.className = "status " + (value === "HIGH" || value === "LOW" ? "active" : "idle");
    gauge.style.width = value === "HIGH" ? "100%" : (value === "LOW" ? "40%" : "0%");
  } else {
    const pct = parseFloat(value) || 0;
    if (pct > 40) {
      status.innerText = "⚙️ HIGH POWER";
      status.className = "status active";
    } else if (pct > 0) {
      status.innerText = "⚙️ LOW POWER";
      status.className = "status active";
    } else {
      status.innerText = "✅";
      status.className = "status idle";
    }
    gauge.style.width = pct + "%";
  }
}

// Function to fetch live sensor data and update dashboard
async function update() {
  try {
    let data;
    // Try to get simulated data from localStorage (if any)
    const storedSim = localStorage.getItem('simulatedData');
    if (storedSim) {
      data = JSON.parse(storedSim);
    } else {
      // Fallback to real API call if no simulation
      data = await window.plcAPI.getSensorData();
    }
    updateDashboard(data);
  } catch (err) {
    const alertEl = document.getElementById('alerts');
    if (alertEl) alertEl.innerText = "Error: " + err;
  }
}
