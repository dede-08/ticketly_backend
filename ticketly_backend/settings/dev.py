from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, os  # noqa: F401

# Entorno de desarrollo
DEBUG = True

# base.py ya aplica la SECRET_KEY de desarrollo con aviso si no hay una real.

# Debug Toolbar: activar solo si está instalado y se solicita explícitamente
if os.getenv('ENABLE_DEBUG_TOOLBAR', 'false').lower() == 'true':
    try:
        import debug_toolbar  # noqa: F401
        INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']
        MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]
        INTERNAL_IPS = [ip for ip in os.getenv('INTERNAL_IPS', '127.0.0.1').split(',') if ip]
    except ImportError:
        pass