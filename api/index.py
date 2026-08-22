import os
import sys
import traceback

# Ensure the root project directory is added to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set serverless environment cache folders
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('HF_HOME', '/tmp/huggingface')
    os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface')
    os.environ.setdefault('TORCH_HOME', '/tmp/torch')

try:
    from app import create_app
    app = create_app()
except Exception as err:
    tb = traceback.format_exc()
    print(f"[FATAL VERCEL STARTUP ERROR] {tb}", file=sys.stderr)
    from flask import Flask, Response
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all_error(path):
        return Response(
            f"<html><head><title>Application Startup Error</title></head>"
            f"<body style='font-family:sans-serif;padding:30px;background:#f8f9fa;color:#333;'>"
            f"<h2 style='color:#d9534f;'>SVIT-AI Serverless Startup Exception</h2>"
            f"<pre style='background:#fff;padding:15px;border:1px solid #ddd;border-radius:4px;overflow-x:auto;'>{tb}</pre>"
            f"</body></html>",
            status=500,
            mimetype='text/html'
        )
