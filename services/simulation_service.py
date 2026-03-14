from __future__ import annotations

import math
from collections import defaultdict
from random import Random
from typing import Any

from models.entities import Scenario
from services.scenario_service import ScenarioService
from utils.geo import haversine_km, to_mgrs


class SimulationService:
    _PATROL_STEP_RATIO = 0.18
    _WAYPOINT_THRESHOLD = 0.05
    _ORBIT_STEP_RADIANS = 0.9
    _KM_PER_DEG_LAT = 111.0

    def __init__(
        self,
        scenario_service: ScenarioService,
        red_agents: list[Any] | None = None,
    ) -> None:
        self._scenario_service = scenario_service
        self._rng = Random(42)
        self._assignments: dict[str, dict[str, str]] = defaultdict(dict)
        self._manual_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._active_scenario_id: str | None = None
        self._red_agents = red_agents or []

    def build_dashboard(self, scenario_id: str | None, tick: int | None) -> dict[str, Any]:
        scenario = self._scenario_service.get(scenario_id)
        self._record_scenario_load(scenario)
        bounded_tick = self._bounded_tick(scenario, tick)
        blue_forces = self._blue_force_state(scenario, bounded_tick)
        uavs = blue_forces
        for agent in self._red_agents:
            agent.update(uavs)
        red_forces = self._red_force_state(scenario)
        detections = self._build_detections(blue_forces, red_forces)
        rule_state = self._evaluate_rules(scenario, bounded_tick, red_forces)
        event_log = self._build_event_log(scenario, bounded_tick, detections, rule_state["events"])
        risk_summary = self._risk_summary(scenario, rule_state["risk_modifier"])

        return {
            "scenario_id": scenario.scenario_id,
            "operation": scenario.operation,
            "theater": scenario.theater,
            "description": scenario.description,
            "tick": bounded_tick,
            "duration_ticks": scenario.duration_ticks,
            "tick_seconds": scenario.tick_seconds,
            "center": scenario.center,
            "blue_forces": blue_forces,
            "red_forces": red_forces,
            "patrol_sectors": scenario.patrol_sectors,
            "risk_zones": scenario.risk_zones,
            "risk_summary": risk_summary,
            "current_phase": rule_state["phase"],
            "active_effects": sorted(rule_state["flags"]),
            "detections": detections,
            "event_log": event_log,
            "timeline": self._timeline_markers(scenario),
            "assignments": dict(self._assignments[scenario.scenario_id]),
        }

    def reassign_sector(
        self,
        scenario_id: str | None,
        unit_id: str | None,
        sector_id: str | None,
        tick: int | None,
    ) -> dict[str, Any]:
        scenario = self._scenario_service.get(scenario_id)
        if not unit_id or not sector_id:
            raise ValueError("unit_id and sector_id are required")

        valid_units = {unit["id"] for unit in scenario.blue_forces}
        valid_sectors = {sector["id"] for sector in scenario.patrol_sectors}
        if unit_id not in valid_units:
            raise KeyError(f"Unknown unit_id: {unit_id}")
        if sector_id not in valid_sectors:
            raise KeyError(f"Unknown sector_id: {sector_id}")

        bounded_tick = self._bounded_tick(scenario, tick)
        self._assignments[scenario.scenario_id][unit_id] = sector_id
        event = {
            "tick": bounded_tick,
            "type": "uav_route_change",
            "severity": "info",
            "summary": f"{unit_id} route changed to {sector_id}",
            "detail": "UAV patrol sector updated from the dashboard control.",
        }
        self._manual_events[scenario.scenario_id].append(event)
        return {
            "ok": True,
            "assignment": {"unit_id": unit_id, "sector_id": sector_id},
            "event": event,
        }

    def _blue_force_state(self, scenario: Scenario, tick: int) -> list[dict[str, Any]]:
        assignments = self._assignments[scenario.scenario_id]
        forces: list[dict[str, Any]] = []
        for unit in scenario.blue_forces:
            sector_id = assignments.get(unit["id"], unit["default_sector_id"])
            sector = self._sector_by_id(scenario, sector_id)
            lat, lon = self._blue_unit_position(unit, sector, tick)
            forces.append(
                {
                    **unit,
                    "lat": lat,
                    "lon": lon,
                    "mgrs": to_mgrs(lat, lon),
                    "sector_id": sector_id,
                    "sector_name": sector["name"],
                }
            )
        return forces

    def _blue_unit_position(
        self,
        unit: dict[str, Any],
        sector: dict[str, Any],
        tick: int,
    ) -> tuple[float, float]:
        if self._uses_sensor_orbit(unit):
            return self._orbit_position(unit, sector, tick)
        return self._patrol_position(unit["track"], tick)

    def _red_force_state(self, scenario: Scenario) -> list[dict[str, Any]]:
        return [
            {
                **force,
                "lat": force["lat"],
                "lon": force["lon"],
                "mgrs": to_mgrs(force["lat"], force["lon"]),
            }
            for force in scenario.red_forces
        ]

    def _build_detections(
        self, blue_forces: list[dict[str, Any]], red_forces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        for unit in blue_forces:
            for threat in red_forces:
                distance = haversine_km(unit["lat"], unit["lon"], threat["lat"], threat["lon"])
                if distance <= unit["sensor_radius_km"]:
                    confidence = round(0.72 + self._rng.random() * 0.25, 2)
                    detections.append(
                        {
                            "blue_id": unit["id"],
                            "red_id": threat["id"],
                            "target_name": threat["name"],
                            "distance_km": round(distance, 1),
                            "confidence": confidence,
                            "priority": threat["priority"],
                            "type": threat["type"],
                        }
                    )
        return sorted(detections, key=lambda item: (item["distance_km"], item["target_name"]))

    def _build_event_log(
        self,
        scenario: Scenario,
        tick: int,
        detections: list[dict[str, Any]],
        rule_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events = [event for event in self._manual_events[scenario.scenario_id] if event["tick"] <= tick]
        events.extend(rule_events)

        if detections:
            top_detection = detections[0]
            events.append(
                {
                    "tick": tick,
                    "type": "uav_detection",
                    "severity": top_detection["priority"],
                    "summary": f"{top_detection['blue_id']} tracks {top_detection['target_name']}",
                    "detail": f"Contact inside sensor envelope at {top_detection['distance_km']} km.",
                }
            )

        return sorted(events, key=lambda item: (item["tick"], item["summary"]), reverse=True)[:20]

    def _build_ring_breaches(
        self,
        blue_forces: list[dict[str, Any]],
        red_forces: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        breaches: list[dict[str, Any]] = []
        for unit in blue_forces:
            for threat in red_forces:
                distance = haversine_km(unit["lat"], unit["lon"], threat["lat"], threat["lon"])
                if distance <= threat["threat_radius_km"]:
                    breaches.append(
                        {
                            "blue_id": unit["id"],
                            "red_id": threat["id"],
                            "target_name": threat["name"],
                            "type": threat["type"],
                            "distance_km": round(distance, 1),
                        }
                    )
        return breaches

    def _evaluate_rules(
        self,
        scenario: Scenario,
        tick: int,
        red_forces: list[dict[str, Any]],
    ) -> dict[str, Any]:
        flags: dict[str, Any] = {}
        phase = "Baseline"
        events: list[dict[str, Any]] = []
        risk_modifier = 0
        fired_rules: set[str] = set()

        for step in range(tick + 1):
            blue_forces = self._blue_force_state(scenario, step)
            detections = self._build_detections(blue_forces, red_forces)
            ring_breaches = self._build_ring_breaches(blue_forces, red_forces)

            for rule in scenario.rules:
                rule_id = str(rule.get("id", f"rule_{len(fired_rules)}"))
                if rule_id in fired_rules:
                    continue
                if not self._rule_condition_met(
                    rule.get("condition", {}),
                    step,
                    red_forces,
                    detections,
                    ring_breaches,
                    flags,
                ):
                    continue

                fired_rules.add(rule_id)
                for effect in rule.get("effects", []):
                    effect_type = effect.get("type")
                    if effect_type == "set_phase":
                        phase = effect.get("phase", phase)
                    elif effect_type == "set_flag":
                        flags[str(effect.get("flag", "unnamed_flag"))] = effect.get("value", True)
                    elif effect_type == "clear_flag":
                        flags.pop(str(effect.get("flag", "")), None)
                    elif effect_type == "add_risk":
                        risk_modifier += int(effect.get("value", 0))
                    elif effect_type == "add_event":
                        events.append(
                            {
                                "tick": step,
                                "type": "rule_effect",
                                "severity": effect.get("severity", "info"),
                                "summary": effect.get("summary", rule_id),
                                "detail": effect.get("detail", "Scenario rule triggered."),
                            }
                        )

        return {
            "phase": phase,
            "flags": {key for key, value in flags.items() if value},
            "events": events,
            "risk_modifier": risk_modifier,
        }

    def _rule_condition_met(
        self,
        condition: dict[str, Any],
        tick: int,
        red_forces: list[dict[str, Any]],
        detections: list[dict[str, Any]],
        ring_breaches: list[dict[str, Any]],
        flags: dict[str, Any],
    ) -> bool:
        condition_type = condition.get("type")
        if condition_type == "tick_gte":
            return tick >= int(condition.get("tick", 0))
        if condition_type == "tick_eq":
            return tick == int(condition.get("tick", 0))
        if condition_type == "flag_set":
            return bool(flags.get(str(condition.get("flag", ""))))
        if condition_type == "flag_absent":
            return not bool(flags.get(str(condition.get("flag", ""))))
        if condition_type == "detection_count_gte":
            return len(detections) >= int(condition.get("count", 1))
        if condition_type == "radar_detected":
            return self._radar_detected(condition, detections, red_forces)
        if condition_type == "uav_enters_ring":
            return self._uav_enters_ring(condition, ring_breaches)
        if condition_type == "roe_violated":
            return bool(flags.get("roe_violation"))
        if condition_type == "all_of":
            return all(
                self._rule_condition_met(item, tick, red_forces, detections, ring_breaches, flags)
                for item in condition.get("conditions", [])
            )
        if condition_type == "any_of":
            return any(
                self._rule_condition_met(item, tick, red_forces, detections, ring_breaches, flags)
                for item in condition.get("conditions", [])
            )
        return False

    def _radar_detected(
        self,
        condition: dict[str, Any],
        detections: list[dict[str, Any]],
        red_forces: list[dict[str, Any]],
    ) -> bool:
        target_red_id = condition.get("red_id")
        target_type = str(condition.get("red_type", "radar")).lower()
        name_contains = str(condition.get("name_contains", "radar")).lower()

        matching_ids = {
            force["id"]
            for force in red_forces
            if (
                (not target_red_id or force["id"] == target_red_id)
                and (
                    target_type in str(force.get("type", "")).lower()
                    or name_contains in str(force.get("name", "")).lower()
                )
            )
        }
        if target_red_id:
            matching_ids.add(str(target_red_id))

        return any(detection["red_id"] in matching_ids for detection in detections)

    def _uav_enters_ring(
        self,
        condition: dict[str, Any],
        ring_breaches: list[dict[str, Any]],
    ) -> bool:
        target_red_id = condition.get("red_id")
        target_unit_id = condition.get("unit_id")
        return any(
            (not target_red_id or breach["red_id"] == target_red_id)
            and (not target_unit_id or breach["blue_id"] == target_unit_id)
            for breach in ring_breaches
        )

    def _record_scenario_load(self, scenario: Scenario) -> None:
        if self._active_scenario_id == scenario.scenario_id:
            return

        self._active_scenario_id = scenario.scenario_id
        self._manual_events[scenario.scenario_id].append(
            {
                "tick": 0,
                "type": "scenario_load",
                "severity": "info",
                "summary": f"Scenario loaded: {scenario.operation}",
                "detail": f"{scenario.scenario_id} loaded from scenarios/{scenario.scenario_id}.json.",
            }
        )

    def _timeline_markers(self, scenario: Scenario) -> list[dict[str, Any]]:
        markers: list[dict[str, Any]] = []
        red_forces = [dict(force) for force in scenario.red_forces]
        for tick in range(scenario.duration_ticks):
            blue_forces = self._blue_force_state(scenario, tick)
            detections = self._build_timeline_detections(blue_forces, red_forces)
            if not detections:
                continue

            top_detection = detections[0]
            markers.append(
                {
                    "tick": tick,
                    "label": f"{top_detection['blue_id']} detects {top_detection['target_name']}",
                    "severity": top_detection["priority"],
                }
            )
        return markers

    def _build_timeline_detections(
        self, blue_forces: list[dict[str, Any]], red_forces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        for unit in blue_forces:
            for threat in red_forces:
                distance = haversine_km(unit["lat"], unit["lon"], threat["lat"], threat["lon"])
                if distance <= unit["sensor_radius_km"]:
                    detections.append(
                        {
                            "blue_id": unit["id"],
                            "target_name": threat["name"],
                            "distance_km": round(distance, 1),
                            "priority": threat["priority"],
                        }
                    )
        return sorted(detections, key=lambda item: (item["distance_km"], item["target_name"]))

    def _risk_summary(self, scenario: Scenario, modifier: int = 0) -> dict[str, Any]:
        aggregate = sum(zone["weight"] for zone in scenario.risk_zones) + modifier
        label = "ELEVATED" if aggregate >= 9 else "GUARDED"
        return {"score": aggregate, "label": label}

    def _track_position(self, track: list[list[float]], tick: int) -> tuple[float, float]:
        point = track[tick % len(track)]
        return point[0], point[1]

    def _patrol_position(self, route: list[list[float]], tick: int) -> tuple[float, float]:
        if not route:
            raise ValueError("Route must include at least one waypoint")
        if len(route) == 1:
            return route[0][0], route[0][1]

        lat = route[0][0]
        lon = route[0][1]
        target_index = 1

        for _ in range(tick):
            target_lat, target_lon = route[target_index]
            lat += (target_lat - lat) * self._PATROL_STEP_RATIO
            lon += (target_lon - lon) * self._PATROL_STEP_RATIO

            if abs(target_lat - lat) <= self._WAYPOINT_THRESHOLD and abs(target_lon - lon) <= self._WAYPOINT_THRESHOLD:
                target_index = (target_index + 1) % len(route)

        return lat, lon

    def _uses_sensor_orbit(self, unit: dict[str, Any]) -> bool:
        platform = str(unit.get("platform", "")).upper()
        unit_type = str(unit.get("type", "")).upper()
        return "UAV" in platform or unit_type.startswith(("MQ-", "RQ-"))

    def _orbit_position(
        self,
        unit: dict[str, Any],
        sector: dict[str, Any],
        tick: int,
    ) -> tuple[float, float]:
        center_lat = sector["lat"]
        center_lon = sector["lon"]
        orbit_radius_km = min(
            sector["radius_km"] * 0.5,
            max(unit["sensor_radius_km"] * 1.25, 18.0),
        )
        direction = -1 if sum(ord(char) for char in unit["id"]) % 2 else 1
        angle = tick * self._ORBIT_STEP_RADIANS * direction

        lat_radius_deg = orbit_radius_km / self._KM_PER_DEG_LAT
        lon_scale = max(math.cos(math.radians(center_lat)), 0.2)
        lon_radius_deg = orbit_radius_km / (self._KM_PER_DEG_LAT * lon_scale)

        lat = center_lat + math.sin(angle) * lat_radius_deg
        lon = center_lon + math.cos(angle) * lon_radius_deg
        return lat, lon

    def _sector_by_id(self, scenario: Scenario, sector_id: str) -> dict[str, Any]:
        for sector in scenario.patrol_sectors:
            if sector["id"] == sector_id:
                return sector
        raise KeyError(f"Unknown sector_id: {sector_id}")

    def _bounded_tick(self, scenario: Scenario, tick: int | None) -> int:
        value = 0 if tick is None else tick
        return max(0, min(value, scenario.duration_ticks - 1))
