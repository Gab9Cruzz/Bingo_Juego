from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda

from bingo import i18n
from bingo.dominio.patron import mascara
from bingo.persistencia import repo_ganador, repo_ronda
from bingo.servicios.servicio_sorteo import MotorSorteo
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
