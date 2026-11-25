"""
Django settings for the Legal Metrology Packaged Commodity Compliance Checker.
Production-grade configuration reading strictly from environment variables via django-environ.
"""
import os
from pathlib import Path
import sys
import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment parser
env = environ.Env()

# Locate .env file
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))
else:
    # Check if critical env variables are already set in system environment
    if "SECRET_KEY" not in os.environ and not env("SECRET_KEY", default=None):
        raise ImproperlyConfigured(
            "Critical Error: .env file is missing and no environment variables are defined. "
            "Please copy .env.example to .env and configure all required variables."
        )

# ==============================================================================
# MANDATORY SECRETS & SYSTEM CHECK (Fail-Fast)
# ==============================================================================
SECRET_KEY = env("SECRET_KEY", default=None)
if not SECRET_KEY or str(SECRET_KEY).strip() == "" or "your-super-secret-key" in str(SECRET_KEY):
    raise ImproperlyConfigured(
        "CRITICAL SECURITY ERROR: SECRET_KEY is not defined or is set to an insecure placeholder. "
        "Define a valid unique SECRET_KEY in your .env file."
    )

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"]
)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local Apps
    "apps.accounts.apps.AccountsConfig",
    "apps.compliance.apps.ComplianceConfig",
    "apps.scans.apps.ScansConfig",
    "apps.reports.apps.ReportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database Configuration (SQLite)
# Read DATABASE_PATH from env with fallback to db.sqlite3 in BASE_DIR
database_path_str = env("DATABASE_PATH", default="db.sqlite3")
database_path = Path(database_path_str)
if not database_path.is_absolute():
    database_path = BASE_DIR / database_path

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(database_path),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

custom_static_root = env("STATIC_ROOT", default="")
STATIC_ROOT = Path(custom_static_root) if custom_static_root else BASE_DIR / "staticfiles"

# Media files (Product & Label Uploads)
MEDIA_URL = "/media/"
custom_media_root = env("MEDIA_ROOT", default="")
MEDIA_ROOT = Path(custom_media_root) if custom_media_root else BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "scans:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Security & Cookie Settings
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Allows JS CSRF header for asynchronous requests
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Legal Metrology & OCR Application Configuration
TESSERACT_CMD = env("TESSERACT_CMD", default="")
TESSERACT_LANGS = env("TESSERACT_LANGS", default="eng")
OCR_MIN_CONFIDENCE = env.float("OCR_MIN_CONFIDENCE", default=45.0)

# Upload Constraints
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=10)
ALLOWED_IMAGE_TYPES = env.list("ALLOWED_IMAGE_TYPES", default=["jpg", "jpeg", "png", "webp"])

# Email Settings
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="compliance@packagedcommodities.gov.local")

# Seeding Variables (Accessed exclusively via management commands)
DJANGO_SUPERUSER_USERNAME = env("DJANGO_SUPERUSER_USERNAME", default="admin")
DJANGO_SUPERUSER_EMAIL = env("DJANGO_SUPERUSER_EMAIL", default="admin@example.com")
DJANGO_SUPERUSER_PASSWORD = env("DJANGO_SUPERUSER_PASSWORD", default="")
DEMO_USER_PASSWORD = env("DEMO_USER_PASSWORD", default="")
