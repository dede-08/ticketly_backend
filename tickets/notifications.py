from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_ticket_notification(template_name, subject, recipient_email, context):
    """
    Función helper para enviar notificaciones por email
    Retorna True si la notificación se envió exitosamente, False en caso contrario
    """
    if not recipient_email:
        logger.warning(f"Email vacío para notificación: {subject}")
        return False
    
    try:
        # Renderizar el template HTML
        html_message = render_to_string(f'emails/{template_name}', context)
        plain_message = strip_tags(html_message)
        
        # Enviar el email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Notificación enviada a {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {recipient_email}: {str(e)}", exc_info=True)
        return False


def notify_ticket_created(ticket):
    """
    Notifica al creador que su ticket fue creado
    """
    if not ticket.created_by.email:
        logger.warning(f"Usuario {ticket.created_by.username} no tiene email configurado")
        return False
    
    context = {
        'ticket': ticket,
        'site_url': settings.SITE_URL,
    }
    
    return send_ticket_notification(
        template_name='new_ticket.html',
        subject=f'Ticket Creado - {ticket.ticket_number}',
        recipient_email=ticket.created_by.email,
        context=context
    )


def notify_ticket_assigned(ticket, assigned_by):
    """
    Notifica al usuario asignado sobre el nuevo ticket
    """
    if not ticket.assigned_to or not ticket.assigned_to.email:
        return False
    
    context = {
        'ticket': ticket,
        'assigned_by': assigned_by,
        'site_url': settings.SITE_URL,
    }
    
    return send_ticket_notification(
        template_name='ticket_assigned.html',
        subject=f'Ticket Asignado - {ticket.ticket_number}',
        recipient_email=ticket.assigned_to.email,
        context=context
    )


def notify_new_comment(ticket, comment):
    """
    Notifica al creador y al asignado sobre un nuevo comentario
    """
    recipients = set()
    
    # Agregar al creador del ticket
    if ticket.created_by.email:
        recipients.add((ticket.created_by.email, ticket.created_by))
    
    # Agregar al asignado (si existe)
    if ticket.assigned_to and ticket.assigned_to.email:
        recipients.add((ticket.assigned_to.email, ticket.assigned_to))
    
    # No notificar al autor del comentario
    if comment.user.email in [r[0] for r in recipients]:
        recipients = {r for r in recipients if r[0] != comment.user.email}
    
    # Enviar notificación a cada destinatario
    for email, user in recipients:
        context = {
            'ticket': ticket,
            'comment': comment,
            'recipient': user,
            'site_url': settings.SITE_URL,
        }
        
        send_ticket_notification(
            template_name='new_comment.html',
            subject=f'Nuevo Comentario - {ticket.ticket_number}',
            recipient_email=email,
            context=context
        )


def notify_status_changed(ticket, old_status, old_status_display, changed_by):
    """
    Notifica sobre el cambio de estado del ticket
    """
    recipients = set()
    
    # Agregar al creador del ticket
    if ticket.created_by.email:
        recipients.add((ticket.created_by.email, ticket.created_by))
    
    # Agregar al asignado (si existe)
    if ticket.assigned_to and ticket.assigned_to.email:
        recipients.add((ticket.assigned_to.email, ticket.assigned_to))
    
    # No notificar a quien hizo el cambio
    if changed_by.email in [r[0] for r in recipients]:
        recipients = {r for r in recipients if r[0] != changed_by.email}
    
    # Enviar notificación a cada destinatario
    for email, user in recipients:
        context = {
            'ticket': ticket,
            'old_status': old_status,
            'old_status_display': old_status_display,
            'changed_by': changed_by,
            'recipient': user,
            'site_url': settings.SITE_URL,
        }
        
        send_ticket_notification(
            template_name='status_changed.html',
            subject=f'Estado Actualizado - {ticket.ticket_number}',
            recipient_email=email,
            context=context
        )


def notify_priority_changed(ticket, old_priority, changed_by):
    """
    Notifica sobre el cambio de prioridad del ticket (solo si aumenta)
    """
    recipients = set()
    
    if ticket.created_by.email:
        recipients.add((ticket.created_by.email, ticket.created_by))
    
    if ticket.assigned_to and ticket.assigned_to.email:
        recipients.add((ticket.assigned_to.email, ticket.assigned_to))
    
    #solo notificar si la prioridad aumentó
    if ticket.priority.level > old_priority.level:
        for email, user in recipients:
            context = {
                'ticket': ticket,
                'old_priority': old_priority,
                'changed_by': changed_by,
                'recipient': user,
                'site_url': settings.SITE_URL,
            }
            
            send_ticket_notification(
                template_name='status_changed.html',  #se reutiliza este template
                subject=f'Prioridad Aumentada - {ticket.ticket_number}',
                recipient_email=email,
                context=context
            )