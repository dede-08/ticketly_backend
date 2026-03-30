import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.conf import settings
import os
from .models import Ticket, Category, Priority, Status, Comment, TicketHistory, Attachment
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    CategorySerializer, PrioritySerializer, StatusSerializer,
    CommentSerializer, AttachmentSerializer
)
from .permissions import IsTicketCreatorOrAssigned, IsCommentCreator
from .notifications import (
    notify_ticket_created, 
    notify_ticket_assigned, 
    notify_new_comment, 
    notify_status_changed,
    notify_priority_changed
)

#configurar logger
logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    """viewset para categorías"""
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
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        return TicketDetailSerializer
    
    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        
        #enviar notificación de ticket creado
        try:
            notify_ticket_created(ticket)
            #si el ticket ya tiene asignado, notificarle también
            if ticket.assigned_to:
                notify_ticket_assigned(ticket, self.request.user)
        except Exception as e:
            logger.error(f"Error enviando notificación de ticket creado: {e}", exc_info=True)
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        
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
        
        # === NOTIFICACIONES ===
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
        serializer = CommentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            comment = serializer.save(ticket=ticket, user=request.user)
            
            #enviar notificación de nuevo comentario
            try:
                notify_new_comment(ticket, comment)
            except Exception as e:
                logger.error(f"Error enviando notificación de comentario: {e}", exc_info=True)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """asignar ticket a un usuario"""
        ticket = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            from django.contrib.auth.models import User
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
            
            #enviar notificación si se asignó a alguien nuevo
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
            return Response(
                {'error': 'usuario no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """obtener tickets del usuario actual"""
        tickets = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        """obtener tickets asignados al usuario actual"""
        tickets = self.queryset.filter(assigned_to=request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """obtener estadisticas de tickets"""
        from django.db.models import Count
        
        stats = {
            'total': self.queryset.count(),
            'open': self.queryset.filter(status__name='OPEN').count(),
            'in_progress': self.queryset.filter(status__name='IN_PROGRESS').count(),
            'resolved': self.queryset.filter(status__name='RESOLVED').count(),
            'closed': self.queryset.filter(status__name='CLOSED').count(),
            'by_priority': list(
                self.queryset.values('priority__name')
                .annotate(count=Count('id'))
                .order_by('-priority__level')
            ),
            'by_category': list(
                self.queryset.values('category__name')
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
    
    @action(detail=True, methods=['delete'])
    def delete_attachment(self, request, pk=None):
        """eliminar un archivo adjunto"""
        try:
            attachment_id = request.data.get('attachment_id')
            attachment = Attachment.objects.get(id=attachment_id, ticket_id=pk)
            
            #solo el que subio el archivo o el creador del ticket pueden eliminarlo
            if attachment.uploaded_by != request.user and self.get_object().created_by != request.user:
                return Response(
                    {'error': 'no tienes permiso para eliminar este archivo'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
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
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)