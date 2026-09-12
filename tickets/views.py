import logging
import os
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from .models import Ticket, Category, Priority, Status, Comment, TicketHistory, Attachment
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    CategorySerializer, PrioritySerializer, StatusSerializer,
    CommentSerializer, AttachmentSerializer
)
from .permissions import (
    IsTicketCreatorOrAssigned,
    IsCommentCreator,
    IsAttachmentCreatorOrTicketCreator,
    IsAdminOrAgent,
    CanAssignTickets,
    is_staff_or_higher,
)
from .notifications import (
    notify_ticket_created, 
    notify_ticket_assigned, 
    notify_new_comment, 
    notify_status_changed,
    notify_priority_changed
)

User = get_user_model()

#configurar logger
logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """viewset para categorías (solo lectura; se gestionan por admin)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class PriorityViewSet(viewsets.ReadOnlyModelViewSet):
    """viewset para prioridades (solo lectura)"""
    queryset = Priority.objects.all()
    serializer_class = PrioritySerializer
    permission_classes = [IsAuthenticated]


class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    """viewset para estados (solo lectura)"""
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]


class TicketViewSet(viewsets.ModelViewSet):
    """viewset principal para tickets"""
    pagination_class = StandardPagination
    queryset = Ticket.objects.select_related(
        'category', 'priority', 'status', 'created_by', 'assigned_to'
    ).prefetch_related('comments', 'history')
    permission_classes = [IsAuthenticated, IsTicketCreatorOrAssigned]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'assigned_to', 'created_by']
    search_fields = ['title', 'description', 'ticket_number']
    ordering_fields = ['created_at', 'updated_at', 'priority__level']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """los usuarios normales solo ven sus tickets (creados o asignados); el personal ve todos"""
        queryset = self.queryset.annotate(comments_count=Count('comments', distinct=True))
        if not is_staff_or_higher(self.request.user):
            queryset = queryset.filter(
                Q(created_by=self.request.user) | Q(assigned_to=self.request.user)
            )
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        return TicketDetailSerializer
    
    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        
        #enviar notificacion de ticket creado
        try:
            notify_ticket_created(ticket)
            #si el ticket ya tiene asignado, notificarle tambien
            if ticket.assigned_to:
                notify_ticket_assigned(ticket, self.request.user)
        except Exception as e:
            logger.error(f"Error enviando notificación de ticket creado: {e}", exc_info=True)
    
    def _enforce_update_fields(self, serializer):
        """
        Los usuarios normales solo pueden modificar campos permitidos,
        independientemente de que una petición incluya más campos.
        """
        if is_staff_or_higher(self.request.user):
            return
        allowed = {'title', 'description', 'tags'}
        for field in list(serializer.validated_data.keys()):
            if field not in allowed:
                serializer.validated_data.pop(field, None)
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        
        #restringir campos editables para usuarios normales
        self._enforce_update_fields(serializer)
        
        #capturar valores antiguos antes de que se guarden
        old_values = {
            'status': old_instance.status,
            'priority': old_instance.priority,
            'assigned_to': old_instance.assigned_to,
            'category': old_instance.category,
            'title': old_instance.title,
            'description': old_instance.description
        }
        
        new_instance = serializer.save()

        #registrar cambios en el historial
        self._track_changes(old_values, new_instance)
        
        #NOTIFICACIONES
        try:
            #notificar cambio de estado
            if old_values['status'] != new_instance.status:
                notify_status_changed(
                    new_instance, 
                    old_values['status'].name, 
                    old_values['status'].get_name_display(),
                    self.request.user
                )
                
                #actualizar timestamps
                if new_instance.status.name == 'RESOLVED' and not new_instance.resolved_at:
                    new_instance.resolved_at = timezone.now()
                elif new_instance.status.name == 'CLOSED' and not new_instance.closed_at:
                    new_instance.closed_at = timezone.now()
                new_instance.save()
            
            #notificar cambio de prioridad
            if old_values['priority'] != new_instance.priority:
                notify_priority_changed(new_instance, old_values['priority'], self.request.user)
            
            #notificar nueva asignación
            if old_values['assigned_to'] != new_instance.assigned_to and new_instance.assigned_to:
                notify_ticket_assigned(new_instance, self.request.user)
                
        except Exception as e:
            logger.error(f"Error enviando notificación de actualización: {e}", exc_info=True)
    
    def _track_changes(self, old_values, new_instance):
        """registrar cambios importantes en el historial"""
        fields_to_track = ['status', 'priority', 'assigned_to', 'category', 'title', 'description']
        
        for field in fields_to_track:
            old_value = old_values.get(field)
            new_value = getattr(new_instance, field)
            
            if old_value != new_value:
                TicketHistory.objects.create(
                    ticket=new_instance,
                    user=self.request.user,
                    field_name=field,
                    old_value=str(old_value) if old_value else '',
                    new_value=str(new_value) if new_value else ''
                )
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """agregar comentario a un ticket"""
        ticket = self.get_object()
        
        #los comentarios internos solo pueden crearlos el personal de soporte
        if bool(request.data.get('is_internal')) and not is_staff_or_higher(request.user):
            raise PermissionDenied('Solo el personal de soporte puede crear comentarios internos.')
        
        serializer = CommentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            comment = serializer.save(ticket=ticket, user=request.user)
            
            #enviar notificacion de nuevo comentario
            try:
                notify_new_comment(ticket, comment)
            except Exception as e:
                logger.error(f"Error enviando notificación de comentario: {e}", exc_info=True)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanAssignTickets])
    def assign(self, request, pk=None):
        """asignar ticket a un usuario (solo supervisor o administrador)"""
        ticket = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            user = User.objects.get(id=user_id) if user_id else None
            
            old_assigned = ticket.assigned_to
            ticket.assigned_to = user
            ticket.save()
            
            #registrar cambio
            TicketHistory.objects.create(
                ticket=ticket,
                user=request.user,
                field_name='assigned_to',
                old_value=str(old_assigned) if old_assigned else '',
                new_value=str(user) if user else ''
            )
            
            #enviar notificacion si se asigno a alguien nuevo
            try:
                if user and user != old_assigned:
                    notify_ticket_assigned(ticket, request.user)
            except Exception as e:
                logger.error(f"Error enviando notificación de asignación: {e}", exc_info=True)
            
            serializer = self.get_serializer(ticket)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'usuario no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _paginated_list(self, queryset):
        """responde una lista paginada y filtrada (reutiliza backend de filtros)"""
        filtered = self.filter_queryset(queryset)
        page = self.paginate_queryset(filtered)
        serializer = self.get_serializer(page if page is not None else filtered, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """obtener tickets del usuario actual"""
        return self._paginated_list(self.get_queryset().filter(created_by=request.user))

    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        """obtener tickets asignados al usuario actual"""
        return self._paginated_list(self.get_queryset().filter(assigned_to=request.user))

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrAgent])
    def statistics(self, request):
        """obtener estadisticas de tickets (solo personal de soporte)"""
        from django.db.models import Count, Q
        
        base = self.get_queryset()
        counts = base.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status__name='OPEN')),
            in_progress=Count('id', filter=Q(status__name='IN_PROGRESS')),
            resolved=Count('id', filter=Q(status__name='RESOLVED')),
            closed=Count('id', filter=Q(status__name='CLOSED')),
        )
        
        stats = {
            **counts,
            'by_priority': list(
                base.values('priority__name', 'priority__level')
                .annotate(count=Count('id'))
                .order_by('-priority__level')
            ),
            'by_category': list(
                base.values('category__name')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        """subir archivo adjunto a un ticket"""
        ticket = self.get_object()
        file = request.FILES.get('file')
        description = request.data.get('description', '')
        
        if not file:
            return Response(
                {'error': 'no se proporciono ningun archivo'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #validar tamaño del archivo (10MB)
        if file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            return Response(
                {'error': f'el archivo es demasiado grande. maximo {settings.FILE_UPLOAD_MAX_MEMORY_SIZE / 1024 / 1024}MB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #validar extension
        file_extension = os.path.splitext(file.name)[1].lower().replace('.', '')
        if file_extension not in settings.ALLOWED_FILE_EXTENSIONS:
            return Response(
                {'error': f'tipo de archivo no permitido. extensiones permitidas: {", ".join(settings.ALLOWED_FILE_EXTENSIONS)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #crear el attachment
        attachment = Attachment.objects.create(
            ticket=ticket,
            uploaded_by=request.user,
            file=file,
            description=description
        )
        
        serializer = AttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated, IsAttachmentCreatorOrTicketCreator])
    def delete_attachment(self, request, pk=None):
        """eliminar un archivo adjunto"""
        try:
            attachment_id = request.data.get('attachment_id')
            attachment = Attachment.objects.get(id=attachment_id, ticket_id=pk)
            
            #verificar permisos sobre el adjunto
            self.check_object_permissions(request, attachment)
            
            #eliminar el archivo fisico usando Storage API
            if attachment.file:
                try:
                    from django.core.files.storage import default_storage
                    if default_storage.exists(attachment.file.name):
                        default_storage.delete(attachment.file.name)
                except Exception as e:
                    logging.exception(f"Error eliminando archivo fisico: {e}")
            
            attachment.delete()
            return Response({'message': 'archivo eliminado correctamente'}, status=status.HTTP_200_OK)
        except Attachment.DoesNotExist:
            return Response(
                {'error': 'archivo no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CommentViewSet(viewsets.ModelViewSet):
    """viewset para comentarios"""
    queryset = Comment.objects.select_related('ticket', 'user')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsCommentCreator]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ticket_id = self.request.query_params.get('ticket')
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)
        #los comentarios internos solo los ve el personal de soporte
        if not is_staff_or_higher(self.request.user):
            queryset = queryset.filter(is_internal=False)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    def perform_update(self, serializer):
        #los comentarios internos solo los gestiona el personal de soporte
        if serializer.instance.is_internal and not is_staff_or_higher(self.request.user):
            raise PermissionDenied('Solo el personal de soporte puede modificar comentarios internos.')
        serializer.save()