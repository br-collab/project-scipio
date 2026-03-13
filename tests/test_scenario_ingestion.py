from __future__ import annotations

from pathlib import Path
from shutil import copy2

from services.scenario_service import ScenarioService


def _scenario_service(tmp_path: Path) -> ScenarioService:
    source = Path(__file__).resolve().parents[1] / "scenarios" / "default.json"
    copy2(source, tmp_path / "default.json")
    return ScenarioService(tmp_path)


def test_opord_ingestion_recognizes_human_heading_variants(tmp_path: Path) -> None:
    service = _scenario_service(tmp_path)
    opord = """
TRIDENT LIFT
Situation
Friendly Rangers: 3
Enemy MANPADS: 6

2.a Tasks and Purpose
- Seize MUHA
- Establish airbridge

3) Exec
- Assault runway

4.b.(1) Administration & Logistics
- Fuel priority to assault force

4.b.(2) Assessment / Metrics
- Runway open by H+60

5.c C2 / Comms
- Alternate command net at H+15
"""

    result = service.ingest_uploaded_file("trident_lift.txt", opord.encode())

    assert result["validation_ok"] is True
    assert result["content_type"] == "OPORD"
    assert result["parser_confidence"] > 0
    assert result["staff_review"]["missing_sections"] == []
    assert result["normalized_document"]["objectives"] == ["Seize MUHA", "Establish airbridge"]
    assert result["normalized_document"]["evaluation_metrics"] == ["Runway open by H+60"]
    assert "Command & Signal" in result["sections_found"]


def test_staff_review_recommendations_stay_supportive(tmp_path: Path) -> None:
    service = _scenario_service(tmp_path)
    opord = """
TRIDENT LIFT
Situation
Enemy disposition remains degraded.

Mission
- Seize objective

Execution
- Assault runway
"""

    analysis = service._analyze_document(opord, ".txt")

    assert analysis["staff_review"]["missing_sections"] == ["Logistics", "Metrics", "Command & Signal"]
    assert "Consider adding a logistics sustainment plan" in analysis["staff_review"]["recommendations"]
    assert "Consider defining mission success metrics" in analysis["staff_review"]["recommendations"]


def test_opord_ingestion_synthesizes_force_package_from_uploaded_content(tmp_path: Path) -> None:
    service = _scenario_service(tmp_path)
    opord = """
OPORD: AZURE SENTINEL
Situation
Friendly blue package includes MQ-9 Reaper support and RQ-170 Sentinel deep collection.
Enemy forces include Matanzas radar network, Havana Province SAM coverage, and logistics sustainment nodes.

Mission
- Conduct SEAD and precision strike support across Havana Province
- Restore freedom of maneuver in the Florida Straits

Execution
- Use MQ-9 Reaper to patrol the eastern Cuba ISR corridor
- Push RQ-170 Sentinel on deep surveillance over the Matanzas radar network
- Trigger radar activation when ISR assets penetrate defended airspace

Logistics
- Fuel and sustainment support for MQ-9 Reaper and RQ-170 Sentinel

Metrics
- Time required to detect enemy radar activation
- Coverage persistence across the operational area

Command & Signal
- Primary command net remains active throughout the operation
"""

    result = service.ingest_uploaded_file("azure_sentinel.docx", opord.encode())
    scenario = service.get(result["scenario_id"])

    assert result["validation_ok"] is True
    assert {unit["type"] for unit in scenario.blue_forces} >= {"MQ-9", "RQ-170"}
    assert any("Eastern Cuba ISR Corridor" == sector["name"] for sector in scenario.patrol_sectors)
    assert any("Matanzas Radar Network" == sector["name"] for sector in scenario.patrol_sectors)
    assert any(force["type"] == "Radar Node" for force in scenario.red_forces)
    assert any(force["type"] == "SAM Site" for force in scenario.red_forces)
    assert any(rule["condition"]["type"] == "radar_detected" for rule in scenario.rules)
    assert scenario.blue_forces != service.get(service.default_scenario_id).blue_forces
