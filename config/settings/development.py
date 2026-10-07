from .base import *  # noqa

DEBUG = True

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = ["127.0.0.1"]

# Use local file storage in development
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Relaxed security for local dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Show all SQL queries in debug toolbar
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "SHOW_COLLAPSED": True,
}
