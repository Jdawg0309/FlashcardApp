# utils.py - Utility functions
import os
import uuid
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

def save_uploaded_file(file, allowed_extensions, subfolder="uploads"):
    if not file or not file.filename:
        return None
        
    if not allowed_file(file.filename, allowed_extensions):
        return None
        
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(current_app.root_path, "static", subfolder, unique_name)
    
    # Create directory if needed
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    file.save(save_path)
    return unique_name