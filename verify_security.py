#!/usr/bin/env python
"""
VERIFICACIÓN DE SEGURIDAD - Ticketly Backend v1.1.0

Este script verifica que todas las correcciones de seguridad estén implementadas.
Ejecutar después de aplicar los cambios.

Uso: python verify_security.py
"""

import os
import sys
from pathlib import Path

def check_secret_key_validation():
    """Verifica que SECRET_KEY sea obligatoria"""
    print("\n[1/5] Verificando validación de SECRET_KEY...")
    
    settings_file = Path('ticketly_backend/settings.py')
    if not settings_file.exists():
        print("Archivo settings.py no encontrado")
        return False
    
    content = settings_file.read_text()
    
    checks = [
        ('DJANGO_SECRET_KEY es obligatoria', 'SECRET_KEY = os.getenv(\'DJANGO_SECRET_KEY\')'),
        ('Lanza ImproperlyConfigured', 'raise ImproperlyConfigured'),
        ('No hay fallback inseguro', 'set-a-strong-secret-key' not in content),
    ]
    
    all_passed = True
    for check_name, check_condition in checks:
        if isinstance(check_condition, str):
            passed = check_condition in content
        else:
            passed = check_condition
        
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed
    
    return all_passed

def check_permissions_implementation():
    """Verifica que las clases de permisos estén implementadas"""
    print("\n[2/5] Verificando clases de permisos...")
    
    permissions_file = Path('tickets/permissions.py')
    if not permissions_file.exists():
        print("Archivo permissions.py no encontrado")
        return False
    
    content = permissions_file.read_text()
    
    classes = [
        'IsTicketCreatorOrAssigned',
        'IsCommentCreator',
        'IsAttachmentCreatorOrTicketCreator',
    ]
    
    all_passed = True
    for class_name in classes:
        passed = f'class {class_name}' in content
        status = "✓" if passed else "✗"
        print(f"  {status} {class_name}")
        all_passed = all_passed and passed
    
    return all_passed

def check_views_updated():
    """Verifica que los permisos se usen en las vistas"""
    print("\n[3/5] Verificando uso de permisos en views...")
    
    views_file = Path('tickets/views.py')
    if not views_file.exists():
        print("Archivo views.py no encontrado")
        return False
    
    content = views_file.read_text()
    
    checks = [
        ('Import de permisos', 'from .permissions import'),
        ('TicketViewSet con permisos', 'IsTicketCreatorOrAssigned'),
        ('CommentViewSet con permisos', 'IsCommentCreator'),
        ('Logger configurado', 'logger = logging.getLogger'),
        ('Logging en lugar de print', 'logger.error'),
    ]
    
    all_passed = True
    for check_name, check_condition in checks:
        passed = check_condition in content
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed
    
    return all_passed

def check_models_updated():
    """Verifica que ticket_number sea seguro"""
    print("\n[4/5] Verificando seguridad de ticket_number...")
    
    models_file = Path('tickets/models.py')
    if not models_file.exists():
        print("Archivo models.py no encontrado")
        return False
    
    content = models_file.read_text()
    
    checks = [
        ('Import de transaction', 'from django.db import transaction'),
        ('select_for_update() usado', 'select_for_update()'),
        ('Transacción atómica', 'with transaction.atomic():'),
        ('Fallback seguro', 'except (ValueError, IndexError):'),
    ]
    
    all_passed = True
    for check_name, check_condition in checks:
        passed = check_condition in content
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed
    
    return all_passed

def check_notifications_updated():
    """Verifica logging en notificaciones"""
    print("\n[5/5] Verificando logging en notificaciones...")
    
    notifications_file = Path('tickets/notifications.py')
    if not notifications_file.exists():
        print("Archivo notifications.py no encontrado")
        return False
    
    content = notifications_file.read_text()
    
    checks = [
        ('Import de logging', 'import logging'),
        ('Logger configurado', 'logger = logging.getLogger'),
        ('Funciones retornan bool', 'return True'),
        ('Logging en lugar de print', 'logger.error'),
        ('Sin print()', 'print(' not in content),
    ]
    
    all_passed = True
    for check_name, check_condition in checks:
        if isinstance(check_condition, str):
            if check_condition.startswith('not '):
                passed = check_condition[4:] not in content
                check_condition = check_condition[4:]
            else:
                passed = check_condition in content
        
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed
    
    return all_passed

def main():
    print("=" * 60)
    print("VERIFICACIÓN DE SEGURIDAD - Ticketly Backend")
    print("=" * 60)
    
    os.chdir(Path(__file__).parent)
    
    results = {
        'SECRET_KEY': check_secret_key_validation(),
        'Permisos': check_permissions_implementation(),
        'Views': check_views_updated(),
        'Models': check_models_updated(),
        'Notificaciones': check_notifications_updated(),
    }
    
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print("=" * 60)
    
    for check_name, passed in results.items():
        status = "PASÓ" if passed else "❌ FALLÓ"
        print(f"  {status}: {check_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("TODAS LAS VERIFICACIONES PASARON")
        print("\nSiguiente paso: python setup_env.py")
        return 0
    else:
        print("ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisar los cambios e intentar de nuevo")
        return 1

if __name__ == '__main__':
    sys.exit(main())
