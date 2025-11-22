"""
Paquete principal de la aplicación API de Películas.
Este módulo inicializa el paquete y expone los componentes principales.
"""

from .database import get_session, engine, create_db_and_tables
from .models import Usuario, Pelicula, Favorito
from .config import settings, get_settings

__version__ = "1.0.1"
__author__ = "Rafael"

__all__ = [
    "get_session",
    "engine",
    "create_db_and_tables",
    "Usuario",
    "Pelicula",
    "Favorito",
    "settings",
    "get_settings",
]

