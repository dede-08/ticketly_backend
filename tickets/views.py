from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Ticket, Category, Priority, Status, Comment, TicketHistory
from .serializers import (
    TicketListSerializer, TicketDetailSerializer, TicketCreateSerializer,
    CategorySerializer, PrioritySerializer, StatusSerializer,
    CommentSerializer, TicketHistorySerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet para categorías"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class PriorityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para prioridades (solo lectura)"""
    queryset = Priority.objects.all()
    serializer_class = PrioritySerializer
    permission_classes = [IsAuthenticated]


class StatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para estados (solo lectura)"""
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    permission_classes = [IsAuthenticated]


class TicketViewSet(viewsets.ModelViewSet):
    """ViewSet principal para tickets"""
    queryset = Ticket.objects.select_related(
        'category', 'priority', 'status', 'created_by', 'assigned_to'
    ).prefetch_related('comments', 'history')
    permission_classes = [IsAuthenticated]
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
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        new_instance = serializer.save()
        
        # Registrar cambios en el historial
        self._track_changes(old_instance, new_instance)
        
        # Actualizar timestamps si el estado cambió
        if old_instance.status != new_instance.status:
            if new_instance.status.name == 'RESOLVED' and not new_instance.resolved_at:
                new_instance.resolved_at = timezone.now()
                new_instance.save()
            elif new_instance.status.name == 'CLOSED' and not new_instance.closed_at:
                new_instance.closed_at = timezone.now()
                new_instance.save()
    
    def _track_changes(self, old_instance, new_instance):
        """Registrar cambios importantes en el historial"""
        fields_to_track = ['status', 'priority', 'assigned_to', 'category']
        
        for field in fields_to_track:
            old_value = getattr(old_instance, field)
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
        """Agregar comentario a un ticket"""
        ticket = self.get_object()
        serializer = CommentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(ticket=ticket, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Asignar ticket a un usuario"""
        ticket = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id) if user_id else None
            
            old_assigned = ticket.assigned_to
            ticket.assigned_to = user
            ticket.save()
            
            # Registrar cambio
            TicketHistory.objects.create(
                ticket=ticket,
                user=request.user,
                field_name='assigned_to',
                old_value=str(old_assigned) if old_assigned else '',
                new_value=str(user) if user else ''
            )
            
            serializer = self.get_serializer(ticket)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """Obtener tickets del usuario actual"""
        tickets = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        """Obtener tickets asignados al usuario actual"""
        tickets = self.queryset.filter(assigned_to=request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Obtener estadísticas de tickets"""
        from django.db.models import Count, Q
        
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


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet para comentarios"""
    queryset = Comment.objects.select_related('ticket', 'user')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        ticket_id = self.request.query_params.get('ticket')
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)