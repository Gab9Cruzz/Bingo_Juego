"""Sección "Datos del evento": única sección del espacio de trabajo en la fase 1.

Vista de solo lectura: la fase 1 no requiere editar un evento ya creado, solo
crearlo (en `vista_eventos.py`) y verlo. Editar datos del evento es trabajo de
una fase posterior, cuando además haya plantilla y estado que coordinar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from bingo import i18n
from bingo.dominio.dinero import formatear
from bingo.dominio.modelos import Evento
from bingo.i18n import t
from bingo.persistencia import repo_organizacion


class VistaDatosEvento(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento

        self._titulo = QLabel()
        titulo_fuente = self._titulo.font()
        titulo_fuente.setPointSize(titulo_fuente.pointSize() + 4)
        titulo_fuente.setBold(True)
        self._titulo.setFont(titulo_fuente)

        self._logo = QLabel()
        self._logo.setFixedSize(56, 56)
        self._logo.setScaledContents(True)

        organizacion = repo_organizacion.obtener(con, evento.organizacion_id)
        if organizacion and organizacion.logo_path and Path(organizacion.logo_path).exists():
            self._logo.setPixmap(QPixmap(organizacion.logo_path))

        self._formulario = QFormLayout()
        self._valor_organizacion = QLabel(organizacion.nombre if organizacion else "—")
        self._valor_fecha = QLabel(evento.fecha or "—")
        self._valor_hora = QLabel(evento.hora or "—")
        self._valor_lugar = QLabel(evento.lugar or "—")
        idioma = i18n.idioma_actual()
        self._valor_precio = QLabel(formatear(evento.precio_tabla_centavos, idioma))
        self._valor_estado = QLabel(t(f"estado_evento.{evento.estado}"))

        self._etiqueta_organizacion = QLabel()
        self._etiqueta_fecha = QLabel()
        self._etiqueta_hora = QLabel()
        self._etiqueta_lugar = QLabel()
        self._etiqueta_precio = QLabel()
        self._etiqueta_estado = QLabel()
        self._formulario.addRow(self._etiqueta_organizacion, self._valor_organizacion)
        self._formulario.addRow(self._etiqueta_fecha, self._valor_fecha)
        self._formulario.addRow(self._etiqueta_hora, self._valor_hora)
        self._formulario.addRow(self._etiqueta_lugar, self._valor_lugar)
        self._formulario.addRow(self._etiqueta_precio, self._valor_precio)
        self._formulario.addRow(self._etiqueta_estado, self._valor_estado)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._logo)
        distribucion.addWidget(self._titulo)
        distribucion.addLayout(self._formulario)
        distribucion.addStretch()

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def retraducir(self) -> None:
        self._titulo.setText(self._evento.nombre)
        self._etiqueta_organizacion.setText(t("eventos.campo.organizacion"))
        self._etiqueta_fecha.setText(t("eventos.campo.fecha"))
        self._etiqueta_hora.setText(t("eventos.campo.hora"))
        self._etiqueta_lugar.setText(t("eventos.campo.lugar"))
        self._etiqueta_precio.setText(t("eventos.campo.precio"))
        self._etiqueta_estado.setText(t("eventos.campo.estado"))
        self._valor_estado.setText(t(f"estado_evento.{self._evento.estado}"))
