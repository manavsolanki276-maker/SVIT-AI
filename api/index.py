import os
import sys

# Ensure the root project directory is added to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set serverless environment cache folders
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('HF_HOME', '/tmp/huggingface')
    os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface')
    os.environ.setdefault('TORCH_HOME', '/tmp/torch')

from app import create_app

# Top-level WSGI application variable for Vercel Python runtime
app = create_app()
