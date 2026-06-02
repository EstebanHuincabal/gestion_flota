"""
gps_providers/teltonika.py — Esqueleto del adaptador Teltonika (CODEC8 sobre TCP).

Implementación pendiente hasta que llegue el hardware físico. Documenta el
protocolo y deja la estructura lista para activarse sin tocar el resto del
sistema (solo se registra este adaptador y se levanta el servidor TCP).
"""
from typing import Callable, Dict, Optional

from .base import IGPSProvider


class TeltonikaAdapter(IGPSProvider):
    """Adaptador para dispositivos Teltonika (FMB920, FMC125).

    Protocolo: CODEC8 sobre TCP.

    Configuración del dispositivo físico (se hace UNA sola vez con el software
    Teltonika Configurator):
      - Server IP:   la IP pública del servidor Django.
      - Server Port: el puerto configurado en ConfiguracionGPS (default 5000).
      - Protocol:    TCP.
      - APN:         según operador (Entel: 'bam.entelpcs.cl',
                     Movistar: 'web.movistar.cl').

    Flujo del protocolo CODEC8:
      1. El dispositivo abre conexión TCP al servidor.
      2. Envía un paquete de handshake con el IMEI (15 bytes ASCII precedidos
         de 2 bytes de longitud).
      3. El servidor responde 0x01 (aceptado) o 0x00 (rechazado).
      4. Luego envía paquetes de datos AVL (posición + parámetros de I/O).
      5. Estructura del paquete de datos:
            Preamble(4 = 0x00000000) + DataLength(4) + CodecID(1) +
            RecordCount(1) + Records(...) + RecordCount(1) + CRC16(4)

    Para activar cuando llegue el hardware:
      1. Implementar un servidor TCP (p. ej. en `gps_tcp_server.py`) que escuche
         en `ConfiguracionGPS.servidor_puerto`, haga el handshake del IMEI y
         vaya leyendo paquetes CODEC8.
      2. Completar `parse_raw()` con el parser CODEC8 (ver TODO abajo).
      3. Registrar este adaptador asociándolo al modelo
         'teltonika_fmb920' / 'teltonika_fmc125'.
      4. Por cada record decodificado, hacer POST a
         /api/empresa/gps/posicion/ con { imei, latitud, longitud, velocidad },
         exactamente igual que el emulador.
    """

    def __init__(self, imei: str, host: str = '0.0.0.0', puerto: int = 5000):
        self.imei      = imei
        self.host      = host
        self.puerto    = puerto
        self._callback: Optional[Callable[[Dict], None]] = None
        self._conectado = False

    def connect(self) -> None:
        # TODO (hardware): abrir socket TCP servidor, hacer handshake del IMEI
        # y comenzar a leer paquetes CODEC8 en un hilo.
        raise NotImplementedError(
            'TeltonikaAdapter aún no implementado: requiere el hardware físico y '
            'el servidor TCP CODEC8. Usa NMEAEmulatorAdapter en desarrollo.'
        )

    def disconnect(self) -> None:
        # TODO (hardware): cerrar el socket TCP del servidor limpiamente.
        self._conectado = False

    def get_position(self) -> Dict:
        # TODO (hardware): devolver la última posición decodificada.
        raise NotImplementedError

    def on_position_update(self, callback: Callable[[Dict], None]) -> None:
        self._callback = callback

    def parse_raw(self, raw: str) -> Dict:
        # TODO cuando llegue hardware:
        #   1. `raw` son los bytes del paquete CODEC8.
        #   2. Parsear según spec: https://wiki.teltonika-networks.com/view/Codec
        #   3. lat   = record['lat']   / 10000000.0
        #   4. lng   = record['lng']   / 10000000.0
        #   5. speed = record['speed']               # km/h directo en CODEC8
        #   6. Retornar el dict estándar:
        #      { 'latitud': lat, 'longitud': lng, 'velocidad': speed, 'timestamp': ISO8601 }
        raise NotImplementedError(
            'Parser CODEC8 pendiente. Implementar al integrar el hardware Teltonika.'
        )
