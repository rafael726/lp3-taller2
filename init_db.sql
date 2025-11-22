-- ============================================
-- Base de datos: SQLite (peliculas.db)
-- ============================================

-- Tabla Usuario
CREATE TABLE usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para Usuario
CREATE INDEX ix_usuario_nombre ON usuario (nombre);
CREATE INDEX ix_usuario_correo ON usuario (correo);

-- Tabla Pelicula
CREATE TABLE pelicula (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo VARCHAR(200) NOT NULL,
    director VARCHAR(150) NOT NULL,
    genero VARCHAR(100) NOT NULL,
    duracion INTEGER NOT NULL,
    año INTEGER NOT NULL CHECK (año >= 1888 AND año <= 2100),
    clasificacion VARCHAR(10) NOT NULL,
    sinopsis VARCHAR(1000),
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índice para Pelicula
CREATE INDEX ix_pelicula_titulo ON pelicula (titulo);

-- Tabla Favorito (Tabla de unión)
CREATE TABLE favorito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_pelicula INTEGER NOT NULL,
    fecha_marcado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Claves Foráneas
    FOREIGN KEY (id_usuario) REFERENCES usuario (id),
    FOREIGN KEY (id_pelicula) REFERENCES pelicula (id),
    
    -- Restricción única para evitar duplicados
    CONSTRAINT unique_user_movie UNIQUE (id_usuario, id_pelicula)
);

-- Insertar Usuarios
INSERT INTO usuario (nombre, correo, fecha_registro) VALUES
('María García', 'maria.garcia@email.com', datetime('now')),
('Juan Pérez', 'juan.perez@email.com', datetime('now')),
('Ana Martínez', 'ana.martinez@email.com', datetime('now')),
('Carlos Rodríguez', 'carlos.rodriguez@email.com', datetime('now')),
('Laura Fernández', 'laura.fernandez@email.com', datetime('now'));

-- Insertar Películas
INSERT INTO pelicula (titulo, director, genero, duracion, año, clasificacion, sinopsis, fecha_creacion) VALUES
('El Padrino', 'Francis Ford Coppola', 'Drama, Crimen', 175, 1972, 'R', 'La historia de una familia mafiosa italiana y su lucha por mantener el poder en el mundo del crimen organizado.', datetime('now')),
('Inception', 'Christopher Nolan', 'Ciencia Ficción, Acción', 148, 2010, 'PG-13', 'Un ladrón que roba secretos corporativos mediante el uso de tecnología de sueños compartidos recibe la tarea inversa de plantar una idea.', datetime('now')),
('Pulp Fiction', 'Quentin Tarantino', 'Crimen, Drama', 154, 1994, 'R', 'Las vidas de dos sicarios, un boxeador, la esposa de un gánster y dos bandidos se entrelazan en cuatro historias de violencia y redención.', datetime('now')),
('Forrest Gump', 'Robert Zemeckis', 'Drama, Romance', 142, 1994, 'PG-13', 'Las décadas de vida de Forrest Gump, un hombre con buen corazón pero limitaciones intelectuales, que presencia eventos históricos importantes.', datetime('now')),
('Matrix', 'Lana Wachowski, Lilly Wachowski', 'Ciencia Ficción, Acción', 136, 1999, 'R', 'Un hacker descubre que la realidad tal como la conocemos es una simulación creada por máquinas inteligentes.', datetime('now')),
('El Señor de los Anillos: El Retorno del Rey', 'Peter Jackson', 'Fantasía, Aventura', 201, 2003, 'PG-13', 'Gandalf y Aragorn lideran el mundo de los hombres contra el ejército de Sauron para distraer su atención de Frodo y Sam.', datetime('now')),
('Interestelar', 'Christopher Nolan', 'Ciencia Ficción, Drama', 169, 2014, 'PG-13', 'Un equipo de exploradores viaja a través de un agujero de gusano en el espacio para asegurar la supervivencia de la humanidad.', datetime('now')),
('Parásitos', 'Bong Joon-ho', 'Drama, Thriller', 132, 2019, 'R', 'La codicia y la discriminación de clases amenazan la relación simbiótica recién formada entre la rica familia Park y el clan Kim.', datetime('now')),
('El Caballero de la Noche', 'Christopher Nolan', 'Acción, Drama', 152, 2008, 'PG-13', 'Cuando el Joker emerge para sembrar el caos en Gotham City, Batman debe aceptar una de las pruebas psicológicas y físicas más grandes.', datetime('now')),
('La La Land', 'Damien Chazelle', 'Romance, Musical', 128, 2016, 'PG-13', 'Mientras se esfuerzan por triunfar en sus carreras artísticas, un pianista de jazz y una aspirante a actriz se enamoran.', datetime('now'));

-- Insertar favoritos de ejemplo
INSERT INTO favorito (id_usuario, id_pelicula, fecha_marcado) VALUES
(1, 1, datetime('now')),
(1, 5, datetime('now')),
(2, 2, datetime('now')),
(2, 9, datetime('now')),
(3, 10, datetime('now')),
(4, 3, datetime('now')),
(4, 8, datetime('now')),
(5, 6, datetime('now')),
(5, 7, datetime('now'));

-- Verificar los datos insertados
SELECT * FROM usuario;
SELECT id, titulo, director, año, genero FROM pelicula;
SELECT f.id, u.nombre AS usuario, p.titulo AS pelicula, f.fecha_marcado
  FROM favorito f
  JOIN usuario u ON f.id_usuario = u.id
  JOIN pelicula p ON f.id_pelicula = p.id;

