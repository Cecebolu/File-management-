import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Secrets live in a local .env file (see .env.example), not in the repo
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]

    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

    # Whole-folder uploads send one form part per file (Flask's default is 1000)
    MAX_FORM_PARTS = 5000

    # Room for the list of file paths sent with a folder upload
    MAX_FORM_MEMORY_SIZE = 5 * 1024 * 1024