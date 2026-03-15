# Project Scipio

Synthetic operations dashboard showing how planning inputs can become structured scenarios, replayable mission state, and fast after-action outputs.

## Executive Summary

Project Scipio is a lightweight prototype built around a simple workflow:

`Planning Input -> Scenario Model -> Replayable Simulation -> Brief / AAR Output`

The project is meant to demonstrate a product and systems idea:

- turn planning artifacts into structured machine-readable inputs
- make those inputs visible through a replayable operational dashboard
- produce brief and review outputs from the same underlying scenario state

For CTOs, hiring teams, and technical reviewers, the value is less about military subject matter and more about the product pattern: ingestion, normalization, stateful simulation, and narrative output all working from one shared data model.

All force, threat, and target data in this repository are synthetic.

## Why This Project Exists

Many planning workflows still break across disconnected formats:

- a document for planning
- a spreadsheet for tracking
- a map for situational awareness
- a separate narrative for review

Project Scipio explores what happens when those layers are connected instead. The core bet is that a planning artifact should not end as a static file. It should become an executable, inspectable object that can drive replay, analysis, and discussion.

## What The System Does

At a high level, the system supports four motions:

1. Ingest a baseline scenario or uploaded planning file.
2. Normalize that input into a consistent scenario structure.
3. Replay mission state through a dashboard with forces, threats, events, and geographic context.
4. Generate downstream outputs such as a 60-second brief and after-action review material.

The current application is intentionally lightweight, but the workflow is designed to show a scalable product direction.

## Product Walkthrough

The dashboard demonstrates a compact end-to-end loop:

- `Scenario Loader`: choose a baseline scenario or upload a `.txt`, `.md`, `.json`, `.pdf`, or `.docx` file
- `Run Scenario`: render the operational picture and event stream
- `Event Log`: show mission events and detections as replay context
- `View 60-Second Brief`: generate an executive summary artifact from the same scenario state
- `AAR` flow: produce review-oriented output tied to the scenario and replay logic

That combination is the point of the project. The interface is not just a map. It is a thin decision-support surface connected to ingestion, replay, and narrative export.

## Demo Script

For an interview or live walkthrough, this is the shortest high-signal demo flow:

1. Open the dashboard and explain the product promise:
   `planning input becomes replayable operational state`
2. Point to the `Scenario Loader` and show that the system accepts both baseline scenarios and uploaded planning artifacts.
3. Run the default scenario and frame the map as a synchronized view of blue force, red force, threat envelopes, and mission context.
4. Use the `Event Log` to show that the scenario is not static imagery; it is a time-based replay with machine-readable events.
5. Click `View 60-Second Brief` and explain that executive output is generated from the same scenario state, not rewritten manually in a separate workflow.
6. Close by describing the architecture pattern:
   one normalized scenario model drives visualization, replay, and reporting.

## Architecture

Project Scipio uses a simple service-oriented Flask architecture:

- `app.py`: app wiring and dependency setup
- `routes/`: HTTP routes for the dashboard, APIs, and exports
- `services/scenario_service.py`: scenario loading, validation, upload parsing, and normalization
- `services/simulation_service.py`: replay state generation and dashboard state assembly
- `services/brief_service.py`: executive-style brief generation
- `services/aar_service.py`: after-action review generation
- `models/`: reusable scenario entities and data structures
- `templates/` and `static/`: frontend views, scripts, and styles

Architecturally, the important idea is that the reporting layers consume the same structured scenario state as the UI. That keeps ingestion, replay, and narrative outputs aligned.

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
  .github/workflows/
```

Key folders:

- `scenarios/`: synthetic baseline scenarios and uploaded scenario artifacts
- `scripts/`: local helper scripts for starting and restarting the app
- `tests/`: scenario ingestion and replay-oriented test coverage
- `.github/workflows/`: GitHub Actions automation

## Scenario Model

Scenarios are normalized into a common structure with fields such as:

- metadata and scenario identity
- mission duration
- blue force and red force units
- patrol sectors and risk zones
- scripted mission events

Representative examples live under `scenarios/`, including:

- `default.json`
- `opn_taino.json`
- `opn_taino_surge.json`
- `azure_sentinel_001.json`

This shared scenario model is the backbone of the project. It allows upload parsing, replay logic, and export generation to operate on the same source of truth.

## Local Development

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python -m flask --app app run --host=127.0.0.1 --port=8000
```

Open:

```text
http://127.0.0.1:8000
```

Helper script:

```bash
bash scripts/start.sh
```

If port `8000` is already in use, set another local port before running the app.

## GitHub Demo Workflow

The current demo-friendly workflow is:

1. Work locally and push updates to GitHub.
2. Open the repository in GitHub Codespaces when you need a shareable live demo.
3. Start the app in the codespace.
4. Forward port `8000` and mark it `Public`.
5. Share the forwarded URL for interviews or walkthroughs.

The repository already includes:

- `.devcontainer/devcontainer.json` for Codespaces setup
- `.github/workflows/ci.yml` for automated test runs on push and pull request
- a Dockerfile configured for a production-style `gunicorn` startup path

## Quality And Testing

The repo currently includes automated coverage around ingestion and replay behavior. The GitHub Actions workflow runs `pytest` on pushes and pull requests.

Local test command:

```bash
.venv/bin/python -m pytest -q
```

## Current Limitations

- All operational data is synthetic
- The replay engine is intentionally lightweight and not physics-based
- Upload quality depends on the current parser and scenario mapping rules
- Export and ingestion flows are prototype-grade rather than production-hardened
- The dashboard is designed for demonstration, discussion, and evaluation rather than operational deployment

## Roadmap

- Improve OPORD-to-scenario synthesis so uploads change replay behavior more visibly
- Expand scenario validation and confidence reporting
- Improve export formatting for executive and print workflows
- Increase test coverage around upload, replay, and export behavior
- Continue refining the presentation quality for portfolio, interview, and leadership review use

## Positioning Note

Project Scipio is best understood as a product prototype and architecture demonstration, not as a claim of operational readiness. It is designed to show systems thinking, workflow design, and the ability to connect document ingestion, simulation state, and reporting into one coherent application.

## License

This project is released under the MIT License. See `LICENSE` for details.
