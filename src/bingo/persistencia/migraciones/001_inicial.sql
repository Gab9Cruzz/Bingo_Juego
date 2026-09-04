-- Esquema inicial completo (documento técnico §3.1), con las enmiendas de la
-- fase 1: E4a (sin UNIQUE de nombre en evento), E4b (dinero en centavos),
-- E4c (textos legales de organización), E4d (fecha y hora separadas),
-- CHECK en columnas de estado con conjunto de valores cerrado.
--
-- Política de edición: esta migración es editable hasta el primer evento con
-- datos reales (ver docs/convenciones-codigo.md). A partir de ahí, nunca se
-- edita una migración publicada: todo cambio va en 002_*.sql.
--
-- Sin líneas PRAGMA: los PRAGMA de conexión viven en persistencia/conexion.py.
-- Sin BEGIN/COMMIT propios: los añade persistencia/migraciones.py.

CREATE TABLE organizacion (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL,
    logo_path         TEXT,
    logo_secundario   TEXT,
    color_primario    TEXT NOT NULL DEFAULT '#1a1a2e',
    color_secundario  TEXT NOT NULL DEFAULT '#e94560',
    color_texto       TEXT NOT NULL DEFAULT '#ffffff',
    tipografia        TEXT,
    contacto          TEXT,
    eslogan           TEXT,
    pie_pagina        TEXT,
    condiciones       TEXT,
    aviso_legal       TEXT,
    creada_en         TEXT NOT NULL
);

CREATE TABLE evento (
    id                     INTEGER PRIMARY KEY,
    organizacion_id        INTEGER NOT NULL REFERENCES organizacion(id),
    nombre                 TEXT NOT NULL,
    fecha                  TEXT,               -- YYYY-MM-DD, fecha de calendario, sin zona
    hora                   TEXT,               -- HH:MM, hora local del lugar, opcional
    lugar                  TEXT,
    precio_tabla_centavos  INTEGER NOT NULL DEFAULT 0,
    estado                 TEXT NOT NULL DEFAULT 'borrador'
                           CHECK (estado IN ('borrador', 'preparado', 'en_curso', 'finalizado')),
    plantilla_json         TEXT,               -- configuración visual del cartón
    tema_json              TEXT,               -- configuración visual del dashboard
    creado_en              TEXT NOT NULL
);

CREATE INDEX idx_evento_organizacion ON evento(organizacion_id);

CREATE TABLE lote (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    cantidad          INTEGER NOT NULL,
    semilla           TEXT NOT NULL,
    generado_en       TEXT NOT NULL
);

CREATE TABLE carton (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    lote_id           INTEGER NOT NULL REFERENCES lote(id),
    codigo            TEXT NOT NULL,
    numeros           TEXT NOT NULL,
    firma             TEXT NOT NULL,
    estado            TEXT NOT NULL DEFAULT 'generado'
                     CHECK (estado IN ('generado', 'impreso', 'entregado', 'vendido', 'anulado')),
    UNIQUE (evento_id, codigo),
    UNIQUE (evento_id, firma)
);

CREATE INDEX idx_carton_evento_estado ON carton(evento_id, estado);
CREATE INDEX idx_carton_codigo        ON carton(codigo);

CREATE TABLE comprador (
    id                INTEGER PRIMARY KEY,
    carton_id         INTEGER NOT NULL UNIQUE REFERENCES carton(id),
    nombre            TEXT NOT NULL,
    telefono          TEXT,
    cedula            TEXT,
    correo            TEXT,
    registrado_en     TEXT NOT NULL
);

CREATE TABLE patron (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL,
    mascara           INTEGER NOT NULL,
    usa_libre         INTEGER NOT NULL DEFAULT 1,
    es_sistema        INTEGER NOT NULL DEFAULT 0,
    organizacion_id   INTEGER REFERENCES organizacion(id)
);

CREATE TABLE ronda (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    orden             INTEGER NOT NULL,
    nombre            TEXT NOT NULL,
    patron_id         INTEGER NOT NULL REFERENCES patron(id),
    premio_nombre     TEXT,
    premio_tipo       TEXT CHECK (premio_tipo IS NULL OR premio_tipo IN ('efectivo', 'bien')),
    premio_valor      REAL,
    premio_imagen     TEXT,
    -- estado: sin CHECK a propósito. Su máquina de estados sigue abierta
    -- (documento técnico §16); un CHECK no se puede quitar en SQLite sin
    -- reconstruir la tabla. La valida el dominio, como las demás transiciones.
    estado            TEXT NOT NULL DEFAULT 'pendiente',
    UNIQUE (evento_id, orden)
);

CREATE TABLE extraccion (
    id                INTEGER PRIMARY KEY,
    ronda_id          INTEGER NOT NULL REFERENCES ronda(id),
    orden             INTEGER NOT NULL,
    numero            INTEGER NOT NULL,
    extraida_en       TEXT NOT NULL,
    UNIQUE (ronda_id, orden),
    UNIQUE (ronda_id, numero)
);

CREATE TABLE ganador (
    id                INTEGER PRIMARY KEY,
    ronda_id          INTEGER NOT NULL REFERENCES ronda(id),
    carton_id         INTEGER NOT NULL REFERENCES carton(id),
    bola_numero       INTEGER NOT NULL,
    confirmado        INTEGER NOT NULL DEFAULT 0,
    reparte_premio    INTEGER NOT NULL DEFAULT 0,
    registrado_en     TEXT NOT NULL
);

CREATE TABLE auditoria (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER REFERENCES evento(id),
    momento           TEXT NOT NULL,
    accion            TEXT NOT NULL,
    detalle           TEXT
);

CREATE INDEX idx_auditoria_evento ON auditoria(evento_id, momento);
