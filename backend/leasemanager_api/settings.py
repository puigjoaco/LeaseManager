from pathlib import Path
import base64
import hashlib

from cryptography.fernet import Fernet
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
LEGACY_ROOT = PROJECT_ROOT.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, 'leasemanager-dev-only-secret-key'),
    DJANGO_ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1', 'testserver']),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, ['http://localhost:5173', 'http://127.0.0.1:5173']),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, ['http://localhost:5173', 'http://127.0.0.1:5173']),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_SECURE_HSTS_SECONDS=(int, 0),
    DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    DJANGO_SECURE_HSTS_PRELOAD=(bool, False),
    DATABASE_URL=(str, 'postgresql://leasemanager:leasemanager@localhost:5433/leasemanager'),
    REDIS_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/1'),
    DJANGO_CACHE_URL=(str, ''),
    DEMO_LOGIN_USERS=(list, ['demo-admin', 'demo-operador', 'demo-revisor', 'demo-socio']),
    DEMO_LOGIN_PASSWORD=(str, 'demo12345'),
    LEGACY_ROOT_PATH=(str, str(LEGACY_ROOT)),
    FRONTEND_URL=(str, 'http://localhost:5173'),
    DATA_EXPORT_ENCRYPTION_KEY=(str, ''),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env('DJANGO_DEBUG')
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env('DJANGO_CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'core',
    'users',
    'audit',
    'health',
    'patrimonio',
    'operacion',
    'contratos',
    'cobranza',
    'conciliacion',
    'contabilidad',
    'documentos',
    'canales',
    'sii',
    'reporting',
    'compliance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'leasemanager_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'leasemanager_api.wsgi.application'

DATABASES = {
    'default': env.db(),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

CORS_ALLOWED_ORIGINS = env('DJANGO_CORS_ALLOWED_ORIGINS')
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env('DJANGO_SECURE_SSL_REDIRECT') if not DEBUG else False
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_HSTS_SECONDS = env('DJANGO_SECURE_HSTS_SECONDS') if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS') if not DEBUG else False
SECURE_HSTS_PRELOAD = env('DJANGO_SECURE_HSTS_PRELOAD') if not DEBUG else False
X_FRAME_OPTIONS = 'DENY'

CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


def _resolve_cache_location() -> str:
    configured_cache_url = env('DJANGO_CACHE_URL').strip()
    if configured_cache_url:
        return configured_cache_url

    redis_url = env('REDIS_URL').strip()
    if not DEBUG and redis_url:
        return redis_url

    return ''


_cache_location = _resolve_cache_location()

if _cache_location.lower().startswith('locmem://'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': _cache_location.removeprefix('locmem://') or 'leasemanager-local-cache',
            'TIMEOUT': 300,
        }
    }
elif _cache_location:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _cache_location,
            'KEY_PREFIX': 'leasemanager',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'leasemanager-local-cache',
            'TIMEOUT': 300,
        }
    }

LEGACY_ROOT_PATH = env('LEGACY_ROOT_PATH')
DEMO_LOGIN_USERS = set(env('DEMO_LOGIN_USERS'))
DEMO_LOGIN_PASSWORD = env('DEMO_LOGIN_PASSWORD')

_data_export_encryption_key = env('DATA_EXPORT_ENCRYPTION_KEY')


def _normalize_data_export_encryption_key(raw_value: str, *, secret_key: str) -> str:
    if not raw_value:
        return base64.urlsafe_b64encode(
            hashlib.sha256(secret_key.encode('utf-8')).digest()
        ).decode('ascii')

    try:
        Fernet(raw_value.encode('ascii'))
        return raw_value
    except Exception:
        return base64.urlsafe_b64encode(
            hashlib.sha256(raw_value.encode('utf-8')).digest()
        ).decode('ascii')


DATA_EXPORT_ENCRYPTION_KEY = _normalize_data_export_encryption_key(
    _data_export_encryption_key,
    secret_key=SECRET_KEY,
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

