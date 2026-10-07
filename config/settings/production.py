from .base import *  # noqa
import os

DEBUG = False

# Security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Azure Blob Storage for media
if os.environ.get("AZURE_ACCOUNT_NAME"):
    DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
    AZURE_ACCOUNT_NAME = os.environ["AZURE_ACCOUNT_NAME"]
    AZURE_ACCOUNT_KEY = os.environ["AZURE_ACCOUNT_KEY"]
    AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER", "vehicles")
    AZURE_OVERWRITE_FILES = False
    AZURE_URL_EXPIRATION_SECS = None  # public container
    MEDIA_URL = f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_CONTAINER}/"
