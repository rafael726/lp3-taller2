"""
Módulo de utilidades para la aplicación.
Contiene funciones auxiliares utilizadas en diferentes partes de la aplicación.
"""
import re
from datetime import datetime, date

def validar_correo(correo):
    """
    Valida que un correo electrónico tenga un formato válido.
    
    Args:
        correo (str): Correo electrónico a validar
        
    Returns:
        bool: True si el correo es válido, False en caso contrario
    """
    patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(patron, correo))

def formatear_duracion(minutos):
    """
    Convierte una duración en minutos a formato hh:mm
    
    Args:
        minutos (int): Duración en minutos
        
    Returns:
        str: Duración formateada como hh:mm
    """
    hora, minutos = divmod(minutos, 60)
    return f"{hora:02d}:{minutos:02d}"

print(formatear_duracion(180))
def generar_slug(texto):
    """
    Genera un slug a partir de un texto.
    Un slug es una versión de texto amigable para URLs.
    
    Args:
        texto (str): Texto a convertir en slug
        
    Returns:
        str: Slug generado
    """
    # Convertir a minúsculas
    slug = texto.lower().strip()
    
    #  Reemplazar espacios con guiones
    slug = re.sub(r'[\s_-]+', '-', slug)
    # Eliminar caracteres no alfanuméricos (excepto guiones)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Reemplazar múltiples guiones con uno solo
    slug = re.sub(r'-+', '-', slug)
    
    # Eliminar guiones al inicio y final
    slug = slug.strip('-')
    
    return slug

def obtener_año_actual():
    """
    Obtiene el año actual.
    
    Returns:
        int: Año actual
    """
    #  pendiente por implementar
    
    año_actual = date.today().year
    return año_actual
print(obtener_año_actual())

def validar_año(año):
    """
    Valida que un año sea válido (no futuro y no muy antiguo).
    
    Args:
        año (int): Año a validar
        
    Returns:
        bool: True si el año es válido, False en caso contrario
    """
    año_actual = obtener_año_actual()
    return 1900 <= año <= año_actual

print(validar_año(2026))

