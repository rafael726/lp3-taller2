from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import create_db_and_tables
from app.routers import usuarios, peliculas, favoritos
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor de ciclo de vida de la aplicación.
    Se ejecuta al iniciar y al cerrar la aplicación.
    """
    #Crear tablas en la base de datos
    create_db_and_tables()
    yield
    
    #Limpiar recursos si es necesario
    print("cerrando aplicación...")


# Crear la instancia de FastAPI con metadatos apropiados
app = FastAPI(
    title=settings.app_name,
    description="API RESTful para gestionar usuarios, películas y favoritos",
    version=settings.app_version,
    lifespan=lifespan,
    contact={
        "name": "Equipo de Desarrollo",
        "email": "contacto@pelimaniaticos.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)


# Configurar CORS para permitir solicitudes desde diferentes orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Incluir los routers de usuarios, peliculas y favoritos
app.include_router(usuarios.router)
app.include_router(peliculas.router)
app.include_router(favoritos.router)



@app.middleware("http")
async def log_requests(request, call_next):
    """
    Middleware para registrar información de las solicitudes HTTP.
    """
    import time
    import logging
    
    logger = logging.getLogger("uvicorn")
    start_time = time.time()
    
    # Procesar la solicitud
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Registrar información
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    # Agregar header con tiempo de procesamiento
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Manejadores de errores personalizados
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Manejador personalizado para errores de validación.
    """
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación",
            "errors": exc.errors(),
            "body": exc.body
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Manejador general para excepciones no capturadas.
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "message": str(exc) if settings.debug else "Ha ocurrido un error inesperado"
        }
    )


# Crear un endpoint raíz que retorne información básica de la API
@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz de la API.
    Retorna información básica y enlaces a la documentación.
    """
    return {
        "nombre": settings.app_name,
        "version": settings.app_version,
        "descripcion": "API RESTful para gestionar usuarios, películas y favoritos",
        "documentacion": "/docs",
        "documentacion_alternativa": "/redoc",
        "endpoints": {
            "usuarios": "/api/usuarios",
            "peliculas": "/api/peliculas",
            "favoritos": "/api/favoritos"
        }
    }


# Crear un endpoint de health check para monitoreo
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint para verificar el estado de la API.
    Útil para sistemas de monitoreo y orquestación.
    """
    from app.database import engine
    import time
    
    # Verificar conexión a base de datos
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": db_status,
        "environment": settings.environment,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.LOG_LEVEL.lower()
    )

