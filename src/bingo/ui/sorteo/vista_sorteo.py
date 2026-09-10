"""Sección "Sorteo" del espacio de trabajo del evento (contrato §5.5, §5.6).

Jerarquía de tres zonas con proporciones fijas (decisión DU-2), no una
rejilla de `QGroupBox` equitativos: bajo presión, hablando a cámara, el
orden real es el número que acabo de cantar, si hay ganador ahora mismo, y
el botón de extraer.

- **Zona A** (~35%): el número actual, letra BINGO + cifra. Nada más.
- **Zona B** (~45%): tablero de 75 a la izquierda; a-una-bola/ganadores a
  la derecha, **colapsados a altura cero cuando están vacíos** — que
  aparezcan *es* la señal (decisión DU-2).
- **Zona C** (~20%): Extraer (el objetivo de pulsación más grande de la
  aplicación), Pausar/Cerrar, buscador de código siempre activo.

**No lleva Guardar/Cancelar** (decisión DU-2): no edita entidades, ejecuta
acciones — la convención DS14 no aplica aquí.

El motor de sorteo vive en `EspacioEvento`, no aquí (hallazgo S5-3):
recibe `motor_sorteo` por constructor y solo lo envuelve en un
`PuenteSorteo`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.config import preferencias
from bingo.dominio.carton import carton_desde_orden_canonico
from bingo.dominio.modelos import Ganador
from bingo.dominio.tema import TemaDashboard
from bingo.i18n import t
from bingo.persistencia import (
    repo_auditoria,
    repo_carton,
    repo_comprador,
    repo_extraccion,
    repo_ganador,
    repo_patron,
    repo_ronda,
)
from bingo.servicios import servicio_ganadores
from bingo.ui.atajos import ATAJOS
from bingo.ui.dialogos import FranjaError, confirmar
from bingo.ui.sorteo.dialogo_empate import DialogoEmpate
from bingo.ui.sorteo.puente_sorteo import PuenteSorteo
from bingo.ui.transmision.pantallas import elegir_pantalla
from bingo.ui.transmision.ventana_transmision import VentanaTransmision
from bingo.ui.widgets.cuadricula_carton import CuadriculaCarton
from bingo.ui.widgets.rejilla_patron import RejillaPatron
from bingo.ui.widgets.tablero_setenta_cinco import TableroSetentaYCinco
from bingo.utilidades.errores import ErrorBingo

_DURACION_BLOQUEO_DOBLE_CLIC_MS = 400


class VistaSorteo(QWidget):
    def __init__(
        self, con: Any, evento: Any, espacio_evento: Any, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._espacio = espacio_evento
        self._motor = espacio_evento.motor_sorteo
        self._puente = PuenteSorteo(self._motor, con, parent=self)
        self._ronda_actual = None
        self._patron_actual = None

        self._franja = FranjaError()

        # -- Estado vacío (hallazgo S5-16) --------------------------------
        self._etiqueta_vacio = QLabel()
        self._etiqueta_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._etiqueta_vacio.setWordWrap(True)
        self._etiqueta_vacio.setObjectName("etiquetaSecundaria")

        # -- Cabecera: ronda / patrón / premio -----------------------------
        self._etiqueta_ronda = QLabel()
        self._rejilla_patron = RejillaPatron(solo_lectura=True)
        self._etiqueta_premio = QLabel()

        # -- Zona A ----------------------------------------------------------
        self._etiqueta_numero = QLabel("—")
        self._etiqueta_numero.setObjectName("sorteoNumeroActual")
        self._etiqueta_numero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fuente_numero = self._etiqueta_numero.font()
        fuente_numero.setPointSize(72)
        fuente_numero.setBold(True)
        self._etiqueta_numero.setFont(fuente_numero)

        self._etiqueta_estado_ronda = QLabel()
        self._etiqueta_contador = QLabel()

        columna_estado = QVBoxLayout()
        columna_estado.addWidget(self._etiqueta_estado_ronda)
        columna_estado.addWidget(self._etiqueta_contador)
        columna_estado.addStretch()

        zona_a = QHBoxLayout()
        zona_a.addWidget(self._etiqueta_numero, stretch=2)
        zona_a.addLayout(columna_estado, stretch=1)

        # -- Zona B ----------------------------------------------------------
        self._tablero = TableroSetentaYCinco()

        self._grupo_a_una_bola = QGroupBox()
        self._grupo_a_una_bola.setVisible(False)  # DU-2: vacío no se pinta
        self._lista_a_una_bola = QListWidget()
        layout_una_bola = QVBoxLayout(self._grupo_a_una_bola)
        layout_una_bola.addWidget(self._lista_a_una_bola)

        self._grupo_ganadores = QGroupBox()
        self._grupo_ganadores.setObjectName("panelGanadores")
        self._grupo_ganadores.setVisible(False)
        self._lista_ganadores = QListWidget()
        layout_ganadores = QVBoxLayout(self._grupo_ganadores)
        layout_ganadores.addWidget(self._lista_ganadores)

        columna_secundaria = QVBoxLayout()
        columna_secundaria.addWidget(self._grupo_a_una_bola)
        columna_secundaria.addWidget(self._grupo_ganadores)
        columna_secundaria.addStretch()

        zona_b = QHBoxLayout()
        zona_b.addWidget(self._tablero, stretch=2)
        zona_b.addLayout(columna_secundaria, stretch=1)

        # -- Zona C ------------------------------------------------------------
        self._boton_extraer = QPushButton()
        self._boton_extraer.setObjectName("botonExtraer")
        self._boton_extraer.setMinimumHeight(64)
        self._boton_extraer.clicked.connect(self._al_pulsar_extraer)

        self._boton_iniciar = QPushButton()
        self._boton_iniciar.clicked.connect(self._iniciar_ronda)
        self._boton_pausar = QPushButton()
        self._boton_pausar.clicked.connect(self._pausar_o_reanudar)
        self._boton_cerrar_ronda = QPushButton()
        self._boton_cerrar_ronda.clicked.connect(self._cerrar_ronda)

        fila_acciones_ronda = QHBoxLayout()
        fila_acciones_ronda.addWidget(self._boton_extraer)
        fila_acciones_ronda.addWidget(self._boton_iniciar)
        fila_acciones_ronda.addWidget(self._boton_pausar)
        fila_acciones_ronda.addWidget(self._boton_cerrar_ronda)

        self._campo_codigo = QLineEdit()
        self._boton_consultar = QPushButton()
        self._boton_consultar.clicked.connect(lambda: self._validar_reclamo(registrar=False))
        self._boton_registrar_reclamo = QPushButton()
        self._boton_registrar_reclamo.setEnabled(False)
        self._boton_registrar_reclamo.clicked.connect(lambda: self._validar_reclamo(registrar=True))
        self._campo_codigo.returnPressed.connect(lambda: self._validar_reclamo(registrar=False))
        self._etiqueta_veredicto = QLabel()
        self._etiqueta_veredicto.setWordWrap(True)
        self._visor_reclamo = CuadriculaCarton()
        self._reclamo_pendiente: servicio_ganadores.Reclamo | None = None
        self._ganador_pendiente_id: int | None = None

        fila_buscador = QHBoxLayout()
        fila_buscador.addWidget(self._campo_codigo)
        fila_buscador.addWidget(self._boton_consultar)
        fila_buscador.addWidget(self._boton_registrar_reclamo)

        self._boton_modo_vivo = QPushButton()
        self._boton_modo_vivo.setCheckable(True)
        self._boton_modo_vivo.toggled.connect(self._alternar_modo_vivo)

        self._ventana_transmision: VentanaTransmision | None = None
        self._boton_transmision = QPushButton()
        self._boton_transmision.setCheckable(True)
        self._boton_transmision.toggled.connect(self._alternar_transmision)

        fila_terciaria = QHBoxLayout()
        fila_terciaria.addWidget(self._boton_transmision)
        fila_terciaria.addWidget(self._boton_modo_vivo)

        zona_c = QVBoxLayout()
        zona_c.addLayout(fila_acciones_ronda)
        zona_c.addLayout(fila_buscador)
        fila_resultado = QHBoxLayout()
        fila_resultado.addWidget(self._visor_reclamo)
        fila_resultado.addWidget(self._etiqueta_veredicto, stretch=1)
        zona_c.addLayout(fila_resultado)
        zona_c.addLayout(fila_terciaria)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self._etiqueta_ronda)
        cabecera.addWidget(self._rejilla_patron)
        cabecera.addWidget(self._etiqueta_premio)
        cabecera.addStretch()

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._etiqueta_vacio)
        distribucion.addLayout(cabecera)
        distribucion.addLayout(zona_a, stretch=35)
        distribucion.addLayout(zona_b, stretch=45)
        distribucion.addLayout(zona_c, stretch=20)

        self._puente.bola_extraida.connect(self._al_extraer)
        self._puente.cartones_a_una_bola.connect(self._al_actualizar_a_una_bola)
        self._puente.ganadores_detectados.connect(self._al_detectar_ganadores)
        self._puente.ganador_confirmado.connect(self._al_confirmar_ganador)
        self._puente.ronda_cambiada.connect(self._al_cambiar_ronda)
        self._puente.fallo.connect(self._al_fallar)
        self._puente.fallo_log.connect(self._al_fallar_log)

        self._configurar_atajos()
        self._cargar_estado_inicial()
        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    # -- atajos (ámbito "sorteo", decisión D12/DU-5) ------------------------

    def _configurar_atajos(self) -> None:
        def _atajo(accion: str, alcance: str = "sorteo") -> QShortcut:
            atajo = QShortcut(QKeySequence(ATAJOS.secuencia(accion, alcance)), self)
            atajo.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            return atajo

        self._atajo_extraer = _atajo("sorteo.extraer")
        self._atajo_extraer.activated.connect(self._extraer_si_no_hay_foco_en_texto)
        self._atajo_extraer_alterno = _atajo("sorteo.extraer_alterno")
        self._atajo_extraer_alterno.activated.connect(self._al_pulsar_extraer)
        self._atajo_pausar = _atajo("sorteo.pausar_reanudar")
        self._atajo_pausar.activated.connect(
            lambda: self._pausar_o_reanudar() if not self._foco_en_texto() else None
        )
        self._atajo_buscar = _atajo("sorteo.buscar")
        self._atajo_buscar.activated.connect(self._campo_codigo.setFocus)
        self._atajo_confirmar = _atajo("sorteo.confirmar_ganador")
        self._atajo_confirmar.activated.connect(self._confirmar_ganador_seleccionado)
        self._atajo_modo_vivo = _atajo("sorteo.modo_vivo")
        self._atajo_modo_vivo.activated.connect(self._boton_modo_vivo.toggle)

    def _foco_en_texto(self) -> bool:
        return isinstance(QApplication.focusWidget(), QLineEdit)

    def _extraer_si_no_hay_foco_en_texto(self) -> None:
        # DU-5: "Espacio" se inhibe con el foco en el buscador de código —
        # de lo contrario escribiría un espacio ahí y ni siquiera extraería.
        if self._foco_en_texto():
            return
        self._al_pulsar_extraer()

    # -- estado inicial y estado vacío (hallazgo S5-16) ----------------------

    def _cargar_estado_inicial(self) -> None:
        ronda_en_juego = repo_ronda.obtener_en_juego(self._con, self._evento.id)
        rondas = repo_ronda.listar_por_evento(self._con, self._evento.id)
        if not rondas:
            self._mostrar_vacio(True)
            return
        self._mostrar_vacio(False)

        if ronda_en_juego is not None and not self._motor.hay_ronda_en_juego:
            # El motor no tiene nada en memoria (primer paso a esta
            # sección, o la app se reinició): reanudar desde la base
            # (decisión D13). Aquí se adopta directamente sin diálogo de
            # incoherencia — esa conversación la tiene la vista al detectar
            # el error, no la carga silenciosa al abrir la sección.
            try:
                self._motor.reanudar_ronda(self._con, ronda_en_juego.id)
            except ErrorBingo as error:
                self._franja.mostrar_error(error)
        self._sincronizar_con_ronda(
            ronda_en_juego if ronda_en_juego is not None else self._primera_ronda_pendiente(rondas)
        )

    def _primera_ronda_pendiente(self, rondas: list) -> object | None:
        pendientes = [r for r in rondas if r.estado == "pendiente"]
        return pendientes[0] if pendientes else None

    def _mostrar_vacio(self, vacio: bool) -> None:
        self._etiqueta_vacio.setVisible(vacio)
        for widget in (
            self._boton_extraer,
            self._boton_iniciar,
            self._boton_pausar,
            self._boton_cerrar_ronda,
            self._campo_codigo,
            self._tablero,
        ):
            widget.setEnabled(not vacio)

    def _sincronizar_con_ronda(self, ronda: object | None) -> None:
        self._ronda_actual = ronda
        self._tablero.reiniciar()
        self._grupo_a_una_bola.setVisible(False)
        self._grupo_ganadores.setVisible(False)
        if ronda is None:
            self._etiqueta_ronda.setText(t("sorteo.sin_ronda"))
            self._rejilla_patron.setVisible(False)
            self._etiqueta_premio.clear()
            self._actualizar_botones_estado("pendiente")
            return

        self._patron_actual = repo_patron.obtener(self._con, ronda.patron_id)
        self._etiqueta_ronda.setText(ronda.nombre)
        self._etiqueta_premio.setText(ronda.premio_nombre or "")
        if self._patron_actual is not None and self._patron_actual.mascaras:
            self._rejilla_patron.setVisible(True)
            self._rejilla_patron.establecer_mascara(self._patron_actual.mascaras[0])
        else:
            self._rejilla_patron.setVisible(False)

        numeros_salidos = repo_extraccion.numeros_por_ronda(self._con, ronda.id)
        for numero in numeros_salidos:
            self._tablero.marcar(numero)
        if numeros_salidos:
            self._tablero.marcar(numeros_salidos[-1], es_ultima=True)
            self._etiqueta_numero.setText(str(numeros_salidos[-1]))
        self._actualizar_contador()
        self._actualizar_botones_estado(ronda.estado)

    def _actualizar_contador(self) -> None:
        if self._ronda_actual is None:
            self._etiqueta_contador.clear()
            return
        n = repo_extraccion.contar_por_ronda(self._con, self._ronda_actual.id)
        self._etiqueta_contador.setText(t("sorteo.contador", extraidas=n, total=75))

    def _actualizar_botones_estado(self, estado: str) -> None:
        self._etiqueta_estado_ronda.setText(t(f"sorteo.estado_ronda.{estado}"))
        self._boton_extraer.setEnabled(estado == "en_curso")
        self._boton_iniciar.setEnabled(estado == "pendiente")
        self._boton_pausar.setEnabled(estado in ("en_curso", "pausada"))
        self._boton_pausar.setText(
            t("sorteo.accion.pausar") if estado == "en_curso" else t("sorteo.accion.reanudar")
        )
        self._boton_cerrar_ronda.setEnabled(estado in ("en_curso", "pausada"))

    # -- ciclo de vida de la ronda -------------------------------------------

    def _iniciar_ronda(self) -> None:
        if self._ronda_actual is None:
            return
        try:
            self._motor.iniciar_ronda(self._con, self._ronda_actual.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._puente.establecer_modo_automatico(False)
        self._refrescar_ronda_actual()

    def _pausar_o_reanudar(self) -> None:
        if self._ronda_actual is None:
            return
        try:
            if self._ronda_actual.estado == "en_curso":
                self._motor.pausar(self._con, self._ronda_actual.id)
            else:
                self._motor.reanudar(self._con, self._ronda_actual.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._refrescar_ronda_actual()

    def _cerrar_ronda(self) -> None:
        if self._ronda_actual is None:
            return
        # Hallazgo C7: agotar el bombo sin ganador es un final legítimo;
        # cerrar con bolas restantes y sin ganador confirmado es una
        # decisión que merece una confirmación explícita.
        bombo_con_bolas = self._motor.bombo is not None and not self._motor.bombo.agotado
        if bombo_con_bolas and not confirmar(
            self, t("sorteo.confirmar_cerrar.titulo"), t("sorteo.confirmar_cerrar.mensaje")
        ):
            return
        try:
            self._motor.cerrar_ronda(self._con, self._ronda_actual.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._franja.mostrar_exito(
            t("sorteo.exito.ronda_cerrada", nombre=self._ronda_actual.nombre)
        )
        self._refrescar_ronda_actual()

    def _refrescar_ronda_actual(self) -> None:
        if self._ronda_actual is None:
            return
        ronda = repo_ronda.obtener(self._con, self._ronda_actual.id)
        self._sincronizar_con_ronda(ronda)

    def _al_cambiar_ronda(self, ronda_id: int, estado: str) -> None:
        if self._ronda_actual is not None and self._ronda_actual.id == ronda_id:
            self._refrescar_ronda_actual()

    # -- extracción -----------------------------------------------------------

    def _al_pulsar_extraer(self) -> None:
        # Hallazgo S5-9: doble clic no dispara dos bolas. Se deshabilita al
        # pulsar y se rehabilita poco después (aquí no hay animación real
        # que esperar: la persistencia es síncrona, decisión D2).
        self._boton_extraer.setEnabled(False)
        QTimer.singleShot(_DURACION_BLOQUEO_DOBLE_CLIC_MS, self._rehabilitar_boton_extraer)
        self._puente.extraer()

    def _rehabilitar_boton_extraer(self) -> None:
        if self._ronda_actual is not None and self._ronda_actual.estado == "en_curso":
            self._boton_extraer.setEnabled(True)

    def _al_extraer(self, extraccion) -> None:
        self._tablero.marcar(extraccion.numero, es_ultima=True)
        self._etiqueta_numero.setText(str(extraccion.numero))
        self._actualizar_contador()

    def _al_actualizar_a_una_bola(self, cartones: list) -> None:
        self._lista_a_una_bola.clear()
        cantidad = len(cartones)
        if cantidad == 0:
            self._grupo_a_una_bola.setVisible(False)
            return
        self._grupo_a_una_bola.setVisible(True)
        self._grupo_a_una_bola.setTitle(t("sorteo.a_una_bola.titulo", cantidad=cantidad))
        # DU-10: lista nominal solo con pocos, cantidad grande siempre.
        if cantidad <= 8:
            for carton in cartones:
                self._lista_a_una_bola.addItem(QListWidgetItem(carton.codigo))

    def _al_detectar_ganadores(self, cartones: list) -> None:
        """Solo pinta el panel. **No confirma nada**: la detección es un
        hecho objetivo del sorteo (D8), pero confirmar a quién le
        corresponde el premio es una decisión del operador — al validar un
        reclamo (`_registrar_reclamo_pendiente`) o al resolver un empate
        (`_abrir_dialogo_empate`), nunca automáticamente al detectar."""
        self._lista_ganadores.clear()
        if not cartones:
            self._grupo_ganadores.setVisible(False)
            return
        self._grupo_ganadores.setVisible(True)
        self._grupo_ganadores.setTitle(t("sorteo.ganadores.titulo", cantidad=len(cartones)))
        mapa_compradores = repo_comprador.mapa_por_evento(self._con, self._evento.id)
        for carton in cartones:
            comprador = mapa_compradores.get(carton.carton_id)
            nombre = comprador.nombre if comprador is not None else "?"
            self._lista_ganadores.addItem(QListWidgetItem(f"{carton.codigo} — {nombre}"))

    def _detectados_pendientes(self) -> list[Ganador]:
        if self._ronda_actual is None:
            return []
        return [
            g
            for g in repo_ganador.listar_por_ronda(self._con, self._ronda_actual.id)
            if g.anulado_en is None and g.decision is None
        ]

    def _confirmar_ganador_seleccionado(self) -> None:
        # DU-5: sin selección clara, esto no hace nada — nunca elige el
        # primero por defecto (es dinero).
        if self._ronda_actual is None or self._grupo_ganadores.count() == 0:
            return
        self._abrir_dialogo_empate()

    def _abrir_dialogo_empate(self) -> None:
        if self._ronda_actual is None:
            return
        detectados = self._detectados_pendientes()
        if not detectados:
            return
        mapa_compradores = repo_comprador.mapa_por_evento(self._con, self._evento.id)
        dialogo = DialogoEmpate(detectados, mapa_compradores, parent=self)
        if dialogo.exec():
            if dialogo.id_unico is not None:
                self._confirmar_con_id(dialogo.id_unico, "unico")
                for otro in detectados:
                    if otro.id != dialogo.id_unico:
                        self._puente.confirmar_ganador(otro.id, "rechazado")
            elif dialogo.ids_reparto:
                for gid in dialogo.ids_reparto:
                    self._puente.confirmar_ganador(gid, "reparto")
                for otro in detectados:
                    if otro.id not in dialogo.ids_reparto:
                        self._puente.confirmar_ganador(otro.id, "rechazado")

    def _confirmar_con_id(self, ganador_id: int, decision: str) -> None:
        self._puente.confirmar_ganador(ganador_id, decision)

    def _al_confirmar_ganador(self, ganador: Ganador) -> None:
        if ganador.decision in ("unico", "reparto", "desempate_externo"):
            carton = repo_carton.obtener(self._con, ganador.carton_id)
            comprador = repo_comprador.obtener_por_carton(self._con, ganador.carton_id)
            codigo = carton.codigo if carton is not None else "?"
            nombre = comprador.nombre if comprador is not None else "?"
            self._franja.mostrar_exito(
                t("sorteo.exito.ganador_confirmado", codigo=codigo, nombre=nombre)
            )

    # -- validación de reclamo (contrato §5.6, decisión DU-9) ----------------

    def _validar_reclamo(self, *, registrar: bool) -> None:
        if self._ronda_actual is None:
            return
        texto = self._campo_codigo.text().strip()
        if not texto:
            return
        try:
            reclamo = servicio_ganadores.validar_reclamo(self._con, self._ronda_actual.id, texto)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._reclamo_pendiente = reclamo
        self._pintar_reclamo(reclamo)
        if registrar and reclamo.cumple and reclamo.carton is not None:
            self._registrar_reclamo_pendiente(reclamo)

    def _pintar_reclamo(self, reclamo: servicio_ganadores.Reclamo) -> None:
        if reclamo.carton is None:
            self._visor_reclamo.limpiar()
            self._etiqueta_veredicto.setText(
                t(reclamo.motivo_rechazo or "ganador.error.codigo_inexistente")
            )
            self._boton_registrar_reclamo.setEnabled(False)
            return
        matriz = carton_desde_orden_canonico(reclamo.carton.numeros)
        marcados = {bit for bit in range(25) if (reclamo.marcado >> bit) & 1}
        patron_resaltado = (
            self._patron_actual.mascaras[0]
            if self._patron_actual and self._patron_actual.mascaras
            else None
        )
        self._visor_reclamo.actualizar(matriz, marcados=marcados, patron_resaltado=patron_resaltado)
        if reclamo.cumple:
            self._etiqueta_veredicto.setText(t("sorteo.veredicto.cumple"))
        else:
            self._etiqueta_veredicto.setText(
                t(reclamo.motivo_rechazo or "sorteo.veredicto.no_cumple")
            )
        self._boton_registrar_reclamo.setEnabled(reclamo.cumple)

    def _registrar_reclamo_pendiente(self, reclamo: servicio_ganadores.Reclamo) -> None:
        """DU-9: "Registrar reclamo" escribe el instante en auditoría — es
        la defensa ante una disputa posterior (tarea 4.24) — y solo
        confirma directamente si no hay ambigüedad (un único detectado
        pendiente en la ronda). Con más de uno (empate real, V2), pasa el
        control al diálogo de empate en vez de decidir por su cuenta."""
        if self._ronda_actual is None or reclamo.carton is None:
            return
        pendientes = self._detectados_pendientes()
        objetivo = next((g for g in pendientes if g.carton_id == reclamo.carton.id), None)
        if objetivo is None:
            return
        repo_auditoria.registrar(
            self._con,
            self._evento.id,
            "ganador.reclamado",
            detalle=f"ganador_id={objetivo.id} carton={reclamo.carton.codigo}",
        )
        self._franja.mostrar_exito(
            t("sorteo.exito.reclamo_registrado", codigo=reclamo.carton.codigo)
        )
        if len(pendientes) == 1:
            self._puente.confirmar_ganador(objetivo.id, "unico")
        else:
            self._abrir_dialogo_empate()

    # -- modo en vivo (decisión D9/DU-12) -------------------------------------

    def _alternar_modo_vivo(self, activo: bool) -> None:
        if activo:
            self._espacio.activar_modo_vivo()
        else:
            self._espacio.desactivar_modo_vivo()

    # -- ventana de transmisión (contrato §5.4, decisiones D14/DU-17/V7) ------

    def _alternar_transmision(self, activo: bool) -> None:
        if activo:
            self._mostrar_transmision()
        else:
            self._ocultar_transmision()

    def _mostrar_transmision(self) -> None:
        # Siempre una instancia nueva: una ventana ya cerrada (`_cerrada`,
        # decisión de robustez de `VentanaTransmision.closeEvent`) ignora
        # las señales del puente para siempre — reabrir tiene que ser una
        # ventana nueva, no reactivar la vieja.
        self._ventana_transmision = VentanaTransmision(self._con, self._evento, self._puente)
        tema = TemaDashboard.desde_json(self._evento.tema_json)
        self._ventana_transmision.actualizar_tema(tema)
        self._ventana_transmision.establecer_canal_reclamo(tema.juego.canal_reclamo)

        nombres_disponibles = [pantalla.name() for pantalla in QGuiApplication.screens()]
        prefs = preferencias.cargar()
        decision = elegir_pantalla(nombres_disponibles, prefs.ventana.monitor_transmision)

        self._ventana_transmision.mostrar_en(decision.pantalla, modo_ventana=decision.modo_ventana)
        # Hallazgo V7: se guarda por nombre de QScreen, no por índice — solo
        # cuando de verdad se eligió una pantalla real para pantalla
        # completa, no en el modo ventana de respaldo.
        if not decision.modo_ventana and decision.pantalla is not None:
            prefs.ventana.monitor_transmision = decision.pantalla
            preferencias.guardar(prefs)
        if decision.motivo != "transmision.pantalla.guardada":
            self._franja.mostrar_info(t(decision.motivo))

        # D14: `showFullScreen()` en Windows roba la activación; se devuelve
        # el foco a la ventana principal para que los atajos sigan
        # funcionando sin necesidad de un clic manual.
        ventana_principal = self.window()
        if ventana_principal is not None:
            self._ventana_transmision.restaurar_foco_a(ventana_principal)

    def _ocultar_transmision(self) -> None:
        if self._ventana_transmision is not None:
            self._ventana_transmision.close()

    # -- errores ----------------------------------------------------------------

    def _al_fallar(self, error: ErrorBingo) -> None:
        self._franja.mostrar_error(error)

    def _al_fallar_log(self, detalle: str) -> None:
        self._franja.mostrar(t("sorteo.aviso.log_fallo"), nivel="info")

    def retraducir(self) -> None:
        self._etiqueta_vacio.setText(t("sorteo.vacio.mensaje"))
        self._boton_extraer.setText(t("sorteo.accion.extraer"))
        self._boton_iniciar.setText(t("sorteo.accion.iniciar_ronda"))
        self._boton_cerrar_ronda.setText(t("sorteo.accion.cerrar_ronda"))
        self._campo_codigo.setPlaceholderText(t("sorteo.buscador.placeholder"))
        self._boton_consultar.setText(t("sorteo.accion.consultar"))
        self._boton_registrar_reclamo.setText(t("sorteo.accion.registrar_reclamo"))
        self._boton_modo_vivo.setText(t("sorteo.accion.modo_vivo"))
        self._boton_transmision.setText(t("sorteo.accion.mostrar_transmision"))
        self._grupo_a_una_bola.setTitle(t("sorteo.a_una_bola.titulo_generico"))
        self._grupo_ganadores.setTitle(t("sorteo.ganadores.titulo_generico"))
        if self._ronda_actual is not None:
            self._actualizar_botones_estado(self._ronda_actual.estado)
        else:
            self._etiqueta_ronda.setText(t("sorteo.sin_ronda"))
