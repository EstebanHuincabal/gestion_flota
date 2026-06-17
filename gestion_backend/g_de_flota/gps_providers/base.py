"""
gps_providers/base.py — Interfaz estándar de adaptadores GPS.

El sistema de flota solo interactúa con esta interfaz, nunca con el hardware
directamente. Esto permite intercambiar emulador ↔ dispositivo físico sin tocar
las vistas ni el frontend: basta con implementar un nuevo adaptador.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict


class IGPSProvider(ABC):
    """Interfaz que todo adaptador GPS debe implementar."""

    @abstractmethod
    def connect(self) -> None:
        """Establece conexión con el dispositivo o servicio GPS."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra la conexión limpiamente."""
        raise NotImplementedError

    @abstractmethod
    def get_position(self) -> Dict:
        """Retorna la posición actual.

        Returns:
            dict: { 'latitud': float, 'longitud': float,
                    'velocidad': float, 'timestamp': str ISO8601 }
        """
        raise NotImplementedError

    @abstractmethod
    def on_position_update(self, callback: Callable[[Dict], None]) -> None:
        """Registra un callback que se invoca con cada nueva posición.

        El callback recibe el mismo dict que `get_position()`.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_raw(self, raw: str) -> Dict:
        """Parsea una trama cruda del protocolo del dispositivo.

        Returns:
            dict: el dict estándar de posición.
        """
        raise NotImplementedError
