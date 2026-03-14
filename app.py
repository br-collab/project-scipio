from __future__ import annotations

from pathlib import Path

from flask import Flask

from red_agents import RedAgent
from routes.dashboard import dashboard_bp
from services.aar_service import AARService
from services.brief_service import BriefService
from services.scenario_service import ScenarioService
from services.simulation_service import SimulationService


red_agents = []

a = RedAgent("RED-CONVOY", 22.3, -81.2, "patrol")
a.waypoints = [
    (22.3, -81.2),
    (22.7, -80.9),
    (22.5, -80.4),
]

red_agents.append(a)

red_positions = [
    {
        "name": agent.name,
        "lat": agent.lat,
        "lon": agent.lon,
    }
    for agent in red_agents
]


def create_app() -> Flask:
    app = Flask(__name__)

    scenario_dir = Path(__file__).parent / "scenarios"
    scenario_service = ScenarioService(scenario_dir)
    simulation_service = SimulationService(scenario_service, red_agents=red_agents)
    aar_service = AARService(scenario_service, simulation_service, observer_initials="BR")
    brief_service = BriefService(scenario_service, simulation_service, narrator="BR")

    app.config["scenario_service"] = scenario_service
    app.config["simulation_service"] = simulation_service
    app.config["aar_service"] = aar_service
    app.config["brief_service"] = brief_service
    app.register_blueprint(dashboard_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)
