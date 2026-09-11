"""Vista de ajustes: cuatro bloques (enmienda E19, más Respaldos en la tarea
4.12), no diez filas indiferenciadas."""

from __future__ import annotations

import platform
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bingo import __version__, i18n
from bingo.config import preferencias
from bingo.config.rutas import (
    advertencia_ubicacion_bd,
    dir_logs,
    dir_medios,
    dir_respaldos,
    raiz_datos,
    ruta_bd,
    ruta_log_aplicacion,
)
from bingo.i18n import t
from bingo.persistencia.migraciones import version_actual
from bingo.ui.dialogos import confirmar


def _fila_ubicacion(ruta) -> tuple[QLabel, QPushButton]:
    etiqueta = QLabel(str(ruta))
    etiqueta.setWordWrap(True)
    boton = QPushButton()
    boton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))))
    return etiqueta, boton


class VistaAjustes(QWidget):
    def __init__(self, con: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._gancho_restaurar: Callable[[Path], None] | None = None

        self._titulo = QLabel()

        # --- Preferencias ---
        self._grupo_preferencias = QGroupBox()
        self._combo_idioma = QComboBox()
        self._combo_idioma.addItem("Español", "es")
        self._combo_idioma.addItem("English", "en")
        indice = self._combo_idioma.findData(i18n.idioma_actual())
        if indice >= 0:
            self._combo_idioma.setCurrentIndex(indice)
        self._combo_idioma.currentIndexChanged.connect(self._cambiar_idioma)
        self._etiqueta_idioma_guardado = QLabel()
        self._etiqueta_idioma_guardado.setVisible(False)
        self._etiqueta_idioma = QLabel()
        formulario_preferencias = QFormLayout()
        fila_idioma = QHBoxLayout()
        fila_idioma.addWidget(self._combo_idioma)
        fila_idioma.addWidget(self._etiqueta_idioma_guardado)
        formulario_preferencias.addRow(self._etiqueta_idioma, fila_idioma)
        self._grupo_preferencias.setLayout(formulario_preferencias)

        # --- Ubicaciones ---
        self._grupo_ubicaciones = QGroupBox()
        formulario_ubicaciones = QFormLayout()
        self._etiqueta_raiz, boton_raiz = _fila_ubicacion(raiz_datos())
        self._etiqueta_bd, boton_bd = _fila_ubicacion(ruta_bd())
        self._etiqueta_logs, boton_logs = _fila_ubicacion(dir_logs())
        self._etiqueta_respaldos, boton_respaldos = _fila_ubicacion(dir_respaldos())
        self._etiqueta_medios, boton_medios = _fila_ubicacion(dir_medios())
        self._botones_ubicacion = [boton_raiz, boton_bd, boton_logs, boton_respaldos, boton_medios]
        self._etiqueta_fila_raiz = QLabel()
        self._etiqueta_fila_bd = QLabel()
        self._etiqueta_fila_logs = QLabel()
        self._etiqueta_fila_respaldos = QLabel()
        self._etiqueta_fila_medios = QLabel()
        for etiqueta_campo, valor, boton in (
            (self._etiqueta_fila_raiz, self._etiqueta_raiz, boton_raiz),
            (self._etiqueta_fila_bd, self._etiqueta_bd, boton_bd),
            (self._etiqueta_fila_logs, self._etiqueta_logs, boton_logs),
            (self._etiqueta_fila_respaldos, self._etiqueta_respaldos, boton_respaldos),
            (self._etiqueta_fila_medios, self._etiqueta_medios, boton_medios),
        ):
            fila = QHBoxLayout()
            fila.addWidget(valor, stretch=1)
            fila.addWidget(boton)
            formulario_ubicaciones.addRow(etiqueta_campo, fila)

        self._aviso_sincronizada = QLabel()
        self._aviso_sincronizada.setWordWrap(True)
        self._aviso_sincronizada.setStyleSheet(
            "background-color: rgba(226,163,61,0.15); border: 1px solid #e2a33d;"
            " border-radius: 6px; padding: 8px;"
        )
        self._aviso_sincronizada.setVisible(advertencia_ubicacion_bd() is not None)
        formulario_ubicaciones.addRow(self._aviso_sincronizada)
        self._grupo_ubicaciones.setLayout(formulario_ubicaciones)

        # --- Diagnóstico ---
        self._grupo_diagnostico = QGroupBox()
        formulario_diagnostico = QFormLayout()
        self._etiqueta_version_app = QLabel()
        self._valor_version_app = QLabel(__version__)
        self._etiqueta_version_python = QLabel()
        self._valor_version_python = QLabel(platform.python_version())
        self._etiqueta_version_esquema = QLabel()
        self._valor_version_esquema = QLabel(self._leer_version_esquema())
        self._boton_abrir_log = QPushButton()
        self._boton_abrir_log.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta_log_aplicacion())))
        )
        formulario_diagnostico.addRow(self._etiqueta_version_app, self._valor_version_app)
        formulario_diagnostico.addRow(self._etiqueta_version_python, self._valor_version_python)
        formulario_diagnostico.addRow(self._etiqueta_version_esquema, self._valor_version_esquema)
        formulario_diagnostico.addRow(self._boton_abrir_log)
        self._grupo_diagnostico.setLayout(formulario_diagnostico)

        # --- Respaldos (tarea 4.12) ---
        # "Restaurar" no restaura desde aquí (hallazgo B4): cierra la
        # conexión, suelta el `QLockFile` y los manejadores de log, y
        # relanza el proceso con `--restaurar <zip>` — el único camino que
        # no deja `bingo.db` abierto a mitad de la operación. El gancho lo
        # entrega `__main__.principal()` vía `VentanaPrincipal` (es quien
        # tiene la conexión, el `QLockFile` y el `QApplication` reales);
        # sin gancho el botón no hace nada (defensivo para pruebas que
        # instancian esta vista sola).
        self._grupo_respaldos = QGroupBox()
        formulario_respaldos = QFormLayout()
        self._boton_restaurar = QPushButton()
        self._boton_restaurar.clicked.connect(self._restaurar_desde_respaldo)
        formulario_respaldos.addRow(self._boton_restaurar)
        self._grupo_respaldos.setLayout(formulario_respaldos)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._titulo)
        distribucion.addWidget(self._grupo_preferencias)
        distribucion.addWidget(self._grupo_ubicaciones)
        distribucion.addWidget(self._grupo_diagnostico)
        distribucion.addWidget(self._grupo_respaldos)
        distribucion.addStretch()

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def establecer_gancho_restaurar(self, callback: Callable[[Path], None] | None) -> None:
        self._gancho_restaurar = callback

    def _restaurar_desde_respaldo(self) -> None:
        if self._gancho_restaurar is None:
            return
        ruta, _filtro = QFileDialog.getOpenFileName(self, "", str(dir_respaldos()), "Zip (*.zip)")
        if not ruta:
            return
        if not confirmar(
            self,
            t("ajustes.restaurar.confirmar.titulo"),
            t("ajustes.restaurar.confirmar.mensaje"),
        ):
            return
        self._gancho_restaurar(Path(ruta))

    def _leer_version_esquema(self) -> str:
        try:
            return str(version_actual(self._con))
        except Exception:  # noqa: BLE001 - diagnóstico de solo lectura, no debe tumbar la vista
            return t("ajustes.version_esquema.ilegible")

    def _cambiar_idioma(self) -> None:
        idioma = self._combo_idioma.currentData()
        i18n.cargar(idioma)
        prefs = preferencias.cargar()
        prefs.idioma = idioma
        preferencias.guardar(prefs)
        self._etiqueta_idioma_guardado.setText(t("ajustes.idioma.guardado"))
        self._etiqueta_idioma_guardado.setVisible(True)
        QTimer.singleShot(2000, lambda: self._etiqueta_idioma_guardado.setVisible(False))

    def retraducir(self) -> None:
        self._titulo.setText(t("ajustes.titulo"))
        self._grupo_preferencias.setTitle(t("ajustes.seccion.preferencias"))
        self._etiqueta_idioma.setText(t("ajustes.idioma"))
        self._grupo_ubicaciones.setTitle(t("ajustes.seccion.ubicaciones"))
        self._etiqueta_fila_raiz.setText(t("ajustes.ubicacion.raiz"))
        self._etiqueta_fila_bd.setText(t("ajustes.ubicacion.base_datos"))
        self._etiqueta_fila_logs.setText(t("ajustes.ubicacion.logs"))
        self._etiqueta_fila_respaldos.setText(t("ajustes.ubicacion.respaldos"))
        self._etiqueta_fila_medios.setText(t("ajustes.ubicacion.medios"))
        for boton in self._botones_ubicacion:
            boton.setText(t("comun.abrir_carpeta"))
        self._aviso_sincronizada.setText(t("ajustes.aviso_ubicacion_sincronizada"))
        self._grupo_diagnostico.setTitle(t("ajustes.seccion.diagnostico"))
        self._etiqueta_version_app.setText(t("ajustes.version_app"))
        self._etiqueta_version_python.setText(t("ajustes.version_python"))
        self._etiqueta_version_esquema.setText(t("ajustes.version_esquema"))
        self._boton_abrir_log.setText(t("ajustes.abrir_log"))
        self._grupo_respaldos.setTitle(t("ajustes.seccion.respaldos"))
        self._boton_restaurar.setText(t("ajustes.restaurar.boton"))
