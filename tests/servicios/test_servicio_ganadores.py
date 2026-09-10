import sqlite3

import pytest
from factorias import (
    crear_carton,
    crear_comprador,
    crear_extraccion,
    crear_ganador,
    crear_patron,
    crear_ronda,
)

from bingo.dominio.carton import BIT_LIBRE, carton_desde_orden_canonico, numeros_por_bit
from bingo.dominio.firma import contenido_qr, firmar_codigo, generar_clave_evento
from bingo.dominio.patron import mascara
from bingo.persistencia import repo_evento, repo_ganador
from bingo.servicios import servicio_ganadores
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorValidacion


@pytest.fixture
def escenario(con: sqlite3.Connection, evento_creado, lote_creado):
    """Patrón trivial (fila 0, columna 0), como en `test_servicio_sorteo.py`:
    determinista sin depender de completar un patrón real."""
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2, estado="vendido")
    crear_comprador(con, c1.id)
    crear_comprador(con, c2.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    return ronda, c1, c2


def _numero_de_la_esquina(carton) -> int:
    npb = numeros_por_bit(carton_desde_orden_canonico(carton.numeros))
    return next(numero for numero, bit in npb.items() if bit == 0)


def test_validar_reclamo_codigo_inexistente(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, "NO-EXISTE")
    assert reclamo.motivo_rechazo == "ganador.error.codigo_inexistente"
    assert reclamo.carton is None


def test_validar_reclamo_no_vendido(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=9)  # sin vendido
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, carton.codigo)
    assert reclamo.motivo_rechazo == "ganador.error.no_vendido"
    assert reclamo.carton is not None


def test_validar_reclamo_sin_comprador(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(
        con, evento_creado.id, lote_creado.id, semilla=9, estado="vendido"
    )  # vendido pero sin fila de comprador
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, carton.codigo)
    assert reclamo.motivo_rechazo == "ganador.error.sin_comprador"


def test_validar_reclamo_patron_no_cumplido_sin_bolas(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, _ = escenario
    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, c1.codigo)
    assert reclamo.cumple is False
    assert reclamo.motivo_rechazo == "ganador.error.patron_no_cumplido"
    assert reclamo.marcado == 1 << BIT_LIBRE


def test_validar_reclamo_cumple_tras_extraer_la_bola(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, _ = escenario
    numero_ganador = _numero_de_la_esquina(c1)
    crear_extraccion(con, ronda.id, orden=1, numero=numero_ganador)

    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, c1.codigo)
    assert reclamo.cumple is True
    assert reclamo.motivo_rechazo is None
    assert reclamo.comprador is not None


def test_validar_reclamo_por_qr_valido(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, _ = escenario
    clave = generar_clave_evento()
    repo_evento.actualizar_clave(con, ronda.evento_id, clave)
    qr = contenido_qr(clave, c1.codigo)

    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, qr)
    assert reclamo.carton is not None
    assert reclamo.carton.id == c1.id


def test_validar_reclamo_por_qr_de_otro_evento_rechaza_duro(
    con: sqlite3.Connection, escenario
) -> None:
    """Hallazgo S1, alto: con `|` en el texto, una firma inválida es rechazo
    duro — nunca cae a tratarlo como código tecleado."""
    ronda, c1, _ = escenario
    repo_evento.actualizar_clave(con, ronda.evento_id, generar_clave_evento())
    qr_de_otra_clave = f"{c1.codigo}|{firmar_codigo(generar_clave_evento(), c1.codigo)}"

    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, qr_de_otra_clave)
    assert reclamo.motivo_rechazo == "ganador.error.qr_invalido"
    assert reclamo.carton is None


def test_validar_reclamo_sin_clave_de_evento_y_con_pipe_rechaza(
    con: sqlite3.Connection, escenario
) -> None:
    ronda, c1, _ = escenario
    # El evento nunca generó clave_evento (nunca se imprimió un QR real).
    reclamo = servicio_ganadores.validar_reclamo(con, ronda.id, f"{c1.codigo}|00000000")
    assert reclamo.motivo_rechazo == "ganador.error.qr_invalido"


def test_confirmar_decision_invalida_falla(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, _ = escenario
    ganador = crear_ganador(con, ronda.id, c1.id, bola_numero=1)
    with pytest.raises(ErrorValidacion):
        servicio_ganadores.confirmar(con, ganador.id, "no_es_una_decision")


def test_confirmar_inexistente_falla(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_ganadores.confirmar(con, 999, "unico")


@pytest.mark.parametrize(
    ("decision", "reparte_premio"),
    [
        ("unico", True),
        ("reparto", True),
        ("desempate_externo", True),
        ("no_reclamado", False),
        ("rechazado", False),
    ],
)
def test_confirmar_cada_decision(
    con: sqlite3.Connection, escenario, decision: str, reparte_premio: bool
) -> None:
    ronda, c1, _ = escenario
    ganador = crear_ganador(con, ronda.id, c1.id, bola_numero=1)
    servicio_ganadores.confirmar(con, ganador.id, decision, nota="detalle")

    recargado = repo_ganador.obtener(con, ganador.id)
    assert recargado.confirmado is True
    assert recargado.decision == decision
    assert recargado.reparte_premio is reparte_premio
    assert recargado.confirmado_en is not None
    assert recargado.nota == "detalle"


def test_confirmar_registra_en_auditoria(con: sqlite3.Connection, escenario) -> None:
    from bingo.persistencia import repo_auditoria

    ronda, c1, _ = escenario
    ganador = crear_ganador(con, ronda.id, c1.id, bola_numero=1)
    servicio_ganadores.confirmar(con, ganador.id, "unico")

    registros = repo_auditoria.listar_por_evento(con, ronda.evento_id)
    assert any(r.accion == "ganador.confirmado" for r in registros)


def test_resolver_empate_reparto_entre_varios(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, c2 = escenario
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    g2 = crear_ganador(con, ronda.id, c2.id, bola_numero=10)

    servicio_ganadores.resolver_empate(con, ronda.id, ids_reparto=[g1.id, g2.id])

    filas = {g.id: g for g in repo_ganador.listar_por_ronda(con, ronda.id)}
    assert filas[g1.id].decision == "reparto"
    assert filas[g1.id].reparte_premio is True
    assert filas[g2.id].decision == "reparto"


def test_resolver_empate_uno_solo_rechaza_a_los_demas(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, c2 = escenario
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    g2 = crear_ganador(con, ronda.id, c2.id, bola_numero=10)

    servicio_ganadores.resolver_empate(con, ronda.id, id_unico=g1.id)

    filas = {g.id: g for g in repo_ganador.listar_por_ronda(con, ronda.id)}
    assert filas[g1.id].decision == "unico"
    assert filas[g1.id].reparte_premio is True
    assert filas[g2.id].decision == "rechazado"
    assert filas[g2.id].reparte_premio is False


def test_resolver_empate_bolas_distintas_exige_confirmacion(
    con: sqlite3.Connection, escenario
) -> None:
    """Defensa (V2): en el flujo normal nunca hay dos bolas distintas en
    `ganador` para la misma ronda (D8), pero si aparecieran, repartir entre
    ellas exige `permitir_bolas_distintas=True`."""
    ronda, c1, c2 = escenario
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    g2 = crear_ganador(con, ronda.id, c2.id, bola_numero=20)

    with pytest.raises(ErrorValidacion):
        servicio_ganadores.resolver_empate(con, ronda.id, ids_reparto=[g1.id, g2.id])

    servicio_ganadores.resolver_empate(
        con, ronda.id, ids_reparto=[g1.id, g2.id], permitir_bolas_distintas=True
    )
    assert repo_ganador.obtener(con, g1.id).decision == "reparto"


def test_resolver_empate_sin_detectados_falla(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    with pytest.raises(ErrorValidacion):
        servicio_ganadores.resolver_empate(con, ronda.id, id_unico=1)


def test_resolver_empate_ambos_argumentos_falla(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, _ = escenario
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    with pytest.raises(ErrorValidacion):
        servicio_ganadores.resolver_empate(con, ronda.id, ids_reparto=[g1.id], id_unico=g1.id)


def test_resolver_empate_no_deja_ninguno_en_limbo(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, c2 = escenario
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    crear_ganador(con, ronda.id, c2.id, bola_numero=10)

    servicio_ganadores.resolver_empate(con, ronda.id, id_unico=g1.id)

    for fila in repo_ganador.listar_por_ronda(con, ronda.id):
        assert fila.decision is not None
        assert fila.confirmado is True
