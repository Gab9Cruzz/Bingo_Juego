from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda
from PySide6.QtCore import QObject, Signal

from bingo import i18n
from bingo.dominio.patron import mascara
from bingo.persistencia import repo_carton, repo_evento, repo_ganador, repo_ronda
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.ui.sorteo import vista_sorteo as modulo_vista
from bingo.ui.sorteo.vista_sorteo import VistaSorteo


class _RngSecuencial:
    """Mismo convenio que `tests/servicios/test_servicio_sorteo.py`: elige
    siempre el primero de los restantes, así las bolas salen 1, 2, 3... —
    determinista y fácil de razonar en las pruebas."""

    def choice(self, secuencia: Sequence[int]) -> int:
        return secuencia[0]


class _EspacioEventoFalso:
    """Doble de prueba: solo lo que `VistaSorteo` de verdad necesita del
    `EspacioEvento` real (hallazgo S5-3 — el motor vive ahí, no en la
    vista)."""

    def __init__(self) -> None:
        self.motor_sorteo = MotorSorteo(rng=_RngSecuencial())
        self.modo_vivo = False
        self.activadas = 0
        self.desactivadas = 0

    def activar_modo_vivo(self) -> None:
        self.modo_vivo = True
        self.activadas += 1

    def desactivar_modo_vivo(self) -> None:
        self.modo_vivo = False
        self.desactivadas += 1

    def hay_ronda_viva(self) -> bool:
        # Aproximación suficiente para esta prueba: el `EspacioEvento` real
        # mira la base (`en_curso` o `pausada`, decisión DU-11); aquí no hay
        # base propia que consultar, así que se delega en lo que el motor
        # de sorteo ya sabe en memoria (tarea 4.13, bloqueo de respaldo).
        return self.motor_sorteo.hay_ronda_en_juego


def _numero_de_la_esquina(carton) -> int:
    from bingo.dominio.carton import carton_desde_orden_canonico, numeros_por_bit

    npb = numeros_por_bit(carton_desde_orden_canonico(carton.numeros))
    return next(numero for numero, bit in npb.items() if bit == 0)


def test_vista_vacia_sin_rondas(qapp, con: sqlite3.Connection, evento_creado) -> None:
    i18n.cargar("es")
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert not vista._etiqueta_vacio.isHidden()  # noqa: SLF001
    assert not vista._boton_extraer.isEnabled()  # noqa: SLF001


def test_iniciar_ronda_habilita_extraer(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert vista._etiqueta_vacio.isHidden()  # noqa: SLF001

    vista._iniciar_ronda()  # noqa: SLF001

    assert vista._boton_extraer.isEnabled()  # noqa: SLF001
    assert vista._ronda_actual.estado == "en_curso"  # noqa: SLF001


def test_extraer_actualiza_numero_y_tablero(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001

    vista._al_pulsar_extraer()  # noqa: SLF001

    assert vista._etiqueta_numero.text() != "—"  # noqa: SLF001
    assert len(vista._tablero.marcadas()) == 1  # noqa: SLF001


def test_ganador_detectado_confirma_solo_al_registrar_reclamo(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """Detectar no confirma (D8): el panel de ganadores se llena, pero
    `ganador.decision` sigue `None` hasta que el operador registra el
    reclamo desde el buscador."""
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    numero_ganador = _numero_de_la_esquina(carton)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    assert not vista._grupo_ganadores.isHidden()  # noqa: SLF001
    fila = repo_ganador.listar_por_ronda(con, ronda.id)[0]
    assert fila.decision is None

    vista._campo_codigo.setText(carton.codigo)  # noqa: SLF001
    vista._validar_reclamo(registrar=True)  # noqa: SLF001

    recargado = repo_ganador.obtener(con, fila.id)
    assert recargado.decision == "unico"


def test_buscador_consultar_no_registra_nada(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    numero_ganador = _numero_de_la_esquina(carton)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    vista._campo_codigo.setText(carton.codigo)  # noqa: SLF001
    vista._validar_reclamo(registrar=False)  # noqa: SLF001

    assert repo_ganador.listar_por_ronda(con, ronda.id)[0].decision is None


def test_cerrar_ronda_sin_pedir_confirmacion_si_no_hay_bombo(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """Con el bombo agotado no debe pedir confirmación (solo cuando quedan
    bolas y nadie ganó, hallazgo C7)."""
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(75):
        vista._al_pulsar_extraer()  # noqa: SLF001

    vista._cerrar_ronda()  # noqa: SLF001

    assert repo_ronda.obtener(con, ronda.id).estado == "cerrada"


def test_boton_transmision_crea_y_cierra_la_ventana(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    vista._boton_transmision.setChecked(True)  # noqa: SLF001
    assert vista._ventana_transmision is not None  # noqa: SLF001

    vista._boton_transmision.setChecked(False)  # noqa: SLF001
    assert vista._ventana_transmision._cerrada  # noqa: SLF001


def test_selector_lista_todas_las_rondas_del_evento(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id, orden=1, nombre="R1")
    crear_ronda(con, evento_creado.id, patron.id, orden=2, nombre="R2")
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    assert vista._selector_ronda.count() == 2  # noqa: SLF001


def test_cerrar_ronda_avanza_al_siguiente_pendiente(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado, monkeypatch
) -> None:
    """Sin esto no habría manera de llegar a la ronda 2 tras cerrar la 1."""
    i18n.cargar("es")
    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", lambda *a, **k: True)
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    r1 = crear_ronda(con, evento_creado.id, patron.id, orden=1, nombre="R1")
    r2 = crear_ronda(con, evento_creado.id, patron.id, orden=2, nombre="R2")

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._cargar_lista_rondas(seleccionar_id=r1.id)  # noqa: SLF001
    vista._iniciar_ronda()  # noqa: SLF001
    vista._cerrar_ronda()  # noqa: SLF001

    assert vista._ronda_actual.id == r2.id  # noqa: SLF001


def test_boton_reabrir_visible_solo_en_ronda_cerrada(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado, monkeypatch
) -> None:
    i18n.cargar("es")
    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", lambda *a, **k: True)
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert vista._boton_reabrir_ronda.isHidden()  # noqa: SLF001

    vista._iniciar_ronda()  # noqa: SLF001
    vista._cerrar_ronda()  # noqa: SLF001

    assert not vista._boton_reabrir_ronda.isHidden()  # noqa: SLF001
    assert vista._boton_reabrir_ronda.isEnabled()  # noqa: SLF001
    assert repo_ronda.obtener(con, ronda.id).estado == "cerrada"


def test_reabrir_ronda_reconstruye_el_motor_y_conserva_marcado(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado, monkeypatch
) -> None:
    i18n.cargar("es")
    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", lambda *a, **k: True)
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    vista._al_pulsar_extraer()  # noqa: SLF001
    vista._cerrar_ronda()  # noqa: SLF001
    assert not vista._motor.hay_ronda_en_juego  # noqa: SLF001

    vista._reabrir_ronda()  # noqa: SLF001

    assert repo_ronda.obtener(con, ronda.id).estado == "en_curso"
    assert vista._motor.hay_ronda_en_juego  # noqa: SLF001
    assert vista._boton_extraer.isEnabled()  # noqa: SLF001


def test_generar_y_verificar_acta(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado, monkeypatch
) -> None:
    i18n.cargar("es")
    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", lambda *a, **k: True)
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    vista._cerrar_ronda()  # noqa: SLF001

    assert not vista._boton_generar_acta.isHidden()  # noqa: SLF001
    vista._generar_acta()  # noqa: SLF001

    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.acta_hash is not None

    vista._verificar_acta()  # noqa: SLF001  # no debe lanzar


def test_modo_vivo_delega_en_espacio_evento(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    vista._boton_modo_vivo.setChecked(True)  # noqa: SLF001
    assert espacio.activadas == 1

    vista._boton_modo_vivo.setChecked(False)  # noqa: SLF001
    assert espacio.desactivadas == 1


# ── Cierre del evento (tarea 4.13) ──────────────────────────────────────────


def test_boton_finalizar_evento_solo_habilitado_con_todas_cerradas(
    qapp, con: sqlite3.Connection, evento_creado
) -> None:
    i18n.cargar("es")
    repo_evento.actualizar_estado(con, evento_creado.id, "en_curso")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    ronda_1 = crear_ronda(con, evento_creado.id, patron.id, nombre="Ronda 1", orden=1)
    crear_ronda(con, evento_creado.id, patron.id, nombre="Ronda 2", orden=2)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert not vista._boton_finalizar_evento.isEnabled()  # noqa: SLF001

    repo_ronda.actualizar_estado(con, ronda_1.id, "cerrada")
    vista._cargar_lista_rondas()  # noqa: SLF001
    assert not vista._boton_finalizar_evento.isEnabled()  # noqa: SLF001 — falta la 2


def test_finalizar_evento_llama_al_servicio_y_oculta_el_boton(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    i18n.cargar("es")
    repo_evento.actualizar_estado(con, evento_creado.id, "en_curso")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    crear_ronda(con, evento_creado.id, patron.id, estado="cerrada")

    # Confirma SOLO el primer diálogo (finalizar) — los siguientes (ofrecer
    # reporte, ofrecer respaldo) se rechazan para no disparar un
    # `QFileDialog` ni una `Tarea` real desde esta prueba.
    llamadas = {"n": 0}

    def _confirmar_fake(*_a: object, **_k: object) -> bool:
        llamadas["n"] += 1
        return llamadas["n"] == 1

    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", _confirmar_fake)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert vista._boton_finalizar_evento.isEnabled()  # noqa: SLF001

    vista._finalizar_evento()  # noqa: SLF001

    assert repo_evento.obtener(con, evento_creado.id).estado == "finalizado"
    assert vista._evento.estado == "finalizado"  # noqa: SLF001
    assert vista._boton_finalizar_evento.isHidden()  # noqa: SLF001
    assert llamadas["n"] == 3  # finalizar + ofrecer reporte + ofrecer respaldo


def test_finalizar_evento_con_rondas_sin_cerrar_muestra_error(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    """El botón ya lo impide, pero el servicio es la fuente de verdad
    (hallazgo defensivo: nada garantiza que `_actualizar_boton_finalizar_evento`
    corra antes de un clic en cola)."""
    i18n.cargar("es")
    repo_evento.actualizar_estado(con, evento_creado.id, "en_curso")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    crear_ronda(con, evento_creado.id, patron.id)  # pendiente, nunca cerrada

    monkeypatch.setattr("bingo.ui.sorteo.vista_sorteo.confirmar", lambda *a, **k: True)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    vista._finalizar_evento()  # noqa: SLF001

    assert repo_evento.obtener(con, evento_creado.id).estado == "en_curso"
    assert not vista._franja.isHidden()  # noqa: SLF001


# ── Respaldo manual (tarea 4.12/4.13) ───────────────────────────────────────


class _TareaFalsa(QObject):
    """Mismo convenio que `tests/ui/test_vista_cartones.py::_TareaFalsa`:
    mismas señales que `ui/tarea.py::Tarea`, sin `QThread` real — la prueba
    controla a mano cuándo "termina"."""

    progreso = Signal(int, int)
    terminado = Signal(object)
    fallado = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.iniciada = False
        self.cancelada = False

    def start(self) -> None:
        self.iniciada = True

    def cancelar(self) -> None:
        self.cancelada = True


def test_boton_respaldo_deshabilitado_con_ronda_viva(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    crear_ronda(con, evento_creado.id, patron.id)

    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)
    assert vista._boton_respaldo.isEnabled()  # noqa: SLF001

    vista._iniciar_ronda()  # noqa: SLF001

    assert not vista._boton_respaldo.isEnabled()  # noqa: SLF001


def test_generar_respaldo_exitoso_rehabilita_el_boton_y_avisa(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._generar_respaldo()  # noqa: SLF001

    assert tarea.iniciada
    assert not vista._boton_respaldo.isEnabled()  # noqa: SLF001

    tarea.terminado.emit(Path("respaldo-evento.zip"))

    assert vista._boton_respaldo.isEnabled()  # noqa: SLF001
    assert "respaldo-evento.zip" in vista._franja._etiqueta.text()  # noqa: SLF001


def test_generar_respaldo_cancelado_muestra_aviso_sin_ruta(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    """`servicio_respaldos.exportar` devuelve `None` cuando se cancela a
    mitad — sin dejar ningún `.zip` parcial (decisión del propio servicio)."""
    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._generar_respaldo()  # noqa: SLF001

    tarea.terminado.emit(None)

    assert vista._boton_respaldo.isEnabled()  # noqa: SLF001
    assert vista._franja._etiqueta.text() == "Respaldo cancelado"  # noqa: SLF001


def test_generar_respaldo_fallado_muestra_error_y_rehabilita(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    from bingo.utilidades.errores import ErrorValidacion

    i18n.cargar("es")
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento_creado, espacio)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._generar_respaldo()  # noqa: SLF001

    tarea.fallado.emit(ErrorValidacion("respaldo.error.ronda_en_curso"))

    assert vista._boton_respaldo.isEnabled()  # noqa: SLF001
    assert not vista._franja.isHidden()  # noqa: SLF001


# ── Cuenta regresiva de reclamo (tarea 4.24, alcance §6.2) ──────────────────


def _preparar_ronda_con_ganador(con, evento, lote, *, tema=None):
    from bingo.dominio.modelos import Evento

    if tema is not None:
        repo_evento.actualizar_tema(con, evento.id, tema.a_json())
        evento = repo_evento.obtener(con, evento.id)
        assert isinstance(evento, Evento)
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento.id, lote.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento.id, patron.id)
    numero_ganador = _numero_de_la_esquina(carton)
    return evento, ronda, numero_ganador


def test_detectar_ganador_inicia_la_cuenta_regresiva(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """El tema por defecto trae `segundos_reclamo=60` (decisión de la tarea
    4.24)."""
    i18n.cargar("es")
    evento, _ronda, numero_ganador = _preparar_ronda_con_ganador(con, evento_creado, lote_creado)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento, espacio)
    vista._iniciar_ronda()  # noqa: SLF001

    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    assert vista._temporizador_reclamo.isActive()  # noqa: SLF001
    assert vista._segundos_restantes_reclamo == 60  # noqa: SLF001
    assert not vista._etiqueta_cuenta_reclamo.isHidden()  # noqa: SLF001


def test_segundos_reclamo_cero_no_arranca_temporizador(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    from bingo.dominio.tema import ConfigJuego, TemaDashboard

    i18n.cargar("es")
    tema = TemaDashboard(juego=ConfigJuego(segundos_reclamo=0))
    evento, _ronda, numero_ganador = _preparar_ronda_con_ganador(
        con, evento_creado, lote_creado, tema=tema
    )
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento, espacio)
    vista._iniciar_ronda()  # noqa: SLF001

    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    assert not vista._temporizador_reclamo.isActive()  # noqa: SLF001
    assert vista._etiqueta_cuenta_reclamo.isHidden()  # noqa: SLF001


def test_registrar_reclamo_detiene_la_cuenta_regresiva(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    evento, _ronda, numero_ganador = _preparar_ronda_con_ganador(con, evento_creado, lote_creado)
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001
    assert vista._temporizador_reclamo.isActive()  # noqa: SLF001

    carton = repo_carton.obtener(
        con, repo_ganador.listar_por_ronda(con, vista._ronda_actual.id)[0].carton_id
    )  # noqa: SLF001
    vista._campo_codigo.setText(carton.codigo)  # noqa: SLF001
    vista._validar_reclamo(registrar=True)  # noqa: SLF001

    assert not vista._temporizador_reclamo.isActive()  # noqa: SLF001
    assert vista._segundos_restantes_reclamo is None  # noqa: SLF001


def test_tick_agota_cuenta_y_avisa_reclamo_vencido_sin_cerrar(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    from bingo.dominio.tema import ConfigJuego, TemaDashboard

    i18n.cargar("es")
    tema = TemaDashboard(juego=ConfigJuego(segundos_reclamo=2, sin_reclamo="continuar"))
    evento, ronda, numero_ganador = _preparar_ronda_con_ganador(
        con, evento_creado, lote_creado, tema=tema
    )
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    vista._tick_reclamo()  # noqa: SLF001 — 2 -> 1
    assert vista._temporizador_reclamo.isActive()  # noqa: SLF001
    vista._tick_reclamo()  # noqa: SLF001 — 1 -> 0, agota

    assert not vista._temporizador_reclamo.isActive()  # noqa: SLF001
    assert repo_ronda.obtener(con, ronda.id).estado == "en_curso"  # no se cerró sola
    assert vista._etiqueta_cuenta_reclamo.isHidden()  # noqa: SLF001


def test_agotar_cuenta_con_sin_reclamo_cerrar_cierra_la_ronda_sola(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """Sin operador delante de la cuenta atrás, `sin_reclamo="cerrar"`
    cierra directo — nunca pide la confirmación de `_cerrar_ronda()` (el
    botón manual), que se quedaría esperando un clic que puede no llegar."""
    from bingo.dominio.tema import ConfigJuego, TemaDashboard

    i18n.cargar("es")
    tema = TemaDashboard(juego=ConfigJuego(segundos_reclamo=1, sin_reclamo="cerrar"))
    evento, ronda, numero_ganador = _preparar_ronda_con_ganador(
        con, evento_creado, lote_creado, tema=tema
    )
    espacio = _EspacioEventoFalso()
    vista = VistaSorteo(con, evento, espacio)
    vista._iniciar_ronda()  # noqa: SLF001
    for _ in range(numero_ganador):
        vista._al_pulsar_extraer()  # noqa: SLF001

    vista._tick_reclamo()  # noqa: SLF001 — 1 -> 0, agota y cierra

    assert repo_ronda.obtener(con, ronda.id).estado == "cerrada"
