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

@app.route("/upload", methods=["POST"])
def simple_upload():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400

    if not allowed_file(file.filename):
        return "Unsupported file type", 400

    # Use default rules for simple mode
    rules = ["name", "email", "phone", "marks", "duplicates"]

    try:
        saved_path, original_name = save_uploaded_file(file, app.config.get("UPLOAD_FOLDER"))
        validation_result = validate_file(saved_path, rules)
    except Exception as e:
        return f"Error while processing: {e}", 500

    report_id = uuid.uuid4().hex[:8]
    report_basename = f"report_{report_id}.xlsx"
    report_path = os.path.join(REPORT_FOLDER, report_basename)

    clean_only_basename = f"clean_{report_id}.xlsx"
    clean_only_path = os.path.join(REPORT_FOLDER, clean_only_basename)

    try:
        generate_report(validation_result, report_path, clean_only_path)
    except Exception as e:
        return f"Report generation failed: {e}", 500

    # Save metadata
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

    # Return a simple HTML response (like your old version)
    return f"""
    <h3>Report generated successfully!</h3>
    <p>Total rows: {record['summary']['total']}<br>
       Valid rows: {record['summary']['valid']}<br>
       Invalid rows: {record['summary']['invalid']}</p>
    <a href='/download/{report_id}' class='btn btn-primary'>Download Full Report</a><br>
    <a href='/download_clean/{report_id}' class='btn btn-success'>Download Clean Data</a>
    """
