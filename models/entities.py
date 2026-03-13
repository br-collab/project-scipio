from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    operation: str
    theater: str
    description: str
    center: dict[str, float]
    tick_seconds: int
    duration_ticks: int
    blue_forces: list[dict[str, Any]]
    red_forces: list[dict[str, Any]]
    patrol_sectors: list[dict[str, Any]]
    risk_zones: list[dict[str, Any]]
    scripted_events: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    scenario_name: str | None = None
    objectives: list[str] = field(default_factory=list)
    blufor: dict[str, int] = field(default_factory=dict)
    opfor: dict[str, int] = field(default_factory=dict)
    phases: list[str] = field(default_factory=list)
    triggers: list[dict[str, str]] = field(default_factory=list)
    evaluation_metrics: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Scenario":
        return cls(
            scenario_id=payload["scenario_id"],
            operation=payload["operation"],
            theater=payload["theater"],
            description=payload["description"],
            center=payload["center"],
            tick_seconds=payload["tick_seconds"],
            duration_ticks=payload["duration_ticks"],
            blue_forces=payload["blue_forces"],
            red_forces=payload["red_forces"],
            patrol_sectors=payload["patrol_sectors"],
            risk_zones=payload["risk_zones"],
            scripted_events=payload["scripted_events"],
            rules=payload.get("rules", []),
            scenario_name=payload.get("scenario_name"),
            objectives=payload.get("objectives", []),
            blufor=payload.get("blufor", {}),
            opfor=payload.get("opfor", {}),
            phases=payload.get("phases", []),
            triggers=payload.get("triggers", []),
            evaluation_metrics=payload.get("evaluation_metrics", []),
        )
