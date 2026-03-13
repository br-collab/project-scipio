# Architecture

This document explains how Project Scipio moves data from uploaded planning artifacts to replayable dashboard state and exported analysis outputs.

## System Summary

Project Scipio follows a simple pipeline:

`OPORD / scenario input -> scenario normalization -> replay state generation -> UI rendering -> AAR / brief export`

At a high level:

- `app.py` creates the Flask application and wires the core services together
- `routes/dashboard.py` exposes HTML pages and JSON endpoints
- `services/scenario_service.py` handles ingestion, parsing, validation, and scenario persistence
- `services/simulation_service.py` converts a scenario and a tick into live dashboard state
- `services/aar_service.py` and `services/brief_service.py` turn replay state into exported narrative artifacts

## 1. OPORD Ingestion

The ingestion entry point is `ScenarioService.ingest_uploaded_file()` in [services/scenario_service.py](../services/scenario_service.py).

Accepted file types:

- `.txt`
- `.md`
- `.json`
- `.pdf`
- `.docx`

The ingestion flow is:

1. The upload arrives through `POST /api/scenario-upload` in [routes/dashboard.py](../routes/dashboard.py).
2. The service extracts text from the file.
3. The document is analyzed for recognizable OPORD sections such as `Situation`, `Mission`, `Execution`, `Logistics`, `Metrics`, and `Command & Signal`.
4. The service attempts to parse the content directly as structured JSON.
5. If direct JSON parsing fails but the document looks like an OPORD, the service falls back to OPORD-derived scenario construction.
6. The resulting payload is validated and written to `scenarios/uploaded_scenario.json`.

Important design choices:

- The service accepts imperfect human-authored inputs and tries to normalize them rather than assuming perfect formatting.
- PDF and DOCX uploads are reduced to extracted text before analysis.
- Uploaded content is treated as scenario input, not as executable code.

Current constraint:

- Uploaded OPORDs still depend on rule-based extraction and synthetic defaults. They are not full freeform natural-language mission understanding.

## 2. Scenario Synthesis

Scenario synthesis is handled inside `ScenarioService`, primarily through parsing, validation, and OPORD conversion helpers in [services/scenario_service.py](../services/scenario_service.py).

The goal of this layer is to produce a runnable scenario object with a stable shape. A scenario typically includes:

- scenario metadata such as `scenario_id`, `operation`, and `theater`
- `blue_forces`
- `red_forces`
- `patrol_sectors`
- `risk_zones`
- `scripted_events`
- rule and trigger blocks used by replay and reporting

The service loads baseline scenarios from the `scenarios/` directory at startup and exposes them through `ScenarioService.get()` and `ScenarioService.list_summaries()`.

Synthesis responsibilities:

- normalize uploaded content into the scenario schema
- preserve a consistent structure for the simulation layer
- provide deterministic defaults where the uploaded content is incomplete
- refresh in-memory scenario inventory after a successful upload

Why this layer matters:

- It is the translation boundary between business intent and runnable system behavior.
- If the synthesized scenario is too template-driven, the dashboard can appear to “accept” an upload without materially changing the replay.
- That makes this layer the most important place for trust, debuggability, and future product maturity.

## 3. Simulation Loop

The replay engine lives in [services/simulation_service.py](../services/simulation_service.py).

The main entry point is `SimulationService.build_dashboard(scenario_id, tick)`.

For each request, the service:

1. Loads the requested scenario from `ScenarioService`.
2. Bounds the requested tick to the valid replay window.
3. Computes blue-force positions for that tick.
4. Computes red-force state.
5. Generates detections by comparing blue sensor radii against red-force positions.
6. Evaluates rule conditions and effects.
7. Builds the event log and risk summary.
8. Returns a single dashboard payload for the frontend.

Key simulation concepts:

- `tick_seconds` defines how much simulated time each replay tick represents.
- Blue forces move either along predefined tracks or in sensor orbits around assigned patrol sectors.
- Red forces are currently synthetic and mostly static in the scenario payload, with optional `red_agents` support wired from `app.py`.
- Detections are generated from geospatial proximity using sensor radius checks.
- Rule evaluation can change mission phase, set flags, add risk, and generate replay events.
- Manual patrol-sector reassignments are stored in-memory and become part of later replay state.

This design keeps the simulation deterministic enough for demonstration and review while remaining simple to inspect.

## 4. UI Rendering

The frontend is served by Flask templates and static assets:

- main dashboard template: [templates/index.html](../templates/index.html)
- dashboard behavior: [static/js/dashboard.js](../static/js/dashboard.js)
- dashboard styles: [static/css/dashboard.css](../static/css/dashboard.css)
- executive brief page: [templates/brief.html](../templates/brief.html)

Rendering flow:

1. `GET /` serves the dashboard shell.
2. The frontend loads scenario metadata from `GET /api/scenarios`.
3. The frontend requests replay state from `GET /api/dashboard`.
4. The response is rendered into map layers, counters, event panels, timeline controls, and AAR readiness state.
5. Additional actions such as sector reassignment, coordinate conversion, scenario upload, brief generation, and AAR export call dedicated endpoints.

The map uses Leaflet and renders:

- blue-force markers
- red-force markers
- blue sensor circles
- red threat rings
- patrol sector overlays
- generic risk overlays

The UI is intentionally split between:

- left-side operational controls and logs
- center map and replay view
- separate executive brief page for presentation-style explanation

## 5. AAR Generation

After-action reporting is handled by [services/aar_service.py](../services/aar_service.py).

The AAR flow is:

1. The frontend requests `GET /api/aar` after the replay is complete.
2. `AARService.generate_report()` iterates across replay ticks by repeatedly calling `SimulationService.build_dashboard()`.
3. The service aggregates detections, phases, effects, and event narratives.
4. Structured report sections are generated for summary, phase review, metrics, lessons learned, and logic adjustments.
5. The report is returned as JSON and can also be exported as a Word document through `GET /api/aar-export`.

This means the AAR is not a separate simulation. It is a reporting layer built on top of replay state that already exists.

Related output flow:

- [services/brief_service.py](../services/brief_service.py) produces the lighter-weight `60-Second Brief` for presentation and interview use.
- Both AAR and brief exports use `python-docx` to generate `.docx` files.

## Request / Response Flow

A common end-to-end path looks like this:

1. User opens the dashboard.
2. Frontend loads scenario summaries.
3. User selects or uploads a scenario.
4. Backend normalizes the scenario into the schema.
5. Frontend requests replay state for a tick.
6. Simulation service returns computed positions, detections, events, and risk.
7. Frontend renders the map and mission timeline.
8. User completes replay and requests AAR or opens the executive brief page.
9. Backend generates narrative outputs from the replay state.

## Maintainer Notes

Areas most likely to evolve next:

- improving OPORD-to-scenario synthesis so uploaded documents visibly change replay behavior
- expanding rule coverage and scenario validation
- separating screenshot assets into cleaner documentation paths
- improving export fidelity for print and executive-review workflows

If you are new to the codebase, the best order to read is:

1. [app.py](../app.py)
2. [routes/dashboard.py](../routes/dashboard.py)
3. [services/scenario_service.py](../services/scenario_service.py)
4. [services/simulation_service.py](../services/simulation_service.py)
5. [services/aar_service.py](../services/aar_service.py)
6. [static/js/dashboard.js](../static/js/dashboard.js)
