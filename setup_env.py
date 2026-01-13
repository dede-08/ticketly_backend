#!/usr/bin/env python
"""
Script de configuración inicial para Ticketly Backend

Usa este script para generar valores seguros para tu .env
"""

import os
import sys
import secrets
from pathlib import Path

def generate_secret_key():
    """Genera una SECRET_KEY segura"""
    return secrets.token_urlsafe(50)

def create_env_file():
    """Crea un archivo .env con configuración inicial"""
    project_root = Path(__file__).resolve().parent
    env_file = project_root / '.env'
    env_example = project_root / '.env.example'
    
    if env_file.exists():
        print(f"⚠️  El archivo .env ya existe en {env_file}")
        response = input("¿Deseas sobrescribirlo? (s/n): ").lower().strip()
        if response != 's':
            print("Configuración cancelada.")
            return False
    
    # Generar valores seguros
    secret_key = generate_secret_key()
    
    env_content = f"""# Django Settings
DEBUG=True
DJANGO_SECRET_KEY={secret_key}
ALLOWED_HOSTS=localhost,127.0.0.1,127.0.0.1:8000

# Database (PostgreSQL recomendado)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ticketly_db
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Email Configuration (Gmail recomendado)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Ticketly <noreply@ticketly.com>

# CORS & Security
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
CSRF_TRUSTED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
SITE_URL=http://localhost:4200

# SSL/Security (False para desarrollo, True para producción)
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_HTTPONLY=False
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0

# Logging
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO
"""
    
    # Crear archivo .env
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"Archivo .env creado en {env_file}")
    print(f"\nSECRET_KEY generada (guardada en .env)")
    print(f"\nIMPORTANTE:")
    print(f"   1. Configura DB_PASSWORD con tu contraseña de PostgreSQL")
    print(f"   2. Configura EMAIL_HOST_USER y EMAIL_HOST_PASSWORD para notificaciones")
    print(f"   3. En producción, establece DEBUG=False")
    
    return True

if __name__ == '__main__':
    if create_env_file():
        print("\nConfiguración completada. Próximo paso: python manage.py migrate")
    else:
        sys.exit(1)
