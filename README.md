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

6. Crear los roles del sistema (Usuario Normal, Agente de Soporte, Supervisor, Administrador):

```powershell
python manage.py setup_roles
```

7. Correr servidor:

```powershell
python manage.py runserver
```

> La API es versionada: todos los endpoints viven bajo `/api/v1/`.
> `migrate` aplica también las tablas del blacklist de JWT (logout).

## Ejecutar tests

```powershell
python manage.py test
```

## Documentación de la API

Con el servidor corriendo, en `http://localhost:8000/api/docs/` (Swagger UI)
y `http://localhost:8000/api/schema/` (schema OpenAPI).

## CI/CD (GitHub Actions)

Hay workflow en `.github/workflows/django.yml` que ejecuta tests y `ruff`.

## Contenerización

Levantar API + PostgreSQL + Redis:

```powershell
docker-compose up --build
```

> El contenedor usa la configuración de producción (`settings.prod`) y
> `DB_HOST=db`/`REDIS_URL` ya se inyectan. Asegura `DJANGO_SECRET_KEY` en `.env`.

## Entornos de configuración

- `ticketly_backend.settings.dev` — desarrollo (por defecto, `DEBUG=True`).
- `ticketly_backend.settings.prod` — producción (`DEBUG=False`, HSTS/cookies seguras).

Selección con la variable `DJANGO_SETTINGS_MODULE`.
`setup_env.py` genera un `.env` inicial con valores seguros.

## Mejores prácticas aplicadas

- Configuración por entorno (`.env`, `django-dotenv`, paquete `settings/` base/dev/prod).
- Seguridad de cookies/HSTS ajustable.
- Logging de errores con `logging.exception`.
- `Ticket.ticket_number` generado con `transaction.atomic` + `select_for_update`.
- Validación de adjuntos en backend (tamaño y extensiones).
- Control de acceso por roles (grupos): los usuarios normales solo ven sus
  tickets; solo Supervisor/Administrador pueden asignar; los comentarios
  internos son exclusivos del personal de soporte.
- Modelo de usuario personalizado (`users.User` con `AUTH_USER_MODEL`):
  punto de extensión para futuros campos sin migraciones destructivas.
- Archivos estáticos servidos con whitenoise en producción (`collectstatic`).
- Cache Redis opcional para throttling global entre workers.
- Documentación OpenAPI con `drf-spectacular`.
