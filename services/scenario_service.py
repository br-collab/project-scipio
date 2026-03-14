from __future__ import annotations

import json
import math
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import BadZipFile
from zipfile import ZipFile

from models.entities import Scenario


class ScenarioService:
    _OPORD_SECTION_WEIGHTS = {
        "Situation": 20,
        "Mission": 22,
        "Execution": 24,
        "Logistics": 14,
        "Metrics": 10,
        "Command & Signal": 10,
    }

    _ALLOWED_UPLOAD_SUFFIXES = {".txt", ".md", ".json", ".pdf", ".docx"}
    _HEADING_PREFIX = r"(?:(?:\d+[\.\)]|[a-zA-Z](?:[\.\)])?|\(\d+\))\s*)+"
    _LOCATION_ANCHORS = {
        "havana_province": {"name": "Havana Province", "lat": 23.1136, "lon": -82.3666, "focus": "capital air-defense zone"},
        "matanzas_radar_network": {"name": "Matanzas Radar Network", "lat": 23.0411, "lon": -81.5775, "focus": "integrated radar coverage"},
        "eastern_cuba_isr_corridor": {"name": "Eastern Cuba ISR Corridor", "lat": 20.1800, "lon": -75.8300, "focus": "persistent ISR corridor"},
        "florida_straits": {"name": "Florida Straits", "lat": 23.3500, "lon": -80.8500, "focus": "maritime maneuver lane"},
        "holguin_approach": {"name": "Holguin Approach", "lat": 20.8869, "lon": -76.2590, "focus": "eastern approach routes"},
    }
    _LOCATION_PATTERNS = (
        ("matanzas_radar_network", (r"\bmatanzas\b", r"\bradar network\b")),
        ("eastern_cuba_isr_corridor", (r"\beastern cuba\b", r"\bisr corridor\b")),
        ("havana_province", (r"\bhavana province\b", r"\bhavana\b")),
        ("florida_straits", (r"\bflorida straits\b",)),
        ("holguin_approach", (r"\bholgu[ií]n\b",)),
    )
    _BLUE_PLATFORM_CATALOG = (
        {
            "matchers": (r"\bmq-9\b", r"\breaper\b"),
            "type": "MQ-9",
            "platform": "ISR UAV",
            "name": "Reaper Strike Screen",
            "speed_kts": 120,
            "sensor_radius_km": 28,
            "mission": "corridor",
        },
        {
            "matchers": (r"\brq-170\b", r"\bsentinel\b"),
            "type": "RQ-170",
            "platform": "Stealth ISR Aircraft",
            "name": "Sentinel Deep Look",
            "speed_kts": 108,
            "sensor_radius_km": 22,
            "mission": "deep_surveillance",
        },
        {
            "matchers": (r"\bmq-4c\b", r"\bmaritime patrol\b", r"\bp-8\b"),
            "type": "MQ-4C",
            "platform": "Maritime Patrol Aircraft",
            "name": "Maritime Patrol Screen",
            "speed_kts": 205,
            "sensor_radius_km": 34,
            "mission": "maritime",
        },
    )
    _RED_SYSTEM_CATALOG = (
        {
            "kind": "radar",
            "matchers": (r"\bradar\b", r"\bemission", r"\bsurveillance node\b"),
            "type": "Radar Node",
            "priority": "medium",
            "threat_radius_km": 44,
        },
        {
            "kind": "sam",
            "matchers": (r"\bsam\b", r"\bair defense\b", r"\bsa-?\d+\b", r"\bs-300\b", r"\bmissile battery\b"),
            "type": "SAM Site",
            "priority": "high",
            "threat_radius_km": 30,
        },
        {
            "kind": "logistics",
            "matchers": (r"\blogistics\b", r"\bfuel\b", r"\bdepot\b"),
            "type": "Logistics Depot",
            "priority": "medium",
            "threat_radius_km": 14,
        },
    )
    _OPORD_SECTION_PATTERNS = (
        (
            "Situation",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"situation"
                r"|situ?"
                r"|operational situation"
                r"|enemy situation"
                r"|friendly situation"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
        (
            "Mission",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"mission"
                r"|missn?"
                r"|task(?:s)?(?:\s+and\s+purpose)?"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
        (
            "Execution",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"execution"
                r"|exec"
                r"|concept of operations"
                r"|scheme of maneuver"
                r"|conops"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
        (
            "Logistics",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"logistics"
                r"|sustainment"
                r"|service support"
                r"|administration\s*(?:and|&|\/)\s*logistics"
                r"|administration\s*(?:and|&|\/)\s*log"
                r"|admin(?:istration)?\s*(?:and|&|\/)?\s*log(?:istics)?"
                r"|admin\s*\/\s*log"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
        (
            "Metrics",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"metrics"
                r"|assessment"
                r"|assessment\s*(?:\/|&|and)\s*metrics"
                r"|metrics\s*(?:\/|&|and)\s*assessment"
                r"|measures"
                r"|measures of effectiveness"
                r"|measures of performance"
                r"|moe(?:s)?"
                r"|mop(?:s)?"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
        (
            "Command & Signal",
            re.compile(
                rf"^\s*(?:[#>*-]+\s*)?(?:{_HEADING_PREFIX}\s*)?(?:"
                r"command\s*(?:and|&)\s*signal"
                r"|command\s*\/\s*signal"
                r"|cmd\s*(?:and|&|\/)?\s*sig"
                r"|c2"
                r"|c2\s*(?:\/|&|and)\s*comms?"
                r"|signal"
                r"|communications?"
                r")\b.*$",
                re.IGNORECASE,
            ),
        ),
    )

    def __init__(self, scenario_dir: Path) -> None:
        self._scenario_dir = scenario_dir
        self._scenarios, self.default_scenario_id = self._load_scenarios()

    def _load_scenarios(self) -> tuple[dict[str, Scenario], str]:
        scenarios: dict[str, Scenario] = {}
        default_scenario_id: str | None = None
        for path in sorted(self._scenario_dir.glob("*.json")):
            payload = json.loads(path.read_text())
            if not self._is_runnable_scenario(payload):
                continue
            scenario = Scenario.from_dict(payload)
            scenarios[scenario.scenario_id] = scenario
            if path.stem == "default":
                default_scenario_id = scenario.scenario_id
        if not scenarios:
            raise RuntimeError("No synthetic scenarios were found in scenarios/.")
        return scenarios, default_scenario_id or next(iter(scenarios))

    def _is_runnable_scenario(self, payload: dict[str, Any]) -> bool:
        return isinstance(payload, dict) and "scenario_id" in payload

    def get(self, scenario_id: str | None) -> Scenario:
        key = scenario_id or self.default_scenario_id
        if key not in self._scenarios:
            raise KeyError(f"Unknown scenario_id: {key}")
        return self._scenarios[key]

    def list_summaries(self) -> list[dict[str, str]]:
        return [
            {
                "scenario_id": scenario.scenario_id,
                "operation": scenario.operation,
                "theater": scenario.theater,
                "description": scenario.description,
            }
            for scenario in self._scenarios.values()
        ]

    def ingest_uploaded_file(self, filename: str, content: bytes) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix not in self._ALLOWED_UPLOAD_SUFFIXES:
            raise ValueError("Unsupported file type. Use .txt, .md, .json, .pdf, or .docx")

        text = self._extract_upload_text(content, suffix)
        analysis = self._analyze_document(text, suffix)

        try:
            payload = self._parse_uploaded_text(text)
            self._validate_payload(payload)
        except ValueError as exc:
            if analysis["content_type"] == "OPORD":
                try:
                    payload = self._build_scenario_from_opord(filename, text, analysis)
                    self._validate_payload(payload)
                except ValueError as opord_exc:
                    analysis.update(
                        {
                            "validation_ok": False,
                            "validation_error": str(opord_exc),
                        }
                    )
                    return analysis
            else:
                analysis.update(
                    {
                        "validation_ok": False,
                        "validation_error": str(exc),
                    }
                )
                return analysis

        target_path = self._scenario_dir / "uploaded_scenario.json"
        target_path.write_text(json.dumps(payload, indent=2))
        self._scenarios, self.default_scenario_id = self._load_scenarios()

        scenario = self.get(payload["scenario_id"])
        analysis.update(
            {
                "validation_ok": True,
                "scenario_id": scenario.scenario_id,
                "operation": scenario.operation,
                "theater": scenario.theater,
                "description": scenario.description,
                "blue_force_count": len(scenario.blue_forces),
                "red_force_count": len(scenario.red_forces),
                "saved_as": target_path.name,
                "normalized_document": {
                    "scenario_name": payload.get("scenario_name", scenario.operation),
                    "theater": payload.get("theater", scenario.theater),
                    "objectives": payload.get("objectives", []),
                    "blufor": payload.get("blufor", {}),
                    "opfor": payload.get("opfor", {}),
                    "phases": payload.get("phases", []),
                    "triggers": payload.get("triggers", []),
                    "evaluation_metrics": payload.get("evaluation_metrics", []),
                },
            }
        )
        return analysis

    def save_uploaded_scenario(self, filename: str, content: bytes) -> dict[str, Any]:
        result = self.ingest_uploaded_file(filename, content)
        if not result.get("validation_ok"):
            raise ValueError(result.get("validation_error", "Scenario validation failed"))
        return result

    def _parse_uploaded_text(self, text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = json.loads(self._extract_json_block(text))

        if not isinstance(payload, dict):
            raise ValueError("Scenario payload must resolve to a JSON object")
        return payload

    def _extract_upload_text(self, content: bytes, suffix: str) -> str:
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                raise ValueError("No extractable text found in PDF upload")
            return text
        if suffix == ".docx":
            return self._extract_docx_text(content)
        return content.decode("utf-8", errors="ignore")

    def _extract_docx_text(self, content: bytes) -> str:
        try:
            with ZipFile(BytesIO(content)) as archive:
                document_xml = archive.read("word/document.xml")
        except BadZipFile:
            fallback_text = content.decode("utf-8", errors="ignore").strip()
            if fallback_text:
                return fallback_text
            raise ValueError("Invalid DOCX upload: file is not a valid Word document")
        except KeyError as exc:
            raise ValueError("Invalid DOCX upload: missing document.xml") from exc

        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []

        for paragraph in root.findall(".//w:p", namespace):
            fragments = [
                node.text
                for node in paragraph.findall(".//w:t", namespace)
                if node.text
            ]
            if fragments:
                paragraphs.append("".join(fragments))

        text = "\n".join(paragraphs).strip()
        if not text:
            raise ValueError("No extractable text found in DOCX upload")
        return text

    def _analyze_document(self, text: str, suffix: str) -> dict[str, Any]:
        sections_found: list[str] = []
        sections: dict[str, str] = {}
        section_statuses: list[dict[str, Any]] = []
        for canonical_name, pattern in self._OPORD_SECTION_PATTERNS:
            detected = any(pattern.match(line) for line in text.splitlines())
            if detected:
                sections_found.append(canonical_name)
            section_statuses.append(
                {
                    "name": canonical_name,
                    "detected": detected,
                }
            )
        if sections_found:
            sections = self._extract_opord_sections(text)
        section_scores = self._section_scores(sections)

        file_type = suffix.replace(".", "").upper()
        if suffix == ".docx":
            file_type = "DOCX"
        elif suffix == ".pdf":
            file_type = "PDF"

        content_type = "Structured Scenario"
        if sections_found:
            content_type = "OPORD"
        elif suffix == ".json":
            content_type = "Scenario JSON"

        parser_confidence = self._parser_confidence(content_type, sections_found, sections, text)
        missing_sections = [status["name"] for status in section_statuses if not status["detected"]]

        for status in section_statuses:
            status["score"] = section_scores.get(status["name"], 0)

        return {
            "file_type": file_type,
            "content_type": content_type,
            "sections_found": sections_found,
            "sections": sections,
            "section_statuses": section_statuses,
            "parser_confidence": parser_confidence,
            "staff_review": {
                "title": "OPORD VALIDATION",
                "parsing_confidence": parser_confidence,
                "detected_sections": sections_found,
                "missing_sections": missing_sections,
                "recommendations": self._staff_review_recommendations(missing_sections),
            },
        }

    def _parser_confidence(
        self,
        content_type: str,
        sections_found: list[str],
        sections: dict[str, str],
        text: str,
    ) -> int:
        if content_type == "OPORD":
            section_scores = self._section_scores(sections)
            structure_bonus = 6 if len(sections_found) >= 3 else 0
            content_bonus = min(8, max(0, len(text.split()) // 40))
            return min(100, sum(section_scores.values()) + structure_bonus + content_bonus)
        if content_type == "Scenario JSON":
            return 100
        return 68 if sections_found else 54

    def _section_scores(self, sections: dict[str, str]) -> dict[str, int]:
        scores: dict[str, int] = {}
        for section_name, weight in self._OPORD_SECTION_WEIGHTS.items():
            section_text = sections.get(section_name, "").strip()
            if not section_text:
                scores[section_name] = 0
                continue

            word_count = len(section_text.split())
            bullet_count = len(
                [
                    line
                    for line in section_text.splitlines()
                    if re.match(r"^\s*(?:[-*•]|\d+[\.\)])\s+", line)
                ]
            )

            richness = 0.35
            richness += min(0.45, word_count / 120)
            richness += min(0.20, bullet_count * 0.05)
            scores[section_name] = min(weight, round(weight * min(1.0, richness)))
        return scores

    def _staff_review_recommendations(self, missing_sections: list[str]) -> list[str]:
        recommendations: list[str] = []
        if "Logistics" in missing_sections:
            recommendations.append("Consider adding a logistics sustainment plan")
        if "Metrics" in missing_sections:
            recommendations.append("Consider defining mission success metrics")
        if "Command & Signal" in missing_sections:
            recommendations.append("Consider adding command and signal instructions")
        if "Situation" in missing_sections:
            recommendations.append("Consider clarifying the operational environment and opposing forces")
        if "Mission" in missing_sections:
            recommendations.append("Consider stating the mission in a single clear task-and-purpose format")
        if "Execution" in missing_sections:
            recommendations.append("Consider adding the concept of operations and phase sequencing")
        return recommendations[:4]

    def _extract_opord_sections(self, text: str) -> dict[str, str]:
        sections: dict[str, list[str]] = {}
        current_section: str | None = None

        for line in text.splitlines():
            matched_heading = self._matching_heading(line.strip())
            if matched_heading:
                current_section = matched_heading
                sections.setdefault(current_section, [])
                continue
            if current_section:
                sections[current_section].append(line)

        return {name: "\n".join(lines).strip() for name, lines in sections.items()}

    def _matching_heading(self, line: str) -> str | None:
        for canonical_name, pattern in self._OPORD_SECTION_PATTERNS:
            if pattern.match(line):
                return canonical_name
        return None

    def _build_scenario_from_opord(
        self,
        filename: str,
        text: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        template = self.get(self.default_scenario_id)
        sections = analysis.get("sections", {})
        scenario_name = self._detect_scenario_name(filename, text)
        theater = self._detect_theater(text) or template.theater
        combined_text = "\n".join(
            filter(
                None,
                [
                    text,
                    sections.get("Situation", ""),
                    sections.get("Mission", ""),
                    sections.get("Execution", ""),
                    sections.get("Logistics", ""),
                    sections.get("Metrics", ""),
                ],
            )
        )
        objectives = self._extract_list_like_items(sections.get("Mission", ""))
        if not objectives:
            objectives = self._extract_list_like_items(sections.get("Execution", ""))
        phases = self._extract_list_like_items(sections.get("Execution", ""))
        triggers = self._extract_triggers(text)
        metrics = self._extract_list_like_items(sections.get("Metrics", ""))
        situation_text = sections.get("Situation", "")
        blufor = self._extract_force_summary(situation_text, ("friendly", "blufor", "blue"))
        opfor = self._extract_force_summary(situation_text, ("enemy", "opfor", "red"))
        mentioned_locations = self._extract_location_keys(combined_text)
        patrol_sectors = self._build_patrol_sectors_from_opord(mentioned_locations, objectives, template)
        blue_forces = self._build_blue_forces_from_opord(combined_text, patrol_sectors)
        red_forces = self._build_red_forces_from_opord(combined_text, mentioned_locations, opfor)
        risk_zones = self._build_risk_zones_from_opord(red_forces, patrol_sectors)
        center = self._resolve_center(patrol_sectors, red_forces, template.center)
        rules = self._build_uploaded_rules(phases, triggers, metrics, blue_forces, red_forces)

        return {
            "scenario_id": self._slugify(scenario_name),
            "scenario_name": scenario_name,
            "operation": scenario_name,
            "theater": theater,
            "description": self._build_description(scenario_name, theater, objectives),
            "center": center,
            "tick_seconds": template.tick_seconds,
            "duration_ticks": template.duration_ticks,
            "blue_forces": blue_forces,
            "red_forces": red_forces,
            "patrol_sectors": patrol_sectors,
            "risk_zones": risk_zones,
            "scripted_events": self._build_scripted_events(objectives, phases, triggers, metrics),
            "rules": rules,
            "objectives": objectives,
            "blufor": blufor,
            "opfor": opfor,
            "phases": phases,
            "triggers": triggers,
            "evaluation_metrics": metrics,
        }

    def _extract_location_keys(self, text: str) -> list[str]:
        lowered = text.lower()
        matches: list[str] = []
        for key, patterns in self._LOCATION_PATTERNS:
            if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in patterns):
                matches.append(key)
        return matches

    def _build_patrol_sectors_from_opord(
        self,
        mentioned_locations: list[str],
        objectives: list[str],
        template: Scenario,
    ) -> list[dict[str, Any]]:
        sector_keys = list(dict.fromkeys(mentioned_locations))
        if not sector_keys:
            objective_text = " ".join(objectives).lower()
            if "matanzas" in objective_text or "radar" in objective_text:
                sector_keys.append("matanzas_radar_network")
            if "eastern cuba" in objective_text or "isr" in objective_text:
                sector_keys.append("eastern_cuba_isr_corridor")

        if not sector_keys:
            return [dict(sector) for sector in template.patrol_sectors[:2]]

        sectors: list[dict[str, Any]] = []
        for index, key in enumerate(sector_keys[:3], start=1):
            anchor = self._LOCATION_ANCHORS[key]
            sectors.append(
                {
                    "id": f"SEC-{index:02d}",
                    "name": anchor["name"],
                    "lat": anchor["lat"],
                    "lon": anchor["lon"],
                    "radius_km": 72 if "corridor" in key else 58,
                    "focus": anchor["focus"],
                }
            )
        return sectors

    def _build_blue_forces_from_opord(
        self,
        text: str,
        patrol_sectors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        lowered = text.lower()
        detected_specs: list[dict[str, Any]] = []
        for spec in self._BLUE_PLATFORM_CATALOG:
            if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in spec["matchers"]):
                detected_specs.append(spec)

        if not detected_specs:
            detected_specs.append(self._BLUE_PLATFORM_CATALOG[0])

        forces: list[dict[str, Any]] = []
        for index, spec in enumerate(detected_specs, start=1):
            sector = self._sector_for_blue_mission(spec["mission"], patrol_sectors)
            route = self._build_route_for_mission(spec["mission"], sector)
            heading = self._heading_from_route(route)
            forces.append(
                {
                    "id": f"UAV-{index:02d}",
                    "name": spec["name"],
                    "type": spec["type"],
                    "platform": spec["platform"],
                    "heading": heading,
                    "speed_kts": spec["speed_kts"],
                    "sensor_radius_km": spec["sensor_radius_km"],
                    "default_sector_id": sector["id"],
                    "track": route,
                }
            )

        return forces

    def _build_red_forces_from_opord(
        self,
        text: str,
        mentioned_locations: list[str],
        opfor: dict[str, int],
    ) -> list[dict[str, Any]]:
        lowered = text.lower()
        red_forces: list[dict[str, Any]] = []
        preferred_locations = mentioned_locations or ["matanzas_radar_network", "havana_province", "eastern_cuba_isr_corridor"]

        for catalog in self._RED_SYSTEM_CATALOG:
            if not any(re.search(pattern, lowered, re.IGNORECASE) for pattern in catalog["matchers"]):
                continue
            location_key = self._location_for_red_kind(catalog["kind"], preferred_locations, len(red_forces))
            anchor = self._LOCATION_ANCHORS[location_key]
            force_id = f"{catalog['kind'].upper()}-{len(red_forces) + 1:03d}"
            red_forces.append(
                {
                    "id": force_id,
                    "name": f"{anchor['name']} {catalog['type']}",
                    "lat": anchor["lat"],
                    "lon": anchor["lon"],
                    "priority": catalog["priority"],
                    "type": catalog["type"],
                    "threat_radius_km": catalog["threat_radius_km"],
                }
            )

        if not red_forces:
            radar_anchor = self._LOCATION_ANCHORS["matanzas_radar_network"]
            sam_anchor = self._LOCATION_ANCHORS["havana_province"]
            red_forces = [
                {
                    "id": "RADAR-001",
                    "name": f"{radar_anchor['name']} Radar Node",
                    "lat": radar_anchor["lat"],
                    "lon": radar_anchor["lon"],
                    "priority": "medium",
                    "type": "Radar Node",
                    "threat_radius_km": 44,
                },
                {
                    "id": "SAM-001",
                    "name": f"{sam_anchor['name']} SAM Site",
                    "lat": sam_anchor["lat"],
                    "lon": sam_anchor["lon"],
                    "priority": "high",
                    "type": "SAM Site",
                    "threat_radius_km": 30,
                },
            ]

        if opfor:
            for label, count in opfor.items():
                if "radar" in label and not any(force["type"] == "Radar Node" for force in red_forces):
                    anchor = self._LOCATION_ANCHORS["matanzas_radar_network"]
                    red_forces.append(
                        {
                            "id": f"RADAR-{len(red_forces) + 1:03d}",
                            "name": f"{anchor['name']} Radar Node",
                            "lat": anchor["lat"],
                            "lon": anchor["lon"],
                            "priority": "medium",
                            "type": "Radar Node",
                            "threat_radius_km": 44,
                        }
                    )
                if "sam" in label and count > 0 and not any(force["type"] == "SAM Site" for force in red_forces):
                    anchor = self._LOCATION_ANCHORS["havana_province"]
                    red_forces.append(
                        {
                            "id": f"SAM-{len(red_forces) + 1:03d}",
                            "name": f"{anchor['name']} SAM Site",
                            "lat": anchor["lat"],
                            "lon": anchor["lon"],
                            "priority": "high",
                            "type": "SAM Site",
                            "threat_radius_km": 30,
                        }
                    )

        return red_forces[:5]

    def _build_risk_zones_from_opord(
        self,
        red_forces: list[dict[str, Any]],
        patrol_sectors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        zones: list[dict[str, Any]] = []
        for index, force in enumerate(red_forces[:3], start=1):
            zones.append(
                {
                    "id": f"RISK-{index:02d}",
                    "name": f"{force['name']} Risk Envelope",
                    "lat": force["lat"],
                    "lon": force["lon"],
                    "radius_km": force["threat_radius_km"] + 24,
                    "weight": 3 if force["priority"] == "high" else 2,
                    "level": "high" if force["priority"] == "high" else "medium",
                }
            )

        if patrol_sectors and not any("transit risk" in zone["name"].lower() for zone in zones):
            sector = patrol_sectors[0]
            zones.append(
                {
                    "id": f"RISK-{len(zones) + 1:02d}",
                    "name": f"{sector['name']} Transit Risk",
                    "lat": sector["lat"],
                    "lon": sector["lon"],
                    "radius_km": max(35, int(sector["radius_km"] * 0.8)),
                    "weight": 2,
                    "level": "medium",
                }
            )
        return zones

    def _build_uploaded_rules(
        self,
        phases: list[str],
        triggers: list[dict[str, str]],
        metrics: list[str],
        blue_forces: list[dict[str, Any]],
        red_forces: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rules = self._build_rule_blocks(phases, triggers, metrics)
        primary_radar = next((force for force in red_forces if "radar" in force["type"].lower()), None)
        primary_sam = next((force for force in red_forces if "sam" in force["type"].lower()), None)
        primary_blue = blue_forces[0] if blue_forces else None

        if primary_radar:
            rules.append(
                {
                    "id": "radar_activation_on_isr_penetration",
                    "condition": {
                        "type": "radar_detected",
                        "red_id": primary_radar["id"],
                        "name_contains": "radar",
                    },
                    "effects": [
                        {"type": "set_flag", "flag": "radar_activation", "value": True},
                        {
                            "type": "add_event",
                            "severity": "high",
                            "summary": "Radar activation on ISR penetration",
                            "detail": f"{primary_radar['name']} activated after ISR penetration.",
                        },
                        {"type": "add_risk", "value": 2},
                    ],
                }
            )

        if primary_blue and primary_sam:
            rules.append(
                {
                    "id": "sam_reaction_on_ring_entry",
                    "condition": {
                        "type": "uav_enters_ring",
                        "red_id": primary_sam["id"],
                        "unit_id": primary_blue["id"],
                    },
                    "effects": [
                        {"type": "set_flag", "flag": "sam_reaction", "value": True},
                        {
                            "type": "add_event",
                            "severity": "high",
                            "summary": "SAM reaction on ISR penetration",
                            "detail": f"{primary_blue['id']} entered the {primary_sam['name']} threat ring.",
                        },
                        {"type": "add_risk", "value": 2},
                    ],
                }
            )

        return rules

    def _sector_for_blue_mission(
        self,
        mission: str,
        patrol_sectors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mission_map = {
            "deep_surveillance": "matanzas",
            "corridor": "eastern",
            "maritime": "florida",
        }
        match_text = mission_map.get(mission, "")
        for sector in patrol_sectors:
            if match_text and match_text in sector["name"].lower():
                return sector
        if mission == "deep_surveillance" and len(patrol_sectors) > 1:
            return patrol_sectors[1]
        return patrol_sectors[0]

    def _build_route_for_mission(
        self,
        mission: str,
        sector: dict[str, Any],
    ) -> list[list[float]]:
        lat = sector["lat"]
        lon = sector["lon"]
        if mission == "deep_surveillance":
            return [
                [lat + 0.18, lon - 0.42],
                [lat + 0.08, lon - 0.16],
                [lat - 0.06, lon + 0.10],
                [lat - 0.14, lon + 0.28],
                [lat + 0.02, lon + 0.12],
                [lat + 0.16, lon - 0.08],
            ]
        if mission == "maritime":
            return [
                [lat + 0.24, lon - 0.34],
                [lat + 0.16, lon - 0.12],
                [lat + 0.08, lon + 0.10],
                [lat - 0.02, lon + 0.28],
                [lat - 0.08, lon + 0.38],
                [lat + 0.12, lon + 0.08],
            ]
        return [
            [lat + 0.12, lon - 0.28],
            [lat + 0.04, lon - 0.10],
            [lat - 0.05, lon + 0.06],
            [lat - 0.10, lon + 0.20],
            [lat + 0.01, lon + 0.10],
            [lat + 0.14, lon - 0.02],
        ]

    def _heading_from_route(self, route: list[list[float]]) -> int:
        if len(route) < 2:
            return 90
        start, nxt = route[0], route[1]
        angle = math.degrees(math.atan2(nxt[1] - start[1], nxt[0] - start[0]))
        heading = int((90 - angle) % 360)
        return heading

    def _location_for_red_kind(
        self,
        kind: str,
        preferred_locations: list[str],
        offset: int,
    ) -> str:
        if kind == "radar":
            for key in preferred_locations:
                if "matanzas" in key or "radar" in key:
                    return key
            return "matanzas_radar_network"
        if kind == "sam":
            for key in preferred_locations:
                if "havana" in key or "eastern" in key:
                    return key
            return "havana_province"
        if kind == "logistics":
            for key in preferred_locations:
                if "florida" in key or "holguin" in key:
                    return key
            return preferred_locations[min(offset, len(preferred_locations) - 1)]
        return preferred_locations[0]

    def _resolve_center(
        self,
        patrol_sectors: list[dict[str, Any]],
        red_forces: list[dict[str, Any]],
        fallback_center: dict[str, float],
    ) -> dict[str, float]:
        points = [(sector["lat"], sector["lon"]) for sector in patrol_sectors]
        points.extend((force["lat"], force["lon"]) for force in red_forces[:2])
        if not points:
            return fallback_center
        return {
            "lat": round(sum(point[0] for point in points) / len(points), 4),
            "lon": round(sum(point[1] for point in points) / len(points), 4),
        }

    def _detect_scenario_name(self, filename: str, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if self._matching_heading(stripped):
                continue
            if len(stripped) <= 80:
                return stripped.upper()
        return Path(filename).stem.replace("_", " ").replace("-", " ").upper()

    def _detect_theater(self, text: str) -> str | None:
        theater_match = re.search(r"\b(?:theater|ao|area of operations)\s*[:\-]\s*([A-Za-z ]+)", text, re.IGNORECASE)
        if theater_match:
            return theater_match.group(1).strip().title()
        if re.search(r"\bcuba\b", text, re.IGNORECASE):
            return "Cuba"
        return None

    def _extract_list_like_items(self, text: str) -> list[str]:
        items: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            bullet_match = re.match(r"^(?:[-*•]\s+|\d+[\.\)]\s+)(.+)$", stripped)
            if bullet_match:
                items.append(bullet_match.group(1).strip())
            elif ":" not in stripped:
                items.append(stripped)
        return items[:8]

    def _extract_force_summary(self, text: str, keywords: tuple[str, ...]) -> dict[str, int]:
        summary: dict[str, int] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if keywords and not any(keyword in stripped.lower() for keyword in keywords):
                continue
            pairs = re.findall(r"([A-Za-z0-9_\- ]+)\s*[:=]\s*(\d+)", stripped)
            for label, count in pairs:
                summary[self._slugify(label)] = int(count)
        return summary

    def _extract_triggers(self, text: str) -> list[dict[str, str]]:
        triggers: list[dict[str, str]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = re.match(r"^condition\s*[:\-]\s*(.+?)\s+effect\s*[:\-]\s*(.+)$", stripped, re.IGNORECASE)
            if match:
                triggers.append({"condition": self._slugify(match.group(1)), "effect": self._slugify(match.group(2))})
            elif re.search(r"\b(if|when|unless)\b", stripped, re.IGNORECASE):
                triggers.append({"condition": self._slugify(stripped), "effect": "pending_effect"})
        return triggers[:6]

    def _build_description(self, scenario_name: str, theater: str, objectives: list[str]) -> str:
        if objectives:
            return f"{scenario_name} synthetic operation over {theater}. Objectives: {'; '.join(objectives[:3])}."
        return f"{scenario_name} synthetic operation over {theater}."

    def _build_scripted_events(
        self,
        objectives: list[str],
        phases: list[str],
        triggers: list[dict[str, str]],
        metrics: list[str],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        tick = 1
        for objective in objectives[:2]:
            events.append(
                {
                    "tick": tick,
                    "type": "report",
                    "severity": "info",
                    "summary": objective,
                    "detail": "Objective extracted from uploaded operations order.",
                }
            )
            tick += 2
        for phase in phases[:2]:
            events.append(
                {
                    "tick": tick,
                    "type": "report",
                    "severity": "medium",
                    "summary": phase,
                    "detail": "Execution phase extracted from uploaded operations order.",
                }
            )
            tick += 2
        if triggers:
            events.append(
                {
                    "tick": tick,
                    "type": "warning",
                    "severity": "high",
                    "summary": triggers[0]["condition"],
                    "detail": f"Trigger effect: {triggers[0]['effect']}.",
                }
            )
            tick += 2
        if metrics:
            events.append(
                {
                    "tick": tick,
                    "type": "report",
                    "severity": "info",
                    "summary": metrics[0],
                    "detail": "Evaluation metric extracted from uploaded operations order.",
                }
            )
        return events or [
            {
                "tick": 1,
                "type": "report",
                "severity": "info",
                "summary": "Uploaded scenario initialized",
                "detail": "Scenario generated from recognized OPORD sections.",
            }
        ]

    def _build_rule_blocks(
        self,
        phases: list[str],
        triggers: list[dict[str, str]],
        metrics: list[str],
    ) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []

        phase_spacing = 3
        for index, phase in enumerate(phases[:4]):
            rules.append(
                {
                    "id": f"phase_transition_{index + 1}",
                    "condition": {"type": "tick_gte", "tick": index * phase_spacing},
                    "effects": [
                        {"type": "set_phase", "phase": phase},
                        {
                            "type": "add_event",
                            "severity": "info",
                            "summary": f"Phase transition: {phase}",
                            "detail": "Phase advanced from uploaded scenario logic.",
                        },
                    ],
                }
            )

        for index, trigger in enumerate(triggers[:4]):
            tick = self._deadline_tick_from_condition(trigger["condition"])
            rules.append(
                {
                    "id": f"trigger_rule_{index + 1}",
                    "condition": {"type": "tick_gte", "tick": tick},
                    "effects": self._effects_from_trigger(trigger),
                }
            )

        for index, metric in enumerate(metrics[:2]):
            rules.append(
                {
                    "id": f"metric_marker_{index + 1}",
                    "condition": {"type": "tick_gte", "tick": 2 + index * 4},
                    "effects": [
                        {
                            "type": "add_event",
                            "severity": "info",
                            "summary": metric,
                            "detail": "Evaluation metric checkpoint reached.",
                        }
                    ],
                }
            )

        return rules

    def _deadline_tick_from_condition(self, condition: str) -> int:
        minute_match = re.search(r"(\d+)\s*min", condition, re.IGNORECASE)
        if minute_match:
            minutes = int(minute_match.group(1))
            return max(1, math.ceil(minutes / 5) - 1)
        return 4

    def _effects_from_trigger(self, trigger: dict[str, str]) -> list[dict[str, Any]]:
        effect = trigger["effect"]
        severity = "medium"
        risk_value = 1
        detail = f"Trigger fired: {trigger['condition']} -> {effect}."
        effects: list[dict[str, Any]] = [
            {"type": "set_flag", "flag": effect, "value": True},
            {"type": "add_event", "severity": severity, "summary": effect, "detail": detail},
        ]

        if any(keyword in effect for keyword in ("failure", "block", "demolition")):
            severity = "high"
            risk_value = 2
            effects[1]["severity"] = severity
            effects.append({"type": "add_risk", "value": risk_value})

        if any(keyword in effect for keyword in ("phase", "transition")):
            effects.append({"type": "set_phase", "phase": effect.replace("_", " ").title()})

        if any(keyword in effect for keyword in ("roe", "refugee", "humanitarian", "population")):
            effects.append({"type": "set_flag", "flag": "humanitarian_penalty", "value": True})
            effects.append({"type": "add_risk", "value": 2})

        if any(keyword in effect for keyword in ("logistics", "airbridge", "fuel")):
            effects.append({"type": "set_flag", "flag": "logistics_blockage", "value": True})
            effects.append({"type": "add_risk", "value": 2})

        if any(keyword in effect for keyword in ("hvt", "neutralization", "success", "failure")):
            effects.append({"type": "set_flag", "flag": effect, "value": True})

        return effects

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "uploaded_scenario"

    def _extract_json_block(self, content: str) -> str:
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1)

        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No structured JSON scenario payload found in uploaded file")
        return content[start : end + 1]

    def _validate_payload(self, payload: dict[str, Any]) -> None:
        required_fields = (
            "scenario_id",
            "operation",
            "theater",
            "description",
            "center",
            "tick_seconds",
            "duration_ticks",
            "blue_forces",
            "red_forces",
            "patrol_sectors",
            "risk_zones",
            "scripted_events",
        )

        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Scenario field '{field}' is required")

        center = payload["center"]
        if not isinstance(center, dict) or "lat" not in center or "lon" not in center:
            raise ValueError("Scenario center must include 'lat' and 'lon'")

        if not isinstance(payload["tick_seconds"], int) or payload["tick_seconds"] <= 0:
            raise ValueError("tick_seconds must be a positive integer")
        if not isinstance(payload["duration_ticks"], int) or payload["duration_ticks"] <= 0:
            raise ValueError("duration_ticks must be a positive integer")

        list_fields = (
            "blue_forces",
            "red_forces",
            "patrol_sectors",
            "risk_zones",
            "scripted_events",
        )
        for field in list_fields:
            if not isinstance(payload[field], list):
                raise ValueError(f"{field} must be a list")

        if not payload["blue_forces"]:
            raise ValueError("blue_forces must include at least one unit")
        if not payload["red_forces"]:
            raise ValueError("red_forces must include at least one unit")

        # Reuse the main dataclass parser as the final schema check.
        Scenario.from_dict(payload)
