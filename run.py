"""
run.py
Local Development Entry Point for SVIT AI Assistant.
Imports and runs create_app() to maintain 100% parity with Vercel serverless production (api/index.py).
"""
import os
from app import create_app

# Instantiate unified application factory
app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  SVIT AI ASSISTANT - LOCAL DEVELOPMENT SERVER")
    print("=" * 60)
    print(f"[*] Environment: Local Development")
    print(f"[*] Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"[*] Running on: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)