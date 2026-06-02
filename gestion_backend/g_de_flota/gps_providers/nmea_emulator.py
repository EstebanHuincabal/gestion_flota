"""
gps_providers/nmea_emulator.py — Adaptador GPS emulado.

Simula un rastreador real recorriendo rutas con coordenadas reales de Santiago.
En cada tick avanza al siguiente punto de su ruta, genera una trama NMEA $GPRMC
válida, invoca el callback registrado y hace POST al endpoint de ingesta del
backend, exactamente como lo haría un dispositivo físico.

Uso típico (desde un script o shell de Django):

    from g_de_flota.gps_providers.nmea_emulator import NMEAEmulatorAdapter
    emu = NMEAEmulatorAdapter(imei='350000000000001', api_url='http://localhost:8000')
    emu.connect()      # empieza a emitir cada 5 s en un hilo aparte
    ...
    emu.disconnect()   # detiene el hilo
"""
import json
import random
import threading
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from .base import IGPSProvider


# Rutas con coordenadas reales de Santiago (lat, lng). Cada ruta es una
# secuencia de waypoints que el emulador recorre de forma circular.
RUTAS = {
    'providencia_lascondes': [
        (-33.4263, -70.6200),  # Providencia (Metro Manuel Montt)
        (-33.4180, -70.6010),  # Av. Providencia / Los Leones
        (-33.4140, -70.5870),  # Tobalaba
        (-33.4090, -70.5720),  # El Golf
        (-33.4030, -70.5560),  # Av. Apoquindo
        (-33.4090, -70.5430),  # Las Condes (Escuela Militar)
    ],
    'nunoa_centro': [
        (-33.4560, -70.5980),  # Plaza Ñuñoa
        (-33.4570, -70.6150),  # Av. Irarrázaval
        (-33.4550, -70.6320),  # Estadio Nacional sector
        (-33.4530, -70.6480),  # Av. Vicuña Mackenna
        (-33.4490, -70.6600),  # Baquedano
        (-33.4420, -70.6500),  # Santiago Centro (Plaza de Armas)
    ],
    'maipu_vitacura': [
        (-33.5110, -70.7580),  # Maipú (Plaza Maipú)
        (-33.4920, -70.7200),  # Av. Pajaritos
        (-33.4700, -70.6900),  # Estación Central
        (-33.4380, -70.6500),  # Santiago Centro
        (-33.4200, -70.6000),  # Providencia
        (-33.3900, -70.5750),  # Vitacura (Av. Vitacura)
    ],
}


def _generar_gprmc(lat: float, lng: float, velocidad_kmh: float) -> str:
    """Construye una trama NMEA $GPRMC válida (con checksum) a partir de la posición."""
    ahora = datetime.now(timezone.utc)
    hhmmss = ahora.strftime('%H%M%S')
    ddmmyy = ahora.strftime('%d%m%y')

    # Latitud → ddmm.mmmm
    lat_abs = abs(lat)
    lat_g   = int(lat_abs)
    lat_m   = (lat_abs - lat_g) * 60
    lat_str = f"{lat_g:02d}{lat_m:07.4f}"
    lat_hem = 'N' if lat >= 0 else 'S'

    # Longitud → dddmm.mmmm
    lng_abs = abs(lng)
    lng_g   = int(lng_abs)
    lng_m   = (lng_abs - lng_g) * 60
    lng_str = f"{lng_g:03d}{lng_m:07.4f}"
    lng_hem = 'E' if lng >= 0 else 'W'

    nudos = velocidad_kmh / 1.852  # km/h → nudos

    cuerpo = (
        f"GPRMC,{hhmmss}.00,A,{lat_str},{lat_hem},"
        f"{lng_str},{lng_hem},{nudos:.1f},000.0,{ddmmyy},,,A"
    )

    # Checksum XOR de todos los caracteres entre '$' y '*'
    checksum = 0
    for c in cuerpo:
        checksum ^= ord(c)

    return f"${cuerpo}*{checksum:02X}"


class NMEAEmulatorAdapter(IGPSProvider):
    """Adaptador que emula un rastreador GPS recorriendo una ruta de Santiago."""

    def __init__(self, imei: str, api_url: str, intervalo_seg: int = 5,
                 ruta_puntos: Optional[list] = None, api_key: str = ''):
        self.imei          = imei
        self.api_url       = api_url.rstrip('/')
        self.intervalo_seg = intervalo_seg
        self.api_key       = api_key

        if ruta_puntos and len(ruta_puntos) >= 2:
            # Recorrer la ruta REAL asignada (polyline OSRM `[[lat, lng], ...]`).
            # Se submuestrea para que el recorrido dure un tiempo razonable.
            self.ruta        = self._submuestrear(ruta_puntos, max_puntos=40)
            self.ruta_nombre = 'ruta_asignada'
            self._ruta_real  = True
        else:
            # Sin ruta asignada: elegir una ruta fija determinística por IMEI.
            nombres_ruta     = list(RUTAS.keys())
            idx              = sum(ord(c) for c in imei) % len(nombres_ruta)
            self.ruta_nombre = nombres_ruta[idx]
            self.ruta        = RUTAS[self.ruta_nombre]
            self._ruta_real  = False

        self._indice    = 0
        self._running   = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[Dict], None]] = None
        self._ultima_posicion: Optional[Dict] = None

    @staticmethod
    def _submuestrear(puntos: list, max_puntos: int = 40) -> list:
        """Reduce una polyline larga a ~max_puntos conservando inicio y fin.

        Las polylines OSRM tienen cientos de vértices; recorrerlos uno por tick
        tomaría demasiado. Tomamos una muestra uniforme para un recorrido fluido.
        """
        pts = [(float(p[0]), float(p[1])) for p in puntos]
        if len(pts) <= max_puntos:
            return pts
        paso = len(pts) / max_puntos
        muestra = [pts[int(i * paso)] for i in range(max_puntos)]
        if muestra[-1] != pts[-1]:
            muestra.append(pts[-1])
        return muestra

    # ── IGPSProvider ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Inicia el hilo emisor. No bloquea."""
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def disconnect(self) -> None:
        """Detiene el hilo emisor de forma cooperativa."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.intervalo_seg + 1)
        self._thread = None

    def get_position(self) -> Dict:
        """Última posición emitida, o el primer punto de la ruta si no hay ninguna."""
        if self._ultima_posicion:
            return self._ultima_posicion
        lat, lng = self.ruta[0]
        return {
            'latitud':   lat,
            'longitud':  lng,
            'velocidad': 0.0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    def on_position_update(self, callback: Callable[[Dict], None]) -> None:
        self._callback = callback

    def parse_raw(self, raw: str) -> Dict:
        """Parsea una trama NMEA $GPRMC real y devuelve el dict estándar de posición.

        Soporta el formato:
            $GPRMC,hhmmss.ss,A,ddmm.mmmm,N,dddmm.mmmm,E,vel_nudos,rumbo,ddmmyy,...*CS
        """
        cuerpo = raw.strip()
        if cuerpo.startswith('$'):
            cuerpo = cuerpo[1:]
        if '*' in cuerpo:
            cuerpo = cuerpo.split('*', 1)[0]

        campos = cuerpo.split(',')
        if len(campos) < 8 or not campos[0].endswith('GPRMC'):
            raise ValueError('Trama NMEA no es un $GPRMC válido')

        lat_raw, lat_hem = campos[3], campos[4]
        lng_raw, lng_hem = campos[5], campos[6]
        vel_nudos        = campos[7]

        # ddmm.mmmm → grados decimales
        lat_deg = float(lat_raw[:2]) + float(lat_raw[2:]) / 60.0
        if lat_hem == 'S':
            lat_deg = -lat_deg

        lng_deg = float(lng_raw[:3]) + float(lng_raw[3:]) / 60.0
        if lng_hem == 'W':
            lng_deg = -lng_deg

        velocidad_kmh = float(vel_nudos or 0) * 1.852  # nudos → km/h

        return {
            'latitud':   round(lat_deg, 6),
            'longitud':  round(lng_deg, 6),
            'velocidad': round(velocidad_kmh, 1),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    # ── Internos ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Bucle principal del hilo: emite una posición cada `intervalo_seg`."""
        import time
        while self._running:
            try:
                self._tick()
            except Exception:
                # Nunca dejamos morir el hilo por un error puntual de red.
                pass
            time.sleep(self.intervalo_seg)

    def _tick(self) -> None:
        """Avanza un punto en la ruta y emite la posición."""
        lat_base, lng_base = self.ruta[self._indice]
        self._indice = (self._indice + 1) % len(self.ruta)  # circular

        # En ruta real el ruido es mínimo (seguir el trazado); en ruta fija algo mayor.
        ruido = 0.0001 if self._ruta_real else 0.0005
        lat = lat_base + random.uniform(-ruido, ruido)
        lng = lng_base + random.uniform(-ruido, ruido)
        velocidad = round(random.uniform(20, 70), 1)

        # Trama NMEA (se reparsea para validar el ciclo generar→parsear)
        trama = _generar_gprmc(lat, lng, velocidad)
        posicion = self.parse_raw(trama)

        self._ultima_posicion = posicion

        # 1. Callback en proceso (si hay alguien escuchando)
        if self._callback:
            try:
                self._callback(posicion)
            except Exception:
                pass

        # 2. POST al endpoint de ingesta, igual que un dispositivo físico
        self._enviar_posicion(posicion)

    def _enviar_posicion(self, posicion: Dict) -> None:
        """POST {api_url}/api/empresa/gps/posicion/ con el IMEI y la posición."""
        cuerpo = {
            'imei':      self.imei,
            'latitud':   posicion['latitud'],
            'longitud':  posicion['longitud'],
            'velocidad': posicion['velocidad'],
        }
        if self.api_key:
            cuerpo['api_key'] = self.api_key
        payload = json.dumps(cuerpo).encode('utf-8')

        req = urllib.request.Request(
            f"{self.api_url}/api/empresa/gps/posicion/",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            # El emulador no debe caerse si el backend no responde un tick.
            pass
