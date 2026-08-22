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


class VercelPathFix:
    """
    WSGI Middleware to ensure proper request routing on Vercel Serverless environment.
    Vercel rewrites routes to the serverless function (e.g. /api/index), passing the
    original client path in `x-vercel-matched-path` (or `x-matched-path`).
    This middleware normalizes PATH_INFO so Flask's URL routing matches the intended route.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = (
            environ.get('HTTP_X_VERCEL_MATCHED_PATH') or 
            environ.get('HTTP_X_MATCHED_PATH') or 
            environ.get('x-vercel-matched-path') or 
            environ.get('x-matched-path')
        )
        if matched_path:
            path = matched_path.split('?')[0]
            if path in ('/api/index.py', '/api/index', '/api', '/api/'):
                environ['PATH_INFO'] = '/'
            elif path:
                environ['PATH_INFO'] = path
        else:
            path_info = environ.get('PATH_INFO', '')
            if path_info in ('/api/index.py', '/api/index', '/api', '/api/'):
                environ['PATH_INFO'] = '/'
        return self.wsgi_app(environ, start_response)


# Wrap Flask's WSGI application with the Vercel path fix middleware
app.wsgi_app = VercelPathFix(app.wsgi_app)
