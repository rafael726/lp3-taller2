"""
Servicio para integración con The Movie Database (TMDB) API.
Transforma los datos de TMDB al formato de la aplicación.
"""

import requests
from typing import List, Optional, Dict, Any
from app.services.types import Config


def download_image_from_tmdb(poster_path: str) -> Optional[bytes]:
    """
    Descarga una imagen de TMDB y la retorna como bytes.
    
    Args:
        poster_path: Ruta del poster en TMDB (ej: "/abc123.jpg")
        
    Returns:
        Bytes de la imagen o None si hay error
    """
    if not poster_path:
        return None
    
    base_url = "https://image.tmdb.org/t/p/w500"
    image_url = f"{base_url}{poster_path}"
    
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error descargando imagen {poster_path}: {e}")
        return None


def map_tmdb_to_pelicula(tmdb_movie: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforma un objeto de película de TMDB al formato de PeliculaCreate.
    
    Mapeo de campos:
    - title -> titulo
    - release_date -> año (extraído del año)
    - overview -> sinopsis
    - id -> genero (requiere mapeo adicional)
    - runtime -> duracion (si está disponible)
    - vote_average -> usado para clasificación aproximada
    
    Args:
        tmdb_movie: Diccionario con datos de película de TMDB
        
    Returns:
        Diccionario compatible con PeliculaCreate
    """
    # Mapeo de géneros de TMDB (IDs a nombres)
    GENRE_MAP = {
        28: "Acción",
        12: "Aventura",
        16: "Animación",
        35: "Comedia",
        80: "Crimen",
        99: "Documental",
        18: "Drama",
        10751: "Familia",
        14: "Fantasía",
        36: "Historia",
        27: "Terror",
        10402: "Música",
        9648: "Misterio",
        10749: "Romance",
        878: "Ciencia Ficción",
        10770: "Película de TV",
        53: "Thriller",
        10752: "Guerra",
        37: "Western"
    }
    
    # Extraer año de release_date
    release_date = tmdb_movie.get("release_date", "")
    año = int(release_date.split("-")[0]) if release_date else 2000
    
    # Mapear géneros
    genre_ids = tmdb_movie.get("genre_ids", [])
    generos = [GENRE_MAP.get(gid, "Otro") for gid in genre_ids[:3]]  # Máximo 3 géneros
    genero = ", ".join(generos) if generos else "Sin género"
    
    # Determinar clasificación basada en vote_average y adult flag
    is_adult = tmdb_movie.get("adult", False)
    vote_average = tmdb_movie.get("vote_average", 5.0)
    
    if is_adult:
        clasificacion = "R"
    elif vote_average >= 7.5:
        clasificacion = "PG-13"
    elif vote_average >= 6.0:
        clasificacion = "PG"
    else:
        clasificacion = "G"
    
    return {
        "titulo": tmdb_movie.get("title", "Sin título"),
        "director": "Director desconocido",  # TMDB no incluye director en listados, requiere consulta adicional
        "genero": genero,
        "duracion": tmdb_movie.get("runtime", 120),  # Default 120 min si no está disponible
        "año": año,
        "clasificacion": clasificacion,
        "sinopsis": tmdb_movie.get("overview", "Sin sinopsis disponible")[:1000],  # Límite de 1000 caracteres
        "id": tmdb_movie.get("id"),  # ID de TMDB para referencia
        "image_url": tmdb_movie.get("poster_path"),  # Para cargar imágenes después
    }


def get_movie_details(movie_id: int, bearer_token: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene detalles completos de una película específica de TMDB.
    Incluye información del director y runtime exacto.
    
    Args:
        movie_id: ID de TMDB de la película
        bearer_token: Bearer token de TMDB
        
    Returns:
        Diccionario con detalles completos de la película o None si hay error
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"append_to_response": "credits"}
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        movie_data = response.json()
        
        # Extraer director del crew
        director = "Director desconocido"
        credits = movie_data.get("credits", {})
        crew = credits.get("crew", [])
        for person in crew:
            if person.get("job") == "Director":
                director = person.get("name", "Director desconocido")
                break
        
        # Actualizar con información completa
        movie_data["director"] = director
        
        return map_tmdb_to_pelicula_detallado(movie_data)
    except Exception as e:
        print(f"Error obteniendo detalles de película {movie_id}: {e}")
        return None


def map_tmdb_to_pelicula_detallado(tmdb_movie: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforma datos detallados de TMDB (con información de créditos).
    
    Args:
        tmdb_movie: Diccionario con datos detallados de TMDB
        
    Returns:
        Diccionario compatible con PeliculaCreate
    """
    # Mapeo de géneros (ahora como objetos con nombre)
    genres = tmdb_movie.get("genres", [])
    genero = ", ".join([g.get("name", "") for g in genres[:3]]) if genres else "Sin género"
    
    # Extraer año
    release_date = tmdb_movie.get("release_date", "")
    año = int(release_date.split("-")[0]) if release_date else 2000
    
    # Clasificación real si está disponible
    clasificacion = "PG-13"  # Default
    releases = tmdb_movie.get("release_dates", {}).get("results", [])
    for release in releases:
        if release.get("iso_3166_1") == "US":
            release_data = release.get("release_dates", [])
            if release_data:
                cert = release_data[0].get("certification", "")
                if cert:
                    clasificacion = cert
                    break
    
    return {
        "titulo": tmdb_movie.get("title", "Sin título"),
        "director": tmdb_movie.get("director", "Director desconocido"),
        "genero": genero,
        "duracion": tmdb_movie.get("runtime", 120),
        "año": año,
        "clasificacion": clasificacion,
        "sinopsis": tmdb_movie.get("overview", "Sin sinopsis disponible")[:1000],
        "id": tmdb_movie.get("id"),
        "image_url": tmdb_movie.get("poster_path"),
    }


def get_movie_list(config: Config) -> List[Dict[str, Any]]:
    """
    Obtiene lista de películas de TMDB y las transforma al formato de la aplicación.
    
    Args:
        config: Configuración con URL y headers
        
    Returns:
        Lista de películas en formato compatible con PeliculaCreate
    """
    url = config.url
    headers = config.headers
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        movies = data.get("results", [])
        
        # Transformar cada película al formato de la aplicación
        transformed_movies = [map_tmdb_to_pelicula(movie) for movie in movies]
        
        return transformed_movies
    except Exception as e:
        print(f"Error obteniendo lista de películas: {e}")
        return []


def search_movies_tmdb(query: str, bearer_token: str, page: int = 1) -> List[Dict[str, Any]]:
    """
    Busca películas en TMDB por título.
    
    Args:
        query: Término de búsqueda
        bearer_token: Bearer token de TMDB
        page: Número de página
        
    Returns:
        Lista de películas transformadas
    """
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "query": query,
        "page": page,
        "language": "es-ES"
    }
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        movies = data.get("results", [])
        return [map_tmdb_to_pelicula(movie) for movie in movies]
    except Exception as e:
        print(f"Error buscando películas: {e}")
        return []


def get_popular_movies_tmdb(bearer_token: str, page: int = 1) -> List[Dict[str, Any]]:
    """
    Obtiene películas populares de TMDB.
    
    Args:
        bearer_token: Bearer token de TMDB
        page: Número de página
        
    Returns:
        Lista de películas transformadas
    """
    url = "https://api.themoviedb.org/3/movie/popular"
    params = {
        "page": page,
        "language": "es-ES"
    }
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        print(response)
        data = response.json()
        
        movies = data.get("results", [])
        return [map_tmdb_to_pelicula(movie) for movie in movies]
    except Exception as e:
        print(f"Error obteniendo películas populares: {e}")
        return []
