-- Fase 5 (sorteo en vivo y cierre). Decisión D3
-- (docs/Fase_5/Plan_Implementacion_Fase5.md): solo `ADD COLUMN` e índices,
-- ninguna tabla se reconstruye.
--
-- `ronda.premio_valor` (REAL, 001) queda muerta a propósito: E4b ya se
-- cumple desde la 003 (`premio_valor_centavos`), y reconstruir `ronda` sobre
-- una tabla que ya puede tener filas reales solo para borrar una columna
-- que nadie lee es riesgo puro a cambio de estética (decisión D3, corrección
-- del hallazgo M3). Queda escrito en docs/decisiones.md como estado
-- permanente aceptado.
--
-- Sin líneas PRAGMA ni BEGIN/COMMIT propios (los añade
-- persistencia/migraciones/__init__.py, ver docs/convenciones-codigo.md).

-- ── ronda ────────────────────────────────────────────────────────────────
-- `estado` sigue SIN CHECK a propósito (decisión de la fase 1, todavía
-- vigente: el conjunto puede crecer — ver hallazgo V5 — y un CHECK no se
-- quita en SQLite sin reconstruir la tabla). La valida
-- `dominio/estados.py::TRANSICIONES_RONDA`.
ALTER TABLE ronda ADD COLUMN iniciada_en      TEXT;
ALTER TABLE ronda ADD COLUMN cerrada_en       TEXT;
ALTER TABLE ronda ADD COLUMN acta_hash        TEXT;
ALTER TABLE ronda ADD COLUMN acta_generada_en TEXT;

-- ── ganador ──────────────────────────────────────────────────────────────
-- `decision`: unico | reparto | desempate_externo | no_reclamado | rechazado
-- (dominio/estados.py no la valida como máquina de estados; la fija
-- servicio_ganadores.confirmar, contrato §5.6).
ALTER TABLE ganador ADD COLUMN confirmado_en TEXT;
ALTER TABLE ganador ADD COLUMN decision      TEXT;
ALTER TABLE ganador ADD COLUMN anulado_en    TEXT;
ALTER TABLE ganador ADD COLUMN nota          TEXT;

-- Índice único TOTAL, no parcial (corrección del hallazgo V1, crítico): un
-- cartón solo puede ganar una ronda una vez, anulado o no. La versión con
-- `WHERE anulado_en IS NULL` dejaba un ganador anulado fuera del índice, y
-- la reanudación lo podía reinsertar vivo.
CREATE UNIQUE INDEX idx_ganador_ronda_carton ON ganador(ronda_id, carton_id);
CREATE INDEX idx_ganador_ronda ON ganador(ronda_id);
CREATE INDEX idx_extraccion_ronda ON extraccion(ronda_id, orden);
