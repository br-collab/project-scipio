# Project Scipio

Synthetic operations dashboard exploring how structured planning inputs can become replayable scenario views, event timelines, and after-action review outputs.

---

## Overview

Project Scipio is a lightweight prototype that demonstrates how operational planning documents can move through a clear workflow:

- planning input is uploaded or selected
- scenario data is normalized into a runnable structure
- simulation state is replayed through a dashboard
- post-mission observations are captured in an AAR-style output

The current system uses fully synthetic force, threat, and target data so the repository can be discussed and shared safely as a portfolio project.

---

## Core Concept

Project Scipio explores a different approach to operational simulation.

Instead of manually authoring simulation state, the simulator treats the operational order (OPORD) as the primary source of truth.

Mission documents are parsed, normalized into scenario data, validated against a schema, and executed through a rule-driven simulation engine.

This allows planners to move from:

`static document -> executable scenario -> replay analysis`

---

## Why This Project Exists

The core concept is:

`OPORD -> Scenario -> Simulation -> AAR`

Most plans begin life as static documents. Project Scipio explores what happens when those documents become structured inputs that can be reviewed, replayed, and discussed inside an operational dashboard. The goal is not to replace planning, but to show how planning artifacts can become more executable, observable, and useful for analysis.

---

## Features

- Scenario loader for synthetic baseline and uploaded scenarios
- OPORD-style ingestion for `.txt`, `.md`, `.json`, `.pdf`, and `.docx`
- Mission replay with timeline controls and tick-based event updates
- Interactive event log and after-action review workflow
- Patrol sector reassignment controls
- Blue-force sensor coverage and red-force threat ring overlays
- Generic risk overlay for scenario context
- Coordinate readout with MGRS support
- Executive-style `60-Second Brief` page with a linked Word export option
- Synthetic scenario schema that supports blue forces, red forces, patrol sectors, risk zones, and scripted events

---

## Architecture

High-level flow:

```text
+------------------+      +-------------------+      +-------------------+
|  OPORD / JSON    | ---> | Scenario Service  | ---> | Simulation Service|
|  Upload / Select |      | Parse + Normalize |      | Tick + Replay     |
+------------------+      +-------------------+      +-------------------+
           |                           |                          |
           v                           v                          v
+------------------+      +-------------------+      +-------------------+
| Stored Scenario  |      | Dashboard Routes  | ---> | UI + AAR + Brief  |
| JSON Artifacts   |      | Flask API Layer   |      | Map + Panels      |
+------------------+      +-------------------+      +-------------------+
```

Primary layers in the current prototype:

For a deeper maintainer view, see [docs/architecture.md](docs/architecture.md).

- `routes/`: Flask endpoints for dashboard state, scenario loading, brief pages, and exports
- `services/`: scenario parsing, replay logic, AAR support, and brief generation
- `models/`: scenario and simulation data structures
- `templates/` and `static/`: dashboard UI, brief page, styles, JavaScript, and icons
- `scenarios/`: synthetic scenario definitions and uploaded scenario artifacts

---

## Example Workflow

1. Upload or select a scenario.
2. Parse the source into structured scenario data.
3. Simulate the scenario through replay ticks and event generation.
4. Replay the mission on the dashboard timeline.
5. Review observations through the event log and AAR outputs.

---

## Screenshots

The repository includes screenshot directories for current views and supporting visual artifacts:

- `docs/screenshots/dashboard/`
- `docs/screenshots/opord_upload/`
- `docs/screenshots/replay/`
- `docs/screenshots/aar/`

Recommended assets to embed for a polished GitHub presentation:

- dashboard home view
- successful OPORD upload state
- replay timeline in motion
- 60-Second Brief page

---

## Quick Start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Open the dashboard at:

```text
http://127.0.0.1:8000
```

To restart with the helper script:

```bash
bash scripts/restart_server.sh
```

---

## Repository Structure

```text
Project Scipio/
  app.py
  routes/
  services/
  models/
  scenarios/
  static/
  templates/
  utils/
  scripts/
  tests/
  docs/
```

Directory summary:

- `routes/`: Flask route handlers and API endpoints
- `services/`: business logic for ingestion, simulation, AAR, and brief generation
- `models/`: reusable scenario and replay model objects
- `scenarios/`: synthetic scenario JSON files and uploaded scenario artifacts
- `static/`: CSS, JavaScript, and map/icon assets
- `templates/`: dashboard and brief HTML views
- `utils/`: shared helper utilities such as geospatial support
- `scripts/`: local development helpers such as restart tooling
- `tests/`: pytest coverage for key behaviors
- `docs/`: screenshots and supporting documentation assets

---

## Scenario Schema

Example synthetic scenario shape used by the simulator:

```json
{
  "scenario_id": "default",
  "operation": "Project Scipio",
  "theater": "Cuba",
  "tick_seconds": 300,
  "duration_ticks": 12,
  "blue_forces": [
    {
      "id": "UAV-ALPHA",
      "type": "MQ-9",
      "platform": "ISR UAV",
      "speed_kts": 92,
      "sensor_radius_km": 24,
      "track": [[23.1106, -82.3666], [22.85, -81.9]]
    }
  ],
  "red_forces": [
    {
      "id": "SAM-001",
      "type": "SAM Site",
      "lat": 22.9892,
      "lon": -82.4091,
      "threat_radius_km": 32
    }
  ],
  "patrol_sectors": [
    {
      "id": "SEC-NORTH",
      "name": "Northern Screen",
      "lat": 22.75,
      "lon": -81.3,
      "radius_km": 85
    }
  ],
  "risk_zones": [
    {
      "id": "RISK-ALPHA",
      "name": "Integrated Air Defense Arc",
      "lat": 22.6,
      "lon": -81.2,
      "radius_km": 160,
      "level": "high"
    }
  ],
  "scripted_events": [
    {
      "tick": 1,
      "type": "report",
      "summary": "Mission replay initialized"
    }
  ]
}
```

Reference examples live under `scenarios/`, including `default.json`, `opn_taino.json`, `opn_taino_surge.json`, and `azure_sentinel_001.json`. Uploaded scenario artifacts can also be written there during local use.

---

## Current Limitations

- All force, threat, and target data are synthetic
- Uploaded OPORDs are only as strong as the current parser and mapping rules
- Print output does not fully preserve the live interactive dashboard experience
- The replay engine is intentionally lightweight and not a physics-based simulation
- Export and scenario-ingestion flows are prototype-grade rather than production-hardened
- The dashboard is designed for demonstration, learning, and presentation rather than operational use

---

## Roadmap

- Improve OPORD-to-scenario synthesis so uploaded plans change replay behavior more visibly
- Expand scenario validation and confidence reporting
- Add cleaner screenshot assets and embedded README imagery
- Improve print/export formatting for executive brief artifacts
- Grow test coverage around uploads, replay state, and export workflows
- Continue refining the repository for public GitHub presentation and interview use

---

## License

This project is released under the MIT License. See `LICENSE` for details.

Branding note: Scipio is presented in the UI and documentation as a Ravelo Strategic Solutions, LLC product identity.

# Project Scipio

Synthetic operations dashboard showing how planning inputs can move through a structured workflow into replayable mission state, event timelines, and after-action review outputs.

## Purpose

Project Scipio is a lightweight prototype built around a simple operating model:

`OPORD -> Scenario -> Simulation -> AAR`

The goal is not to replace planning. The goal is to show how planning artifacts can become structured, executable, reviewable inputs that support clearer analysis and shared understanding.

All force, threat, and target data in this repository are synthetic so the project can be discussed and shared safely.

## What The System Does

The current prototype supports five connected steps:

1. A user selects or uploads a planning document or scenario file.
2. The backend normalizes that input into a consistent scenario structure.
3. The simulation layer turns that scenario into tick-based replay state.
4. The dashboard renders positions, detections, threats, and mission events.
5. The system produces an AAR-style report and a short executive brief.

This creates a more structured path from static document to operational discussion:

`static document -> executable scenario -> replay analysis`

## Key Features

- Scenario loader for baseline synthetic scenarios and uploaded artifacts
- OPORD-style ingestion for `.txt`, `.md`, `.json`, `.pdf`, and `.docx`
- Tick-based replay with timeline controls and event generation
- Patrol-sector reassignment controls
- Blue-force sensor coverage and red-force threat ring overlays
- Coordinate readout with MGRS support
- Executive-style `60-Second Brief` page with Word export
- AAR generation with Word export
- Synthetic scenario schema for forces, sectors, risk zones, scripted events, and rules

## Workflow

Project Scipio is easiest to understand as a workflow rather than as a web app:

1. Planning input enters the system through scenario selection or file upload.
2. `ScenarioService` parses, validates, and normalizes the input.
3. `SimulationService` computes replay state for a scenario and tick.
4. Flask routes expose that state to the UI and export endpoints.
5. The dashboard, AAR output, and brief page consume the same structured replay data.

High-level flow:

```text
+------------------+      +-------------------+      +-------------------+
|  OPORD / JSON    | ---> | Scenario Service  | ---> | Simulation Service|
|  Upload / Select |      | Parse + Normalize |      | Tick + Replay     |
+------------------+      +-------------------+      +-------------------+
           |                           |                          |
           v                           v                          v
+------------------+      +-------------------+      +-------------------+
| Stored Scenario  |      | Dashboard Routes  | ---> | UI + AAR + Brief  |
| JSON Artifacts   |      | Flask API Layer   |      | Map + Panels      |
+------------------+      +-------------------+      +-------------------+
```

For a deeper maintainer view, see [docs/architecture.md](docs/architecture.md).

## Quick Start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python -m flask --app app run --host=127.0.0.1 --port=8000 --no-reload
```

Open the dashboard at:

```text
http://127.0.0.1:8000
```

To restart with the helper script:

```bash
bash scripts/restart_server.sh
```

Notes:

- If `8000` is already in use, start the app on another port such as `8011`.
- Run the app from the project virtual environment. If plain `python3 app.py` fails with `ModuleNotFoundError`, the shell is using the wrong Python interpreter.

## How To Run The Project Reliably

Recommended local sequence:

1. Activate `.venv`.
2. Install dependencies from `requirements.txt`.
3. Start Flask with `python -m flask --app app run --host=127.0.0.1 --port=8000 --no-reload`.
4. Open the dashboard in the browser.

## GitHub Deployment Workflow

Project Scipio now treats the local checkout as the editing and validation environment, with GitHub as the system of record for deployment.

Recommended flow:

1. Make and test changes locally.
2. Commit and push to `main`.
3. Let GitHub Actions run the automated test suite from `.github/workflows/ci.yml`.
4. Let your hosting platform deploy from GitHub after the push succeeds.

Deployment readiness in this repository:

- `Dockerfile` starts the Flask app with `gunicorn` and respects the `PORT` environment variable used by cloud hosts.
- `requirements.txt` includes the production WSGI server dependency.
- `scripts/start.sh` remains available for local verification.

The remaining live-hosting step is to connect the GitHub repository to a deployment provider such as Render, Railway, or Fly.io.

## Repository Structure

```text
Project Scipio/
  app.py
  routes/
  services/
  models/
  scenarios/
  static/
  templates/
  utils/
  scripts/
  tests/
  docs/
```

Directory summary:

- `app.py`: Flask app creation and service wiring
- `routes/`: HTTP routes for dashboard pages, APIs, uploads, and exports
- `services/`: ingestion, simulation, AAR, and brief logic
- `models/`: reusable scenario data structures
- `scenarios/`: baseline synthetic scenarios and uploaded scenario artifacts
- `static/`: CSS, JavaScript, and icon assets
- `templates/`: dashboard and brief HTML templates
- `utils/`: shared helpers such as geospatial utilities
- `scripts/`: local development helpers
- `tests/`: pytest coverage for key backend behavior
- `docs/`: architecture notes and screenshots

## Scenario Model

Example synthetic scenario shape used by the simulator:

```json
{
  "scenario_id": "default",
  "operation": "Project Scipio",
  "theater": "Cuba",
  "tick_seconds": 300,
  "duration_ticks": 12,
  "blue_forces": [
    {
      "id": "UAV-ALPHA",
      "type": "MQ-9",
      "platform": "ISR UAV",
      "speed_kts": 92,
      "sensor_radius_km": 24,
      "track": [[23.1106, -82.3666], [22.85, -81.9]]
    }
  ],
  "red_forces": [
    {
      "id": "SAM-001",
      "type": "SAM Site",
      "lat": 22.9892,
      "lon": -82.4091,
      "threat_radius_km": 32
    }
  ],
  "patrol_sectors": [
    {
      "id": "SEC-NORTH",
      "name": "Northern Screen",
      "lat": 22.75,
      "lon": -81.3,
      "radius_km": 85
    }
  ],
  "risk_zones": [
    {
      "id": "RISK-ALPHA",
      "name": "Integrated Air Defense Arc",
      "lat": 22.6,
      "lon": -81.2,
      "radius_km": 160,
      "level": "high"
    }
  ],
  "scripted_events": [
    {
      "tick": 1,
      "type": "report",
      "summary": "Mission replay initialized"
    }
  ]
}
```

Reference examples live in `scenarios/`, including `default.json`, `opn_taino.json`, `opn_taino_surge.json`, and `azure_sentinel_001.json`.

## Screenshots

The repository includes screenshot directories for current views and supporting artifacts:

- `docs/screenshots/dashboard/`
- `docs/screenshots/opord_upload/`
- `docs/screenshots/aar/`

Useful README visuals to embed later:

- dashboard home view
- successful OPORD upload state
- replay timeline in motion
- 60-Second Brief page

## Current Limitations

- All operational data is synthetic
- Uploaded OPORD quality depends on the current parser and mapping rules
- The replay engine is intentionally lightweight and not physics-based
- Export and ingestion flows are still prototype-grade
- The dashboard is designed for demonstration and discussion, not operational deployment

## Roadmap

- Improve OPORD-to-scenario synthesis so uploads change replay behavior more clearly
- Expand scenario validation and confidence reporting
- Improve export formatting for executive and print workflows
- Increase test coverage around upload, replay, and export behavior
- Continue refining presentation quality for portfolio and interview use

## License

This project is released under the MIT License. See `LICENSE` for details.
