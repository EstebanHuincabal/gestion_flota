import math
import requests


def haversine_km(lat1, lng1, lat2, lng2):
    """Distancia en km entre dos coordenadas (fórmula de Haversine)."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calcular_ruta_osrm(paradas):
    """
    Llama al servidor público OSRM para calcular la ruta entre las paradas.
    paradas: lista de dicts con {'lat': float, 'lng': float} en orden.
    Retorna {'distancia_km', 'duracion_min', 'polyline': [[lat, lng], ...]} o None si falla.
    """
    if len(paradas) < 2:
        return None
    coords = ';'.join(f"{p['lng']},{p['lat']}" for p in paradas)
    url = f"https://router.project-osrm.org/route/v1/driving/{coords}"
    try:
        resp = requests.get(
            url,
            params={'overview': 'full', 'geometries': 'geojson'},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get('code') != 'Ok' or not data.get('routes'):
            return None
        route = data['routes'][0]
        # OSRM GeoJSON devuelve [lng, lat] → convertir a [lat, lng]
        polyline = [[c[1], c[0]] for c in route['geometry']['coordinates']]
        return {
            'distancia_km': round(route['distance'] / 1000, 2),
            'duracion_min': round(route['duration'] / 60),
            'polyline': polyline,
        }
    except Exception:
        return None


def _dist_peaje_segmento(plat, plng, alat, alng, blat, blng):
    """
    Distancia mínima en km entre un punto P y el segmento A-B.
    Usa proyección en coordenadas planas (válido para distancias cortas).
    """
    dAlat = blat - alat
    dAlng = blng - alng
    dPlat = plat - alat
    dPlng = plng - alng
    denom = dAlat ** 2 + dAlng ** 2
    if denom < 1e-12:
        return haversine_km(plat, plng, alat, alng)
    t = max(0.0, min(1.0, (dPlat * dAlat + dPlng * dAlng) / denom))
    proj_lat = alat + t * dAlat
    proj_lng = alng + t * dAlng
    return haversine_km(plat, plng, proj_lat, proj_lng)


def detectar_peajes_en_ruta(polyline, radio_km=2.0):
    """
    Detecta peajes activos cuya posición esté dentro de radio_km de algún
    segmento de la polyline. Usa distancia al segmento (no solo a los puntos)
    para cubrir tramos donde OSRM simplifica y los puntos quedan separados.
    Retorna lista de objetos Peaje sin duplicados.
    """
    from .models import Peaje

    peajes = list(Peaje.objects.filter(activo=True))
    detectados = []
    ids_vistos = set()

    for peaje in peajes:
        if peaje.id in ids_vistos:
            continue
        plat = float(peaje.latitud)
        plng = float(peaje.longitud)

        encontrado = False
        for i in range(len(polyline) - 1):
            dist = _dist_peaje_segmento(
                plat, plng,
                polyline[i][0], polyline[i][1],
                polyline[i + 1][0], polyline[i + 1][1],
            )
            if dist <= radio_km:
                encontrado = True
                break

        # Verificar también el último punto
        if not encontrado and polyline:
            dist = haversine_km(plat, plng, polyline[-1][0], polyline[-1][1])
            if dist <= radio_km:
                encontrado = True

        if encontrado:
            detectados.append(peaje)
            ids_vistos.add(peaje.id)

    return detectados


def calcular_costos(distancia_km, vehiculo, peajes, config_ruta, es_punta=False):
    """
    Calcula el costo estimado de combustible y peajes para una ruta.

    Retorna:
        combustible     — costo estimado de combustible (CLP)
        peajes_total    — suma de tarifas de peajes detectados (CLP)
        total           — combustible + peajes_total
        desglose_peajes — lista de {id, nombre, tarifa} por peaje
        litros_estimados
    """
    consumo = float(vehiculo.consumo_l_100km) if vehiculo else 10.0

    if vehiculo and vehiculo.tipo_combustible == 'diesel':
        precio_litro = float(config_ruta.precio_diesel)
    else:
        precio_litro = float(config_ruta.precio_bencina)

    litros = (distancia_km / 100) * consumo
    costo_combustible = round(litros * precio_litro)

    desglose = []
    costo_peajes = 0
    for p in peajes:
        usar_punta = es_punta and p.tarifa_punta is not None
        tarifa = float(p.tarifa_punta if usar_punta else p.tarifa_normal)
        costo_peajes += tarifa
        desglose.append({'id': p.id, 'nombre': p.nombre, 'tarifa': int(tarifa)})

    return {
        'combustible':      costo_combustible,
        'peajes_total':     int(costo_peajes),
        'total':            costo_combustible + int(costo_peajes),
        'desglose_peajes':  desglose,
        'litros_estimados': round(litros, 2),
    }
