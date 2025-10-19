import os
import uuid
import json
from datetime import datetime
from flask import Flask, request, send_from_directory, render_template, jsonify, url_for
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


# ------------------ Utility Functions ------------------
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


# ------------------ Routes ------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/download/<report_id>")
def download_report(report_id):
    records = load_metadata()
    rec = next((r for r in records if r["id"] == report_id), None)
    if not rec:
        return "Report not found", 404
    return send_from_directory(REPORT_FOLDER, os.path.basename(rec["report_path"]), as_attachment=True)


@app.route("/download_clean/<report_id>")
def download_clean(report_id):
    records = load_metadata()
    rec = next((r for r in records if r["id"] == report_id), None)
    if not rec:
        return "Clean report not found", 404
    return send_from_directory(REPORT_FOLDER, os.path.basename(rec["clean_path"]), as_attachment=True)


# ------------------ Upload Route ------------------
@app.route("/upload", methods=["POST"])
def simple_upload():
    if "file" not in request.files:
        return "No file uploaded", 400
    
    file = request.files["file"]
    if file.filename == "":
        return "Empty filename", 400

    if not allowed_file(file.filename):
        return "Unsupported file type", 400

    # Default validation rules
    rules = request.form.getlist("rules")
    if not rules:
        rules = ["name", "email", "phone", "marks", "duplicates"]

    # Save uploaded file
    try:
        saved_path, original_name = save_uploaded_file(file, app.config.get("UPLOAD_FOLDER"))
        validation_result = validate_file(saved_path, rules)
    except Exception as e:
        return f"Error while processing: {e}", 500

    # Generate report files
    report_id = uuid.uuid4().hex[:8]
    report_path = os.path.join(REPORT_FOLDER, f"report_{report_id}.xlsx")
    clean_path = os.path.join(REPORT_FOLDER, f"clean_{report_id}.xlsx")

    try:
        generate_report(validation_result, report_path, clean_path)
    except Exception as e:
        return f"Report generation failed: {e}", 500

    # Save metadata
    records = load_metadata()
    record = {
        "id": report_id,
        "original_filename": original_name,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "report_path": report_path,
        "clean_path": clean_path,
        "rules": rules,
        "summary": {
            "total": validation_result.get("total", 0),
            "valid": len(validation_result.get("clean_data", [])),
            "invalid": len(validation_result.get("errors", [])),
        },
        "errors": validation_result.get("errors", [])
    }
    records.insert(0, record)
    save_metadata(records)

   #  Build dynamic HTML with inline error summary
    error_html = ""
    errors = validation_result.get("errors", [])
    if errors:
        error_html = """
        <div class="error-section">
          <h5>⚠️ Validation Errors</h5>
          <ul class="error-list">
        """
        for err in errors[:10]:  # Show first 10 errors only
            error_html += f"<li class='error-item'>Row {err.get('Row')} → {err.get('Errors')}</li>"
        if len(errors) > 10:
            error_html += f"<li class='error-item' style='background: var(--info-bg); border-color: var(--info-border);'>... and {len(errors)-10} more errors in the full report</li>"
        error_html += "</ul></div>"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Validation Result</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Inter', sans-serif;
}}

:root {{
  --bg-primary: #000000;
  --bg-gradient-1: rgba(255, 255, 255, 0.05);
  --bg-gradient-2: rgba(255, 255, 255, 0.03);
  --card-bg: rgba(255, 255, 255, 0.03);
  --card-border: rgba(255, 255, 255, 0.1);
  --text-primary: #ffffff;
  --text-secondary: rgba(255, 255, 255, 0.8);
  --text-muted: rgba(255, 255, 255, 0.6);
  --success-color: #10b981;
  --danger-color: #ef4444;
  --info-bg: rgba(59, 130, 246, 0.1);
  --info-border: rgba(59, 130, 246, 0.3);
  --button-primary: #ffffff;
  --button-primary-text: #000000;
  --button-success: #10b981;
  --button-success-text: #ffffff;
  --shadow-color: rgba(0, 0, 0, 0.5);
}}

body.light-mode {{
  --bg-primary: #f5f7fa;
  --bg-gradient-1: rgba(99, 102, 241, 0.08);
  --bg-gradient-2: rgba(139, 92, 246, 0.05);
  --card-bg: rgba(255, 255, 255, 0.95);
  --card-border: rgba(0, 0, 0, 0.08);
  --text-primary: #1e293b;
  --text-secondary: #475569;
  --text-muted: #64748b;
  --success-color: #10b981;
  --danger-color: #ef4444;
  --info-bg: rgba(99, 102, 241, 0.1);
  --info-border: rgba(99, 102, 241, 0.3);
  --button-primary: #6366f1;
  --button-primary-text: #ffffff;
  --button-success: #10b981;
  --button-success-text: #ffffff;
  --shadow-color: rgba(0, 0, 0, 0.1);
}}

body {{
  background: var(--bg-primary);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
  overflow-x: hidden;
  transition: background 0.3s ease;
}}

body::before {{
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--bg-gradient-1) 0%, transparent 70%);
  border-radius: 50%;
  top: -200px;
  right: -200px;
  animation: pulse 8s ease-in-out infinite;
}}

body::after {{
  content: '';
  position: absolute;
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, var(--bg-gradient-2) 0%, transparent 70%);
  border-radius: 50%;
  bottom: -150px;
  left: -150px;
  animation: pulse 10s ease-in-out infinite reverse;
}}

@keyframes pulse {{
  0%, 100% {{ transform: scale(1); opacity: 0.5; }}
  50% {{ transform: scale(1.1); opacity: 0.8; }}
}}

.theme-toggle {{
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  padding: 10px 18px;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px var(--shadow-color);
}}

.theme-toggle:hover {{
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--shadow-color);
}}

.theme-toggle span {{
  font-size: 1.2rem;
}}

.container {{
  position: relative;
  z-index: 1;
  max-width: 800px;
}}

.result-card {{
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 20px;
  box-shadow: 0 20px 60px var(--shadow-color);
  padding: 40px;
  transition: all 0.3s ease;
}}

.result-card:hover {{
  transform: translateY(-5px);
  box-shadow: 0 30px 80px var(--shadow-color);
}}

h3 {{
  color: var(--success-color);
  font-weight: 700;
  font-size: 1.75rem;
  margin-bottom: 25px;
}}

.summary-box {{
  background: var(--info-bg);
  border: 1px solid var(--info-border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 25px;
  text-align: left;
}}

.summary-box p {{
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 0.95rem;
}}

.summary-box p:last-child {{
  margin-bottom: 0;
}}

.summary-box strong {{
  font-weight: 600;
}}

.error-section {{
  margin: 25px 0;
}}

.error-section h5 {{
  color: var(--danger-color);
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 15px;
  text-align: left;
}}

.error-list {{
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
}}

.error-item {{
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 12px 15px;
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 0.88rem;
}}

.btn-download {{
  padding: 12px 30px;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: 12px;
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 6px 15px var(--shadow-color);
  text-decoration: none;
  display: inline-block;
  margin: 5px;
}}

.btn-download:hover {{
  transform: translateY(-2px);
  box-shadow: 0 10px 25px var(--shadow-color);
  text-decoration: none;
}}

.btn-primary-custom {{
  background: var(--button-primary);
  color: var(--button-primary-text);
}}

.btn-success-custom {{
  background: var(--button-success);
  color: var(--button-success-text);
}}

.btn-link-custom {{
  color: var(--text-secondary);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  display: inline-block;
  margin-top: 20px;
}}

.btn-link-custom:hover {{
  color: var(--text-primary);
  text-decoration: none;
}}

@media (max-width: 768px) {{
  .result-card {{
    padding: 30px 20px;
  }}

  h3 {{
    font-size: 1.4rem;
  }}

  .btn-download {{
    width: 100%;
    margin: 5px 0;
  }}

  .theme-toggle {{
    top: 10px;
    right: 10px;
    padding: 8px 14px;
  }}
}}
</style>
</head>
<body>
<button class="theme-toggle" id="themeToggle">
  <span id="themeIcon">🌙</span>
</button>

<div class="container">
  <div class="result-card">
    <h3 class="text-center">✅ Report Generated Successfully!</h3>
    
    <div class="summary-box">
      <p><strong>Total Rows:</strong> {record['summary']['total']}</p>
      <p><strong>Valid Rows:</strong> {record['summary']['valid']}</p>
      <p><strong>Invalid Rows:</strong> {record['summary']['invalid']}</p>
    </div>

    {error_html}

    <div class="text-center mt-4">
      <a href='/download/{report_id}' class='btn-download btn-primary-custom'>⬇️ Download Full Report</a>
      <a href='/download_clean/{report_id}' class='btn-download btn-success-custom'>⬇️ Download Clean Data</a>
    </div>

    <div class="text-center">
      <a href='/' class='btn-link-custom'>← Back to Upload</a>
    </div>
  </div>
</div>

<script>
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');

const savedTheme = localStorage.getItem('theme') || 'dark';
if (savedTheme === 'light') {{
  document.body.classList.add('light-mode');
  themeIcon.textContent = '☀️';
}}

themeToggle.addEventListener('click', () => {{
  document.body.classList.toggle('light-mode');
  const isLight = document.body.classList.contains('light-mode');
  themeIcon.textContent = isLight ? '☀️' : '🌙';
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
}});
</script>
</body>
</html>
"""
