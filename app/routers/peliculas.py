"""
Router de Películas.
Endpoints para gestionar películas en la plataforma.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlmodel import Session, select, or_, col
from typing import List, Optional

from app.database import get_session
from app.models import Pelicula, Favorito
from app.schemas import PeliculaCreate, PeliculaRead, PeliculaUpdate, peliculas_paginadas, ImagenUploadResp
from app.services.TMDB import get_popular_movies_tmdb, search_movies_tmdb, get_movie_details, download_image_from_tmdb
from app.config import settings


router = APIRouter(
    prefix="/api/peliculas",
    tags=["Películas"]
)


@router.get("/", response_model=peliculas_paginadas)
def listar_peliculas(
    session: Session = Depends(get_session),
    page: int = 0,
    limit: int = 100
):
    """
    Lista todas las películas disponibles.
    
    - **skip**: Número de registros a omitir (para paginación)
    - **limit**: Número máximo de registros a retornar
    """
    offset = (page - 1) * limit

    statement = select(Pelicula).order_by(Pelicula.id).offset(offset).limit(limit)
    peliculas = session.exec(statement).all()

    # Convertir a PeliculaRead con URLs de imagen generadas
    peliculas_read = [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]

    return peliculas_paginadas.from_query(
        items=peliculas_read,
        entity_class=Pelicula,
        session=session,
        current_pg=page,
        limit=limit
    )


@router.get('/{pelicula_id}', response_model=PeliculaRead)
def obtener_pelicula(
    pelicula_id:int ,
    session: Session = Depends(get_session)
):
    """
    Obtine una pelicula por su id

    Args:
        id: id unico de la pelicula

    Returns:
        pelicula: PeliculaRead
    """

    statement = select(Pelicula).where(Pelicula.id == pelicula_id)
    pelicula = session.exec(statement).first()

    if not pelicula:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"no se encontró la pelicula con {pelicula_id}"
        )

    return PeliculaRead.from_db_model(pelicula)


@router.post("/{pelicula_id}/imagen", response_model=ImagenUploadResp)
def cargar_imagen(
    pelicula_id:int,
    imagen:UploadFile = File(...),
    session:Session = Depends(get_session)
):
    """
    Carga una imagen para la pelicula especificada por id
    - **pelicula_id**: ID de la pelicula
    - **imagen**: Archivo de imagen (JPEG, PNG, etc...)
    """

    pelicula = session.get(Pelicula, pelicula_id)
    if not pelicula:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no se encontro la pelicla con id {pelicula_id}"
        )
    range_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if imagen.content_type not in range_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No se permite el tipo de archivo. Solo se permiten: {', '.join(range_types)}"
        )
    
    max_size = 5 * 1024 * 1024 # 5MB

    try:
        content = imagen.file.read()

        if len(content) > max_size:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La imagen no debe superar los 5MB"
            )
    
        pelicula.image_file = content
        session.add(pelicula)
        session.commit()
        session.refresh(pelicula)

        return ImagenUploadResp(
            message="Imagen subida exitosamente",
            image_url=f"/api/peliculas/imagen/{pelicula_id}",
            pelicula_id=pelicula_id
        )
    
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Error al cargar la imagen {str(e)}"
        )
    finally:
        imagen.file.close()
    


@router.get('/imagen/{pelicula_id}')
def obtener_imagen(
    pelicula_id: int,
    session: Session = Depends(get_session)
):
    """
    Obtiene la imagen de una película por su ID.
    
    - **pelicula_id**: ID de la película
    
    Returns:
        Response: Imagen en formato binario con headers apropiados
    """
    # Buscar la película
    pelicula = session.get(Pelicula, pelicula_id)
    
    if not pelicula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Película con id {pelicula_id} no encontrada"
        )
    
    # Verificar si la película tiene imagen
    if not pelicula.image_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La película con id {pelicula_id} no tiene imagen"
        )
    
    # Retornar la imagen como binaria
    return Response(
        content=pelicula.image_file,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"inline; filename=pelicula_{pelicula_id}.jpg",
            "Cache-Control": "public, max-age=3600"  # Cache por 1 hora
        }
    )


@router.post("/", response_model=PeliculaRead, status_code=status.HTTP_201_CREATED)
def crear_pelicula(
    pelicula: PeliculaCreate,
    session: Session = Depends(get_session),
):
    """
    Crea una nueva película en la plataforma.
    Requiere autenticación.
    
    - **titulo**: Título de la película
    - **director**: Director de la película
    - **genero**: Género cinematográfico
    - **duracion**: Duración en minutos
    - **año**: Año de estreno
    - **clasificacion**: Clasificación por edad (G, PG, PG-13, R, etc.)
    - **sinopsis**: Breve descripción de la trama
    """
    statement = select(Pelicula).where(Pelicula.titulo == pelicula.titulo, Pelicula.año == pelicula.año)
    existing_pelicula = session.exec(statement).first()

    if existing_pelicula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una película con el título '{pelicula.titulo}' del año {pelicula.año}"
        )
    
    pelicula_data = pelicula.model_dump()
    db_pelicula = Pelicula(**pelicula_data)
    session.add(db_pelicula)
    session.commit()
    session.refresh(db_pelicula)
    
    return PeliculaRead.from_db_model(db_pelicula)


@router.get('/{pelicula_id}', response_model=PeliculaRead)
def obtener_pelicula(
    pelicula_id:int ,
    session: Session = Depends(get_session)
):
    """
    Obtine una pelicula por su id

    Args:
        id: id unico de la pelicula

    Returns:
        pelicula: PeliculaRead
    """

    statement = select(Pelicula).where(Pelicula.id == pelicula_id)
    pelicula = session.exec(statement).first()

    if not pelicula:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"no se encontró la pelicula con {pelicula_id}"
        )

    return PeliculaRead.from_db_model(pelicula)


@router.put("/{pelicula_id}", response_model=PeliculaRead)
def actualizar_pelicula(
    pelicula_id: int,
    pelicula_update: PeliculaUpdate,
    session: Session = Depends(get_session),
):
    """
    Actualiza la información de una película existente.
    Solo el creador de la película puede actualizarla.
    
    - **pelicula_id**: ID de la película a actualizar
    - Los campos son opcionales, solo se actualizan los proporcionados
    """
    db_pelicula = session.exec(select(Pelicula).where(Pelicula.id == pelicula_id)).first()
    if not db_pelicula:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"La pelicula con id {pelicula_id} no existe"
        )   

    pelicula_data = pelicula_update.model_dump(exclude_unset=True)

    for field, value in pelicula_data.items():
        if field is not None:
            setattr(db_pelicula, field, value)

    session.add(db_pelicula)
    session.commit()
    session.refresh(db_pelicula)

    return PeliculaRead.from_db_model(db_pelicula)


@router.delete("/{pelicula_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pelicula(
    pelicula_id: int,
    session: Session = Depends(get_session),
):
    """
    Elimina una película de la plataforma.
    Solo el creador de la película puede eliminarla.
    
    - **pelicula_id**: ID de la película a eliminar
    
    También se eliminarán todos los favoritos asociados a esta película.
    """
    # Buscar la película
    pelicula = session.get(Pelicula, pelicula_id)
    if not pelicula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Película con id {pelicula_id} no encontrada"
        )
    
    
    # Eliminar la película (los favoritos se eliminan por CASCADE)
    session.delete(pelicula)
    session.commit()
    return None


@router.get("/buscar/", response_model=List[PeliculaRead])
def buscar_peliculas(
    titulo: Optional[str] = Query(None, description="Buscar por título"),
    director: Optional[str] = Query(None, description="Buscar por director"),
    genero: Optional[str] = Query(None, description="Buscar por género"),
    año: Optional[int] = Query(None, description="Buscar por año exacto"),
    año_min: Optional[int] = Query(None, description="Año mínimo"),
    año_max: Optional[int] = Query(None, description="Año máximo"),
    session: Session = Depends(get_session)
):
    """
    Busca películas según diferentes criterios.
    Todos los parámetros son opcionales y se pueden combinar.
    
    - **titulo**: Busca películas que contengan este texto en el título
    - **director**: Busca películas que contengan este texto en el director
    - **genero**: Busca películas que contengan este género
    - **año**: Busca películas de un año específico
    - **año_min**: Busca películas desde este año en adelante
    - **año_max**: Busca películas hasta este año
    """
    statement = select(Pelicula)
    
    if titulo:
        statement = statement.where(col(Pelicula.titulo).contains(titulo))
    
    if director:
        statement = statement.where(col(Pelicula.director).contains(director))
    
    if genero:
        statement = statement.where(col(Pelicula.genero).contains(genero))
    
    if año:
        statement = statement.where(Pelicula.año == año)
    
    if año_min:
        statement = statement.where(Pelicula.año >= año_min)
    
    if año_max:
        statement = statement.where(Pelicula.año <= año_max)
    
    peliculas = session.exec(statement).all()
    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]


@router.get("/populares/top", response_model=List[PeliculaRead])
def peliculas_populares(
    limit: int = Query(10, ge=1, le=50, description="Número de películas a retornar"),
    session: Session = Depends(get_session)
):
    """
    Obtiene las películas más populares basado en la cantidad de favoritos.
    
    - **limit**: Número de películas a retornar (máximo 50)
    """
    from sqlalchemy import func
    statement = (
        select(Pelicula, func.count(Favorito.id).label("count"))
        .join(Favorito)
        .group_by(Pelicula.id)
        .order_by(func.count(Favorito.id).desc()).limit(limit)
    )

    results = session.exec(statement).all()
    peliculas = [result[0] for result in results]
    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]


@router.get("/clasificacion/{clasificacion}", response_model=List[PeliculaRead])
def peliculas_por_clasificacion(
    clasificacion: str,
    session: Session = Depends(get_session),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página")
):
    """
    Obtiene películas filtradas por clasificación de edad.
    
    - **clasificacion**: G, PG, PG-13, R, NC-17
    """
    
    clasificaciones_validas = ["G", "PG", "PG-13", "R", "NC-17"]
    if clasificacion.upper() not in clasificaciones_validas:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el recurso clasificado por {clasificacion}"

        )
    
    statement = select(Pelicula).where(
        Pelicula.clasificacion == clasificacion.upper()
    ).limit(limit)
    peliculas = session.exec(statement).all()
    
    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]



@router.get("/recientes/nuevas", response_model=List[PeliculaRead])
def peliculas_recientes(
    limit: int = Query(10, ge=1, le=100, description="Elementos por página"),
    session: Session = Depends(get_session)
):
    """
    Obtiene las películas más recientes basado en fecha de creación.
    
    - **limit**: Número de películas a retornar
    """
    statement = select(Pelicula).order_by(Pelicula.fecha_creacion.desc()).limit(limit)
    peliculas = session.exec(statement).all()
    
    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]



@router.get("/usuario/{usuario_id}", response_model=List[PeliculaRead])
def peliculas_por_usuario(
    usuario_id: int,
    session: Session = Depends(get_session)
):
    """
    Obtiene todas las películas creadas por un usuario específico.
    Requiere autenticación.
    
    - **usuario_id**: ID del usuario creador
    
    Returns:
        Lista de películas creadas por el usuario
    """    
    statement = select(Pelicula).where(Pelicula.user_id == usuario_id).order_by(Pelicula.fecha_creacion.desc())
    peliculas = session.exec(statement).all()
    
    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]


# =============================================================================
# ENDPOINTS DE INTEGRACIÓN CON TMDB
# =============================================================================

@router.get("/tmdb/populares")
def obtener_peliculas_tmdb_populares(
    page: int = Query(1, ge=1, le=500, description="Número de página de TMDB"),
    importar: bool = Query(False, description="Si es True, importa las películas a la BD"),
    session: Session = Depends(get_session)
):
    """
    Obtiene películas populares desde TMDB.
    
    - **page**: Número de página (1-500)
    - **importar**: Si es True, importa las películas a la base de datos local
    
    Returns:
        Lista de películas en formato compatible con la aplicación
    """
    # Obtener Bearer token desde configuración o variable de entorno
    import os
    bearer_token = os.getenv("TMDB_BEARER_TOKEN", "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIzZTlmYWNiYTA4NGM3NTVhYmEyYmZjYzYzM2M5MzE2NiIsIm5iZiI6MTcyMTM1MTkyMS44OCwic3ViIjoiNjY5OWJlZjE0MjkxNzVmMGFlMTg1ZDU1Iiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.9ywy6ChlgqlRwJxzJXxbFpXCV8mIWSh7Fqy53d4Llwk")
    
    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TMDB_BEARER_TOKEN no configurado. Configura la variable de entorno TMDB_BEARER_TOKEN"
        )
    
    # Obtener películas de TMDB
    peliculas_tmdb = get_popular_movies_tmdb(bearer_token, page)
    
    if not peliculas_tmdb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se pudieron obtener películas de TMDB"
        )
    
    # Si se solicita importar, guardar en la base de datos
    peliculas_importadas = []
    if importar:
        for pelicula_data in peliculas_tmdb:
            # Verificar si ya existe (por título y año)
            statement = select(Pelicula).where(
                Pelicula.titulo == pelicula_data["titulo"],
                Pelicula.año == pelicula_data["año"]
            )
            existing = session.exec(statement).first()
            
            if not existing:
                # Obtener detalles completos para tener el director
                tmdb_id = pelicula_data.get("id")
                poster_path = pelicula_data.get("image_url")
                
                if tmdb_id:
                    detalle = get_movie_details(tmdb_id, bearer_token)
                    if detalle:
                        pelicula_data = detalle
                        poster_path = detalle.get("image_url")
                
                # Remover campos que no están en el modelo
                pelicula_data.pop("id", None)
                pelicula_data.pop("image_url", None)
                
                # Descargar imagen si está disponible
                image_file = None
                if poster_path:
                    image_file = download_image_from_tmdb(poster_path)
                    if image_file:
                        pelicula_data["image_file"] = image_file
                
                # Crear película en BD
                try:
                    nueva_pelicula = Pelicula(**pelicula_data)
                    session.add(nueva_pelicula)
                    session.commit()
                    session.refresh(nueva_pelicula)
                    peliculas_importadas.append(PeliculaRead.from_db_model(nueva_pelicula))
                except Exception as e:
                    session.rollback()
                    print(f"Error importando película {pelicula_data.get('titulo')}: {e}")
        
        return {
            "mensaje": f"Se importaron {len(peliculas_importadas)} películas nuevas",
            "total_obtenidas": len(peliculas_tmdb),
            "peliculas_importadas": peliculas_importadas
        }
    
    return peliculas_tmdb


@router.get("/tmdb/buscar")
def buscar_peliculas_tmdb(
    query: str = Query(..., min_length=1, description="Término de búsqueda"),
    page: int = Query(1, ge=1, le=500, description="Número de página"),
    importar: bool = Query(False, description="Si es True, importa las películas a la BD"),
    session: Session = Depends(get_session)
):
    """
    Busca películas en TMDB por título.
    
    - **query**: Término de búsqueda (mínimo 1 carácter)
    - **page**: Número de página
    - **importar**: Si es True, importa las películas encontradas a la BD local
    
    Returns:
        Lista de películas encontradas
    """
    import os
    bearer_token = os.getenv("TMDB_BEARER_TOKEN", "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIzZTlmYWNiYTA4NGM3NTVhYmEyYmZjYzYzM2M5MzE2NiIsIm5iZiI6MTcyMTM1MTkyMS44OCwic3ViIjoiNjY5OWJlZjE0MjkxNzVmMGFlMTg1ZDU1Iiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.9ywy6ChlgqlRwJxzJXxbFpXCV8mIWSh7Fqy53d4Llwk")
    
    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TMDB_BEARER_TOKEN no configurado"
        )
    
    peliculas_tmdb = search_movies_tmdb(query, bearer_token, page)
    
    if not peliculas_tmdb:
        return []
    
    if importar:
        peliculas_importadas = []
        for pelicula_data in peliculas_tmdb:
            statement = select(Pelicula).where(
                Pelicula.titulo == pelicula_data["titulo"],
                Pelicula.año == pelicula_data["año"]
            )
            existing = session.exec(statement).first()
            
            if not existing:
                # Obtener detalles completos
                tmdb_id = pelicula_data.get("id")
                poster_path = pelicula_data.get("image_url")
                
                if tmdb_id:
                    detalle = get_movie_details(tmdb_id, bearer_token)
                    if detalle:
                        pelicula_data = detalle
                        poster_path = detalle.get("image_url")
                
                # Remover campos extra
                pelicula_data.pop("id", None)
                pelicula_data.pop("image_url", None)
                
                # Descargar imagen si está disponible
                image_file = None
                if poster_path:
                    image_file = download_image_from_tmdb(poster_path)
                    if image_file:
                        pelicula_data["image_file"] = image_file
                
                try:
                    nueva_pelicula = Pelicula(**pelicula_data)
                    session.add(nueva_pelicula)
                    session.commit()
                    session.refresh(nueva_pelicula)
                    peliculas_importadas.append(PeliculaRead.from_db_model(nueva_pelicula))
                except Exception as e:
                    session.rollback()
                    print(f"Error importando película: {e}")
        
        return {
            "mensaje": f"Se importaron {len(peliculas_importadas)} películas nuevas",
            "total_encontradas": len(peliculas_tmdb),
            "peliculas_importadas": peliculas_importadas
        }
    
    return peliculas_tmdb


@router.post("/tmdb/importar/{tmdb_id}", response_model=PeliculaRead, status_code=status.HTTP_201_CREATED)
def importar_pelicula_tmdb(
    tmdb_id: int,
    session: Session = Depends(get_session)
):
    """
    Importa una película específica desde TMDB usando su ID.
    
    - **tmdb_id**: ID de la película en The Movie Database
    
    Returns:
        Película importada con todos sus detalles
    """
    import os
    bearer_token = os.getenv("TMDB_BEARER_TOKEN", "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIzZTlmYWNiYTA4NGM3NTVhYmEyYmZjYzYzM2M5MzE2NiIsIm5iZiI6MTcyMTM1MTkyMS44OCwic3ViIjoiNjY5OWJlZjE0MjkxNzVmMGFlMTg1ZDU1Iiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.9ywy6ChlgqlRwJxzJXxbFpXCV8mIWSh7Fqy53d4Llwk")
    
    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TMDB_BEARER_TOKEN no configurado"
        )
    
    # Obtener detalles completos de la película
    pelicula_data = get_movie_details(tmdb_id, bearer_token)
    
    if not pelicula_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró película con ID {tmdb_id} en TMDB"
        )
    
    # Verificar si ya existe
    statement = select(Pelicula).where(
        Pelicula.titulo == pelicula_data["titulo"],
        Pelicula.año == pelicula_data["año"]
    )
    existing = session.exec(statement).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La película '{pelicula_data['titulo']}' ({pelicula_data['año']}) ya existe en la base de datos"
        )
    
    # Remover campos que no están en el modelo
    poster_path = pelicula_data.pop("image_url", None)
    pelicula_data.pop("id", None)
    
    # Descargar imagen si está disponible
    if poster_path:
        image_file = download_image_from_tmdb(poster_path)
        if image_file:
            pelicula_data["image_file"] = image_file
    
    # Crear película
    try:
        nueva_pelicula = Pelicula(**pelicula_data)
        session.add(nueva_pelicula)
        session.commit()
        session.refresh(nueva_pelicula)
        
        return PeliculaRead.from_db_model(nueva_pelicula)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al importar película: {str(e)}"
        )
