"""
Paquete de routers de la API.
Contiene los endpoints organizados por recurso.
"""

from . import usuarios, peliculas, favoritos

__all__ = [
    "usuarios",
    "peliculas",
    "favoritos"
]

