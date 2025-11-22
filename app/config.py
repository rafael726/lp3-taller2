"""
Configuración de la aplicación.
Maneja diferentes entornos: desarrollo, pruebas y producción.
"""

import json
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Literal, Optional


class Settings(BaseSettings):
    """
    Configuración de la aplicación usando Pydantic Settings.
    Lee las variables de entorno desde el archivo .env
    """
    
    #  Configuración básica de la aplicación
    
    app_name: str = "pelimaniaticos"
    app_version: str = "1.0.1"
    
    # : Configuración del entorno
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="entorno de ejecucion"
    )
    
    
    
    database_url: str = Field(
        default="sqlite:///./peliculas.db",
        description="URL de conexion a la base de datos"
    )
   
    
    # : Configuración del servidor
    host: str = Field(default="localhost", description="host del servidor")
    port: int = Field(default=8000, ge=1, le=65535, description="puerto del servidor")
    debug: bool = Field(default=True, description="modo debug") 
    
    #: Configuración de CORS
    cors_origins: list[str] = Field(
        default=["*"],
        description="origenes permitidos para CORS"
    )
    
    
    # : Configuración de logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="nivel de logging"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="archivo de log (opcional)"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_nested_delimiter": "__"
    }
    

        
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """valida url de la base de datos que no este vacio"""
        if not v or not v.strip():
            raise ValueError("DATABASE_URL no debe estar vacio")
        return v.strip()
    
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls,v):
        """convertir string JSON a lista si es necesario"""
        if isinstance(v, str):
            try:
                #si viene como strign json desde env
                return json.loads(v)
            except json.JSONDecodeError:
                #viene como strign simple para crear lista
                return [v.strip()]
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Normaliza nivel de logging"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL debe ser uno de: {', '.join(valid_levels)}")
        return v_upper
        
    

settings = Settings()


class DevelopmentSettings(Settings):
    """Configuración para el entorno de desarrollo."""
    debug: bool = True
    LOG_LEVEL: str = "DEBUG"
    cors_origins: list[str] = ['*']
    log_file: Optional[str] = None



def get_settings() -> Settings:
    """
    Retorna la configuración apropiada según el entorno.
    """
    settings = Settings()
    env = settings.environment.lower() # Cuando se requiera otros entornos se usará la variable para validar
    # por ahoro retorna entorno de development
    
    return DevelopmentSettings()




