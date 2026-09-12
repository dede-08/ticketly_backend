# Dockerfile para la aplicación Ticketly
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ticketly_backend.settings.prod

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app/

# collectstatic no depende del entorno: se ejecuta con settings de desarrollo
# para no requerir secretos en tiempo de build.
RUN python manage.py collectstatic --noinput --settings=ticketly_backend.settings.dev

EXPOSE 8000

CMD ["gunicorn", "ticketly_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
