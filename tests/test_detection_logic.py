from __future__ import annotations

from pathlib import Path

from services.scenario_service import ScenarioService
from services.simulation_service import SimulationService


def test_azure_sentinel_generates_detection_contacts() -> None:
    scenario_service = ScenarioService(Path(__file__).resolve().parents[1] / "scenarios")
    simulation_service = SimulationService(scenario_service)

    state = simulation_service.build_dashboard("AZURE_SENTINEL_001", 0)

    assert state["detections"]
    assert state["detections"][0]["target_name"] == "Matanzas Radar Node"
    assert state["detections"][0]["blue_id"] == "UAV-ALPHA"
    assert state["event_log"][0]["type"] == "uav_detection"
