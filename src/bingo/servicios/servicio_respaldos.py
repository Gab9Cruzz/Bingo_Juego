"""Respaldo y restauración del evento (contrato §5.10).

**`exportar()` recibe `evento_id`, no `con` (hallazgo B2, crítico) — la
única excepción de la fase a "`con` va siempre primero", documentada en
`docs/convenciones-codigo.md` porque corre en otro hilo.** `persistencia/
conexion.py` abre con `check_same_thread=True`, y el convenio de
`ui/tarea.py` exige que el invocable abra su propia conexión *dentro* de la
llamada — pasar una conexión ya abierta a un `Tarea` revienta con
"SQLite objects created in a thread can only be used in that same thread".

**Bloqueado mientras haya ronda `en_curso` o `pausada` (hallazgo E-1,
crítico).** La API de respaldo en línea de SQLite reinicia la copia si la
base de origen cambia mientras corre; con una bola escribiéndose cada pocos
segundos, un respaldo lanzado durante el sorteo no terminaría nunca — no
falla, no avanza. Se comprueba aquí, no solo en la interfaz: es la
diferencia entre un botón deshabilitado y una garantía real.

`restaurar()` es solo para la CLI (`python -m bingo --restaurar <zip>`,
hallazgo B4): con la aplicación corriendo, `bingo.db` está abierto,
`.bingo.lock` está tomado y el log de aplicación tiene su archivo abierto —
mover datos por debajo mientras eso pasa es `WinError 32` a mitad de
camino.
"""

from __future__ import annotations

import contextlib
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from bingo.config.rutas import (
    dir_impresos_evento,
    dir_logs_evento,
    dir_medios_evento,
    dir_respaldos,
    raiz_datos,
    ruta_bd,
)
from bingo.persistencia import repo_evento, repo_ronda
from bingo.persistencia.conexion import abrir_conexion
from bingo.persistencia.migraciones import version_actual, version_maxima_disponible
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorPersistencia, ErrorValidacion
from bingo.utilidades.fechas import ahora_iso

TEXTO_LEEME = (
    "Este archivo contiene datos personales de compradores (nombre, telefono,\n"
    "cedula, correo). Guardalo en un disco cifrado (por ejemplo con BitLocker)\n"
    "y no lo compartas por un canal sin cifrar.\n"
)

_NOMBRE_BD_EN_ZIP = "datos/bingo.db"
_NOMBRE_LEEME_EN_ZIP = "RESPALDO_LEEME.txt"


class _CancelacionRespaldo(Exception):
    """Interna: la usa el callback de progreso de `Connection.backup()`
    para abortar la copia desde dentro — nunca sale de este módulo."""


def _sello_de_tiempo(momento: str) -> str:
    fecha, _, hora = momento.partition("T")
    return f"{fecha.replace('-', '')}-{hora.rstrip('Z').replace(':', '')}"


def _respaldar_base_en_linea(
    origen: sqlite3.Connection, destino: Path, *, debe_cancelar: Callable[[], bool] | None
) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    con_destino = sqlite3.connect(str(destino))
    try:

        def _progreso(status: int, remaining: int, total: int) -> None:
            if debe_cancelar is not None and debe_cancelar():
                raise _CancelacionRespaldo

        try:
            origen.backup(con_destino, pages=100, progress=_progreso)
        except _CancelacionRespaldo:
            con_destino.close()
            destino.unlink(missing_ok=True)
            raise
    finally:
        with contextlib.suppress(sqlite3.ProgrammingError):
            con_destino.close()


def _agregar_carpeta_si_existe(archivo_zip: zipfile.ZipFile, carpeta: Path, prefijo: str) -> None:
    """Hallazgo P5: `dir_logs_evento`/`dir_impresos_evento` no existen si
    nunca se escribió nada ahí (ningún acta, ninguna bola extraída) — no es
    un error, simplemente no hay nada que copiar."""
    if not carpeta.is_dir():
        return
    for ruta in carpeta.rglob("*"):
        if ruta.is_file():
            archivo_zip.write(ruta, f"{prefijo}/{ruta.relative_to(carpeta)}")


def exportar(
    evento_id: int,
    carpeta_destino: Path | None = None,
    *,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
) -> Path | None:
    """`None` si se cancela a mitad — sin dejar ningún `.zip` parcial."""
    con = abrir_conexion()
    try:
        evento = repo_evento.obtener(con, evento_id)
        if evento is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})
        if repo_ronda.obtener_en_juego(con, evento_id) is not None:
            raise ErrorValidacion("respaldo.error.ronda_en_curso")

        if al_progresar is not None:
            al_progresar(0, 100)

        clave = evento.clave_evento or f"evento-{evento_id}"
        nombre_zip = f"respaldo-{clave}-{_sello_de_tiempo(ahora_iso())}.zip"
        carpeta = carpeta_destino or dir_respaldos()
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta_zip = carpeta / nombre_zip
        ruta_zip_temporal = ruta_zip.with_suffix(ruta_zip.suffix + ".tmp")

        with tempfile.TemporaryDirectory() as directorio_temporal:
            copia_bd = Path(directorio_temporal) / "bingo.db"
            try:
                _respaldar_base_en_linea(con, copia_bd, debe_cancelar=debe_cancelar)
            except _CancelacionRespaldo:
                return None
            if al_progresar is not None:
                al_progresar(60, 100)

            with zipfile.ZipFile(ruta_zip_temporal, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
                archivo_zip.write(copia_bd, _NOMBRE_BD_EN_ZIP)
                archivo_zip.writestr(_NOMBRE_LEEME_EN_ZIP, TEXTO_LEEME)
                _agregar_carpeta_si_existe(archivo_zip, dir_medios_evento(evento_id), "medios")
                _agregar_carpeta_si_existe(archivo_zip, dir_logs_evento(evento_id), "logs")
                _agregar_carpeta_si_existe(archivo_zip, dir_impresos_evento(evento_id), "impresos")

        ruta_zip_temporal.replace(ruta_zip)
        if al_progresar is not None:
            al_progresar(100, 100)
        return ruta_zip
    finally:
        con.close()


# ── Restauración (solo CLI, hallazgo B4) ──


def _extraer_seguro(archivo_zip: zipfile.ZipFile, destino: Path) -> None:
    """Contra zip-slip (hallazgo E-2, crítico): cada miembro se acepta solo
    si su ruta resuelta queda **dentro** de `destino` — rutas absolutas,
    `..` y letras de unidad quedan fuera por construcción, porque
    `Path.is_relative_to` compara la ruta ya resuelta, nunca el texto
    crudo del `.zip`. Nada de `extractall()` a secas: el `.zip` es un
    archivo que el operador pudo recibir por WhatsApp. Miembro a miembro,
    y solo archivos regulares (`is_dir()` se salta, no hay symlinks en un
    `.zip` de `zipfile`)."""
    destino_resuelto = destino.resolve()
    for miembro in archivo_zip.infolist():
        if miembro.is_dir():
            continue
        ruta_destino = (destino / miembro.filename).resolve()
        if not ruta_destino.is_relative_to(destino_resuelto):
            raise ErrorValidacion(
                "respaldo.error.zip_invalido", parametros={"miembro": miembro.filename}
            )
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        with archivo_zip.open(miembro) as origen, ruta_destino.open("wb") as salida:
            shutil.copyfileobj(origen, salida)


def validar_zip_de_respaldo(ruta_zip: Path) -> None:
    """Valida el `.zip` **entero** antes de tocar un solo archivo real
    (hallazgo B4, crítico): el orden peligroso es mover los datos vivos y
    *después* validar — un `.zip` corrupto dejaría al operador sin datos y
    sin restauración. Aquí no se mueve nada todavía."""
    if not ruta_zip.exists():
        raise ErrorValidacion("respaldo.error.zip_no_existe", parametros={"ruta": str(ruta_zip)})
    try:
        with zipfile.ZipFile(ruta_zip) as archivo_zip:
            malo = archivo_zip.testzip()
            if malo is not None:
                raise ErrorValidacion("respaldo.error.zip_corrupto", parametros={"miembro": malo})
            if _NOMBRE_BD_EN_ZIP not in archivo_zip.namelist():
                raise ErrorValidacion("respaldo.error.zip_sin_base")
            with tempfile.TemporaryDirectory() as tmp:
                ruta_bd_extraida = Path(tmp) / "bingo.db"
                with (
                    archivo_zip.open(_NOMBRE_BD_EN_ZIP) as origen,
                    ruta_bd_extraida.open("wb") as salida,
                ):
                    shutil.copyfileobj(origen, salida)
                con = sqlite3.connect(str(ruta_bd_extraida))
                con.row_factory = sqlite3.Row
                try:
                    version = version_actual(con)
                finally:
                    con.close()
                maxima = version_maxima_disponible()
                if version > maxima:
                    raise ErrorPersistencia(
                        "error.migracion.version_futura",
                        detalle=f"schema_version={version} > máxima disponible={maxima}",
                    )
    except zipfile.BadZipFile as error:
        raise ErrorValidacion("respaldo.error.zip_corrupto", parametros={"miembro": "?"}) from error


def restaurar(ruta_zip: Path) -> Path:
    """Solo se llama con la aplicación cerrada (hallazgo B4) — el proceso
    que orquesta esto es `__main__.py --restaurar`, que corre esta función
    **antes** de `QLockFile` y **antes** de `abrir_conexion` (hallazgo
    E-11). Copia lo que haya en `raiz_datos()` a
    `datos.pre-restauracion-<fecha>` y extrae el `.zip` encima — las
    migraciones corren solas en el arranque normal si la base venía de una
    versión anterior.
    """
    validar_zip_de_respaldo(ruta_zip)

    raiz = raiz_datos()
    sello = _sello_de_tiempo(ahora_iso())

    # El `.zip` suele vivir en `dir_respaldos()`, que es una subcarpeta de
    # `raiz_datos()`: si se mueve la raíz entera antes de leerlo, el propio
    # `.zip` se iría con ella. Se copia fuera primero, siempre — sea cual
    # sea su ubicación real.
    with tempfile.TemporaryDirectory() as directorio_temporal:
        copia_zip = Path(directorio_temporal) / "respaldo.zip"
        shutil.copyfile(ruta_zip, copia_zip)

        if raiz.exists() and any(raiz.iterdir()):
            copia_previa = raiz.parent / f"{raiz.name}.pre-restauracion-{sello}"
            shutil.move(str(raiz), str(copia_previa))

        raiz.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(copia_zip) as archivo_zip:
            _extraer_seguro(archivo_zip, raiz)

    # El zip guarda "datos/bingo.db"; `ruta_bd()` ya apunta a
    # `raiz_datos()/datos/bingo.db`, así que no hace falta mover nada más.
    return ruta_bd()
