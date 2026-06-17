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


def calcular_ruta_fallback(puntos):
    """
    Fallback cuando OSRM no está disponible.
    Distancia = suma de segmentos Haversine × 1.3 (factor de sinuosidad).
    Duración  = distancia_km / 60 km·h (velocidad media en carretera).
    Polyline  = sólo los waypoints (el frontend lo dibuja como línea punteada).
    """
    if len(puntos) < 2:
        return None
    distancia_recta = sum(
        haversine_km(
            puntos[i]['lat'], puntos[i]['lng'],
            puntos[i + 1]['lat'], puntos[i + 1]['lng'],
        )
        for i in range(len(puntos) - 1)
    )
    distancia_km = round(distancia_recta * 1.3, 2)
    duracion_min = max(1, round((distancia_km / 60) * 60))
    polyline     = [[p['lat'], p['lng']] for p in puntos]
    return {
        'distancia_km': distancia_km,
        'duracion_min': duracion_min,
        'polyline':     polyline,
        'es_fallback':  True,
    }


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


def detectar_peajes_en_ruta(polyline, categoria_vehiculo='liviano', radio_default_km=0.8):
    """
    Detecta peajes usando radio variable por peaje (radio_metros del modelo).
    Filtra por categoría del vehículo para retornar solo las tarifas correctas.
    Cada peaje tiene su propio radio de detección — los de autopistas urbanas
    necesitan radio menor (200 m) para no detectar peajes de carriles paralelos,
    los rurales pueden tener radio mayor (1000 m).
    Retorna lista de objetos Peaje sin duplicados.
    """
    from .models import Peaje

    peajes_activos = list(Peaje.objects.filter(activo=True, categoria=categoria_vehiculo))
    detectados = []
    ids_vistos = set()

    for peaje in peajes_activos:
        if peaje.id in ids_vistos:
            continue
        radio_km = (peaje.radio_metros / 1000) if peaje.radio_metros else radio_default_km
        plat = float(peaje.latitud)
        plng = float(peaje.longitud)

        encontrado = False
        for punto in polyline:
            dist = haversine_km(punto[0], punto[1], plat, plng)
            if dist <= radio_km:
                encontrado = True
                break

        if encontrado:
            detectados.append(peaje)
            ids_vistos.add(peaje.id)

    return detectados


def calcular_costos(distancia_km, vehiculo, peajes, config_ruta, es_punta=False,
                    categoria_vehiculo=None):
    """
    Calcula el costo estimado de combustible y peajes para una ruta.
    Los peajes ya deben estar filtrados por categoría del vehículo desde
    detectar_peajes_en_ruta().

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
