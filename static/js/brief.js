const pageScenarioId = window.SCIPIO_BRIEF_SCENARIO || "";

function renderBriefPoints(containerId, points) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  points.forEach((point) => {
    const wrapper = document.createElement("div");
    wrapper.className = "stack-item";
    wrapper.innerHTML = `<strong>Why this matters</strong><p>${point}</p>`;
    container.appendChild(wrapper);
  });
}

async function loadBriefPage() {
  const params = new URLSearchParams();
  if (pageScenarioId) {
    params.set("scenario", pageScenarioId);
  }
  const response = await fetch(`/api/brief?${params.toString()}`);
  const result = await response.json();
  document.getElementById("brief-page-summary").textContent = result.summary;
  document.getElementById("brief-page-operation").textContent = result.operation;
  renderBriefPoints("brief-page-points", result.key_points || []);
  document.getElementById("brief-page-export").addEventListener("click", async () => {
    const exportParams = new URLSearchParams();
    exportParams.set("scenario", result.scenario_id);
    window.location.href = `/api/brief-export?${exportParams.toString()}`;
  }, { once: true });
}

loadBriefPage();
