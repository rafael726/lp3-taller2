"""
Router de Usuarios.
Endpoints para gestionar usuarios en la plataforma.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from typing import List

from app.database import get_session
from app.models import Usuario, Favorito, Pelicula
from app.schemas import (
    Login,
    MessageResponse,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
    PeliculaRead,
    usuarios_paginados
)


router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuarios"]
)


@router.post("/login", response_model=UsuarioRead)
def login(
    usuario:Login,
    session:Session = Depends(get_session)
):
    usuario = session.exec(
        select(Usuario)
        .where(
            Usuario.correo == usuario.correo,
            Usuario.nombre == usuario.nombre
            )).first()

    if not usuario:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "credenciales incorrectas"
        )
    
    return usuario

@router.get("/", response_model=usuarios_paginados)
def listar_usuarios(
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1, description="numero de pagina"),
    limit: int = Query(10, ge=1, le=100, description="elementos por pagina")
):
    """
    Lista todos los usuarios registrados.
    
    - **skip**: Número de registros a omitir (para paginación)
    - **limit**: Número máximo de registros a retornar
    """
    offset = (page - 1) * limit
    statement = select(Usuario).order_by(Usuario.id).offset(offset).limit(limit)
    usuarios = session.exec(statement).all()
    response = [UsuarioRead.model_validate(item) for item in usuarios]
    # usar el metodo from query para uso de calculos automaticos     
    return usuarios_paginados.from_query(
        items=response,
        entity_class=Usuario,
        session=session,
        current_pg=page,
        limit=limit,
        )
    


@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    usuario: UsuarioCreate,
    session: Session = Depends(get_session)
):
    """
    Crea un nuevo usuario en la plataforma.
    
    - **nombre**: Nombre del usuario
    - **correo**: Correo electrónico único
    - **contraseña**: Contraseña que se usará para acceder a la aplicación
    """
    statement = select(Usuario).where(Usuario.correo == usuario.correo.lower())
    existing_user = session.exec(statement).first()
    if existing_user: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f'{usuario.correo} ya se encuentra en uso'
        )
    
    usuario_data = usuario.model_dump()
    
    db_usuario = Usuario(**usuario_data)
    session.add(db_usuario)
    session.commit()
    session.refresh(db_usuario) 
    
    return db_usuario


@router.get("/{usuario_id}", response_model=UsuarioRead)
def obtener_usuario(
    usuario_id:int,
    session:Session = Depends(get_session)
    
):
    """
    Obtiene un usuario específico por su ID.    
    - **usuario_id**: ID del usuario
    """
    statement = select(Usuario).where(Usuario.id == usuario_id)
    usuario = session.exec(statement).first()
    if not usuario:
        raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"Usuario con id {usuario_id} no enconteado"
      )
    return usuario
      
@router.put("/{usuario_id}",response_model=UsuarioRead)
def actualizar_usuario(
    usuario_id: int,
    usuario_update: UsuarioUpdate,
    session: Session = Depends(get_session),
):

    """
    Actualiza la información de un usuario existente.
    
    - **usuario_id**: ID del usuario a actualizar
    - **nombre**: Nuevo nombre (opcional)
    - **correo**: Nuevo correo (opcional)
    """
    db_usuario = session.exec(select(Usuario).where(Usuario.id == usuario_id)).first()
    if not db_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"usuario con id {usuario_id} no encontrado"
        )
        
        
    if usuario_update.correo:
        validate_email = session.exec(
            select(Usuario).
            where(
                Usuario.correo == usuario_update.correo.lower(), Usuario.id != usuario_id)
            ).first()
        if validate_email:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"{usuario_update.correo} ya está registrado, intenta con otro correo"
            )
    update_data = usuario_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(db_usuario, field, value)
    session.add(db_usuario)
    session.commit()
    session.refresh()
    return db_usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    usuario_id:int,
    session:Session = Depends(get_session),
):
    """
    Elimina un usuario de la plataforma.
    
    - **usuario_id**: ID del usuario a eliminar
    
    También se eliminarán todos los favoritos asociados al usuario.
    """
    # Buscar el usuario
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {usuario_id} no encontrado"
        )
    
    # Eliminar el usuario (los favoritos se eliminan por CASCADE)
    session.delete(usuario)
    session.commit()
    return None


@router.get("/{usuario_id}/favoritos", response_model=List[PeliculaRead])
def listar_favoritos_usuario(
    usuario_id: int,
    session: Session = Depends(get_session)
):
    """
    Lista todas las películas favoritas de un usuario.
    
    - **usuario_id**: ID del usuario
    """

    usuario = session.exec(select(Usuario).where(Usuario.id == usuario_id)).first()
    if not usuario:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"El usuario con id {usuario_id} no existe")
    

    statement = select(Pelicula).join(Favorito).where(Favorito.id_usuario == usuario_id)
    peliculas = session.exec(statement).all()


    return [PeliculaRead.from_db_model(pelicula) for pelicula in peliculas]


@router.post(
    "/{usuario_id}/favoritos/{pelicula_id}",
    status_code=status.HTTP_201_CREATED
)
def marcar_favorito(
    usuario_id: int,
    pelicula_id: int,
    session: Session = Depends(get_session)
):
    """
    Marca una película como favorita para un usuario.
    
    - **usuario_id**: ID del usuario
    - **pelicula_id**: ID de la película
    """
    # Verificar que el usuario existe
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {usuario_id} no encontrado"
        )
    
    # Verificar que la película existe
    pelicula = session.get(Pelicula, pelicula_id)
    if not pelicula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Película con id {pelicula_id} no encontrada"
        )
   
    # Verificar si ya existe el favorito
    statement = select(Favorito).where(
        Favorito.id_usuario == usuario_id,
        Favorito.id_pelicula == pelicula_id
    )
    existing_favorito = session.exec(statement).first()
    if existing_favorito:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La película ya está marcada como favorita"
        )
    
    favorito = Favorito(id_pelicula = pelicula_id, id_usuario = usuario_id)
    session.add(favorito)
    session.commit()
    return MessageResponse(message="Pelicula agregada a favoritos")


@router.delete(
    "/{usuario_id}/favoritos/{pelicula_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_favorito(
    usuario_id: int,
    pelicula_id: int,
    session: Session = Depends(get_session)
):
    """
    Elimina una película de los favoritos de un usuario.
    
    - **usuario_id**: ID del usuario
    - **pelicula_id**: ID de la película
    """
    favorito = session.exec(
        select(Favorito).where(
            Favorito.id_pelicula == pelicula_id,
            Favorito.id_usuario == usuario_id
        )
    ).first()
    
    if not favorito:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El favorito no existe"
        )
    
    session.delete(favorito)
    session.commit()    
    return None


# Endpoint para estadísticas del usuario
@router.get("/{usuario_id}/estadisticas")
def obtener_estadisticas_usuario(
    usuario_id: int,
    session: Session = Depends(get_session)
):
    """
    Obtiene estadísticas del usuario (películas favoritas, géneros preferidos, etc.)
    
    - **usuario_id**: ID del usuario
    """
    from sqlalchemy import func
    from collections import Counter
    
    # Verificar que el usuario existe
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {usuario_id} no encontrado"
        )
    
    # Calcular número total de favoritos
    total_favoritos = session.exec(
        select(func.count(Favorito.id)).where(Favorito.id_usuario == usuario_id)
    ).one()
    
    # Obtener todas las películas favoritas con sus detalles
    statement = (
        select(Pelicula)
        .join(Favorito)
        .where(Favorito.id_usuario == usuario_id)
    )
    peliculas_favoritas = session.exec(statement).all()
    
    if not peliculas_favoritas:
        return {
            "usuario_id": usuario_id,
            "nombre_usuario": usuario.nombre,
            "total_favoritos": 0,
            "duracion_total_minutos": 0,
            "duracion_total_horas": 0,
            "generos_favoritos": [],
            "directores_favoritos": [],
            "decada_favorita": None,
            "clasificacion_mas_vista": None
        }
    
    # Obtener géneros más favoritos
    generos = [p.genero for p in peliculas_favoritas]
    contador_generos = Counter(generos)
    generos_favoritos = [
        {"genero": genero, "cantidad": cantidad}
        for genero, cantidad in contador_generos.most_common(5)
    ]
    
    # Obtener directores favoritos
    directores = [p.director for p in peliculas_favoritas]
    contador_directores = Counter(directores)
    directores_favoritos = [
        {"director": director, "cantidad": cantidad}
        for director, cantidad in contador_directores.most_common(5)
    ]
    
    # Calcular tiempo total de películas favoritas
    duracion_total_minutos = sum(p.duracion for p in peliculas_favoritas)
    duracion_total_horas = round(duracion_total_minutos / 60, 2)
    
    # Calcular década favorita
    decadas = [(p.año // 10) * 10 for p in peliculas_favoritas]
    contador_decadas = Counter(decadas)
    decada_favorita = contador_decadas.most_common(1)[0] if contador_decadas else None
    
    # Clasificación más vista
    clasificaciones = [p.clasificacion for p in peliculas_favoritas]
    contador_clasificaciones = Counter(clasificaciones)
    clasificacion_mas_vista = contador_clasificaciones.most_common(1)[0] if contador_clasificaciones else None
    
    return {
        "usuario_id": usuario_id,
        "nombre_usuario": usuario.nombre,
        "total_favoritos": total_favoritos,
        "duracion_total_minutos": duracion_total_minutos,
        "duracion_total_horas": duracion_total_horas,
        "generos_favoritos": generos_favoritos,
        "directores_favoritos": directores_favoritos,
        "decada_favorita": {
            "decada": f"{decada_favorita[0]}s",
            "cantidad": decada_favorita[1]
        } if decada_favorita else None,
        "clasificacion_mas_vista": {
            "clasificacion": clasificacion_mas_vista[0],
            "cantidad": clasificacion_mas_vista[1]
        } if clasificacion_mas_vista else None,
        "promedio_duracion": round(duracion_total_minutos / total_favoritos, 2) if total_favoritos > 0 else 0
    }
