import os
import sys
from urllib.parse import parse_qs, urlencode

# Ensure the root project directory is added to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Set serverless environment cache folders
if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ.setdefault('HF_HOME', '/tmp/huggingface')
    os.environ.setdefault('TRANSFORMERS_CACHE', '/tmp/huggingface')
    os.environ.setdefault('TORCH_HOME', '/tmp/torch')

from werkzeug.middleware.proxy_fix import ProxyFix
from app import create_app

# Top-level WSGI application variable for Vercel Python runtime
app = create_app()


class VercelPathFix:
    """
    WSGI Middleware to restore the original client request path on Vercel Serverless Functions.
    Vercel rewrites incoming routes to /api/index.py while passing the original client path in
    headers (HTTP_X_MATCHED_PATH, HTTP_X_VERCEL_MATCHED_PATH) or query parameters (__vercel_path__).
    This middleware updates PATH_INFO so Flask routes properly without generating external redirects.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING', '')
        if '__vercel_path__' in query_string:
            params = parse_qs(query_string, keep_blank_values=True)
            if '__vercel_path__' in params:
                raw_path = params.pop('__vercel_path__')[0]
                path = raw_path if raw_path.startswith('/') else f'/{raw_path}'
                path_only = path.split('?', 1)[0]
                if path_only in ('/api/index.py', '/api/index', '/api', '/api/'):
                    environ['PATH_INFO'] = '/'
                else:
                    environ['PATH_INFO'] = path_only
                pairs = []
                for k, vals in params.items():
                    for v in vals:
                        pairs.append((k, v))
                environ['QUERY_STRING'] = urlencode(pairs)
        else:
            matched_path = (
                environ.get('HTTP_X_MATCHED_PATH') or
                environ.get('HTTP_X_VERCEL_MATCHED_PATH') or
                environ.get('HTTP_X_FORWARDED_PATH') or
                environ.get('HTTP_X_ORIGINAL_URI')
            )
            if matched_path:
                path_only = matched_path.split('?', 1)[0]
                if path_only in ('/api/index.py', '/api/index', '/api', '/api/'):
                    environ['PATH_INFO'] = '/'
                else:
                    environ['PATH_INFO'] = path_only
            else:
                path_info = environ.get('PATH_INFO', '')
                if path_info in ('/api/index.py', '/api/index', '/api', '/api/'):
                    environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)


# Apply ProxyFix for Vercel reverse proxy headers (HTTPS, host, client IP)
# and VercelPathFix for original request path restoration
app.wsgi_app = VercelPathFix(
    ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_prefix=0
    )
)
