from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "imagekit",
    "axes",
    "django_extensions",
]

LOCAL_APPS = [
    "core.apps.CoreConfig",
    "vehicles.apps.VehiclesConfig",
    "catalogue.apps.CatalogueConfig",
    "analytics.apps.AnalyticsConfig",
    "currency.apps.CurrencyConfig",
    "administration.apps.AdministrationConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware.AnalyticsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "currency.middleware.CurrencyMiddleware",
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
                "core.context_processors.site_settings",
                "currency.context_processors.currency_context",
                "vehicles.context_processors.navigation_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

DATABASES["default"]["CONN_MAX_AGE"] = env.int(
    "DB_CONN_MAX_AGE",
    default=60,
)

# Cache — Redis
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,   # graceful Redis failure
        },
        "KEY_PREFIX": "autoyard",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media (local dev — overridden in production for Azure)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL",
                        default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND",
                            default="redis://127.0.0.1:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Nairobi"
CELERY_BEAT_SCHEDULE = {
    "refresh-exchange-rates": {
        "task": "currency.tasks.refresh_exchange_rates",
        "schedule": 3600,
    },
    "warm-homepage-cache": {
        "task": "catalogue.tasks.warm_homepage_cache",
        "schedule": 600,
    },
    "aggregate-analytics": {
        "task": "analytics.tasks.aggregate_daily_stats",
        "schedule": 86400,
    },
    "warm-vehicle-caches": {
        "task": "vehicles.tasks.warm_vehicle_caches",
        "schedule": 600,
    },
}

# Celery routing — analytics on separate queue to isolate from vehicle tasks
CELERY_TASK_ROUTES = {
    "analytics.tasks.*": {"queue": "analytics"},
    "currency.tasks.*":  {"queue": "currency"},
    "vehicles.tasks.*":  {"queue": "vehicles"},
    "catalogue.tasks.*": {"queue": "default"},
}

# Axes (brute-force protection)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_TEMPLATE = "403.html"
AXES_RESET_ON_SUCCESS = True

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Dealership settings
DEALERSHIP_NAME = env("DEALERSHIP_NAME", default="GRANDPA MOTORS")
DEALERSHIP_SITE_URL = env("DEALERSHIP_SITE_URL",
                          default="http://localhost:8000")
DEALERSHIP_COUNTRY = env("DEALERSHIP_COUNTRY", default="KE")
DEALERSHIP_CURRENCY = env("DEALERSHIP_CURRENCY", default="KES")
DEALERSHIP_PHONE = env("DEALERSHIP_PHONE", default="+254100984091")
DEALERSHIP_EMAIL = env("DEALERSHIP_EMAIL", default="info@grandpamotors.co.ke")
DEALERSHIP_LOCATION = env("DEALERSHIP_LOCATION", default="Nairobi, Kenya")
WHATSAPP_BUSINESS_NUMBER = env(
    "WHATSAPP_BUSINESS_NUMBER", default="2547100984091")

# Exchange rates
EXCHANGE_RATE_API_KEY = env("EXCHANGE_RATE_API_KEY", default="")
EXCHANGE_RATE_API_URL = env("EXCHANGE_RATE_API_URL",
                            default="https://v6.exchangerate-api.com/v6")
EXCHANGE_RATE_CACHE_TIMEOUT = 3600  # 1 hour

# Supported currencies
SUPPORTED_CURRENCIES = [
    ("KES", "KSh", "Kenyan Shilling"),
    ("USD", "$", "US Dollar"),
    ("GBP", "£", "British Pound"),
    ("EUR", "€", "Euro"),
    ("UGX", "USh", "Ugandan Shilling"),
    ("TZS", "TSh", "Tanzanian Shilling"),
    ("AED", "AED", "UAE Dirham"),
]

# Image settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
THUMBNAIL_SIZES = {
    "card": (400, 280),
    "gallery": (800, 600),
    "hero": (1200, 800),
    "thumb": (120, 80),
}

# Catalogue
VEHICLES_PER_PAGE = 24
RELATED_VEHICLES_COUNT = 4
RECENTLY_VIEWED_MAX = 10

# Geolocation
GEOIP_API_URL = env("GEOIP_API_URL", default="https://ipapi.co")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "vehicles": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "analytics": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "currency": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
