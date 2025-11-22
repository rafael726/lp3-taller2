"""
Configuración de la base de datos y gestión de sesiones.
Utiliza SQLModel para ORM y gestión de conexiones.
"""

from pydoc import text
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Muestra las consultas SQL en consola si debug=True
    connect_args={"check_same_thread": False}  # Necesario para SQLite
)


def create_db_and_tables():
    """
    Crea todas las tablas en la base de datos.
    Se llama al iniciar la aplicación.
    """
    from app.models import Usuario, Pelicula, Favorito
    
    SQLModel.metadata.create_all(engine)
    print("Tablas de la base de datos creadas correctamente")


def drop_db_and_tables():
    """
    Elimina todas las tablas de la base de datos.
    Usar con precaución - elimina todos los datos.
    """
    SQLModel.metadata.drop_all(engine)
    print("Tablas de la base de datos eliminadas")


# Obtener una sesión de base de datos
def get_session() -> Generator[Session, None, None]:
    """
    Generador de sesiones de base de datos.
    Se usa como dependencia en los endpoints de FastAPI.
    
    Uso en endpoints:
        @app.get("/items")
        def read_items(session: Session = Depends(get_session)):
            items = session.exec(select(Item)).all()
            return items
    """
    with Session(engine) as session:
        yield session



def check_database_connection() -> bool:
    """
    Verifica que la conexión a la base de datos funcione correctamente.
    Retorna True si la conexión es exitosa, False en caso contrario.
    """
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")
        return False


class DatabaseSession:
    """
    Context manager para manejar sesiones de base de datos.
    Útil para operaciones fuera de endpoints FastAPI.
    
    Uso:
        with DatabaseSession() as session:
            user = session.get(Usuario, user_id)
    """
    def __init__(self, auto_commit:bool = True):
        self.auto_commit = auto_commit
        self.session = None
        pass
    
    def __enter__(self) -> Session:
        self.session = Session(engine)
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.session.rollback()
                print("Rollback debido a exepción", exc_type.__name__)
            elif self.auto_commit:
                self.session.commit()
                print("Commit automático realizado")
        except Exception as exc:
            self.session.rollback()
            print(f"Error al realziar commit, se inicia rollback", exc)


