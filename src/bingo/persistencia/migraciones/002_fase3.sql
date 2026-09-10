-- Fase 3 (plantilla e impresión): añade la clave HMAC del evento (contrato de
-- la fase 3, §3.3 — firma del contenido del QR). Primera migración numerada
-- desde que 001_inicial.sql dejó de ser editable (decisión D1,
-- docs/Fase_3/Plan_Implementacion_Fase3.md §3): a partir de esta fase hay una
-- organización con evento real agendado, así que "editable hasta el primer
-- evento con datos reales" (docs/convenciones-codigo.md) ya se cumplió.
--
-- Sin líneas PRAGMA ni BEGIN/COMMIT propios (los añade
-- persistencia/migraciones/__init__.py).

ALTER TABLE evento ADD COLUMN clave_evento TEXT;
