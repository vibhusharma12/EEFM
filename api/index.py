import os
import sys

# Ensure backend folder is in Python path for Vercel Serverless
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Vercel serverless functions have a read-only filesystem except for /tmp
os.environ.setdefault("MODEL_DIR", "/tmp/models")
os.environ.setdefault("PERSIST_MODELS", "false")
os.environ.setdefault("CORS_ORIGINS", "*")

from app.main import app
