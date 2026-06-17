import getpass
import hashlib
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from g_de_flota.models import Usuario, PerfilUsuario, Rol, normalizar_rut


class Command(BaseCommand):
    help = "Crea un superusuario con todos los campos requeridos."

    def handle(self, *args, **kwargs):
        self.stdout.write("\n=== Crear Superusuario ===\n")

        nombre_completo = self._pedir("Nombre completo")
        rut             = self._pedir("RUT (ej: 12.345.678-9)")
        email           = self._pedir("Email")
        password        = self._pedir_password()

        if Usuario.objects.filter(email_hash=Usuario.hash_email(email)).exists():
            self.stderr.write(f"Error: el email '{email}' ya existe.")
            return

        rut_hash = hashlib.sha256(normalizar_rut(rut).encode()).hexdigest()
        if Usuario.objects.filter(rut_hash=rut_hash).exists():
            self.stderr.write(f"Error: el RUT '{rut}' ya está registrado.")
            return

        try:
            # Este comando crea el SUPER ADMINISTRADOR del SaaS: además del acceso
            # a /admin/ (is_superuser), le concede explícitamente el rol de negocio.
            user = Usuario.objects.create_superuser(
                email=email,
                password=password,
                rut=rut,
                nombre_completo=nombre_completo,
                rol=Rol.SUPERADMIN,
            )
            PerfilUsuario.objects.create(user=user)
            self.stdout.write(self.style.SUCCESS(
                f"\nSuperusuario '{email}' creado correctamente."
            ))
        except Exception as e:
            self.stderr.write(f"Error: {e}")

    def _pedir(self, campo: str) -> str:
        while True:
            valor = input(f"{campo}: ").strip()
            if valor:
                return valor
            self.stderr.write(f"  '{campo}' no puede estar vacío.")

    def _pedir_password(self) -> str:
        while True:
            password = getpass.getpass("Contraseña: ")
            if not password:
                self.stderr.write("  La contraseña no puede estar vacía.")
                continue
            confirmacion = getpass.getpass("Confirmar contraseña: ")
            if password != confirmacion:
                self.stderr.write("  Las contraseñas no coinciden.")
                continue
            try:
                validate_password(password)
                return password
            except ValidationError as e:
                for msg in e.messages:
                    self.stderr.write(f"  {msg}")
