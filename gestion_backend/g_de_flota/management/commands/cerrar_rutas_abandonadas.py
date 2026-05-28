from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Marca como canceladas las rutas que llevan más de 24 h en estado "activo" sin actualizarse.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--horas', type=int, default=24,
            help='Horas de inactividad antes de cancelar una ruta activa (default: 24)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra las rutas que se cancelarían, sin modificar nada.',
        )

    def handle(self, *args, **options):
        from g_de_flota.models import Ruta

        horas    = options['horas']
        dry_run  = options['dry_run']
        umbral   = timezone.now() - timezone.timedelta(hours=horas)

        rutas = Ruta.objects.filter(
            estado='activo',
            updated_at__lt=umbral,
        ).select_related('empresa', 'conductor', 'vehiculo')

        if not rutas.exists():
            self.stdout.write(self.style.SUCCESS('No hay rutas abandonadas.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Rutas activas sin actualizar por más de {horas} h: {rutas.count()}')
        )

        for ruta in rutas:
            horas_sin_act = (timezone.now() - ruta.updated_at).total_seconds() / 3600
            self.stdout.write(
                f'  Ruta #{ruta.id} "{ruta.nombre}" — empresa: {ruta.empresa.nombre} '
                f'— conductor: {ruta.conductor} — {horas_sin_act:.1f} h inactiva'
            )

        if dry_run:
            self.stdout.write(self.style.NOTICE('Modo dry-run: no se modificó nada.'))
            return

        actualizadas = rutas.update(
            estado='cancelado',
            fecha_fin=timezone.now(),
        )
        self.stdout.write(
            self.style.SUCCESS(f'{actualizadas} ruta(s) marcadas como canceladas.')
        )
