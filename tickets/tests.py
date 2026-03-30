from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from .models import Ticket, Category, Priority, Status


class TicketlyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.category = Category.objects.create(name='Soporte', description='Soporte técnico')
        self.priority = Priority.objects.create(name='MEDIUM', level=2)
        self.status = Status.objects.create(name='OPEN')

    def test_create_ticket_assigns_ticket_number(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'Ticket de prueba',
            'description': 'Descripción de prueba',
            'category': self.category.id,
            'priority': self.priority.id,
            'status': self.status.id
        }
        response = self.client.post(reverse('ticket-list'), data, format='json')
        self.assertEqual(response.status_code, 201)

        # TicketCreateSerializer no incluye ID en la respuesta, así que verificamos en DB
        ticket = Ticket.objects.get(title='Ticket de prueba', created_by=self.user)
        self.assertTrue(ticket.ticket_number.startswith('TKT-'))
        self.assertEqual(len(ticket.ticket_number), 10)

    def test_my_tickets_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ticket = Ticket.objects.create(
            title='Ticket 2',
            description='Descripcion',
            category=self.category,
            priority=self.priority,
            status=self.status,
            created_by=self.user
        )

        response = self.client.get(reverse('ticket-my-tickets'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertTrue(any(t['id'] == ticket.id for t in response.data))

