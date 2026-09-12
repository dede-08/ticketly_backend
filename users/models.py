from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Usuario personalizado del sistema.

    Punto de extensión para futuros campos (teléfono, avatar, etc.).
    El rol se deriva de los grupos (ver tickets/permissions.py:get_user_role).
    """

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return self.get_full_name() or self.username