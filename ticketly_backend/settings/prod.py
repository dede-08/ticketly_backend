from .base import *  # noqa: F401,F403
from .base import os  # noqa: F401

# Entorno de producción: DEBUG siempre desactivado
DEBUG = False

# SECRET_KEY obligatorio en producción
if not os.getenv('DJANGO_SECRET_KEY') and not os.getenv('SECRET_KEY'):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY environment variable is required in production. '
        'Generar con: from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
    )

# Seguridad endurecida por defecto en producción (sobreescribible vía entorno)
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
CSRF_COOKIE_HTTPONLY = os.getenv('CSRF_COOKIE_HTTPONLY', 'True').lower() == 'true'
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() == 'true'
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')