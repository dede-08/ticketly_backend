from rest_framework import permissions


class IsTicketCreatorOrAssigned(permissions.BasePermission):
    """
    Permiso personalizado: solo el creador del ticket o el asignado pueden modificarlo
    """
    def has_object_permission(self, request, view, obj):
        #lLos metodos seguros (GET, HEAD, OPTIONS) requieren solo autenticación
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Para modificaciones: solo el creador o el asignado
        return obj.created_by == request.user or obj.assigned_to == request.user


class IsCommentCreator(permissions.BasePermission): 
    """
    Permiso personalizado: solo el autor del comentario puede modificarlo
    """
    def has_object_permission(self, request, view, obj):
        #los metodos seguros requieren solo autenticación
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Para modificaciones: solo el creador del comentario
        return obj.user == request.user


class IsAttachmentCreatorOrTicketCreator(permissions.BasePermission):
    """
    Permiso personalizado: solo quien subió el archivo o el creador del ticket pueden eliminarlo
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        #solo quien subió o creador del ticket
        return obj.uploaded_by == request.user or obj.ticket.created_by == request.user
