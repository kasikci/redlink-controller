const configForm = document.getElementById("config-form");
const errorBanner = document.getElementById("error-banner");
const statusPill = document.getElementById("status-pill");

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

function renderSnapshot(snapshot) {
  if (!snapshot) {
    return;
  }
  const status = snapshot.status || {};
  const controller = snapshot.controller || {};
  const config = snapshot.config || {};

  setText("temperature", formatTemp(status.temperature));
  setText("hold-until", formatMaybe(status.hold_until));
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
  document.getElementById("hysteresis-enabled").checked =
    config.hysteresis_enabled ?? true;
  document.getElementById("enable-heat").checked = config.enable_heat ?? true;
  document.getElementById("enable-cool").checked = config.enable_cool ?? true;
  document.getElementById("heat-on").value = config.heat_on_below ?? "";
  document.getElementById("heat-off").value = config.heat_off_at ?? "";
  document.getElementById("cool-on").value = config.cool_on_above ?? "";
  document.getElementById("cool-off").value = config.cool_off_at ?? "";
  document.getElementById("hold-minutes").value = config.hold_minutes ?? "";
  document.getElementById("poll-interval").value =
    config.poll_interval_seconds ?? "";
  document.getElementById("login-refresh").value =
    config.login_refresh_seconds ?? "";
  document.getElementById("username").value = config.username ?? "";
  document.getElementById("device-id").value = config.device_id ?? "";
  document.getElementById("base-url").value = config.base_url ?? "";
  document.getElementById("bind-host").value = config.bind_host ?? "";
  document.getElementById("bind-port").value = config.bind_port ?? "";
  document.getElementById("timeout").value = config.timeout_seconds ?? "";
  document.getElementById("time-offset").value =
    config.time_offset_minutes ?? "";

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
    hysteresis_enabled: document.getElementById("hysteresis-enabled").checked,
    enable_heat: document.getElementById("enable-heat").checked,
    enable_cool: document.getElementById("enable-cool").checked,
    heat_on_below: numberValue("heat-on"),
    heat_off_at: numberValue("heat-off"),
    cool_on_above: numberValue("cool-on"),
    cool_off_at: numberValue("cool-off"),
    hold_minutes: numberValue("hold-minutes"),
    poll_interval_seconds: numberValue("poll-interval"),
    login_refresh_seconds: numberValue("login-refresh"),
    username: stringValue("username"),
    device_id: numberValue("device-id"),
    base_url: stringValue("base-url"),
    bind_host: stringValue("bind-host"),
    bind_port: numberValue("bind-port"),
    timeout_seconds: numberValue("timeout"),
  };

  const timeOffset = stringValue("time-offset");
  if (timeOffset !== "") {
    payload.time_offset_minutes = Number(timeOffset);
  }

  const password = stringValue("password");
  if (password) {
    payload.password = password;
  }

  return payload;
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
      await apiPost("/api/config", payload);
      document.getElementById("password").value = "";
      await refreshConfig();
      await refreshStatus();
    } catch (error) {
      updateError(error.message || "Failed to save config");
    }
  });

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
