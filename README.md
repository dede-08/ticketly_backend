# Ticketly Backend

Backend Django REST API para gestión de tickets (helpdesk) con usuarios, asignación, comentarios y adjuntos.

## Requisitos

- Python 3.12
- PostgreSQL
- pip

## Configuración

1. Crear y activar virtualenv:

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
```

2. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

3. Copiar archivo de ejemplo:

```powershell
copy .env.example .env
```

4. Ajustar variables en `.env` (incluyendo `DJANGO_SECRET_KEY`, DB y email).

5. Migrar y crear superusuario:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

6. Correr servidor:

```powershell
python manage.py runserver
```

## Ejecutar tests

```powershell
python manage.py test
```

## CI/CD (GitHub Actions)

Hay workflow en `.github/workflows/django.yml` que ejecuta tests y `ruff`.

## Contenerización

```powershell
docker-compose up --build
```

## Mejores prácticas aplicadas

- Configuración por entorno (`.env`, `django-dotenv`).
- Seguridad de cookies/HSTS ajustable.
- Logging de errores con `logging.exception`.
- `Ticket.ticket_number` generado con `transaction.atomic` + `select_for_update`.
- Validación de adjuntos en backend (tamaño y extensiones).
- Test básico del endpoint de tickets.
