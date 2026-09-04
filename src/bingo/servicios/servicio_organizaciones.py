"""Casos de uso de `organizacion`.

Es el único punto de la fase 1 donde el sistema de archivos y la base de datos
tienen que quedar consistentes entre sí (enmienda G8). El `id` de la
organización no existe hasta después del `INSERT`, así que el orden real,
todo dentro de la misma transacción, es:

```
BEGIN IMMEDIATE
  ├─ validar
  ├─ normalizar la imagen a un temporal (fuera de medios/)
  ├─ INSERT organizacion            ──▶ id = lastrowid
  ├─ copiar el temporal a medios/<id>/logo_principal.png
  ├─ UPDATE organizacion SET logo_path = ...
  ├─ registrar en auditoria
COMMIT
  └─ si algo falla: ROLLBACK + borrar el PNG ya copiado
```

En la edición, donde el `id` ya existe, el orden es el mismo menos el `INSERT`.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from bingo.config.ajustes import LADO_MAX_LOGO
from bingo.config.rutas import dir_medios_organizacion
from bingo.dominio.modelos import Organizacion
from bingo.persistencia import repo_auditoria, repo_organizacion
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorValidacion
from bingo.utilidades.imagenes import validar_y_normalizar

NOMBRE_LOGO_PRINCIPAL = "logo_principal.png"
NOMBRE_LOGO_SECUNDARIO = "logo_secundario.png"


def _validar(datos: Organizacion) -> None:
    if not datos.nombre.strip():
        raise ErrorValidacion("organizaciones.error.nombre_vacio", campo="nombre")


def _normalizar_a_temporal(logo_origen: Path) -> Path:
    descriptor, ruta_texto = tempfile.mkstemp(suffix=".png", prefix="bingo_logo_")
    import os

    os.close(descriptor)
    temporal = Path(ruta_texto)
    return validar_y_normalizar(logo_origen, temporal, lado_max=LADO_MAX_LOGO)


def _mover_logo_definitivo(temporal: Path, organizacion_id: int) -> str:
    destino = dir_medios_organizacion(organizacion_id) / NOMBRE_LOGO_PRINCIPAL
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(temporal), str(destino))
    return str(destino)


def crear_organizacion(
    con: sqlite3.Connection, datos: Organizacion, logo_origen: Path | None
) -> Organizacion:
    _validar(datos)

    temporal_logo = _normalizar_a_temporal(logo_origen) if logo_origen is not None else None
    logo_copiado: Path | None = None
    try:
        with transaccion(con):
            creada = repo_organizacion.crear(con, datos)
            if temporal_logo is not None:
                ruta_logo = _mover_logo_definitivo(temporal_logo, creada.id)
                logo_copiado = Path(ruta_logo)
                creada.logo_path = ruta_logo
                repo_organizacion.actualizar(con, creada)
            repo_auditoria.registrar(con, None, "organizacion.creada", detalle=creada.nombre)
        return creada
    except BaseException:
        if logo_copiado is not None and logo_copiado.exists():
            logo_copiado.unlink(missing_ok=True)
        raise


def actualizar_organizacion(
    con: sqlite3.Connection, datos: Organizacion, logo_origen: Path | None
) -> Organizacion:
    _validar(datos)
    if datos.id is None:
        raise ValueError("No se puede actualizar una organización sin id")

    temporal_logo = _normalizar_a_temporal(logo_origen) if logo_origen is not None else None
    logo_copiado: Path | None = None
    try:
        with transaccion(con):
            if temporal_logo is not None:
                ruta_logo = _mover_logo_definitivo(temporal_logo, datos.id)
                logo_copiado = Path(ruta_logo)
                datos.logo_path = ruta_logo
            repo_organizacion.actualizar(con, datos)
            repo_auditoria.registrar(con, None, "organizacion.editada", detalle=datos.nombre)
        return datos
    except BaseException:
        if logo_copiado is not None and logo_copiado.exists():
            logo_copiado.unlink(missing_ok=True)
        raise


def eliminar_organizacion(con: sqlite3.Connection, organizacion_id: int) -> None:
    """`repo_organizacion.eliminar` ya bloquea si hay eventos o patrones propios.

    Sin papelera (enmienda G29): borrar solo es posible cuando no hay nada que
    perder, así que la carpeta de medios se borra directo, dentro de la misma
    transacción, después del `DELETE`.
    """
    carpeta_medios = dir_medios_organizacion(organizacion_id)
    with transaccion(con):
        repo_organizacion.eliminar(con, organizacion_id)
        repo_auditoria.registrar(con, None, "organizacion.eliminada", detalle=str(organizacion_id))
        if carpeta_medios.exists():
            shutil.rmtree(carpeta_medios, ignore_errors=True)
