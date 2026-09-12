from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()


ROLE_USER = 'Usuario Normal'
ROLE_AGENT = 'Agente de Soporte'
ROLE_SUPERVISOR = 'Supervisor'
ROLE_ADMIN = 'Administrador'

ROLES = {
    ROLE_USER: [
        'add_ticket',
        'view_ticket',
        'add_comment',
        'view_comment',
    ],
    ROLE_AGENT: [
        'add_ticket',
        'view_ticket',
        'change_ticket',
        'add_comment',
        'view_comment',
        'change_comment',
        'view_category',
    ],
    ROLE_SUPERVISOR: [
        'add_ticket',
        'view_ticket',
        'change_ticket',
        'delete_ticket',
        'add_comment',
        'view_comment',
        'change_comment',
        'delete_comment',
        'view_category',
        'add_category',
        'change_category',
    ],
}


class Command(BaseCommand):
    help = 'Crea los roles del sistema y asigna el rol por defecto a usuarios sin grupo.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Configurando roles y permisos...'))

        # Rol Administrador: todos los permisos
        admin_group, created = Group.objects.get_or_create(name=ROLE_ADMIN)
        if created:
            admin_group.permissions.set(Permission.objects.all())
            self.stdout.write(f'  + Permisos asignados a {ROLE_ADMIN}')

        # Resto de roles
        for role_name, codenames in ROLES.items():
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                permissions = Permission.objects.filter(codename__in=codenames)
                group.permissions.set(permissions)
                self.stdout.write(f'  + Permisos asignados a {role_name}')
            else:
                self.stdout.write(f'  = Rol {role_name} ya existía')

        self._assign_default_role()
        self._show_user_roles()

    def _assign_default_role(self):
        user_group = Group.objects.get(name=ROLE_USER)
        users_without_group = User.objects.filter(groups__isnull=True).exclude(is_superuser=True)
        count = 0
        for user in users_without_group:
            user.groups.add(user_group)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'  ~ {count} usuario(s) asignados a {ROLE_USER}'))

    def _show_user_roles(self):
        self.stdout.write('Usuarios actuales:')
        for user in User.objects.prefetch_related('groups').order_by('username'):
            roles = ', '.join(g.name for g in user.groups.all()) or 'Sin rol'
            prefix = 'Superusuario' if user.is_superuser else roles
            self.stdout.write(f'  {user.username:20s} -> {prefix}')
        self.stdout.write(self.style.SUCCESS('Roles configurados correctamente.'))