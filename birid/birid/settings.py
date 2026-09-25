"""
Django settings for birid project.
"""

from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# .env lives at the repo root (BASE_DIR.parent) - alongside pyproject.toml
# and docker-compose.yaml, not inside the Django project itself. Secrets/
# JWT key paths (below) stay resolved against BASE_DIR though, since that's
# still the Django project's own directory both locally and in the container.
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Full origins (scheme included), e.g. https://admin.birid.silently.watch -
# Django rejects an HTTPS form POST (the admin login) whose Origin isn't here
# or doesn't match the request's own host+scheme.
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# Behind nginx, which terminates TLS and proxies plain HTTP to gunicorn -
# trust its X-Forwarded-Proto so request.is_secure() (CSRF origin check,
# absolute URLs) reflects the client's real https scheme. Only safe because
# gunicorn is reachable solely through that proxy, never directly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "drf_spectacular",

    "core",
    "stores",
    "buyers",
    "products",
    "news",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "birid.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "birid.wsgi.application"


# Database
# Only used by django.contrib.admin/auth/sessions here - StoreAdmin/Buyer auth
# is stateless JWT, not Django sessions.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ["DB_PORT"],
        # DB_HOST/DB_PORT point at pgbouncer (POOL_MODE=transaction), not
        # postgres directly - a server-side cursor can outlive the single
        # pooled backend connection it was opened on, so Django must not use
        # them. CONN_MAX_AGE is left at 0 (the default): pgbouncer already
        # pools connections, Django holding its own persistent ones on top
        # would just double up the pooling for no benefit.
        "DISABLE_SERVER_SIDE_CURSORS": True,
    }
}


# Password hashing - Argon2 first (matches the old backend's argon2-based hashing),
# Django falls back to the rest only to verify hashes made with a different hasher.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# File storage - MinIO (S3-compatible), via django-storages

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
    # Served by gunicorn itself via WhiteNoise (admin/DRF assets only - user
    # uploads go to MinIO above). Collected on container start, see entrypoint.sh.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

AWS_ACCESS_KEY_ID = os.environ["MINIO_ACCESS_KEY"]
AWS_SECRET_ACCESS_KEY = os.environ["MINIO_SECRET_KEY"]
AWS_STORAGE_BUCKET_NAME = os.environ["MINIO_BUCKET_NAME"]
# AWS_S3_ENDPOINT_URL is where Django/Celery actually send S3 API calls - the
# docker-internal minio:9000 host, not reachable from a browser. File URLs
# handed to clients (model_field.url) need a separately reachable host, so
# MINIO_PUBLIC_URL (domain + bucket, reverse-proxied to minio:9000) overrides
# just the URL that gets built, without changing where API calls go. Unset
# in bare local dev, where the endpoint itself is already browser-reachable.
AWS_S3_ENDPOINT_URL = os.environ["MINIO_ENDPOINT_URL"]
AWS_S3_CUSTOM_DOMAIN = os.environ.get("MINIO_PUBLIC_URL") or None
AWS_S3_URL_PROTOCOL = "https:"
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None


# Celery - offloads CPU-bound work (photo resizing) off the request/response cycle

CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]
CELERY_RESULT_BACKEND = os.environ["CELERY_RESULT_BACKEND"]
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE


# Django REST Framework / drf-spectacular

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPagination",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Birid API",
    "DESCRIPTION": "Clothing marketplace backend - buyers and store admins.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Without this, drf-spectacular reuses the response schema for request
    # bodies too - breaks file upload fields (ImageField/FileField render as
    # a URI string instead of a binary file picker in Swagger).
    "COMPONENT_SPLIT_REQUEST": True,
    # Swagger UI forgets the "Authorize" token on every page reload otherwise.
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    # StoreCategory.cover_processing_status and Buyer.avatar_processing_status
    # both use an identical pending/ready/failed choice set - without this,
    # drf-spectacular can't deterministically name the shared enum component
    # and warns about it. Pin it to one canonical name explicitly.
    "ENUM_NAME_OVERRIDES": {
        "PhotoProcessingStatusEnum": "products.models.PhotoProcessingStatus.choices",
        "OrderStatusEnum": "orders.models.OrderStatus.choices",
        # StoreNews.status and StoreDiscount.status both use an identical
        # draft/active/archived choice set - same reasoning as
        # PhotoProcessingStatusEnum above.
        "ContentStatusEnum": "news.models.NewsStatus.choices",
    },
}


# JWT (RS256, one keypair per principal type - see core/jwt.py)

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "RS256")

STORE_ADMIN_JWT = {
    "PRIVATE_KEY_PATH": BASE_DIR / os.environ["STORE_ADMIN_PRIVATE_KEY_PATH"],
    "PUBLIC_KEY_PATH": BASE_DIR / os.environ["STORE_ADMIN_PUBLIC_KEY_PATH"],
    "ACCESS_TOKEN_EXPIRE_SECONDS": int(os.environ["STORE_ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS"]),
    "REFRESH_TOKEN_EXPIRE_SECONDS": int(os.environ["STORE_ADMIN_REFRESH_TOKEN_EXPIRE_SECONDS"]),
}

BUYER_JWT = {
    "PRIVATE_KEY_PATH": BASE_DIR / os.environ["BUYER_PRIVATE_KEY_PATH"],
    "PUBLIC_KEY_PATH": BASE_DIR / os.environ["BUYER_PUBLIC_KEY_PATH"],
    "ACCESS_TOKEN_EXPIRE_SECONDS": int(os.environ["BUYER_ACCESS_TOKEN_EXPIRE_SECONDS"]),
    "REFRESH_TOKEN_EXPIRE_SECONDS": int(os.environ["BUYER_REFRESH_TOKEN_EXPIRE_SECONDS"]),
}
