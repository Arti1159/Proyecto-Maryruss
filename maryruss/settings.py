import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get('MARYRUSS_DATA_DIR', BASE_DIR / '.data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEMO_MODE = os.environ.get('MARYRUSS_DEMO', '0') == '1'
DEBUG = os.environ.get('MARYRUSS_DEBUG', '1') == '1'
key_path = DATA_DIR / 'secret-key'
if not key_path.exists():
    try:
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get('MARYRUSS_SECRET_KEY') or key_path.read_text().strip()
ALLOWED_HOSTS = os.environ.get('MARYRUSS_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('MARYRUSS_CSRF_ORIGINS', '').split(',') if x]
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'studio', 'planner',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'maryruss.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages', 'studio.context_processors.environment',
    ]},
}]
WSGI_APPLICATION = 'maryruss.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.environ.get('MARYRUSS_DB', str(DATA_DIR / ('demo.sqlite3' if DEMO_MODE else 'maryruss.sqlite3'))),
    'OPTIONS': {'timeout': 30},
}}
from django.core.exceptions import ImproperlyConfigured
database_path = Path(DATABASES['default']['NAME']).resolve()
if DEMO_MODE and database_path == (DATA_DIR / 'maryruss.sqlite3').resolve():
    raise ImproperlyConfigured('El modo demo no puede abrir la base real maryruss.sqlite3.')
if not DEMO_MODE and database_path == (DATA_DIR / 'demo.sqlite3').resolve():
    raise ImproperlyConfigured('La base demo.sqlite3 requiere MARYRUSS_DEMO=1.')
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/ingresar/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/ingresar/'
SESSION_COOKIE_NAME = 'maryruss_demo_session' if DEMO_MODE else 'maryruss_session'
CSRF_COOKIE_NAME = 'maryruss_demo_csrf' if DEMO_MODE else 'maryruss_csrf'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
if os.environ.get('MARYRUSS_TRUST_PROXY') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Optional real online research. Keys stay on the server and never in templates.
MARYRUSS_RESEARCH_API_KEY = os.environ.get('MARYRUSS_RESEARCH_API_KEY') or os.environ.get('TAVILY_API_KEY', '')

# Bounded variant formsets use up to 5 fields per row plus management fields.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 7000
