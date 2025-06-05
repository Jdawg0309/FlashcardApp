# config.py

import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-for-prod")

    # Either hard‐code these here, or set them in your environment:
    DB_USER = os.environ.get("DB_USER", "admin")
    DB_PASS = os.environ.get("DB_PASS", "Zubaed123")
    DB_HOST = os.environ.get("DB_HOST", "flashcards.cevge02u6cv8.us-east-1.rds.amazonaws.com")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "flashcards")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
