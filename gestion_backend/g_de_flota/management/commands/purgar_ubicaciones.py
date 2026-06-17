from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from g_de_flota.models import Ubicacion

class Command(BaseCommand):
    help = 'Elimina ubicaciones de más de 30 días.'

    def handle(self, *args, **kwargs):
        limite = timezone.now() - timedelta(days=30)
        eliminadas, _ = Ubicacion.objects.filter(
            timestamp__lt=limite
        ).delete()
        self.stdout.write(self.style.SUCCESS(f'{eliminadas} ubicaciones eliminadas.'))
