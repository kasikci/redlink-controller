const configForm = document.getElementById("config-form");
const errorBanner = document.getElementById("error-banner");
const statusPill = document.getElementById("status-pill");
const modeHysteresisButton = document.getElementById("mode-hysteresis");
const modeScheduleButton = document.getElementById("mode-schedule");

let currentControlMode = "hysteresis";

async function apiGet(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function updateError(message) {
  if (!message) {
    errorBanner.hidden = true;
    errorBanner.textContent = "";
    return;
  }
  errorBanner.hidden = false;
  errorBanner.textContent = message;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = value ?? "--";
  }
}

function formatTemp(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return Number(value).toFixed(1);
}

function formatMaybe(value, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${value}${suffix}`;
}

function formatHoldUntil(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (typeof value === "string" && value.includes(":")) {
    return value;
  }
  const totalMinutes = Number(value);
  if (!Number.isFinite(totalMinutes)) {
    return String(value);
  }
  const minutes = Math.max(0, Math.round(totalMinutes)) % (24 * 60);
  const hours24 = Math.floor(minutes / 60);
  const mins = minutes % 60;
  const suffix = hours24 >= 12 ? "PM" : "AM";
  const hours12 = ((hours24 + 11) % 12) + 1;
  return `${hours12}:${String(mins).padStart(2, "0")} ${suffix}`;
}

function renderSnapshot(snapshot) {
  if (!snapshot) {
    return;
  }
  const status = snapshot.status || {};
  const controller = snapshot.controller || {};
  const config = snapshot.config || {};

  setText("temperature", formatTemp(status.temperature));
  setText("hold-until", formatHoldUntil(status.hold_until));
  setText(
    "setpoints",
    `${formatMaybe(status.heat_setpoint)} / ${formatMaybe(status.cool_setpoint)}`
  );
  setText("mode", controller.mode || "idle");
  setText("service-status", snapshot.error ? "Attention" : "Online");
  updateError(snapshot.error || "");

  const pillText = controller.mode ? controller.mode.toUpperCase() : "IDLE";
  statusPill.textContent = pillText;
  statusPill.classList.remove("cool", "heat");
  if (controller.mode === "cool") {
    statusPill.classList.add("cool");
  }
  if (controller.mode === "heat") {
    statusPill.classList.add("heat");
  }
}

function fillConfig(config) {
  if (!config) {
    return;
  }
  const controlMode = config.control_mode || "hysteresis";
  currentControlMode = controlMode;
  applyControlModeUi(controlMode);
  document.getElementById("enable-heat").checked = config.enable_heat ?? true;
  document.getElementById("enable-cool").checked = config.enable_cool ?? true;
  document.getElementById("heat-on").value = config.heat_on_below ?? "";
  document.getElementById("heat-off").value = config.heat_off_at ?? "";
  document.getElementById("cool-on").value = config.cool_on_above ?? "";
  document.getElementById("cool-off").value = config.cool_off_at ?? "";
  document.getElementById("hold-minutes").value = config.hold_minutes ?? "";
  document.getElementById("poll-interval").value =
    config.poll_interval_seconds ?? "";

  const configPill = document.getElementById("config-status");
  if (config.has_password) {
    configPill.textContent = "Configured";
    configPill.classList.remove("neutral");
  } else {
    configPill.textContent = "Missing";
    configPill.classList.add("neutral");
  }
}

function collectConfig() {
  const payload = {
    enable_heat: document.getElementById("enable-heat").checked,
    enable_cool: document.getElementById("enable-cool").checked,
    heat_on_below: numberValue("heat-on"),
    heat_off_at: numberValue("heat-off"),
    cool_on_above: numberValue("cool-on"),
    cool_off_at: numberValue("cool-off"),
    hold_minutes: numberValue("hold-minutes"),
    poll_interval_seconds: numberValue("poll-interval"),
  };

  return payload;
}

function applyControlModeUi(mode) {
  const hysteresisActive = mode === "hysteresis";
  if (modeHysteresisButton) {
    modeHysteresisButton.classList.toggle("active", hysteresisActive);
    modeHysteresisButton.setAttribute("aria-pressed", String(hysteresisActive));
  }
  if (modeScheduleButton) {
    modeScheduleButton.classList.toggle("active", !hysteresisActive);
    modeScheduleButton.setAttribute("aria-pressed", String(!hysteresisActive));
  }
  const hysteresisCard = document.getElementById("hysteresis-card");
  if (hysteresisCard) {
    hysteresisCard.hidden = !hysteresisActive;
  }
  const manualCard = document.getElementById("manual-card");
  if (manualCard) {
    manualCard.classList.toggle("full-span", !hysteresisActive);
  }
  const scheduleNote = document.getElementById("schedule-note");
  if (scheduleNote) {
    scheduleNote.hidden = hysteresisActive;
  }
}

async function setControlMode(mode) {
  if (!mode || mode === currentControlMode) {
    return;
  }
  currentControlMode = mode;
  applyControlModeUi(mode);
  try {
    const updated = await apiPost("/api/config", { control_mode: mode });
    fillConfig(updated);
    await refreshStatus();
  } catch (error) {
    updateError(error.message || "Failed to set control mode");
    await refreshConfig();
  }
}

function numberValue(id) {
  const value = document.getElementById(id).value;
  if (value === "") {
    return undefined;
  }
  return Number(value);
}

function stringValue(id) {
  return document.getElementById(id).value.trim();
}

async function refreshStatus() {
  try {
    const snapshot = await apiGet("/api/status");
    renderSnapshot(snapshot);
  } catch (error) {
    updateError(error.message || "Failed to load status");
  }
}

async function refreshConfig() {
  try {
    const config = await apiGet("/api/config");
    fillConfig(config);
  } catch (error) {
    updateError(error.message || "Failed to load config");
  }
}

async function sendCommand(action, payload = {}) {
  await apiPost("/api/command", { action, ...payload });
}

function requireNumber(id, label) {
  const value = numberValue(id);
  if (value === undefined || Number.isNaN(value)) {
    throw new Error(`${label} is required`);
  }
  return value;
}

function bindEvents() {
  configForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const payload = collectConfig();
      const updated = await apiPost("/api/config", payload);
      const passwordField = document.getElementById("password");
      if (passwordField) {
        passwordField.value = "";
      }
      fillConfig(updated);
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Failed to save config");
    }
  });

  if (modeHysteresisButton) {
    modeHysteresisButton.addEventListener("click", async () => {
      await setControlMode("hysteresis");
    });
  }
  if (modeScheduleButton) {
    modeScheduleButton.addEventListener("click", async () => {
      await setControlMode("schedule");
    });
  }

  document.getElementById("manual-heat").addEventListener("click", async () => {
    try {
      await sendCommand("heat", {
        setpoint: requireNumber("manual-heat-setpoint", "Heat setpoint"),
        hold_minutes: numberValue("manual-heat-hold"),
      });
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Heat command failed");
    }
  });

  document.getElementById("manual-cool").addEventListener("click", async () => {
    try {
      await sendCommand("cool", {
        setpoint: requireNumber("manual-cool-setpoint", "Cool setpoint"),
        hold_minutes: numberValue("manual-cool-hold"),
      });
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Cool command failed");
    }
  });

  document.getElementById("manual-fan").addEventListener("click", async () => {
    try {
      await sendCommand("fan", { mode: stringValue("manual-fan-mode") });
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Fan command failed");
    }
  });

  document.getElementById("manual-cancel").addEventListener("click", async () => {
    try {
      await sendCommand("cancel");
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Cancel failed");
    }
  });
}

bindEvents();
refreshConfig();
refreshStatus();
setInterval(refreshStatus, 10000);
