"""Ventana pública de transmisión (contrato §5.4). Sin bordes, a pantalla
completa sobre el monitor elegido (decisión D14) — o en una ventana movible
si solo hay una pantalla, o si la elegida ya no existe (decisión DU-17).

**Nunca recibe foco de teclado (decisión DU-5).** Un `Alt+F4` accidental en
directo no puede matarla, y el foco no se escapa de la superficie del
operador. La única tecla que de verdad actúa aquí es `Esc`, y solo porque
Qt entrega el evento aunque la ventana no tenga el foco lógico mientras
`WindowDoesNotAcceptFocus` esté activo — al usuario le basta con que la app
principal tenga el foco y pulse `Esc` para que el operador cierre esta
ventana desde el atajo de la sección Sorteo (`ATAJOS["sorteo.modo_vivo"]`
y afines), no al revés.

**Cierre de la ventana de transmisión no cierra el sorteo; cerrar la
principal sí cierra esta.** Lo segundo lo garantiza `parent=ventana_principal`
al construirla (Qt destruye los hijos con el padre); lo primero es que esta
clase no toca el `MotorSorteo` en absoluto — solo escucha.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeyEvent, QPainter
from PySide6.QtWidgets import QWidget

from bingo.dominio.modelos import Extraccion, Ganador
from bingo.dominio.partida import CartonEnJuego
from bingo.dominio.tema import TemaDashboard
from bingo.persistencia import repo_carton, repo_comprador, repo_extraccion, repo_patron, repo_ronda
from bingo.ui.sorteo.puente_sorteo import PuenteSorteo
from bingo.ui.transmision.bloques import ContextoTransmision, pintar_fotograma
from bingo.ui.transmision.escala import calcular_escala
from bingo.ui.transmision.estado_transmision import EstadoTransmision, MaquinaEstadoTransmision


class VentanaTransmision(QWidget):
    def __init__(
        self, con: Any, evento: Any, puente: PuenteSorteo, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._con = con
        self._evento = evento
        self._puente = puente
        self._maquina = MaquinaEstadoTransmision()
        self._tema = TemaDashboard.desde_json(evento.tema_json)
        self._numero_actual: int | None = None
        self._a_una_bola_cantidad = 0
        self._canal_reclamo = ""
        self._codigo_ganador = ""
        self._nombre_ganador = ""
        # Bandera de cierre (ver `closeEvent`): cada receptor la comprueba
        # antes de tocar nada, en vez de confiar en `disconnect()`.
        self._cerrada = False

        # Decisión DU-5: nunca roba el foco, ni lo acepta.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        puente.bola_extraida.connect(self._al_extraer)
        puente.cartones_a_una_bola.connect(self._al_a_una_bola)
        puente.ganadores_detectados.connect(self._al_detectar_ganadores)
        puente.ganador_confirmado.connect(self._al_confirmar_ganador)
        puente.ronda_cambiada.connect(self._al_cambiar_ronda)

    @property
    def estado(self) -> EstadoTransmision:
        return self._maquina.estado

    def establecer_canal_reclamo(self, canal: str) -> None:
        self._canal_reclamo = canal
        self.update()

    def actualizar_tema(self, tema: TemaDashboard) -> None:
        self._tema = tema
        self.update()

    def reclamo_vencido(self) -> None:
        self._maquina.reclamo_vencido()
        self.update()

    def continuar_tras_reclamo_vencido(self) -> None:
        self._maquina.continuar_tras_reclamo_vencido()
        self.update()

    def finalizar_evento(self) -> None:
        self._maquina.finalizar_evento()
        self.update()

    # -- geometría y monitor (decisiones D14/DU-17) --------------------------

    def mostrar_en(self, nombre_pantalla: str | None, *, modo_ventana: bool) -> None:
        pantalla_elegida = None
        if nombre_pantalla is not None:
            for pantalla in QGuiApplication.screens():
                if pantalla.name() == nombre_pantalla:
                    pantalla_elegida = pantalla
                    break

        if modo_ventana or pantalla_elegida is None:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)
            self.resize(960, 540)
            self.show()
            return

        # `setGeometry()` **antes** de `showFullScreen()`: poner solo
        # `setScreen()` no reubica la ventana en Windows (decisión D14).
        self.setGeometry(pantalla_elegida.geometry())
        self.showFullScreen()

    def restaurar_foco_a(self, ventana_principal: QWidget) -> None:
        ventana_principal.activateWindow()

    # -- teclado --------------------------------------------------------------

    def keyPressEvent(self, evento: QKeyEvent) -> None:  # noqa: N802 - override Qt
        if evento.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(evento)

    def closeEvent(self, evento: QCloseEvent) -> None:  # noqa: N802 - override Qt
        # Cerrar esta ventana no cierra el sorteo: el motor sigue vivo en
        # `EspacioEvento` (hallazgo S5-3) y el puente sigue emitiendo. Una
        # bandera, no `disconnect()` — PySide6 no siempre reconoce el mismo
        # método ligado entre el `connect()` original y un `disconnect()`
        # posterior sobre una señal de tipo Python (`Signal(object)` /
        # `Signal(list)`), y falla en silencio (solo un aviso) dejando la
        # ventana escuchando igual. Cada receptor comprueba `_cerrada` antes
        # de tocar nada.
        self._cerrada = True
        super().closeEvent(evento)

    # -- pintado -----------------------------------------------------------

    def paintEvent(self, _evento: object) -> None:  # noqa: N802 - override Qt
        pintor = QPainter(self)
        try:
            escala = calcular_escala(self.width(), self.height())
            pintor.setTransform(escala.transform)
            pintar_fotograma(pintor, self._construir_contexto())
        finally:
            pintor.end()

    def _construir_contexto(self) -> ContextoTransmision:
        ronda = repo_ronda.obtener_en_juego(self._con, self._evento.id)
        numeros: frozenset[int] = frozenset()
        mascara = None
        nombre_patron = ""
        premio = ""
        if ronda is not None:
            numeros = frozenset(repo_extraccion.numeros_por_ronda(self._con, ronda.id))
            patron = repo_patron.obtener(self._con, ronda.patron_id)
            if patron is not None and patron.mascaras:
                mascara = patron.mascaras[0]
            nombre_patron = ronda.nombre
            premio = ronda.premio_nombre or ""

        return ContextoTransmision(
            tema=self._tema,
            estado=self._maquina.estado,
            idioma=self._tema.idioma_publico,
            numero_actual=self._numero_actual,
            numeros_extraidos=numeros,
            restantes_bombo=75 - len(numeros),
            patron_mascara=mascara,
            nombre_patron=nombre_patron,
            premio_texto=premio,
            canal_reclamo=self._canal_reclamo,
            segundos_restantes_reclamo=self._tema.juego.segundos_reclamo or None,
            a_una_bola_cantidad=self._a_una_bola_cantidad,
            codigo_ganador=self._codigo_ganador,
            nombre_ganador=self._nombre_ganador,
            texto_bienvenida=self._tema.pantalla_bienvenida.texto,
            texto_cierre=self._tema.pantalla_cierre.texto,
        )

    # -- señales del puente ---------------------------------------------------

    def _al_extraer(self, extraccion: Extraccion) -> None:
        if self._cerrada:
            return
        self._numero_actual = extraccion.numero
        self._maquina.bola_extraida()
        self.update()

    def _al_a_una_bola(self, cartones: list[CartonEnJuego]) -> None:
        if self._cerrada:
            return
        self._a_una_bola_cantidad = len(cartones)
        self._maquina.cartones_a_una_bola(len(cartones))
        self.update()

    def _al_detectar_ganadores(self, cartones: list[CartonEnJuego]) -> None:
        if self._cerrada:
            return
        self._maquina.ganadores_detectados()
        self.update()

    def _al_confirmar_ganador(self, ganador: Ganador) -> None:
        if self._cerrada:
            return
        carton = repo_carton.obtener(self._con, ganador.carton_id)
        comprador = repo_comprador.obtener_por_carton(self._con, ganador.carton_id)
        self._codigo_ganador = carton.codigo if carton is not None else ""
        self._nombre_ganador = comprador.nombre if comprador is not None else ""
        self._maquina.ganador_confirmado()
        self.update()

    def _al_cambiar_ronda(self, ronda_id: int, estado: str) -> None:
        if self._cerrada:
            return
        if estado == "en_curso":
            if self._maquina.estado == EstadoTransmision.PAUSA:
                self._maquina.ronda_reanudada()
            else:
                self._maquina.ronda_iniciada()
        elif estado == "pausada":
            self._maquina.ronda_pausada()
        elif estado == "cerrada":
            self._maquina.ronda_cerrada()
        self.update()
