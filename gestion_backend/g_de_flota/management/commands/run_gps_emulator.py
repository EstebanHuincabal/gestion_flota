"""
run_gps_emulator — Arranca emuladores GPS para dispositivos modelo 'emulador'.

Cada emulador recorre una ruta real de Santiago y hace POST a
/api/empresa/gps/posicion/ cada N segundos, exactamente como un dispositivo
físico. Sirve para demostrar el mapa de flota en tiempo real sin hardware.

Uso:
    # Todos los dispositivos modelo 'emulador' que tengan vehículo asignado
    python manage.py run_gps_emulator

    # Un IMEI específico
    python manage.py run_gps_emulator --imei 350000000000001

    # Cambiar URL del backend e intervalo
    python manage.py run_gps_emulator --api-url http://localhost:8000 --intervalo 5

Detener con Ctrl+C.
"""
import time

from django.core.management.base import BaseCommand

from g_de_flota.models import DispositivoGPS
from g_de_flota.gps_providers.nmea_emulator import NMEAEmulatorAdapter


class Command(BaseCommand):
    help = 'Arranca emuladores GPS que reportan posiciones al backend.'

    def add_arguments(self, parser):
        parser.add_argument('--imei', type=str, default=None,
                            help='IMEI específico a emular (por defecto: todos los emuladores asignados).')
        parser.add_argument('--api-url', type=str, default='http://localhost:8000',
                            help='URL base del backend (default: http://localhost:8000).')
        parser.add_argument('--intervalo', type=int, default=5,
                            help='Segundos entre reportes de posición (default: 5).')

    def handle(self, *args, **opts):
        qs = DispositivoGPS.objects.filter(activo=True, vehiculo__isnull=False)
        if opts['imei']:
            qs = qs.filter(imei=opts['imei'])
        else:
            qs = qs.filter(modelo='emulador')

        dispositivos = list(qs)
        if not dispositivos:
            self.stdout.write(self.style.WARNING(
                'No hay dispositivos emulador activos con vehículo asignado. '
                'Registra uno en Gestión GPS y asígnale un vehículo.'
            ))
            return

        emuladores = []
        for d in dispositivos:
            # Si el vehículo tiene una ruta en curso, el emulador recorre su
            # trazado real (polyline OSRM). Si no, usa una ruta fija de demo.
            ruta_activa = (
                d.vehiculo.rutas
                .filter(estado='activo')
                .order_by('-fecha_inicio')
                .first()
            )
            ruta_puntos = ruta_activa.polyline if (ruta_activa and ruta_activa.polyline) else None

            emu = NMEAEmulatorAdapter(
                imei=d.imei,
                api_url=opts['api_url'],
                intervalo_seg=opts['intervalo'],
                ruta_puntos=ruta_puntos,
                api_key=d.api_key,   # autenticar la ingesta si el dispositivo tiene clave
            )
            emu.connect()
            emuladores.append(emu)

            if ruta_puntos:
                self.stdout.write(self.style.SUCCESS(
                    f'▶ Emulando {d.imei} → ruta asignada "{ruta_activa.nombre}" '
                    f'(vehículo {d.vehiculo.patente}, {len(emu.ruta)} puntos)'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'▶ Emulando {d.imei} → ruta fija "{emu.ruta_nombre}" '
                    f'(vehículo {d.vehiculo.patente} — sin ruta activa)'
                ))

        self.stdout.write(self.style.NOTICE(
            f'\n{len(emuladores)} emulador(es) activos. Ctrl+C para detener.\n'
        ))

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write('\nDeteniendo emuladores...')
            for emu in emuladores:
                emu.disconnect()
            self.stdout.write(self.style.SUCCESS('Emuladores detenidos.'))
