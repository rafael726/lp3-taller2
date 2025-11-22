"""
Esquemas Pydantic para validación y serialización de datos.
Estos esquemas se usan en los endpoints de la API para:
- Validar datos de entrada (request)
- Serializar datos de salida (response)
"""

from fastapi import Depends
from sqlmodel import Session, select
from app.database import get_session
from app.models import Favorito, Pelicula, Usuario
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, TypeVar, Generic
from datetime import datetime

from utils import validar_año, validar_correo, obtener_año_actual

# Generics para paginación

T = TypeVar('T') # Generics para el esquema de 
E = TypeVar('E') # Generic para Entidad(Model)

# =============================================================================
# ESQUEMAS DE USUARIO
# =============================================================================



class Login(BaseModel):
    nombre:str
    correo:EmailStr
    pass



class UsuarioCreate(BaseModel):
    """
    Schema para crear un nuevo usuario.
    No incluye id ni fecha_registro (se generan automáticamente).
    """
    nombre: str = Field(min_length=1, max_length=100, description="Nombre del usuario")
    correo: EmailStr = Field(description="Correo electrónico único")
    
    @field_validator("correo")
    @classmethod
    def validate_email(cls, correo: EmailStr):
        if not validar_correo(correo):
            raise ValueError("El correo no es valido")
        return correo.lower()
    
    
    
    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, nombre:str):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre no puede estar vacio")
        if len(nombre) < 2 and len(nombre) <= 50:
            raise ValueError("la cantidad de caracteres del nombre de estar entre 2 y 50 caracteres")
        if not all(c.isalnum() or c.isspace() for c in nombre):
            raise ValueError("El nombre solo puede contener letras, numeros y espacios")
        return nombre
    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Juan Pérez",
                "correo": "juan.perez@email.com"
            }
        }
    )
    pass


class UsuarioUpdate(BaseModel):
    """
    Schema para actualizar un usuario existente.
    Todos los campos son opcionales.
    """
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    correo: Optional[EmailStr] = None
    
    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, nombre: Optional[str]):
        """Valida el formato del nombre si se proporciona"""
        if nombre is not None:
            nombre = nombre.strip()
            if not nombre:
                raise ValueError("El nombre no puede estar vacío")
            if not all(c.isalnum() or c.isspace() for c in nombre):
                raise ValueError("El nombre solo puede contener letras, números y espacios")
        return nombre
    
    @field_validator('correo')
    @classmethod
    def validate_email(cls, correo: Optional[EmailStr]):
        """Valida el correo si se proporciona"""
        if correo is not None:
            if not validar_correo(correo):
                raise ValueError(f'{correo} no es un correo válido')
            return correo.lower()
        return correo
    pass


class UsuarioRead(BaseModel):
    """
    Schema para retornar información de un usuario.
    Incluye todos los campos del modelo.
    """
    id: int
    nombre: str
    correo: str
    fecha_registro: datetime
    
    model_config = ConfigDict(from_attributes=True)
    pass


class UsuarioWithFavoritos(UsuarioRead):
    """
    Schema para retornar un usuario con sus películas favoritas.
    """
    favoritos: List["FavoritoRead"] = []
    pass


# =============================================================================
# ESQUEMAS DE PELÍCULA
# =============================================================================

class PeliculaCreate(BaseModel):
    """
    Schema para crear una nueva película.
    """
    titulo: str = Field(min_length=1, max_length=200, description="Título de la película")
    director: str = Field(min_length=1, max_length=150, description="Director de la película")
    genero: str = Field(min_length=1, max_length=100, description="Género de la película")
    duracion: int = Field(gt=0, le=600, description="Duración en minutos")
    año: int = Field(ge=1888, description="Año de estreno")
    clasificacion: str = Field(max_length=10, description="Clasificación por edades")
    sinopsis: Optional[str] = Field(None, max_length=1000, description="Sinopsis de la película")
    
    @field_validator('titulo')
    @classmethod
    def validate_titulo(cls, titulo: str):
        """Valida el título de la película"""
        titulo = titulo.strip()
        if not titulo:
            raise ValueError("El título no puede estar vacío")
        return titulo
    
    @field_validator('director')
    @classmethod
    def validate_director(cls, director: str):
        """Valida el nombre del director"""
        director = director.strip()
        if not director:
            raise ValueError("El director no puede estar vacío")
        if not all(c.isalnum() or c.isspace() or c in ".,'-" for c in director):
            raise ValueError("El director contiene caracteres no válidos")
        return director
    
    @field_validator('año')
    @classmethod
    def validate_año(cls, año: int):
        """Valida que el año sea válido"""
        if not validar_año(año):
            raise ValueError(f"El año debe estar entre 1900 y {obtener_año_actual()}")
        return año
    
    @field_validator('clasificacion')
    @classmethod
    def validate_clasificacion(cls, clasificacion: str):
        """Valida la clasificación de la película"""
        clasificaciones_validas = ["G", "PG", "PG-13", "R", "NC-17", "NR", "ATP", "+13", "+16", "+18"]
        if clasificacion.upper() not in clasificaciones_validas:
            raise ValueError(f"Clasificación debe ser una de: {', '.join(clasificaciones_validas)}")
        return clasificacion.upper()
    
    @field_validator('duracion')
    @classmethod
    def validate_duracion(cls, duracion: int):
        """Valida la duración de la película"""
        if duracion < 1:
            raise ValueError("La duración debe ser mayor a 0 minutos")
        if duracion > 600:  # 10 horas máximo
            raise ValueError("La duración no puede ser mayor a 600 minutos (10 horas)")
        return duracion
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "titulo": "Inception",
                "director": "Christopher Nolan",
                "genero": "Ciencia Ficción, Acción",
                "duracion": 148,
                "año": 2010,
                "clasificacion": "PG-13",
                "sinopsis": "Un ladrón que roba secretos mediante tecnología de sueños..."
            }
        }
    )
    pass

class PeliculaUpdate(BaseModel):
    """
    Schema para actualizar una película existente.
    Todos los campos son opcionales.
    """
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    director: Optional[str] = Field(None, min_length=1, max_length=150)
    genero: Optional[str] = Field(None, max_length=100)
    duracion: Optional[int] = Field(None, gt=0, le=600)
    año: Optional[int] = Field(None, ge=1888)
    clasificacion: Optional[str] = Field(None, max_length=10)
    sinopsis: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('titulo')
    @classmethod
    def validate_titulo(cls, titulo: Optional[str]):
        if titulo is not None:
            titulo = titulo.strip()
            if not titulo:
                raise ValueError("El título no puede estar vacío")
        return titulo
    
    @field_validator('director')
    @classmethod
    def validate_director(cls, director: Optional[str]):
        if director is not None:
            director = director.strip()
            if not director:
                raise ValueError("El director no puede estar vacío")
            if not all(c.isalnum() or c.isspace() or c in ".,'-" for c in director):
                raise ValueError("El director contiene caracteres no válidos")
        return director
    
    @field_validator('año')
    @classmethod
    def validate_año(cls, año: Optional[int]):
        if año is not None and not validar_año(año):
            raise ValueError(f"El año debe estar entre 1900 y {obtener_año_actual()}")
        return año
    
    @field_validator('clasificacion')
    @classmethod
    def validate_clasificacion(cls, clasificacion: Optional[str]):
        if clasificacion is not None:
            clasificaciones_validas = ["G", "PG", "PG-13", "R", "NC-17", "NR", "ATP", "+13", "+16", "+18"]
            if clasificacion.upper() not in clasificaciones_validas:
                raise ValueError(f"Clasificación debe ser una de: {', '.join(clasificaciones_validas)}")
            return clasificacion.upper()
        return clasificacion
    
    @field_validator('duracion')
    @classmethod
    def validate_duracion(cls, duracion: Optional[int]):
        if duracion is not None:
            if duracion < 1:
                raise ValueError("La duración debe ser mayor a 0 minutos")
            if duracion > 600:
                raise ValueError("La duración no puede ser mayor a 600 minutos (10 horas)")
        return duracion



class PeliculaRead(BaseModel):
    """
    Schema para retornar información de una película.
    """
    id: int
    titulo: str
    director: str
    genero: str
    duracion: int
    año: int
    clasificacion: str
    sinopsis: Optional[str]
    fecha_creacion: datetime
    image_url: Optional[str] = None
    
    @classmethod
    def from_db_model(cls, pelicula: "Pelicula", base_url: str = ""):
        """
        Crea una instancia desde el modelo de base de datos, generando la URL de imagen automáticamente.
        """
        image_url = None
        if pelicula.image_file:
            image_url = f"{base_url}/api/peliculas/imagen/{pelicula.id}"
        
        return cls(
            id=pelicula.id,
            titulo=pelicula.titulo,
            director=pelicula.director,
            genero=pelicula.genero,
            duracion=pelicula.duracion,
            año=pelicula.año,
            clasificacion=pelicula.clasificacion,
            sinopsis=pelicula.sinopsis,
            fecha_creacion=pelicula.fecha_creacion,
            image_url=image_url,
        )
    
    model_config = ConfigDict(from_attributes=True)
    pass


class ImagenUploadResp(BaseModel):
    """
    Schema para respuesta al subir imagen de película.
    """
    message: str
    image_url: str
    pelicula_id: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Imagen cargada",
                "image_url": "/api/peliculas/imagen/1",
                "pelicula_id": 1
            }
        }
    )

# =============================================================================
# ESQUEMAS DE FAVORITO
# =============================================================================


class FavoritoCreate(BaseModel):
    """
    Schema para marcar una película como favorita.
    """
    id_usuario: int = Field(gt=0, description="ID del usuario")
    id_pelicula: int = Field(gt=0, description="ID de la película")
    
    @field_validator('id_usuario', 'id_pelicula')
    @classmethod
    def validate_positive_ids(cls, value: int):
        """Valida que los IDs sean positivos"""
        if value <= 0:
            raise ValueError("Los IDs deben ser números positivos")
        return value


class FavoritoRead(BaseModel):
    """
    Schema para retornar información de un favorito.
    """
    id: int
    id_usuario: int
    id_pelicula: int
    fecha_marcado: datetime
    
    model_config = ConfigDict(from_attributes=True)
    pass


class FavoritoWithDetails(FavoritoRead):
    """
    Schema para retornar un favorito con información del usuario y película.
    """
    usuario: UsuarioRead
    pelicula: PeliculaRead
    pass


# =============================================================================
# ESQUEMAS DE RESPUESTA GENÉRICOS
# =============================================================================



class MessageResponse(BaseModel):
    """
    Schema genérico para respuestas con mensajes.
    """
    message: str
    detail: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example":{
                "message":"Operación completada",
                "detail":"Recurso creado exitosamente"
                }
        }
    )


class PaginatedResponse(BaseModel, Generic[T, E]):
    """
    Schema genérico para respuestas paginadas con tipos específicos y cálculos automáticos.
    
    Uso:
        # Para usuarios
        PaginatedResponse[UsuarioRead, Usuario]
        
        # Para películas
        PaginatedResponse[PeliculaRead, Pelicula]
        
        # Para favoritos
        PaginatedResponse[FavoritoRead, Favorito]
    """
    items: List[T] = Field(description="Lista de elementos de la página actual")
    total_records: int = Field(ge=0, description="Total de elementos en toda la colección")
    current_pg: int = Field(ge=1, description="Número de página actual")
    limit: int = Field(ge=1, le=100, description="Cantidad de elementos por página")
    pages: int = Field(ge=1, description="Total de páginas disponibles")
    has_next: Optional[bool] = Field(description="Indica si hay una página siguiente")
    has_prev: Optional[bool] = Field(description="Indica si hay una página anterior")
    next_page: Optional[int] = Field(None, description="Número de la página siguiente (si existe)")
    prev_page: Optional[int] = Field(None, description="Número de la página anterior (si existe)")

    
    @field_validator('current_pg')
    @classmethod
    def validate_current_pg(cls, current_pg: int):
        """Valida que la página sea un número positivo"""
        if current_pg < 1:
            raise ValueError("La página debe ser mayor a 0")
        return current_pg
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, limit: int):
        """Valida que el tamaño esté dentro de los límites permitidos"""
        if limit < 1:
            raise ValueError("El tamaño debe ser mayor a 0")
        if limit > 100:
            raise ValueError("El tamaño no puede ser mayor a 100")
        return limit
    
    @model_validator(mode='after')
    def calculate_pagination_info(self):
        """Calcula automáticamente la información de paginación"""
        # Calcular total de páginas
        if self.total_records == 0:
            self.pages = 1
        else:
            self.pages = (self.total_records + self.limit - 1) // self.limit
        
        # Validar que la página solicitada existe
        if self.current_pg > self.pages:
            raise ValueError(f"La página {self.current_pg} no existe. Máximo: {self.pages}")
        
        # Calcular información de navegación
        self.has_prev = self.current_pg > 1
        self.has_next = self.current_pg < self.pages
        
        # Calcular números de página anterior y siguiente
        self.prev_page = self.current_pg - 1 if self.has_prev else None
        self.next_page = self.current_pg + 1 if self.has_next else None
        
        return self
    
    @classmethod
    def from_query(
        cls,
        items:List[T],
        entity_class: type[E],
        current_pg: int,
        limit: int,
        session: Session = Depends(get_session),
    ) -> "PaginatedResponse[T, E]":
        """
        Crea una respuesta paginada calculando automáticamente desde la base de datos.
        
        Args:
            items: Lista de items que se retornan
            entity_class: Clase de la entidad de base de datos (Usuario, Pelicula, etc.)
            session: Sesión de SQLModel para consultas
            current_pg: Número de página actual
            limit: Elementos por página
            
        Returns:
            PaginatedResponse[T, E]: Instancia configurada con datos de la BD
        """
        # Contar total de registros
        total_records = len(session.exec(select(entity_class)).all())

        # Crear la instancia con cálculos automáticos
        return cls(
            items=items,
            total_records=total_records,
            current_pg=current_pg,
            limit=limit,
            pages=1, 
            has_next=None,
            has_prev=None,
        )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total_records": 150,
                "current_pg": 2,
                "limit": 10,
                "pages": 15,
                "has_next": True,
                "has_prev": True,
                "next_page": 3,
                "prev_page": 1
            }
        }
    )


peliculas_paginadas = PaginatedResponse[PeliculaRead, Pelicula]
usuarios_paginados = PaginatedResponse[UsuarioRead, Usuario]
favoritos_paginados = PaginatedResponse[FavoritoRead, Favorito]


class PeliculaSearchParams(BaseModel):
    """
    Parámetros de búsqueda para películas.
    """
    titulo: Optional[str] = Field(None, max_length=200, description="Buscar por título")
    director: Optional[str] = Field(None, max_length=150, description="Buscar por director")
    genero: Optional[str] = Field(None, max_length=100, description="Buscar por género")
    año: Optional[int] = Field(None, ge=1888, description="Buscar por año específico")
    año_min: Optional[int] = Field(None, ge=1888, description="Año mínimo")
    año_max: Optional[int] = Field(None, ge=1888, description="Año máximo")
    clasificacion: Optional[str] = Field(None, max_length=10, description="Buscar por clasificación")
    duracion_min: Optional[int] = Field(None, gt=0, description="Duración mínima en minutos")
    duracion_max: Optional[int] = Field(None, gt=0, le=600, description="Duración máxima en minutos")
    
    @model_validator(mode='after')
    def validate_year_range(self):
        """Valida que el rango de años sea válido"""
        if self.año_min is not None and self.año_max is not None:
            if self.año_min > self.año_max:
                raise ValueError("El año mínimo no puede ser mayor al año máximo")
        
        if self.año is not None and (self.año_min is not None or self.año_max is not None):
            raise ValueError("No se puede especificar un año específico junto con un rango de años")
        
        return self
    
    @model_validator(mode='after')
    def validate_duration_range(self):
        """Valida que el rango de duración sea válido"""
        if self.duracion_min is not None and self.duracion_max is not None:
            if self.duracion_min > self.duracion_max:
                raise ValueError("La duración mínima no puede ser mayor a la duración máxima")
        
        return self
    pass

