-- Fase 4 (compradores, rondas y premios). Migración consolidada — la única
-- fuente de verdad de lo que la fase 4 necesita en el esquema. El plan de la
-- fase (docs/Fase_4/Plan_Implementacion_Fase4.md, ANEXO E-M9) llegó a tener
-- cuatro dueños distintos para esta migración; queda unificada aquí antes de
-- escribir ningún repositorio.
--
-- Reconstruye `patron` y `comprador` completas porque SQLite no permite
-- quitar un NOT NULL ni añadir un UNIQUE con ALTER TABLE (hallazgos C3 y
-- E-C3 de la revisión de ingeniería). Es el único momento en que vale la
-- pena reconstruir: ninguna fase anterior escribe en estas dos tablas, así
-- que no hay ninguna fila real que se pueda perder en ninguna base.
--
-- Sin líneas PRAGMA ni BEGIN/COMMIT propios (los añade
-- persistencia/migraciones/__init__.py, ver docs/convenciones-codigo.md).

-- ── patron ──────────────────────────────────────────────────────────────
-- `mascara` (INTEGER NOT NULL, 001) se sustituye por `mascaras` (TEXT, lista
-- JSON de enteros): un patrón gana con cualquiera de sus máscaras (decisión
-- D1, doc técnico §16.1). A diferencia de `ronda.premio_valor` más abajo
-- (que se deja muerta porque solo admite ALTER TABLE ADD COLUMN), aquí ya
-- hace falta reconstruir la tabla entera por el NOT NULL — no hay razón
-- para arrastrar además la columna vieja como cadáver: se reemplaza limpio.
-- `clave_i18n` + `version_semilla` (por fila, no marca global — decisión
-- M10) permiten que `asegurar_patrones_sistema` sea idempotente y sepa qué
-- patrones del sistema puede actualizar cuando cambian sus máscaras.
-- `nombre` se conserva como respaldo en español si `clave_i18n` no resuelve
-- (decisión M9): la vista prioriza siempre `t(clave_i18n)`.
CREATE TABLE patron_nuevo (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL,
    clave_i18n        TEXT,
    mascaras          TEXT NOT NULL,
    descripcion       TEXT,
    usa_libre         INTEGER NOT NULL DEFAULT 1,
    es_sistema        INTEGER NOT NULL DEFAULT 0,
    version_semilla   INTEGER NOT NULL DEFAULT 0,
    organizacion_id   INTEGER REFERENCES organizacion(id)
);

INSERT INTO patron_nuevo (id, nombre, mascaras, usa_libre, es_sistema, organizacion_id)
    SELECT id, nombre, '[' || mascara || ']', usa_libre, es_sistema, organizacion_id
    FROM patron;

DROP TABLE patron;
ALTER TABLE patron_nuevo RENAME TO patron;

CREATE INDEX idx_patron_organizacion ON patron(organizacion_id);
-- Índice único parcial (decisión C4): dos patrones del sistema no pueden
-- compartir clave_i18n, pero los patrones propios de una organización
-- (clave_i18n NULL) no participan de esa unicidad.
CREATE UNIQUE INDEX idx_patron_clave_sistema ON patron(clave_i18n) WHERE clave_i18n IS NOT NULL;

-- ── comprador ───────────────────────────────────────────────────────────
-- `carton_id UNIQUE` (001, a nivel de columna) se sustituye por un índice
-- único parcial: un comprador anulado (`anulado_en` no nulo, borrado lógico
-- — decisión A3) no debe seguir bloqueando el cartón para una reventa
-- (hallazgo E-C3; con el UNIQUE de columna, anular una venta habría dejado
-- el cartón inutilizable para siempre).
-- `provisional` marca las filas que crea `marcar_vendidos_por_rango` sin
-- datos de contacto, para que un cartón vendido en puerta pueda participar
-- bajo la regla de elegibilidad estricta (decisión UC-1 + D4, ANEXO D.1).
-- `estado_carton_previo` es lo que permite devolver el cartón a su estado
-- real al anular la venta (hallazgo C2: no siempre era "entregado").
CREATE TABLE comprador_nuevo (
    id                    INTEGER PRIMARY KEY,
    carton_id             INTEGER NOT NULL REFERENCES carton(id),
    nombre                TEXT NOT NULL,
    telefono              TEXT,
    cedula                TEXT,
    correo                TEXT,
    provisional           INTEGER NOT NULL DEFAULT 0 CHECK (provisional IN (0, 1)),
    estado_carton_previo  TEXT,
    anulado_en            TEXT,
    registrado_en         TEXT NOT NULL
);

INSERT INTO comprador_nuevo
        (id, carton_id, nombre, telefono, cedula, correo, registrado_en)
    SELECT id, carton_id, nombre, telefono, cedula, correo, registrado_en
    FROM comprador;

DROP TABLE comprador;
ALTER TABLE comprador_nuevo RENAME TO comprador;

CREATE UNIQUE INDEX idx_comprador_carton_vivo ON comprador(carton_id) WHERE anulado_en IS NULL;

-- ── ronda ───────────────────────────────────────────────────────────────
-- `premio_valor` (REAL, 001) contradecía la enmienda E4b (dinero en
-- centavos) y docs/convenciones-codigo.md desde que se escribió: la fase 4
-- es su primer consumidor real (decisión D3). Se corrige con una columna
-- nueva; la vieja queda muerta a propósito: `ALTER TABLE` no permite
-- `DROP COLUMN` sin reconstruir la tabla, y a diferencia de `patron` y
-- `comprador` (que SÍ hacía falta reconstruir por el NOT NULL/UNIQUE), aquí
-- nada más obliga a tocar la tabla — no vale reconstruirla solo por esto.
ALTER TABLE ronda ADD COLUMN premio_valor_centavos INTEGER;
ALTER TABLE ronda ADD COLUMN premio_descripcion TEXT;

-- ── evento ──────────────────────────────────────────────────────────────
-- Recaudación real declarada por el operador (ANEXO A, hallazgo R8): sin
-- esto, "el reporte de conciliación cuadra con la base" comparaba el número
-- teórico contra sí mismo. NULL = todavía no declarada.
ALTER TABLE evento ADD COLUMN recaudado_real_centavos INTEGER;
