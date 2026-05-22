from django.core.management.base import BaseCommand
from g_de_flota.models import Peaje

# (nombre, ruta, lat, lng, tarifa_normal, tarifa_punta)
PEAJES = [
    # Ruta 5 Norte
    ('Lampa Troncal',       'Ruta 5 Norte', -33.2800, -70.7400, 2917, None),
    ('Las Vegas Troncal',   'Ruta 5 Norte', -32.8200, -71.1210, 2917, None),
    ('Pichidangui Troncal', 'Ruta 5 Norte', -32.1456, -71.5234, 4376, None),
    ('Los Vilos Troncal',   'Ruta 5 Norte', -31.9098, -71.5012, 4050, None),
    ('Socos Troncal',       'Ruta 5 Norte', -30.7200, -71.5250, 4050, None),
    ('Serena Troncal',      'Ruta 5 Norte', -29.9500, -71.2840, 4050, None),
    # Ruta 5 Sur
    ('Río Maipo Troncal',   'Ruta 5 Sur',  -33.6500, -70.7200, 1320, None),
    ('Angostura Troncal',   'Ruta 5 Sur',  -33.7900, -70.7300, 3100, None),
    ('Graneros Troncal',    'Ruta 5 Sur',  -34.0600, -70.7530, 3100, None),
    ('Talca Troncal',       'Ruta 5 Sur',  -35.4234, -71.6234, 3100, None),
    ('Linares Troncal',     'Ruta 5 Sur',  -35.8503, -71.6293, 3100, None),
    ('Chillán Troncal',     'Ruta 5 Sur',  -36.6200, -72.1571, 3500, None),
    ('Collipulli Troncal',  'Ruta 5 Sur',  -37.9456, -72.4345, 3500, None),
    ('Temuco Troncal',      'Ruta 5 Sur',  -38.7305, -72.5475, 3500, None),
    ('Osorno Troncal',      'Ruta 5 Sur',  -40.5678, -73.1234, 3500, None),
    # Ruta 68 (Santiago–Valparaíso)
    ('Zapata',              'Ruta 68',     -33.4456, -70.9789, 2700, 4100),
    ('Lo Prado',            'Ruta 68',     -33.4012, -71.1234, 2700, 4100),
    ('Casablanca',          'Ruta 68',     -33.3234, -71.4123, 2700, 4100),
    # Ruta 78
    ('Melipilla A',         'Ruta 78',     -33.6890, -71.2134, 3300, None),
    ('Melipilla B',         'Ruta 78',     -33.7234, -71.4012, 5940, None),
    # Ruta 60 CH
    ('Quillota Troncal',    'Ruta 60 CH',  -32.8789, -71.2345, 5000, 7000),
    # Ruta 57 (Los Andes)
    ('Chacabuco',           'Ruta 57',     -33.0234, -70.6789, 2700, None),
    ('Los Andes',           'Ruta 57',     -32.8345, -70.5901, 2700, None),
]


class Command(BaseCommand):
    help = 'Carga los peajes de rutas principales de Chile (datos MOP aproximados).'

    def handle(self, *args, **options):
        creados = actualizados = 0

        for nombre, ruta, lat, lng, tarifa_normal, tarifa_punta in PEAJES:
            _, created = Peaje.objects.update_or_create(
                nombre=nombre,
                ruta=ruta,
                defaults={
                    'latitud':       lat,
                    'longitud':      lng,
                    'tarifa_normal': tarifa_normal,
                    'tarifa_punta':  tarifa_punta,
                    'activo':        True,
                },
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Peajes: {creados} creados, {actualizados} actualizados ({len(PEAJES)} registros total).'
        ))
