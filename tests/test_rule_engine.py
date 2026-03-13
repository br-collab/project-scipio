from __future__ import annotations

from pathlib import Path

from services.scenario_service import ScenarioService
from services.simulation_service import SimulationService


def test_azure_sentinel_rule_effects_persist_across_replay() -> None:
    scenario_service = ScenarioService(Path(__file__).resolve().parents[1] / "scenarios")
    simulation_service = SimulationService(scenario_service)

    early_state = simulation_service.build_dashboard("AZURE_SENTINEL_001", 0)
    late_state = simulation_service.build_dashboard("AZURE_SENTINEL_001", 11)

    assert "sam_activated" in early_state["active_effects"]
    assert "threat_escalated" in early_state["active_effects"]
    assert "sam_activated" in late_state["active_effects"]
    assert "threat_escalated" in late_state["active_effects"]
    assert any(event["summary"] == "SAM activated" for event in late_state["event_log"])
    assert any(event["summary"] == "Threat escalated" for event in late_state["event_log"])
