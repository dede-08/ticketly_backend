from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    """Categorías de tickets"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Priority(models.Model):
    """Prioridades de tickets"""
    PRIORITY_CHOICES = [
        ('LOW', 'Baja'),
        ('MEDIUM', 'Media'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    ]
    
    name = models.CharField(max_length=20, choices=PRIORITY_CHOICES, unique=True)
    level = models.IntegerField(default=1)
    color = models.CharField(max_length=7, default='#6c757d')
    
    class Meta:
        verbose_name_plural = "Priorities"
        ordering = ['-level']
    
    def __str__(self):
        return self.get_name_display()


class Status(models.Model):
    """Estados de tickets"""
    STATUS_CHOICES = [
        ('OPEN', 'Abierto'),
        ('IN_PROGRESS', 'En Progreso'),
        ('ON_HOLD', 'En Espera'),
        ('RESOLVED', 'Resuelto'),
        ('CLOSED', 'Cerrado'),
    ]
    
    name = models.CharField(max_length=20, choices=STATUS_CHOICES, unique=True)
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Statuses"
    
    def __str__(self):
        return self.get_name_display()


class Ticket(models.Model):
    """Modelo principal de tickets"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Relaciones
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='tickets')
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT, related_name='tickets')
    status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='tickets')
    
    # Usuarios
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    attachments = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.ticket_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generar número de ticket único
            last_ticket = Ticket.objects.order_by('-id').first()
            if last_ticket:
                last_num = int(last_ticket.ticket_number.split('-')[1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.ticket_number = f"TKT-{new_num:06d}"
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Comentarios en tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.ticket.ticket_number}"


class TicketHistory(models.Model):
    """Historial de cambios en tickets"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Ticket histories"
    
    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.field_name} changed"