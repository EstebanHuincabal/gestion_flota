from django.utils import timezone
from datetime import timedelta

UMBRAL_INACTIVO_MIN  = 1   # minutos sin señal → desconocido
UMBRAL_DETENIDO_KMH  = 3   # km/h por debajo = detenido
UMBRAL_MOVIMIENTO_KMH = 3  # km/h por encima = en movimiento

def calcular_estado_vehiculo(ultima_ubicacion, ruta_activa=None):
    """
    Retorna: 'en_ruta' | 'en_movimiento' | 'detenido' | 'sin_señal'
    Jerarquía: si tiene ruta activa Y está en movimiento → 'en_ruta'
    """
    if not ultima_ubicacion:
        return 'sin_señal'

    ahora    = timezone.now()
    antiguedad = (ahora - ultima_ubicacion.timestamp).total_seconds() / 60

    if antiguedad > UMBRAL_INACTIVO_MIN:
        return 'sin_señal'

    velocidad = ultima_ubicacion.velocidad or 0

    if ruta_activa and velocidad > UMBRAL_MOVIMIENTO_KMH:
        return 'en_ruta'
    if velocidad > UMBRAL_MOVIMIENTO_KMH:
        return 'en_movimiento'
    return 'detenido'


def get_resumen_flota(empresa):
    """Resumen de estados para los KPI cards."""
    from .models import Vehiculo, Ubicacion, Ruta

    vehiculos = Vehiculo.objects.filter(
        empresa=empresa, activo=True
    ).prefetch_related('asignaciones', 'ubicaciones')

    resumen = {
        'en_ruta':       0,
        'en_movimiento': 0,
        'detenido':      0,
        'sin_señal':     0,
        'total':         0,
    }

    for v in vehiculos:
        ultima = v.ubicaciones.order_by('-timestamp').first()
        ruta   = Ruta.objects.filter(
            vehiculo=v, estado='activo'
        ).first()
        estado = calcular_estado_vehiculo(ultima, ruta)
        resumen[estado] += 1
        resumen['total'] += 1

    return resumen
