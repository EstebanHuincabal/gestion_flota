from django.core.management.base import BaseCommand
from g_de_flota.models import Peaje

# Estructura: (nombre, ruta, lat, lng, radio_metros,
#              t_moto, t_liviano, t_liviano_rem, t_pesado_2, t_pesado_3,
#              p_moto, p_liviano, p_liviano_rem, p_pesado_2, p_pesado_3)
# p_* = tarifa punta (None = no tiene tarifa diferenciada)

PEAJES = [
    # ─── Ruta 68 ─────────────────────────────────────────────────────────────
    ('Zapata',    'Ruta 68', -33.4456, -70.9789, 600,
     800, 2700, 3400, 4800,  8600,
     1200, 4000, 5000, 7200, 12900),
    ('Lo Prado',  'Ruta 68', -33.4012, -71.1234, 600,
     800, 2700, 3400, 4800,  8600,
     1200, 4000, 5000, 7200, 12900),
    ('Casablanca','Ruta 68', -33.3234, -71.4123, 600,
     800, 2700, 3400, 4800,  8600,
     1200, 4000, 5000, 7200, 12900),

    # ─── Ruta 5 Norte — Las Vegas y Pichidangui ──────────────────────────────
    ('Las Vegas',   'Ruta 5 Norte', -32.8234, -71.0123, 1000,
     1200, 4050, 5100, 7300, 12950,
     None, None, None, None,  None),
    ('Pichidangui', 'Ruta 5 Norte', -32.1456, -71.5234, 1000,
     1200, 4050, 5100, 7300, 12950,
     None, None, None, None,  None),

    # ─── Ruta 5 Norte — Lampa ────────────────────────────────────────────────
    ('Lampa', 'Ruta 5 Norte', -33.2847, -70.9142, 800,
     750, 2917, 3700, 5250, 9330,
     None, None, None, None, None),

    # ─── Ruta 5 Norte Los Vilos–Serena ───────────────────────────────────────
    ('Socos',  'Ruta 5 Norte', -30.7234, -71.4567, 1000,
     1200, 4050, 5100, 7300, 12950,
     None, None, None, None,  None),
    ('Serena', 'Ruta 5 Norte', -29.9456, -71.2345, 1000,
     1200, 4050, 5100, 7300, 12950,
     None, None, None, None,  None),

    # ─── Ruta 5 Sur troncal Stgo–Talca ───────────────────────────────────────
    ('Río Maipo',  'Ruta 5 Sur', -33.6789, -70.8901, 1000,
     950, 3800, 4800, 6840, 12160,
     None, None, None, None,  None),
    ('Angostura',  'Ruta 5 Sur', -33.8901, -70.8456, 1000,
     950, 3800, 4800, 6840, 12160,
     None, None, None, None,  None),
    ('Talca',      'Ruta 5 Sur', -35.4234, -71.6234, 1000,
     950, 3800, 4800, 6840, 12160,
     None, None, None, None,  None),

    # ─── Ruta 5 Sur lateral ──────────────────────────────────────────────────
    ('Río Maipo Lateral', 'Ruta 5 Sur', -33.6820, -70.8950, 400,
     230, 900, 1140, 1620, 2880,
     None, None, None, None, None),

    # ─── Ruta 5 Sur Talca–Chillán ────────────────────────────────────────────
    ('Chillán', 'Ruta 5 Sur', -36.6234, -72.1012, 1000,
     900, 3100, 3900, 5580, 9920,
     None, None, None, None, None),

    # ─── Ruta 5 Sur Chillán–Collipulli ───────────────────────────────────────
    ('Collipulli', 'Ruta 5 Sur', -37.9456, -72.4345, 1000,
     1000, 3200, 4030, 5760, 10240,
     None,  None,  None,  None,  None),

    # ─── Ruta 5 Sur Temuco–Osorno ────────────────────────────────────────────
    ('Temuco', 'Ruta 5 Sur', -38.7345, -72.5901, 1000,
     950, 3500, 4400, 6300, 11200,
     None, None, None, None,  None),
    ('Osorno',  'Ruta 5 Sur', -40.5678, -73.1234, 1000,
     950, 3500, 4400, 6300, 11200,
     None, None, None, None,  None),

    # ─── Ruta 57 Santiago–Los Andes ──────────────────────────────────────────
    ('Chacabuco', 'Ruta 57', -33.0234, -70.6789, 700,
     680, 2700, 3400, 4860, 8640,
     None, None, None, None, None),
    ('Los Andes', 'Ruta 57', -32.8345, -70.5901, 700,
     680, 2700, 3400, 4860, 8640,
     None, None, None, None, None),

    # ─── Ruta 78 ─────────────────────────────────────────────────────────────
    ('Melipilla A', 'Ruta 78', -33.6890, -71.2134, 500,
     830,  3300,  4160,  5940, 10560,
     None,  None,  None,  None,  None),
    ('Melipilla B', 'Ruta 78', -33.7234, -71.4012, 500,
     1490,  5940,  7480, 10690, 19010,
     None,  None,  None,  None,  None),

    # ─── Ruta 60 CH ──────────────────────────────────────────────────────────
    ('Quillota', 'Ruta 60 CH', -32.8789, -71.2345, 700,
     1250, 5000, 6300, 9000, 16000,
     1750, 7000, 8820, 12600, 22400),
]

CATEGORIAS = ['moto', 'liviano', 'liviano_rem', 'pesado_2', 'pesado_3']


class Command(BaseCommand):
    help = 'Carga/actualiza los peajes de Chile 2026 con tarifas reales por categoría.'

    def handle(self, *args, **options):
        creados = actualizados = 0

        for row in PEAJES:
            (nombre, ruta, lat, lng, radio,
             t_moto, t_liviano, t_liviano_rem, t_pesado_2, t_pesado_3,
             p_moto, p_liviano, p_liviano_rem, p_pesado_2, p_pesado_3) = row

            tarifas_normal = {
                'moto':        t_moto,
                'liviano':     t_liviano,
                'liviano_rem': t_liviano_rem,
                'pesado_2':    t_pesado_2,
                'pesado_3':    t_pesado_3,
            }
            tarifas_punta = {
                'moto':        p_moto,
                'liviano':     p_liviano,
                'liviano_rem': p_liviano_rem,
                'pesado_2':    p_pesado_2,
                'pesado_3':    p_pesado_3,
            }

            for cat in CATEGORIAS:
                _, created = Peaje.objects.update_or_create(
                    nombre=nombre,
                    ruta=ruta,
                    categoria=cat,
                    defaults={
                        'latitud':       lat,
                        'longitud':      lng,
                        'radio_metros':  radio,
                        'tarifa_normal': tarifas_normal[cat],
                        'tarifa_punta':  tarifas_punta[cat],
                        'activo':        True,
                    },
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

        total = len(PEAJES) * len(CATEGORIAS)
        self.stdout.write(self.style.SUCCESS(
            f'Peajes: {creados} creados, {actualizados} actualizados '
            f'({total} registros — {len(PEAJES)} ubicaciones × {len(CATEGORIAS)} categorías).'
        ))
