from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Ticket, Category, Priority, Status

User = get_user_model()


class TicketlyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.category = Category.objects.create(name='Soporte', description='Soporte técnico')
        self.priority = Priority.objects.create(name='MEDIUM', level=2)
        self.status = Status.objects.create(name='OPEN')

    def _create_ticket(self, created_by, assigned_to=None):
        return Ticket.objects.create(
            title='Ticket X',
            description='Descripcion',
            category=self.category,
            priority=self.priority,
            status=self.status,
            created_by=created_by,
            assigned_to=assigned_to,
        )

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
        self.assertIsInstance(response.data, dict)
        self.assertTrue(any(t['id'] == ticket.id for t in response.data['results']))


class SecurityPermissionsTestCase(TestCase):
    """regresion de los controles de acceso por rol"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other = User.objects.create_user(username='otheruser', password='password123')
        self.category = Category.objects.create(name='Soporte', description='Soporte técnico')
        self.priority = Priority.objects.create(name='MEDIUM', level=2)
        self.status = Status.objects.create(name='OPEN')

    def _create_ticket(self, created_by=None, assigned_to=None):
        return Ticket.objects.create(
            title='Ticket de seguridad',
            description='Descripcion',
            category=self.category,
            priority=self.priority,
            status=self.status,
            created_by=created_by or self.other,
            assigned_to=assigned_to,
        )

    def test_normal_user_cannot_list_others_tickets(self):
        ticket = self._create_ticket(created_by=self.other)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('ticket-list'))
        self.assertEqual(response.status_code, 200)
        ids = [t['id'] for t in response.data['results']]
        self.assertNotIn(ticket.id, ids)

    def test_normal_user_cannot_assign_tickets(self):
        ticket = self._create_ticket(created_by=self.user)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'user_id': self.other.id},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_create_internal_comment(self):
        ticket = self._create_ticket(created_by=self.user)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse('ticket-add-comment', args=[ticket.id]),
            {'content': 'nota interna', 'is_internal': True},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_internal_comments_hidden_from_normal_user(self):
        from .models import Comment
        ticket = self._create_ticket(created_by=self.user)
        internal = Comment.objects.create(ticket=ticket, user=self.other, content='nota interna', is_internal=True)
        public = Comment.objects.create(ticket=ticket, user=self.other, content='publico')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('ticket-detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        comment_ids = [c['id'] for c in response.data['comments']]
        self.assertNotIn(internal.id, comment_ids)
        self.assertIn(public.id, comment_ids)

    def test_supervisor_can_assign_tickets(self):
        Group.objects.get_or_create(name='Supervisor')
        supervisor = User.objects.create_user(username='supervisor', password='password123')
        supervisor.groups.add(Group.objects.get(name='Supervisor'))
        ticket = self._create_ticket(created_by=self.user)
        self.client.force_authenticate(user=supervisor)
        response = self.client.post(
            reverse('ticket-assign', args=[ticket.id]),
            {'user_id': self.other.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)


class AuthAndReadOnlyTestCase(TestCase):
    """registro de usuarios y endpoints de solo lectura"""

    def setUp(self):
        self.client = APIClient()

    def test_register_returns_tokens(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'nuevo_usuario',
                'password': 'Segura123!',
                'password2': 'Segura123!',
                'email': 'nuevo@example.com',
                'first_name': 'Nuevo',
                'last_name': 'Usuario',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

    def test_statistics_forbidden_for_normal_user(self):
        user = User.objects.create_user(username='normal', password='password123')
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse('ticket-statistics'))
        self.assertEqual(response.status_code, 403)

    def test_categories_are_read_only(self):
        user = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse('category-list'),
            {'name': 'Nueva Categoría', 'description': 'test'},
            format='json',
        )
        self.assertEqual(response.status_code, 405)

