"""Sistema de migraciones propio, transaccional.

El runner vive en el `__init__.py` de este mismo paquete (y no en un módulo
`persistencia/migraciones.py` separado) porque `persistencia.migraciones`
tiene que ser un **paquete real** para que `importlib.resources.files()`
encuentre los `.sql` que viven a su lado, y un módulo y un paquete no pueden
coexistir con el mismo nombre en el mismo directorio.

La tabla de control `schema_version` no está en el esquema de negocio: el
runner necesita leerla antes de aplicar la primera migración, así que se crea
en código con `IF NOT EXISTS`, no dentro de un archivo `.sql`.

Los archivos se descubren con `importlib.resources` sobre este paquete (no con
rutas relativas a `__file__`): es la API correcta para acceder a datos
empaquetados con el paquete, tanto en modo `onedir` como `onefile` de
PyInstaller. Que efectivamente viajen en una instalación normal depende de
`[tool.setuptools.package-data]` en `pyproject.toml`, no de esta elección.

**Mecanismo de atomicidad (obligatorio, no opcional):** `executescript()` emite
un `COMMIT` implícito antes de correr el script, así que un `BEGIN` fuera del
script y un `COMMIT` después de él no forman una transacción real — un fallo a
mitad del script deja el esquema a medio construir, sin fila en
`schema_version`. El `BEGIN IMMEDIATE` y el `COMMIT` van **dentro** del texto
que se pasa a `executescript()`. Regla asociada: los archivos de migración
nunca contienen su propio `BEGIN` ni `COMMIT`.
"""

from __future__ import annotations

import contextlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources

from bingo.utilidades.errores import ErrorMigracion

_PATRON_ARCHIVO = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
_PAQUETE_MIGRACIONES = "bingo.persistencia.migraciones"

_SQL_TABLA_CONTROL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    aplicada_en TEXT NOT NULL,
    archivo     TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Migracion:
    numero: int
    nombre: str
    archivo: str
    sql: str


def _asegurar_tabla_control(con: sqlite3.Connection) -> None:
    con.execute(_SQL_TABLA_CONTROL)


def version_actual(con: sqlite3.Connection) -> int:
    _asegurar_tabla_control(con)
    fila = con.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    return fila["version"] if fila and fila["version"] is not None else 0


def _resolver_directorio():
    """Punto de indirección para las pruebas: monkeypatch para apuntar a un
    directorio temporal sin tocar los `.sql` reales del paquete.
    """
    return resources.files(_PAQUETE_MIGRACIONES)


def _todas_las_migraciones() -> list[Migracion]:
    """Lee y valida todos los `.sql` del paquete de migraciones, ordenados."""
    migraciones: dict[int, Migracion] = {}
    paquete = _resolver_directorio()
    for entrada in paquete.iterdir():
        if not entrada.is_file() or entrada.name == "__init__.py":
            continue
        if not entrada.name.endswith(".sql"):
            continue
        coincidencia = _PATRON_ARCHIVO.match(entrada.name)
        if coincidencia is None:
            raise ErrorMigracion(
                "error.migracion",
                detalle=f"Nombre de archivo de migración inválido: {entrada.name}",
                parametros={"numero": "?", "archivo": entrada.name},
            )
        numero = int(coincidencia.group(1))
        if numero in migraciones:
            raise ErrorMigracion(
                "error.migracion",
                detalle=f"Número de migración duplicado: {numero}",
                parametros={"numero": numero, "archivo": entrada.name},
            )
        migraciones[numero] = Migracion(
            numero=numero,
            nombre=coincidencia.group(2),
            archivo=entrada.name,
            sql=entrada.read_text(encoding="utf-8"),
        )

    if migraciones:
        maximo = max(migraciones)
        faltantes = [n for n in range(1, maximo + 1) if n not in migraciones]
        if faltantes:
            raise ErrorMigracion(
                "error.migracion",
                detalle=f"Numeración de migraciones con huecos: faltan {faltantes}",
                parametros={"numero": faltantes[0], "archivo": "?"},
            )

    return [migraciones[n] for n in sorted(migraciones)]


def migraciones_pendientes(version: int) -> list[Migracion]:
    return [m for m in _todas_las_migraciones() if m.numero > version]


def _verificar_base_a_medias(con: sqlite3.Connection, version: int) -> None:
    """Detecta una base con tablas creadas pero `schema_version` vacía.

    Un corte de luz entre `CREATE TABLE` (fuera de la transacción real, en el
    escenario que G1 corrige) y el registro de versión puede dejar el esquema
    a medias con `version_actual() == 0`. Sin esta guardia, el runner reaplica
    la 001 y `CREATE TABLE organizacion` falla con "table already exists",
    dejando al usuario sin salida.
    """
    if version != 0:
        return
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table' AND name != 'schema_version'"
    ).fetchone()
    if fila and fila["n"] > 0:
        raise ErrorMigracion(
            "error.migracion.a_medias",
            detalle="version_actual()==0 pero sqlite_master no está vacío",
        )


def aplicar_migraciones(con: sqlite3.Connection) -> list[int]:
    """Aplica las migraciones pendientes, en orden, cada una en su propia transacción.

    Devuelve la lista de números de versión aplicados. Si `version_actual()`
    supera la migración más alta disponible, la base viene de una versión más
    nueva de la aplicación: se aborta en vez de arrancar contra un esquema
    desconocido.
    """
    version = version_actual(con)
    _verificar_base_a_medias(con, version)

    todas = _todas_las_migraciones()
    maximo_disponible = max((m.numero for m in todas), default=0)
    if version > maximo_disponible:
        raise ErrorMigracion(
            "error.migracion.version_futura",
            detalle=f"schema_version={version} > máxima migración disponible={maximo_disponible}",
        )

    aplicadas: list[int] = []
    for migracion in migraciones_pendientes(version):
        _aplicar_una(con, migracion)
        aplicadas.append(migracion.numero)
    return aplicadas


def _aplicar_una(con: sqlite3.Connection, migracion: Migracion) -> None:
    momento = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    script = (
        "BEGIN IMMEDIATE;\n"
        + migracion.sql
        + "\nINSERT INTO schema_version (version, aplicada_en, archivo) VALUES "
        + f"({migracion.numero}, '{momento}', '{migracion.archivo}');\n"
        + "COMMIT;\n"
    )
    try:
        con.executescript(script)
    except sqlite3.Error as error:
        with contextlib.suppress(sqlite3.Error):
            con.rollback()
        raise ErrorMigracion(
            "error.migracion",
            detalle=f"Migración {migracion.numero} ({migracion.archivo}) falló: {error}",
            parametros={"numero": migracion.numero, "archivo": migracion.archivo},
        ) from error
