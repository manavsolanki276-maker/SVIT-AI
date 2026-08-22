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

from werkzeug.middleware.proxy_fix import ProxyFix
from app import create_app

# Top-level WSGI application variable for Vercel Python runtime
app = create_app()


class VercelEntrypointPathFix:
    """
    WSGI Middleware to ensure proper request routing on Vercel Serverless environment.
    Normalizes PATH_INFO only if the raw invocation path is the serverless entrypoint itself
    (e.g., /api/index, /api/index.py), while preserving all actual application routes
    (e.g., /auth/student/login, /student/chat, /api/chat).
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if path_info in ('/api/index.py', '/api/index', '/api', '/api/'):
            environ['PATH_INFO'] = '/'
        return self.wsgi_app(environ, start_response)


# Apply ProxyFix for Vercel reverse proxy headers (HTTPS, host, client IP)
# and VercelEntrypointPathFix for entrypoint path normalization
app.wsgi_app = ProxyFix(
    VercelEntrypointPathFix(app.wsgi_app),
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1
)

