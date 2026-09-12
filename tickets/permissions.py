from rest_framework import permissions

# Nombres de los roles gestionados a través de grupos
ROLE_ADMIN = 'Administrador'
ROLE_SUPERVISOR = 'Supervisor'
ROLE_AGENT = 'Agente de Soporte'
ROLE_USER = 'Usuario Normal'


def is_staff_or_higher(user):
    """Personal de soporte, supervisor o administrador"""
    return (
        user.is_staff
        or user.is_superuser
        or (getattr(user, 'is_authenticated', False) and user.groups.filter(
            name__in=[ROLE_AGENT, ROLE_SUPERVISOR, ROLE_ADMIN]
        ).exists())
    )


def is_supervisor_or_higher(user):
    """Supervisor o administrador"""
    return (
        user.is_superuser
        or user.groups.filter(name__in=[ROLE_SUPERVISOR, ROLE_ADMIN]).exists()
    )


def get_user_role(user):
    """Devuelve el rol más alto del usuario según sus grupos"""
    if user.is_superuser:
        return ROLE_ADMIN
    names = set(user.groups.values_list('name', flat=True))
    if ROLE_ADMIN in names:
        return ROLE_ADMIN
    if ROLE_SUPERVISOR in names:
        return ROLE_SUPERVISOR
    if ROLE_AGENT in names:
        return ROLE_AGENT
    if ROLE_USER in names:
        return ROLE_USER
    return None


class IsTicketCreatorOrAssigned(permissions.BasePermission):
    """
    Permiso a nivel de objeto: solo el creador del ticket o el asignado pueden modificarlo.
    El personal (agente/supervisor/admin) puede modificar cualquier ticket.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        #los metodos seguros (GET, HEAD, OPTIONS) requieren solo autenticación
        if request.method in permissions.SAFE_METHODS:
            return True

        #el personal de soporte puede modificar cualquier ticket
        if is_staff_or_higher(request.user):
            return True

        #para el resto: solo el creador o el asignado
        return obj.created_by == request.user or obj.assigned_to == request.user


class IsAdminOrAgent(permissions.BasePermission):
    """
    Permite crear tickets a cualquier usuario autenticado,
    pero lista/recupera todos los tickets solo para personal de soporte.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if view.action in ('create',):
            return True
        #list/retrieve (GET) solo para personal de soporte y superiores
        return is_staff_or_higher(request.user)


class CanAssignTickets(permissions.BasePermission):
    """
    Solo supervisor o administrador pueden asignar/reasignar tickets
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_supervisor_or_higher(request.user))


class CanCreateInternalComment(permissions.BasePermission):
    """
    Solo el personal de soporte puede crear/editar comentarios internos
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsCommentCreator(permissions.BasePermission): 
    """
    Permiso personalizado: solo el autor del comentario puede modificarlo
    """
    def has_object_permission(self, request, view, obj):
        #los metodos seguros requieren solo autenticación
        if request.method in permissions.SAFE_METHODS:
            return True
        
        #para modificaciones: solo el creador del comentario
        return obj.user == request.user


class IsAttachmentCreatorOrTicketCreator(permissions.BasePermission):
    """
    Permiso personalizado: solo quien subió el archivo, el creador del ticket
    o el personal de soporte pueden eliminarlo
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        #el personal de soporte puede eliminar cualquier adjunto
        if is_staff_or_higher(request.user):
            return True
        
        #solo quien creó el ticket o lo subió
        return obj.uploaded_by == request.user or obj.ticket.created_by == request.user
