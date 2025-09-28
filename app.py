import os
import uuid
import json
from datetime import datetime
from flask import Flask, request, send_file, render_template, jsonify, url_for
from services.validator import validate_file
from services.report_generator import generate_report
from utils.file_handler import save_uploaded_file, allowed_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
METADATA_FILE = os.path.join(REPORT_FOLDER, "metadata.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def save_metadata(records):
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def api_upload():
    # Expecting: file, rules (multiple checkbox values), clean_only (optional)
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Unsupported file type"}), 400

    # rules passed as multiple values 'rules'
    rules = request.form.getlist("rules") or []
    clean_only = request.form.get("clean_only") in ("1", "true", "on")

    # Save uploaded file
    try:
        saved_path, original_name = save_uploaded_file(file, app.config.get("UPLOAD_FOLDER"))
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to save file: {e}"}), 500

    # Validate
    try:
        validation_result = validate_file(saved_path, rules)
    except Exception as e:
        return jsonify({"success": False, "error": f"Validation error: {e}"}), 500

    # Generate report(s)
    report_id = uuid.uuid4().hex[:8]
    report_basename = f"report_{report_id}.xlsx"
    report_path = os.path.join(REPORT_FOLDER, report_basename)

    clean_only_basename = f"clean_{report_id}.xlsx"
    clean_only_path = os.path.join(REPORT_FOLDER, clean_only_basename)

    try:
        generate_report(validation_result, report_path, clean_only_path)
    except Exception as e:
        return jsonify({"success": False, "error": f"Report generation failed: {e}"}), 500

    # Save metadata record
    records = load_metadata()
    record = {
        "id": report_id,
        "original_filename": original_name,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "report_path": report_path,
        "clean_path": clean_only_path,
        "rules": rules,
        "summary": {
            "total": validation_result.get("total", 0),
            "valid": len(validation_result.get("clean_data", [])),
            "invalid": len(validation_result.get("errors", [])),
        }
    }
    records.insert(0, record)
    save_metadata(records)

    response = {
        "success": True,
        "report_id": report_id,
        "summary": record["summary"],
        "download_report_url": url_for("download_report", report_id=report_id),
        "download_clean_url": url_for("download_clean", report_id=report_id),
    }
    return jsonify(response)


@app.route("/api/reports", methods=["GET"])
def api_reports():
    records = load_metadata()
    # include only necessary metadata
    safe_records = []
    for r in records:
        safe_records.append({
            "id": r.get("id"),
            "original_filename": r.get("original_filename"),
            "uploaded_at": r.get("uploaded_at"),
            "rules": r.get("rules", []),
            "summary": r.get("summary", {"total": 0, "valid": 0, "invalid": 0})
        })
    return jsonify({"success": True, "reports": safe_records})


@app.route("/download/<report_id>")
def download_report(report_id):
    records = load_metadata()
    rec = next((r for r in records if r["id"] == report_id), None)
    if not rec or not os.path.exists(rec["report_path"]):
        return "Report not found", 404
    return send_file(rec["report_path"], as_attachment=True)


@app.route("/download_clean/<report_id>")
def download_clean(report_id):
    records = load_metadata()
    rec = next((r for r in records if r["id"] == report_id), None)
    if not rec or not os.path.exists(rec["clean_path"]):
        return "Clean report not found", 404
    return send_file(rec["clean_path"], as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
