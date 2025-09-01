import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Configuration class for the Flask application.
    Loads settings from environment variables and defines app-wide constants.
    """
    # Secret key for session management
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key')

    # PubMed API Credentials
    PUBMED_API_KEY = os.getenv('PUBMED_API_KEY')
    PUBMED_API_TOOL = 'Protocol-Analyzer'
    PUBMED_API_EMAIL = os.getenv('PUBMED_API_EMAIL')

    # Gemini API Key
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # File Upload Settings
    UPLOAD_FOLDER = 'uploads'
    # Allowed file extensions (for a basic check)
    ALLOWED_EXTENSIONS = {'docx'}
    # Allowed MIME type for more robust validation
    ALLOWED_MIMETYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    # Max file size (e.g., 10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # --- Database Settings ---
    # Use SQLite for simplicity
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///analysis.db')
    # Silence the deprecation warning
    SQLALCHEMY_TRACK_MODIFICATIONS = False
