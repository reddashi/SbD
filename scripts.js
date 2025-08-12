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

// ===== NEW: Override system =====
const overrides = {
  temperature: null,
  moisture: null,
  light: null,
  co2: null
};

function applyOverride(type, value) {
  overrides[type] = value;
  localStorage.setItem('overrides', JSON.stringify(overrides));
  document.getElementById(type + 'OverrideStatus').innerText = `Override set to ${value}`;
}

function resetOverride(type) {
  overrides[type] = null;
  localStorage.setItem('overrides', JSON.stringify(overrides));
  document.getElementById(type + 'OverrideStatus').innerText = "No override set.";
}

// Restore overrides from localStorage
const savedOverrides = JSON.parse(localStorage.getItem('overrides') || '{}');
Object.assign(overrides, savedOverrides);

// Bind override buttons
function bindOverrideControls(type) {
  const applyBtn = document.getElementById(`apply${type}OverrideBtn`);
  const resetBtn = document.getElementById(`reset${type}OverrideBtn`);
  const input = document.getElementById(`${type.toLowerCase()}OverrideInput`);

  if (applyBtn && resetBtn && input) {
    applyBtn.addEventListener('click', () => {
      if (input.value) {
        applyOverride(type.toLowerCase(), parseFloat(input.value));
      }
    });
    resetBtn.addEventListener('click', () => resetOverride(type.toLowerCase()));
  }
}

bindOverrideControls('Temp');
bindOverrideControls('Hum');
bindOverrideControls('Light');
bindOverrideControls('Co2');
// ===== End override system =====

// Dashboard update functions
function updateDashboard(data) {
  const s = data.sensors;
  const a = data.actuators;
  const alerts = data.alerts || {};

  // Apply overrides if set
  if (overrides.temperature !== null) s.temperature = overrides.temperature;
  if (overrides.moisture !== null) s.moisture = overrides.moisture;
  if (overrides.light !== null) s.light = overrides.light;
  if (overrides.co2 !== null) s.co2 = overrides.co2;

  // Sensors
  document.getElementById('tempVal').innerText = s.temperature;
  document.getElementById('humVal').innerText = s.moisture;
  document.getElementById('co2Val').innerText = s.co2;
  document.getElementById('lightVal').innerText = s.light;
  document.getElementById('timestamp').innerText = "Timestamp: " + s.timestamp;

  // Gauges
  document.getElementById('tempBar').style.width = (s.temperature / 50 * 100) + "%";
  document.getElementById('humBar').style.width = (s.moisture / 100 * 100) + "%";
  document.getElementById('co2Bar').style.width = (s.co2 / 1000 * 100) + "%";
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
async function update() {
  try {
    let data;
    const storedSim = localStorage.getItem('simulatedData');
    if (storedSim) {
      data = JSON.parse(storedSim);
    } else {
      data = await window.plcAPI.getSensorData();
    }

    // Apply overrides
    const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
    if (overrides.temperature !== undefined) data.sensors.temperature = overrides.temperature;
    if (overrides.moisture !== undefined) data.sensors.moisture = overrides.moisture;
    if (overrides.light !== undefined) data.sensors.light = overrides.light;
    if (overrides.co2 !== undefined) data.sensors.co2 = overrides.co2;

    updateDashboard(data);
  } catch (err) {
    const alertEl = document.getElementById('alerts');
    if (alertEl) alertEl.innerText = "Error: " + err;
  }
}

// ---- Override controls ----

// Temp override
document.getElementById('applyTempOverrideBtn').addEventListener('click', () => {
  const val = parseFloat(document.getElementById('tempOverrideInput').value);
  if (!isNaN(val)) {
    const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
    overrides.temperature = val;
    localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
    document.getElementById('tempOverrideStatus').innerText = `Override set to ${val}°C`;

    // SEND override to backend
    window.plcAPI.sendOverride('temperature', val);
  }
});

document.getElementById('resetTempOverrideBtn').addEventListener('click', () => {
  const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
  delete overrides.temperature;
  localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
  document.getElementById('tempOverrideStatus').innerText = "No override set.";

  // CLEAR override in backend
  window.plcAPI.clearOverride('temperature');
});

// Repeat similarly for moisture (irrigation), light, and co2:

document.getElementById('applyHumOverrideBtn').addEventListener('click', () => {
  const val = parseFloat(document.getElementById('humOverrideInput').value);
  if (!isNaN(val)) {
    const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
    overrides.moisture = val;
    localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
    document.getElementById('humOverrideStatus').innerText = `Override set to ${val}%`;
    window.plcAPI.sendOverride('moisture', val);  // changed from 'irrigation' to 'moisture'
  }
});

document.getElementById('resetHumOverrideBtn').addEventListener('click', () => {
  const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
  delete overrides.moisture;
  localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
  document.getElementById('humOverrideStatus').innerText = "No override set.";
  window.plcAPI.clearOverride('moisture');  // changed from 'irrigation' to 'moisture'
});

document.getElementById('applyLightOverrideBtn').addEventListener('click', () => {
  const val = parseFloat(document.getElementById('lightOverrideInput').value);
  if (!isNaN(val)) {
    const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
    overrides.light = val;
    localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
    document.getElementById('lightOverrideStatus').innerText = `Override set to ${val} lux`;
    window.plcAPI.sendOverride('light', val);
  }
});
document.getElementById('resetLightOverrideBtn').addEventListener('click', () => {
  const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
  delete overrides.light;
  localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
  document.getElementById('lightOverrideStatus').innerText = "No override set.";
  window.plcAPI.clearOverride('light');
});

document.getElementById('applyCo2OverrideBtn').addEventListener('click', () => {
  const val = parseFloat(document.getElementById('co2OverrideInput').value);
  if (!isNaN(val)) {
    const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
    overrides.co2 = val;
    localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
    document.getElementById('co2OverrideStatus').innerText = `Override set to ${val} ppm`;
    window.plcAPI.sendOverride('co2', val);
  }
});
document.getElementById('resetCo2OverrideBtn').addEventListener('click', () => {
  const overrides = JSON.parse(localStorage.getItem('sensorOverrides') || '{}');
  delete overrides.co2;
  localStorage.setItem('sensorOverrides', JSON.stringify(overrides));
  document.getElementById('co2OverrideStatus').innerText = "No override set.";
  window.plcAPI.clearOverride('co2');
});
