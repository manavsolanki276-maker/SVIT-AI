import os
import tempfile

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'svit-super-secret-key'
    
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        if _db_url.startswith('postgres://'):
            _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    elif os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(tempfile.gettempdir(), "svit_assistant.db")}'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/database.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False