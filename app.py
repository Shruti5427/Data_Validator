from flask import Flask, request, send_file, render_template
from services.validator import validate_file
from services.report_generator import generate_report
import os, uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file uploaded", 400
    
    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400
    
    # Save uploaded file
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    # Validate & generate report
    report_id = str(uuid.uuid4())[:8]
    report_path = os.path.join(REPORT_FOLDER, f"report_{report_id}.xlsx")

    validation_result = validate_file(filepath)
    generate_report(validation_result, report_path)

    return f"Report generated! <a href='/download/{report_id}'>Download here</a>"

@app.route("/download/<report_id>")
def download_report(report_id):
    report_path = os.path.join(REPORT_FOLDER, f"report_{report_id}.xlsx")
    if not os.path.exists(report_path):
        return "Report not found", 404
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
