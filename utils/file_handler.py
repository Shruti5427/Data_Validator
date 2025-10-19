import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"csv", "xlsx"}


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS


def get_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def save_uploaded_file(file_obj, upload_folder):
    """
    Save uploaded file to upload_folder and return (saved_path, original_filename)
    """
    orig_name = file_obj.filename
    ext = get_extension(orig_name)
    safe_name = secure_filename(orig_name)
    unique_name = f"{os.path.splitext(safe_name)[0]}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(upload_folder, unique_name)
    # Ensure upload folder exists
    os.makedirs(upload_folder, exist_ok=True)
    file_obj.save(path)
    return path, orig_name
