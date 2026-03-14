const appState = {
  scenarioId: null,
  tick: 0,
  durationTicks: 1,
  tickSeconds: 0,
  playing: false,
  playTimer: null,
  playbackRate: 1,
  uploadedScenarioId: null,
  layerState: {
    blue: true,
    red: true,
    sensors: true,
    threats: true,
    risk: true
  }
};

const coordinateState = {
  lat: null,
  lon: null,
  mgrs: null
};

const uploadState = {
  filename: "No file selected",
  status: "No file loaded",
  summary: "Upload a `.txt`, `.md`, `.json`, `.pdf`, or `.docx` scenario file.",
  summaryHtml: "",
  valid: false,
  staffReviewHtml: "No review generated yet."
};

const aarState = {
  status: "Awaiting Completion",
  summary: "Complete the scenario replay to unlock the AAR workflow.",
  markdown: "No AAR generated yet.",
  ready: false,
  generated: false,
  filename: ""
};


const map = L.map("map", { zoomControl: true }).setView([21.8, -78.8], 6);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

const mapLayers = {
  blueMarkers: [],
  redMarkers: [],
  sensorCircles: [],
  threatCircles: [],
  riskCircles: [],
  sectorCircles: []
};

const blueIcon = L.icon({
  iconUrl: "/static/icons/blue_force.svg",
  iconSize: [28, 28],
  iconAnchor: [14, 14]
});

const redIcon = L.icon({
  iconUrl: "/static/icons/red_force.svg",
  iconSize: [28, 28],
  iconAnchor: [14, 14]
});

const uavIcons = {
  "MQ-1": L.icon({
    iconUrl: "/static/icons/mq1.svg",
    iconSize: [32, 32]
  }),
  "MQ-9": L.icon({
    iconUrl: "/static/icons/mq9.svg",
    iconSize: [32, 32]
  }),
  "RQ-4": L.icon({
    iconUrl: "/static/icons/globalhawk.svg",
    iconSize: [34, 34]
  }),
  "MQ-4C": L.icon({
    iconUrl: "/static/icons/mq4c.svg",
    iconSize: [34, 34]
  }),
  "RQ-170": L.icon({
    iconUrl: "/static/icons/rq170.svg",
    iconSize: [34, 34]
  })
};

function clearLayers(layers) {
  layers.forEach((layer) => map.removeLayer(layer));
  layers.length = 0;
}

function formatTimeWindow(tick, tickSeconds) {
  const totalMinutes = Math.floor((tick * tickSeconds) / 60);
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
  const minutes = String(totalMinutes % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function markerColor(priority) {
  return priority === "high" ? "#f87171" : "#f59e0b";
}

function severityColor(severity) {
  if (severity === "high") return "#f87171";
  if (severity === "medium") return "#f59e0b";
  return "#7dd3fc";
}

function eventTypeLabel(type) {
  if (type === "uav_detection") return "UAV Detection";
  if (type === "uav_route_change") return "UAV Route Change";
  if (type === "scenario_load") return "Scenario Load";
  return type;
}

function setReplayState() {
  document.getElementById("replay-state").textContent = appState.playing ? "Replay Live" : "Standby";
  document.getElementById("speed-2x").classList.toggle("active", appState.playbackRate === 2);
  document.getElementById("speed-5x").classList.toggle("active", appState.playbackRate === 5);
}

function renderUploadState() {
  document.getElementById("upload-filename").textContent = uploadState.filename;
  document.getElementById("upload-status").textContent = uploadState.status;
  document.getElementById("upload-summary").innerHTML = uploadState.summaryHtml || uploadState.summary;
  document.getElementById("run-uploaded-scenario").disabled = !uploadState.valid;
  document.getElementById("staff-review-body").innerHTML = uploadState.staffReviewHtml;
}

function renderAARState() {
  document.getElementById("aar-status").textContent = aarState.status;
  document.getElementById("aar-summary").textContent = aarState.summary;
  document.getElementById("aar-markdown").textContent = aarState.markdown;
  document.getElementById("generate-aar").disabled = !aarState.ready;
  document.getElementById("export-aar").disabled = !(aarState.ready && aarState.generated);
}


function resetAARState() {
  aarState.status = "Awaiting Completion";
  aarState.summary = "Complete the scenario replay to unlock the AAR workflow.";
  aarState.markdown = "No AAR generated yet.";
  aarState.ready = false;
  aarState.generated = false;
  aarState.filename = "";
  renderAARState();
}


function buildStaffReview(result) {
  const review = result.staff_review || {};
  const detected = (review.detected_sections || [])
    .map((section) => `<li>&#10004; ${section}</li>`)
    .join("");
  const missing = (review.missing_sections || [])
    .map((section) => `<li>&#9888; ${section}</li>`)
    .join("");
  const recommendations = (review.recommendations || [])
    .map((item) => `<li>${item}</li>`)
    .join("");

  return `
    <div class="staff-review-block">
      <p><strong>${review.title || "OPORD VALIDATION"}</strong></p>
      <p><strong>Parsing Confidence:</strong> ${review.parsing_confidence ?? 0}%</p>
      <p><strong>Detected Sections:</strong></p>
      <ul class="upload-sections">
        ${detected || "<li>No sections detected</li>"}
      </ul>
      <p><strong>Missing:</strong></p>
      <ul class="upload-sections">
        ${missing || "<li>No critical gaps detected</li>"}
      </ul>
      <p><strong>Recommendation:</strong></p>
      <ul class="upload-sections">
        ${recommendations || "<li>No recommendation generated</li>"}
      </ul>
    </div>
  `;
}

function buildUploadSummary(result) {
  const sectionItems = (result.section_statuses || [])
    .map((section) => `<li>${section.detected ? "&#10003;" : "&#9888;"} ${section.detected ? section.name : `${section.name} not detected`}</li>`)
    .join("");
  const normalized = result.normalized_document || null;
  const normalizedBlock = normalized
    ? `
      <div class="upload-normalized">
        <p><strong>Runnable Scenario:</strong> ${normalized.scenario_name}</p>
        <p><strong>Theater:</strong> ${normalized.theater}</p>
        <p><strong>Objectives:</strong> ${(normalized.objectives || []).join("; ") || "None parsed"}</p>
        <p><strong>Phases:</strong> ${(normalized.phases || []).join("; ") || "None parsed"}</p>
        <p><strong>Metrics:</strong> ${(normalized.evaluation_metrics || []).join("; ") || "None parsed"}</p>
      </div>
    `
    : "";

  const validationLine = result.validation_ok
    ? `<p class="upload-note">Validated and saved as <code>${result.saved_as}</code>.</p>`
    : `<p class="upload-note">${result.validation_error || "Document recognized, but not yet validated as a runnable scenario."}</p>`;

  return `
    <div class="upload-preview">
      <p><strong>File Type:</strong> ${result.file_type || "Unknown"}</p>
      <p><strong>Content Type:</strong> ${result.content_type || "Unknown"}</p>
      <p><strong>Parsing Confidence:</strong> ${result.parser_confidence ?? 0}%</p>
      <p><strong>Sections Parsed:</strong></p>
      <ul class="upload-sections">
        ${sectionItems || "<li>No OPORD sections detected</li>"}
      </ul>
      ${normalizedBlock}
      ${validationLine}
    </div>
  `;
}

function restartReplayTimer() {
  if (appState.playTimer) {
    window.clearInterval(appState.playTimer);
    appState.playTimer = null;
  }

  if (!appState.playing) {
    return;
  }

  const intervalMs = Math.round(1200 / appState.playbackRate);
  appState.playTimer = window.setInterval(stepReplay, intervalMs);
}

function populateScenarioOptions(scenarios, defaultScenarioId) {
  const select = document.getElementById("scenario-select");
  select.innerHTML = "";
  scenarios.forEach((scenario) => {
    const option = document.createElement("option");
    option.value = scenario.scenario_id;
    option.textContent = `${scenario.operation} | ${scenario.description}`;
    if (scenario.scenario_id === defaultScenarioId) {
      option.selected = true;
    }
    select.appendChild(option);
  });
  appState.scenarioId = appState.uploadedScenarioId || defaultScenarioId;
  select.value = appState.scenarioId;
}

function populateSectorControls(data) {
  const unitSelect = document.getElementById("unit-select");
  const sectorSelect = document.getElementById("sector-select");
  unitSelect.innerHTML = "";
  sectorSelect.innerHTML = "";

  data.blue_forces.forEach((unit) => {
    const option = document.createElement("option");
    option.value = unit.id;
    option.textContent = `${unit.id} | ${unit.platform}`;
    unitSelect.appendChild(option);
  });

  data.patrol_sectors.forEach((sector) => {
    const option = document.createElement("option");
    option.value = sector.id;
    option.textContent = `${sector.id} | ${sector.name}`;
    sectorSelect.appendChild(option);
  });
}

function renderStack(containerId, items) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = '<div class="stack-item"><span>No entries.</span></div>';
    return;
  }

  items.forEach((item) => {
    const wrapper = document.createElement("div");
    wrapper.className = "stack-item";
    wrapper.innerHTML = item;
    container.appendChild(wrapper);
  });
}

function renderMap(data) {
  clearLayers(mapLayers.blueMarkers);
  clearLayers(mapLayers.redMarkers);
  clearLayers(mapLayers.sensorCircles);
  clearLayers(mapLayers.threatCircles);
  clearLayers(mapLayers.riskCircles);
  clearLayers(mapLayers.sectorCircles);

  data.patrol_sectors.forEach((sector) => {
    const layer = L.circle([sector.lat, sector.lon], {
      radius: sector.radius_km * 1000,
      color: "#7dd3fc",
      weight: 1,
      dashArray: "2 8",
      fillOpacity: 0.02
    });
    layer.bindPopup(`<b>${sector.name}</b><br>${sector.focus}`);
    layer.addTo(map);
    mapLayers.sectorCircles.push(layer);
  });

  data.risk_zones.forEach((zone) => {
    const layer = L.circle([zone.lat, zone.lon], {
      radius: zone.radius_km * 1000,
      color: "#f59e0b",
      weight: 1,
      fillColor: "#f59e0b",
      fillOpacity: appState.layerState.risk ? 0.08 : 0
    });
    if (appState.layerState.risk) {
      layer.addTo(map);
    }
    layer.bindPopup(`<b>${zone.name}</b><br>${zone.level} risk`);
    mapLayers.riskCircles.push(layer);
  });

  data.blue_forces.forEach((uav) => {
    const marker = L.marker(
      [uav.lat, uav.lon],
      { icon: uavIcons[uav.type] || blueIcon }
    ).bindPopup(
      `<b>${uav.id}</b><br>${uav.platform}<br>${uav.name}<br>Sector: ${uav.sector_name}<br>Speed: ${uav.speed_kts} kts<br>MGRS: ${uav.mgrs}`
    );
    if (appState.layerState.blue) {
      marker.addTo(map);
    }
    mapLayers.blueMarkers.push(marker);

    const sensor = L.circle([uav.lat, uav.lon], {
      radius: uav.sensor_radius_km * 1000,
      color: "#2563eb",
      weight: 1,
      fillColor: "#2563eb",
      fillOpacity: 0.08
    });
    if (appState.layerState.sensors) {
      sensor.addTo(map);
    }
    mapLayers.sensorCircles.push(sensor);
  });

  data.red_forces.forEach((agent) => {
    const marker = L.marker([agent.lat, agent.lon], {
      icon: redIcon
    }).bindPopup(`<b>${agent.name}</b><br>MGRS: ${agent.mgrs}`);
    if (appState.layerState.red) {
      marker.addTo(map);
    }
    mapLayers.redMarkers.push(marker);

    const threat = L.circle([agent.lat, agent.lon], {
      radius: agent.threat_radius_km * 1000,
      color: "#dc2626",
      weight: 1,
      dashArray: "5 7",
      fillColor: "#dc2626",
      fillOpacity: 0.06
    });
    if (appState.layerState.threats) {
      threat.addTo(map);
    }
    mapLayers.threatCircles.push(threat);
  });
}

function renderCoordinatePanel() {
  document.getElementById("coord-lat").textContent =
    coordinateState.lat === null ? "-" : coordinateState.lat.toFixed(5);
  document.getElementById("coord-lon").textContent =
    coordinateState.lon === null ? "-" : coordinateState.lon.toFixed(5);
  document.getElementById("coord-mgrs").textContent = coordinateState.mgrs || "Click on the map";
}

async function updateCoordinatePanel(lat, lon) {
  coordinateState.lat = lat;
  coordinateState.lon = lon;
  coordinateState.mgrs = "Resolving...";
  renderCoordinatePanel();

  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon)
  });
  const response = await fetch(`/api/coords?${params.toString()}`);
  const data = await response.json();
  coordinateState.mgrs = data.mgrs || "Unavailable";
  renderCoordinatePanel();
}


function renderDashboard(data) {
  appState.tick = data.tick;
  appState.durationTicks = data.duration_ticks;
  appState.tickSeconds = data.tick_seconds;

  document.getElementById("operation-title").textContent = data.operation;
  document.getElementById("theater-name").textContent = data.theater;
  document.getElementById("scenario-description").textContent = data.description;
  document.getElementById("contact-count").textContent = String(data.detections.length);
  document.getElementById("tick-seconds").textContent = `${data.tick_seconds} sec`;
  document.getElementById("tick-label").textContent = `Tick ${data.tick}`;
  document.getElementById("timeline-window").textContent = formatTimeWindow(data.tick, data.tick_seconds);
  document.getElementById("timeline-markers").textContent = `Detections: ${data.timeline.length}`;

  const slider = document.getElementById("timeline-slider");
  slider.max = String(data.duration_ticks - 1);
  slider.value = String(data.tick);

  document.getElementById("risk-score").textContent = String(data.risk_summary.score);
  document.getElementById("risk-label").textContent = data.risk_summary.label;
  document.getElementById("blue-count").textContent = String(data.blue_forces.length);
  document.getElementById("red-count").textContent = String(data.red_forces.length);
  document.getElementById("event-count").textContent = String(data.event_log.length);
  const briefLaunch = document.getElementById("brief-launch");
  if (briefLaunch) {
    briefLaunch.href = `/brief?scenario=${encodeURIComponent(data.scenario_id)}`;
  }

  const scenarioComplete = data.tick >= data.duration_ticks - 1;
  aarState.ready = scenarioComplete;
  aarState.status = scenarioComplete ? "Ready" : "Awaiting Completion";
  aarState.summary = scenarioComplete
    ? "Mission replay complete. Generate the formal AAR or export it as a Word document."
    : "Complete the scenario replay to unlock the AAR workflow.";
  if (!scenarioComplete) {
    aarState.generated = false;
    aarState.filename = "";
    aarState.markdown = "No AAR generated yet.";
  }
  renderAARState();

  renderStack("blue-list", data.blue_forces.map((unit) => `
    <strong>${unit.id} | ${unit.platform}</strong>
    <p>${unit.name}</p>
    <span>${unit.speed_kts} kts · ${unit.sensor_radius_km} km sensor · ${unit.sector_name}</span>
  `));

  renderStack("red-list", data.red_forces.map((force) => `
    <strong>${force.id} | ${force.type}</strong>
    <p>${force.name}</p>
    <span>${force.priority} priority · ${force.threat_radius_km} km threat ring</span>
  `));

  renderStack("risk-zones", data.risk_zones.map((zone) => `
    <strong>${zone.name}</strong>
    <p>${zone.level.toUpperCase()} overlay</p>
    <span>${zone.radius_km} km radius · weight ${zone.weight}</span>
  `));

  renderStack("event-log", data.event_log.map((event) => `
    <strong style="color:${severityColor(event.severity)}">T+${event.tick} | ${event.summary}</strong>
    <p>${event.detail}</p>
    <span>${eventTypeLabel(event.type)}</span>
  `));

  renderTimelineEntries(data.timeline);

  populateSectorControls(data);
  renderMap(data);
}

function renderTimelineEntries(entries) {
  const container = document.getElementById("timeline-entries");
  container.innerHTML = "";

  if (!entries.length) {
    container.innerHTML = '<div class="timeline-entry empty">No detection entries yet.</div>';
    return;
  }

  entries.forEach((entry) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `timeline-entry ${entry.tick === appState.tick ? "active" : ""}`;
    item.innerHTML = `<strong>T+${entry.tick}</strong><span>${entry.label}</span>`;
    item.addEventListener("click", async () => {
      appState.tick = entry.tick;
      appState.playing = false;
      restartReplayTimer();
      setReplayState();
      await loadDashboard();
    });
    container.appendChild(item);
  });
}

async function loadDashboard() {
  const params = new URLSearchParams({
    scenario: appState.scenarioId,
    tick: String(appState.tick)
  });
  const response = await fetch(`/api/dashboard?${params.toString()}`);
  const data = await response.json();
  renderDashboard(data);
}

async function loadScenarios() {
  const response = await fetch("/api/scenarios");
  const data = await response.json();
  populateScenarioOptions(data.scenarios, data.default_scenario_id);
  await loadDashboard();
}

async function uploadScenarioFile(file) {
  uploadState.filename = file.name;
  uploadState.status = "Uploading...";
  uploadState.summary = "Sending scenario file to backend.";
  uploadState.summaryHtml = "";
  uploadState.valid = false;
  uploadState.staffReviewHtml = "No review generated yet.";
  renderUploadState();

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/scenario-upload", {
    method: "POST",
    body: formData
  });

  uploadState.status = "Parsing scenario...";
  uploadState.summary = "Validating structured scenario fields.";
  renderUploadState();

  const result = await response.json();
  if (!response.ok) {
    uploadState.status = "No file loaded";
    uploadState.summary = result.error || "Scenario upload failed.";
    uploadState.summaryHtml = "";
    uploadState.valid = false;
    uploadState.staffReviewHtml = "No review generated yet.";
    renderUploadState();
    return;
  }

  appState.uploadedScenarioId = result.validation_ok ? result.scenario_id : null;
  uploadState.status = result.validation_ok ? "Successful Upload" : "Parsing scenario...";
  uploadState.summary = "";
  uploadState.summaryHtml = buildUploadSummary(result);
  uploadState.staffReviewHtml = buildStaffReview(result);
  uploadState.valid = Boolean(result.validation_ok);
  renderUploadState();
}

async function runUploadedScenario() {
  if (!uploadState.valid || !appState.uploadedScenarioId) {
    return;
  }
  appState.tick = 0;
  appState.scenarioId = appState.uploadedScenarioId;
  resetAARState();
  await loadScenarios();
}

async function generateAAR() {
  if (!aarState.ready) {
    return;
  }

  aarState.status = "Generating";
  aarState.summary = "Building Observer / Controller review from mission replay data.";
  aarState.markdown = "Generating AAR...";
  renderAARState();

  const params = new URLSearchParams({
    scenario: appState.scenarioId
  });
  const response = await fetch(`/api/aar?${params.toString()}`);
  const result = await response.json();

  if (!response.ok) {
    aarState.status = "Error";
    aarState.summary = result.error || "AAR generation failed.";
    aarState.markdown = "AAR generation failed.";
    aarState.generated = false;
    renderAARState();
    return;
  }

  aarState.status = "Generated";
  aarState.summary = `Formal AAR prepared by ${result.observer} at ${result.generated_at}.`;
  aarState.markdown = result.markdown || "No AAR body returned.";
  aarState.generated = true;
  aarState.filename = result.filename || "";
  renderAARState();
}

async function exportAAR() {
  if (!(aarState.ready && aarState.generated)) {
    return;
  }

  const params = new URLSearchParams({
    scenario: appState.scenarioId
  });
  const response = await fetch(`/api/aar-export?${params.toString()}`);
  if (!response.ok) {
    aarState.status = "Error";
    aarState.summary = "Word export failed.";
    renderAARState();
    return;
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = aarState.filename || `${appState.scenarioId || "scenario"}_aar.docx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function reassignSector() {
  const unitId = document.getElementById("unit-select").value;
  const sectorId = document.getElementById("sector-select").value;
  await fetch("/api/reassign-sector", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_id: appState.scenarioId,
      unit_id: unitId,
      sector_id: sectorId,
      tick: appState.tick
    })
  });
  await loadDashboard();
}

function stepReplay() {
  if (!appState.playing) return;
  if (appState.tick >= appState.durationTicks - 1) {
    appState.playing = false;
    restartReplayTimer();
    setReplayState();
    return;
  }
  appState.tick += 1;
  loadDashboard();
}

function bindControls() {
  map.on("click", async (event) => {
    await updateCoordinatePanel(event.latlng.lat, event.latlng.lng);
  });

  document.getElementById("scenario-upload-trigger").addEventListener("click", () => {
    document.getElementById("scenario-upload-input").click();
  });

  document.getElementById("scenario-upload-input").addEventListener("change", async (event) => {
    const [file] = event.target.files || [];
    if (!file) {
      return;
    }
    await uploadScenarioFile(file);
  });

  document.getElementById("run-uploaded-scenario").addEventListener("click", runUploadedScenario);
  document.getElementById("generate-aar").addEventListener("click", generateAAR);
  document.getElementById("export-aar").addEventListener("click", exportAAR);

  document.getElementById("scenario-select").addEventListener("change", async (event) => {
    appState.scenarioId = event.target.value;
    appState.tick = 0;
    resetAARState();
    await loadDashboard();
  });

  document.getElementById("timeline-slider").addEventListener("input", async (event) => {
    appState.tick = Number(event.target.value);
    appState.playing = false;
    restartReplayTimer();
    setReplayState();
    await loadDashboard();
  });

  document.getElementById("pause-replay").addEventListener("click", () => {
    appState.playing = false;
    restartReplayTimer();
    setReplayState();
  });

  document.getElementById("play-replay").addEventListener("click", () => {
    appState.playing = true;
    restartReplayTimer();
    setReplayState();
  });

  document.getElementById("rewind-replay").addEventListener("click", async () => {
    appState.playing = false;
    appState.tick = Math.max(0, appState.tick - 1);
    restartReplayTimer();
    setReplayState();
    await loadDashboard();
  });

  document.getElementById("speed-2x").addEventListener("click", () => {
    appState.playbackRate = 2;
    restartReplayTimer();
    setReplayState();
  });

  document.getElementById("speed-5x").addEventListener("click", () => {
    appState.playbackRate = 5;
    restartReplayTimer();
    setReplayState();
  });

  document.getElementById("reassign-button").addEventListener("click", reassignSector);

  [
    ["toggle-blue", "blue"],
    ["toggle-red", "red"],
    ["toggle-sensors", "sensors"],
    ["toggle-threats", "threats"],
    ["toggle-risk", "risk"]
  ].forEach(([elementId, key]) => {
    document.getElementById(elementId).addEventListener("change", async (event) => {
      appState.layerState[key] = event.target.checked;
      await loadDashboard();
    });
  });
}

async function init() {
  appState.playing = true;
  bindControls();
  setReplayState();
  restartReplayTimer();
  renderCoordinatePanel();
  renderUploadState();
  renderAARState();
  await loadScenarios();
}

init();
