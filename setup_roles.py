
"""
Script para crear roles y permisos en el sistema
"""

import os
import sys
import django
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from tickets.models import Ticket, Comment, Category

#configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticketly_backend.settings')
django.setup()

def create_roles():
    """Crear los 4 roles principales del sistema"""
    
    print("\n" + "="*60)
    print("CONFIGURANDO ROLES Y PERMISOS")
    print("="*60 + "\n")
    
    # ==================== 1. USUARIO NORMAL ====================
    print("Creando rol: Usuario Normal")
    
    usuario_normal, created = Group.objects.get_or_create(name='Usuario Normal')
    
    if created:
        # Permisos: Solo crear tickets y ver los propios
        permisos_usuario = [
            'add_ticket',      # Crear tickets
            'view_ticket',     # Ver tickets (filtrado en views)
            'add_comment',     # Agregar comentarios
            'view_comment',    # Ver comentarios
        ]
        
        for perm in permisos_usuario:
            try:
                permission = Permission.objects.get(codename=perm)
                usuario_normal.permissions.add(permission)
                print(f"   Permiso agregado: {perm}")
            except Permission.DoesNotExist:
                print(f"   Permiso no encontrado: {perm}")
        
        print("   Rol 'Usuario Normal' creado\n")
    else:
        print("   Rol 'Usuario Normal' ya existe\n")
    
    
    # ==================== 2. AGENTE DE SOPORTE ====================
    print("Creando rol: Agente de Soporte")
    
    agente, created = Group.objects.get_or_create(name='Agente de Soporte')
    
    if created:
        # Permisos: Gestionar tickets asignados
        permisos_agente = [
            'add_ticket',
            'view_ticket',
            'change_ticket',   # Modificar tickets
            'add_comment',
            'view_comment',
            'change_comment',
            'view_category',
        ]
        
        for perm in permisos_agente:
            try:
                permission = Permission.objects.get(codename=perm)
                agente.permissions.add(permission)
                print(f"   Permiso agregado: {perm}")
            except Permission.DoesNotExist:
                print(f"   Permiso no encontrado: {perm}")
        
        print("   Rol 'Agente de Soporte' creado\n")
    else:
        print("   Rol 'Agente de Soporte' ya existe\n")
    
    
    # ==================== 3. SUPERVISOR ====================
    print("Creando rol: Supervisor")
    
    supervisor, created = Group.objects.get_or_create(name='Supervisor')
    
    if created:
        # Permisos: Ver todo y asignar tickets
        permisos_supervisor = [
            'add_ticket',
            'view_ticket',
            'change_ticket',
            'delete_ticket',   # Eliminar tickets
            'add_comment',
            'view_comment',
            'change_comment',
            'delete_comment',
            'view_category',
            'add_category',
            'change_category',
        ]
        
        for perm in permisos_supervisor:
            try:
                permission = Permission.objects.get(codename=perm)
                supervisor.permissions.add(permission)
                print(f"   Permiso agregado: {perm}")
            except Permission.DoesNotExist:
                print(f"   Permiso no encontrado: {perm}")
        
        print("  Rol 'Supervisor' creado\n")
    else:
        print("  Rol 'Supervisor' ya existe\n")
    
    
    # ==================== 4. ADMINISTRADOR ====================
    print("Creando rol: Administrador")
    
    administrador, created = Group.objects.get_or_create(name='Administrador')
    
    if created:
        # Permisos: Control total
        permisos_admin = Permission.objects.all()
        administrador.permissions.set(permisos_admin)
        print(f"  Todos los permisos agregados ({permisos_admin.count()} permisos)")
        print("   Rol 'Administrador' creado\n")
    else:
        print("   Rol 'Administrador' ya existe\n")
    
    
    # ==================== RESUMEN ====================
    print("="*60)
    print("CONFIGURACIÓN COMPLETADA")
    print("="*60)
    print("\nRoles creados:")
    print("  Usuario Normal     - Solo ve y crea sus tickets")
    print("  Agente de Soporte  - Gestiona tickets asignados")
    print("  Supervisor         - Ve todo, asigna tickets")
    print("  Administrador      - Control total")
    print("\nAhora puedes asignar roles a los usuarios desde:")
    print("   http://localhost:8000/admin/auth/user/")
    print("")


def assign_default_role_to_users():
    """Asignar rol por defecto a usuarios sin rol"""
    from django.contrib.auth.models import User
    
    print("\n" + "="*60)
    print("ASIGNANDO ROLES POR DEFECTO")
    print("="*60 + "\n")
    
    usuario_normal_group = Group.objects.get(name='Usuario Normal')
    users_without_group = User.objects.filter(groups__isnull=True)
    
    count = 0
    for user in users_without_group:
        if not user.is_superuser:  # No asignar rol a superusuarios
            user.groups.add(usuario_normal_group)
            print(f"Usuario '{user.username}' ahora es 'Usuario Normal'")
            count += 1
    
    if count > 0:
        print(f"\n {count} usuario(s) asignado(s) al rol 'Usuario Normal'\n")
    else:
        print("\n No hay usuarios sin rol\n")


def show_user_roles():
    """Mostrar usuarios y sus roles"""
    from django.contrib.auth.models import User
    
    print("\n" + "="*60)
    print(" USUARIOS Y SUS ROLES")
    print("="*60 + "\n")
    
    users = User.objects.all().prefetch_related('groups')
    
    for user in users:
        roles = ", ".join([g.name for g in user.groups.all()]) or "Sin rol"
        status = "Superusuario" if user.is_superuser else f" {roles}"
        print(f"  {user.username:20s} → {status}")
    
    print("")


if __name__ == '__main__':
    try:
        create_roles()
        assign_default_role_to_users()
        show_user_roles()
        
        print("="*60)
        print("lito")
        print("="*60)
        print("")
    except Exception as e:
        print(f"\n Error: {e}")
        sys.exit(1)