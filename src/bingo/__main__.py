"""Punto de entrada. Secuencia de arranque (documentada íntegra en el plan de
la fase 1, §1.7.1): cada fallo tiene un destino explícito y un código de
salida distinto, y ninguno termina el proceso con un traceback en una consola
que en producción no existe.

Códigos de salida: 0 éxito, 2 sin permisos/estructura, 3 base corrupta,
4 migración fallida, 5 segunda instancia (nunca 0: cero es éxito para
cualquiera que invoque el proceso, incluido un instalador o una tarea
programada).
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox

# La política de DPI se fija ANTES de construir QApplication: después ya no
# tiene efecto (enmienda E16).
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


def principal(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    reiniciar_datos = "--reiniciar-datos" in argv
    forzar_instancia = "--forzar-instancia" in argv

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

    from bingo.ui.tema import aplicar_tema_operador

    aplicar_tema_operador(app)

    from bingo.ui.ventana_principal import VentanaPrincipal

    ventana = VentanaPrincipal(con)
    if aviso_ubicacion and aviso_ubicacion not in prefs.avisos_descartados:
        QMessageBox.warning(ventana, t("ajustes.titulo"), t(aviso_ubicacion))

    ventana.show()
    codigo = app.exec()
    con.close()
    return codigo


if __name__ == "__main__":
    sys.exit(principal())
