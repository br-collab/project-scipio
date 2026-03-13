from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from utils.geo import to_mgrs

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    return render_template("index.html")


@dashboard_bp.get("/brief")
def brief_page():
    scenario_id = request.args.get("scenario")
    return render_template("brief.html", scenario_id=scenario_id)


@dashboard_bp.get("/api/scenarios")
def scenarios():
    scenario_service = current_app.config["scenario_service"]
    return jsonify(
        {
            "default_scenario_id": scenario_service.default_scenario_id,
            "scenarios": scenario_service.list_summaries(),
        }
    )


@dashboard_bp.get("/api/dashboard")
def dashboard_state():
    simulation_service = current_app.config["simulation_service"]
    scenario_id = request.args.get("scenario")
    tick = request.args.get("tick", type=int)
    return jsonify(simulation_service.build_dashboard(scenario_id=scenario_id, tick=tick))


@dashboard_bp.get("/api/state")
def legacy_state():
    simulation_service = current_app.config["simulation_service"]
    return jsonify(simulation_service.build_dashboard(scenario_id=None, tick=None))


@dashboard_bp.post("/api/reassign-sector")
def reassign_sector():
    simulation_service = current_app.config["simulation_service"]
    payload = request.get_json(silent=True) or {}
    result = simulation_service.reassign_sector(
        scenario_id=payload.get("scenario_id"),
        unit_id=payload.get("unit_id"),
        sector_id=payload.get("sector_id"),
        tick=payload.get("tick"),
    )
    return jsonify(result)


@dashboard_bp.get("/api/coords")
def coords():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400
    return jsonify({"lat": lat, "lon": lon, "mgrs": to_mgrs(lat, lon)})


@dashboard_bp.post("/api/scenario-upload")
def scenario_upload():
    scenario_service = current_app.config["scenario_service"]
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({"error": "No file uploaded"}), 400

    filename = Path(uploaded_file.filename).name
    content = uploaded_file.read()

    try:
        summary = scenario_service.ingest_uploaded_file(filename, content)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(summary)




@dashboard_bp.get("/api/brief")
def executive_brief():
    brief_service = current_app.config["brief_service"]
    scenario_id = request.args.get("scenario")
    return jsonify(brief_service.generate_brief(scenario_id))


@dashboard_bp.get("/api/brief-export")
def executive_brief_export():
    brief_service = current_app.config["brief_service"]
    scenario_id = request.args.get("scenario")
    file_buffer, filename = brief_service.export_docx(scenario_id)
    return send_file(
        file_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

@dashboard_bp.get("/api/aar")
def aar_report():
    aar_service = current_app.config["aar_service"]
    scenario_id = request.args.get("scenario")
    return jsonify(aar_service.generate_report(scenario_id))


@dashboard_bp.get("/api/aar-export")
def aar_export():
    aar_service = current_app.config["aar_service"]
    scenario_id = request.args.get("scenario")
    file_buffer, filename = aar_service.export_docx(scenario_id)
    return send_file(
        file_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
