"""Punto de entrada. Secuencia de arranque (documentada íntegra en el plan de
la fase 1, §1.7.1): cada fallo tiene un destino explícito y un código de
salida distinto, y ninguno termina el proceso con un traceback en una consola
que en producción no existe.

Códigos de salida: 0 éxito, 2 sin permisos/estructura, 3 base corrupta,
4 migración fallida, 5 segunda instancia, 6 restauración de respaldo fallida
(tarea 4.12, hallazgo B4 — documentado también en `docs/runbook.md`; nunca 0:
cero es éxito para cualquiera que invoque el proceso, incluido un instalador
o una tarea programada).

**`--restaurar <zip>` corre antes que todo lo demás (hallazgo E-11):**
argumentos → `asegurar_estructura` → validar el zip → restaurar → log →
preferencias → i18n → `QLockFile` → `abrir_conexion` → migraciones. Si el
`QLockFile` de los datos que se van a reemplazar ya está tomado por otra
instancia corriendo, se niega a continuar — restaurar por debajo de un
proceso que sigue con `bingo.db` abierto es un `WinError 32` a mitad de
camino.
"""

from __future__ import annotations

import contextlib
import sqlite3
import sys

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

# La política de DPI se fija ANTES de construir QApplication: después ya no
# tiene efecto (enmienda E16).
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


def _valor_de_argumento(argv: list[str], nombre: str) -> str | None:
    """`--restaurar <valor>`: sin `argparse` completo (deuda anotada en
    `TODOS.md`), pero ya no es un simple `in argv` — los dos flags
    booleanos existentes no necesitan un valor detrás."""
    if nombre not in argv:
        return None
    indice = argv.index(nombre)
    if indice + 1 >= len(argv):
        return None
    return argv[indice + 1]


def principal(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    reiniciar_datos = "--reiniciar-datos" in argv
    forzar_instancia = "--forzar-instancia" in argv
    ruta_restaurar = _valor_de_argumento(argv, "--restaurar")

    # QApplication va PRIMERO (enmienda E7a): un QMessageBox sin QApplication
    # viva aborta el proceso, así que cualquier diálogo de error de más abajo
    # necesita que esto exista antes. Solo puede existir una por proceso;
    # se reutiliza si ya la creó otra cosa (p. ej. una prueba).
    app = QApplication.instance() or QApplication(sys.argv[:1])

    from bingo.utilidades.errores import instalar_manejador_global

    def _mostrar_dialogo_inesperado(_error: BaseException) -> None:
        from bingo.config.rutas import ruta_log_aplicacion
        from bingo.i18n import t

        caja = QMessageBox()
        caja.setIcon(QMessageBox.Icon.Critical)
        caja.setWindowTitle(t("error.titulo"))
        caja.setText(t("error.mensaje"))
        caja.setInformativeText(t("error.ruta_log", ruta=str(ruta_log_aplicacion())))
        caja.exec()

    instalar_manejador_global(mostrar_dialogo=_mostrar_dialogo_inesperado)

    from bingo.config.rutas import asegurar_estructura, ruta_bd, ruta_log_aplicacion

    if reiniciar_datos:
        ruta = ruta_bd()
        for sufijo in ("", "-wal", "-shm"):
            candidato = ruta.with_name(ruta.name + sufijo)
            candidato.unlink(missing_ok=True)

    try:
        asegurar_estructura()
    except OSError:
        from bingo.i18n import cargar as cargar_idioma
        from bingo.i18n import t

        cargar_idioma("es")
        QMessageBox.critical(
            None,
            t("arranque.error.carpetas.titulo"),
            t("arranque.error.carpetas.mensaje", ruta=str(ruta_bd().parent)),
        )
        return 2

    if ruta_restaurar is not None:
        from pathlib import Path

        # Guardia previa (hallazgo E-11): si otra instancia sigue corriendo
        # sobre los datos actuales, su `.bingo.lock` sigue tomado — mover
        # esos datos por debajo sería el `WinError 32` que esto existe para
        # evitar. `deleteOnUnlock` porque este `tryLock` es solo de sondeo,
        # nunca el lock real del proceso (ese llega más abajo).
        lockfile_sondeo = QLockFile(str(ruta_bd().parent / ".bingo.lock"))
        lockfile_sondeo.setStaleLockTime(0)
        if not forzar_instancia and not lockfile_sondeo.tryLock(100):
            from bingo.i18n import cargar as cargar_idioma
            from bingo.i18n import t

            cargar_idioma("es")
            QMessageBox.warning(
                None,
                t("instancia.ya_en_ejecucion.titulo"),
                t("instancia.ya_en_ejecucion.mensaje"),
            )
            return 5
        lockfile_sondeo.unlock()

        from bingo.i18n import cargar as cargar_idioma
        from bingo.i18n import t
        from bingo.servicios import servicio_respaldos
        from bingo.utilidades.errores import ErrorBingo

        cargar_idioma("es")
        try:
            servicio_respaldos.restaurar(Path(ruta_restaurar))
        except ErrorBingo as error:
            QMessageBox.critical(
                None,
                t("respaldo.restaurar.error.titulo"),
                t(error.clave_i18n, **error.parametros),
            )
            return 6

    # El log se configura DESPUÉS de asegurar la estructura (enmienda G9):
    # RotatingFileHandler abre el archivo al construirse, y en un equipo
    # limpio esa carpeta todavía no existe.
    from bingo.utilidades.log import configurar_log

    configurar_log(ruta_log_aplicacion())

    from bingo.config import preferencias

    prefs = preferencias.cargar()

    from bingo import i18n

    i18n.cargar(prefs.idioma)

    from bingo.config.rutas import advertencia_ubicacion_bd
    from bingo.i18n import t

    aviso_ubicacion = advertencia_ubicacion_bd()

    lockfile = QLockFile(str(ruta_bd().parent / ".bingo.lock"))
    lockfile.setStaleLockTime(0)
    if not forzar_instancia and not lockfile.tryLock(100):
        QMessageBox.warning(
            None,
            t("instancia.ya_en_ejecucion.titulo"),
            t("instancia.ya_en_ejecucion.mensaje"),
        )
        return 5  # NUNCA 0 (enmienda G10): cero es éxito.

    from bingo.persistencia.conexion import abrir_conexion
    from bingo.utilidades.errores import ErrorBaseCorrupta, ErrorMigracion

    try:
        con = abrir_conexion()
    except ErrorBaseCorrupta as error:
        from bingo.ui.dialogos import mostrar_error_modal

        mostrar_error_modal(
            None,
            "arranque.error.base.titulo",
            "error.base_corrupta",
            detalle=error.detalle,
            ruta_log=str(ruta_log_aplicacion()),
        )
        return 3

    from bingo.persistencia.migraciones import aplicar_migraciones

    try:
        aplicar_migraciones(con)
    except ErrorMigracion as error:
        from bingo.ui.dialogos import mostrar_error_modal

        mostrar_error_modal(
            None,
            "arranque.error.migracion.titulo",
            error.clave_i18n,
            detalle=error.detalle,
            ruta_log=str(ruta_log_aplicacion()),
        )
        con.close()
        return 4

    from bingo.utilidades.log import registrar_arranque

    registrar_arranque(ruta_bd())

    # Barrido de lotes huérfanos (fase 2): corre antes de mostrar cualquier
    # ventana, para que un lote a medias por un cierre inesperado del proceso
    # anterior nunca llegue a pintarse en el listado de cartones. Un fallo
    # aquí no debe impedir arrancar: se registra en el log y se sigue, igual
    # que un lote corrupto no bloquea la limpieza del resto (ver
    # servicio_cartones.limpiar_lotes_huerfanos).
    import logging

    from bingo.servicios import servicio_cartones
    from bingo.utilidades.errores import ErrorBingo

    try:
        servicio_cartones.limpiar_lotes_huerfanos(con)
    except ErrorBingo as error:
        logging.getLogger("bingo").warning(
            "No se pudo completar el barrido de lotes huérfanos: %s", error.detalle
        )

    # Precarga de los patrones del sistema (fase 4, TODOS.md P2): idempotente,
    # y un fallo aquí tampoco debe impedir arrancar — el catálogo de patrones
    # queda vacío hasta el siguiente arranque, no la app entera.
    from bingo.servicios import servicio_patrones

    try:
        servicio_patrones.asegurar_patrones_sistema(con)
    except ErrorBingo as error:
        logging.getLogger("bingo").warning(
            "No se pudo precargar el catálogo de patrones del sistema: %s", error.detalle
        )

    from bingo.ui.tema import aplicar_tema_operador

    aplicar_tema_operador(app)

    from bingo.ui.ventana_principal import VentanaPrincipal

    ventana = VentanaPrincipal(con)
    if aviso_ubicacion and aviso_ubicacion not in prefs.avisos_descartados:
        QMessageBox.warning(ventana, t("ajustes.titulo"), t(aviso_ubicacion))

    def _comando_relanzamiento() -> list[str]:
        # PyInstaller (tarea 4.14) fija `sys.frozen`; en desarrollo se
        # relanza el mismo intérprete con `-m bingo` — nunca `sys.argv[0]`
        # a secas, que perdería el paquete de entrada.
        if getattr(sys, "frozen", False):
            return [sys.executable]
        return [sys.executable, "-m", "bingo"]

    def _reiniciar_para_restaurar(ruta_zip) -> None:  # noqa: ANN001 - Path, import perezoso abajo
        # Botón "Restaurar" de Ajustes (tarea 4.12, hallazgo B4): "sin
        # evento abierto" no basta — el proceso sigue teniendo `bingo.db`
        # abierto, `.bingo.lock` tomado y `aplicacion.log` abierto por el
        # `RotatingFileHandler`. Los tres se sueltan aquí, EN ESTE ORDEN,
        # antes de relanzar con `--restaurar` — al revés es el `WinError 32`
        # a mitad de camino que esta tarea existe para evitar.
        import subprocess

        from bingo.utilidades.log import reiniciar_para_pruebas as _cerrar_manejadores_log

        con.close()
        lockfile.unlock()
        _cerrar_manejadores_log()
        subprocess.Popen(_comando_relanzamiento() + ["--restaurar", str(ruta_zip)])
        app.quit()

    ventana.establecer_gancho_restaurar(_reiniciar_para_restaurar)

    ventana.show()
    codigo = app.exec()

    # El `QLockFile` se suelta aquí explícitamente, no al salir de ámbito
    # (tarea 4.12): `lockfile` ahora también vive capturado por el gancho de
    # "Restaurar" que cuelga de `VistaAjustes` (un hijo de `ventana`), y
    # `ventana` conecta `destroyed` a un método propio vía
    # `i18n.registrar_para_retraduccion` — un ciclo que solo Qt (no el
    # recolector cíclico de Python) puede romper, así que ya no basta con
    # que esta función retorne para soltar el archivo. `unlock()` no hace
    # nada si ya estaba suelto (p. ej. `_reiniciar_para_restaurar` ya lo
    # soltó antes de relanzar), así que llamarlo de más aquí es inocuo.
    lockfile.unlock()

    with contextlib.suppress(sqlite3.ProgrammingError):
        con.close()  # ya se cerró en _reiniciar_para_restaurar (tarea 4.12)
    return codigo


if __name__ == "__main__":
    sys.exit(principal())
