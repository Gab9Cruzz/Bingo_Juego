import sqlite3
import time
from collections.abc import Sequence
from random import Random

import pytest
from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda

from bingo.dominio.carton import (
    carton_desde_orden_canonico,
    firma,
    generar_carton,
    numeros_por_bit,
    orden_canonico,
)
from bingo.dominio.modelos import Carton, Comprador
from bingo.dominio.patron import mascara
from bingo.persistencia import (
    repo_carton,
    repo_comprador,
    repo_extraccion,
    repo_ganador,
    repo_ronda,
)
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.utilidades.errores import (
    ErrorBaseBloqueada,
    ErrorNoEncontrado,
    ErrorReanudacion,
    ErrorTransicionInvalida,
    ErrorValidacion,
)

_BIT_ESQUINA = 0  # fila 0, columna 0


class _RngSecuencial:
    """Elige siempre el primero de los restantes: con un `Bombo` recién
    creado esto hace que las bolas salgan en orden 1, 2, 3... — determinista
    y fácil de razonar en las pruebas, sin necesitar un `random.Random` real."""

    def choice(self, secuencia: Sequence[int]) -> int:
        return secuencia[0]


def _numero_de_la_esquina(carton) -> int:
    matriz = carton_desde_orden_canonico(carton.numeros)
    npb = numeros_por_bit(matriz)
    return next(numero for numero, bit in npb.items() if bit == _BIT_ESQUINA)


@pytest.fixture
def escenario(con: sqlite3.Connection, evento_creado, lote_creado):
    """Patrón trivial de una sola celda (fila 0, columna 0): el cartón `c1`
    gana en la bola exacta que ocupa esa esquina de su cartón — determinista
    con `_RngSecuencial`, sin depender de completar un patrón real."""
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2, estado="vendido")
    crear_comprador(con, c1.id)
    crear_comprador(con, c2.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    return ronda, c1, c2


def test_iniciar_ronda_transiciona_y_dispara_callback(con: sqlite3.Connection, escenario) -> None:
    ronda, c1, c2 = escenario
    cambios: list[tuple[int, str]] = []
    motor = MotorSorteo(rng=_RngSecuencial(), al_cambiar_ronda=lambda r, e: cambios.append((r, e)))
    motor.iniciar_ronda(con, ronda.id)

    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.estado == "en_curso"
    assert recargada.iniciada_en is not None
    assert cambios == [(ronda.id, "en_curso")]
    assert motor.hay_ronda_en_juego
    assert {c.carton_id for c in motor.cartones} == {c1.id, c2.id}


def test_iniciar_ronda_sin_cartones_elegibles_falla(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    motor = MotorSorteo(rng=_RngSecuencial())
    with pytest.raises(ErrorValidacion):
        motor.iniciar_ronda(con, ronda.id)


def test_iniciar_ronda_inexistente_falla(con: sqlite3.Connection) -> None:
    motor = MotorSorteo(rng=_RngSecuencial())
    with pytest.raises(ErrorNoEncontrado):
        motor.iniciar_ronda(con, 999)


def test_iniciar_ronda_ya_en_curso_falla(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    with pytest.raises(ErrorTransicionInvalida):
        motor.iniciar_ronda(con, ronda.id)


def test_extraer_persiste_y_dispara_al_extraer(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    extraidas = []
    motor = MotorSorteo(rng=_RngSecuencial(), al_extraer=extraidas.append)
    motor.iniciar_ronda(con, ronda.id)

    creada = motor.extraer(con)

    assert creada.numero == 1
    assert creada.orden == 1
    assert extraidas == [creada]
    assert repo_extraccion.numeros_por_ronda(con, ronda.id) == [1]
    assert motor.bombo.restantes == 74
    assert motor.bombo.extraidas == [1]


def test_extraer_setenta_y_cinco_veces_agota_el_bombo(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(75):
        motor.extraer(con)
    assert motor.bombo.agotado
    assert repo_extraccion.numeros_por_ronda(con, ronda.id) == list(range(1, 76))


def test_pausar_y_reanudar_en_memoria(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    cambios: list[tuple[int, str]] = []
    motor = MotorSorteo(rng=_RngSecuencial(), al_cambiar_ronda=lambda r, e: cambios.append((r, e)))
    motor.iniciar_ronda(con, ronda.id)
    motor.extraer(con)

    motor.pausar(con, ronda.id)
    assert repo_ronda.obtener(con, ronda.id).estado == "pausada"

    motor.reanudar(con, ronda.id)
    assert repo_ronda.obtener(con, ronda.id).estado == "en_curso"
    assert cambios[-2:] == [(ronda.id, "pausada"), (ronda.id, "en_curso")]
    # el bombo sigue vivo en memoria: no se perdió nada al pausar
    assert motor.bombo.extraidas == [1]


def test_cerrar_ronda_transiciona_y_libera_el_motor(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    motor.extraer(con)

    motor.cerrar_ronda(con, ronda.id)

    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.estado == "cerrada"
    assert recargada.cerrada_en is not None
    assert not motor.hay_ronda_en_juego


def test_reabrir_ronda_cerrada_es_valido_segun_transiciones_ronda(
    con: sqlite3.Connection, escenario
) -> None:
    """Hallazgo V5: `cerrada -> en_curso` existe. El motor no impone la
    reapertura por sí mismo (eso orquesta `servicio_actas`/la vista con la
    confirmación explícita), pero `cerrar_ronda` deja la fila en un estado
    desde el que `TRANSICIONES_RONDA` permite reabrir."""
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    motor.cerrar_ronda(con, ronda.id)

    repo_ronda.actualizar_cierre(con, ronda.id, estado="en_curso", cerrada_en=None)
    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.estado == "en_curso"
    assert recargada.cerrada_en is None


def test_iniciar_ronda_no_reabre_una_cerrada(con: sqlite3.Connection, escenario) -> None:
    """`iniciar_ronda` es solo el primer arranque: reabrir pasa por
    `reanudar_ronda`, que sí reproduce la historia de extracciones. Si
    `iniciar_ronda` aceptara una ronda `cerrada`, olvidaría en memoria las
    marcas ya hechas."""
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    motor.extraer(con)
    motor.cerrar_ronda(con, ronda.id)

    motor_nuevo = MotorSorteo(rng=_RngSecuencial())
    with pytest.raises(ErrorTransicionInvalida):
        motor_nuevo.iniciar_ronda(con, ronda.id)


def test_ganador_se_detecta_solo_en_su_bola_y_no_de_nuevo(
    con: sqlite3.Connection, escenario
) -> None:
    ronda, c1, c2 = escenario
    numero_ganador = _numero_de_la_esquina(c1)
    detectados: list[list] = []
    motor = MotorSorteo(rng=_RngSecuencial(), al_detectar_ganadores=detectados.append)
    motor.iniciar_ronda(con, ronda.id)

    for _ in range(numero_ganador):
        motor.extraer(con)

    assert len(detectados) == 1
    assert {c.carton_id for c in detectados[0]} == {c1.id}

    filas = repo_ganador.listar_por_ronda(con, ronda.id)
    assert len(filas) == 1
    assert filas[0].carton_id == c1.id
    assert filas[0].bola_numero == numero_ganador
    assert filas[0].confirmado is False
    assert filas[0].decision is None

    # Sigue extrayendo ("continuar", D8) pero no vuelve a notificar ni a
    # persistir nada más, aunque queden bolas por salir.
    restantes = 75 - numero_ganador
    for _ in range(restantes):
        motor.extraer(con)
    assert len(detectados) == 1
    assert len(repo_ganador.listar_por_ronda(con, ronda.id)) == 1


def test_cartones_no_elegibles_nunca_aparecen_como_ganadores(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    c_sin_comprador = crear_carton(
        con, evento_creado.id, lote_creado.id, semilla=3, estado="vendido"
    )
    c_no_vendido = crear_carton(con, evento_creado.id, lote_creado.id, semilla=4)
    crear_comprador(con, c1.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    assert {c.carton_id for c in motor.cartones} == {c1.id}
    for _ in range(75):
        motor.extraer(con)

    ids_ganadores = {g.carton_id for g in repo_ganador.listar_por_ronda(con, ronda.id)}
    assert c_sin_comprador.id not in ids_ganadores
    assert c_no_vendido.id not in ids_ganadores


def test_bombo_no_muta_si_la_transaccion_falla(
    con: sqlite3.Connection, escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hallazgo B1, crítico: si `repo_extraccion.crear` falla dentro de la
    transacción, `Bombo.confirmar()` nunca se llama — `restantes` no se
    mueve, y la bola no desaparece del juego en silencio."""
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)

    def falla(*args: object, **kwargs: object):
        raise ErrorBaseBloqueada("error.base_bloqueada", detalle="ocupado (simulado)")

    monkeypatch.setattr(repo_extraccion, "crear", falla)
    with pytest.raises(ErrorBaseBloqueada):
        motor.extraer(con)

    assert motor.bombo.restantes == 75
    assert motor.bombo.extraidas == []
    assert repo_extraccion.numeros_por_ronda(con, ronda.id) == []


@pytest.mark.parametrize("n", [1, 15, 40, 74])
def test_reanudacion_interrumpida_en_la_bola_n(con: sqlite3.Connection, escenario, n: int) -> None:
    """Sorteo completo de 75 bolas simulando una interrupción en la bola N:
    tras "reanudar" (recargar desde la base con un motor nuevo), `extraccion`
    tiene exactamente N filas y el `marcado` de cada cartón coincide con el
    de antes de morir el proceso."""
    ronda, c1, c2 = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(n):
        motor.extraer(con)

    marcado_antes = {c.carton_id: c.marcado for c in motor.cartones}
    assert repo_extraccion.numeros_por_ronda(con, ronda.id) == list(range(1, n + 1))

    # "matar el proceso": un motor nuevo, sin nada en memoria.
    motor_nuevo = MotorSorteo(rng=_RngSecuencial())
    resultado = motor_nuevo.reanudar_ronda(con, ronda.id)

    assert resultado.coherente
    marcado_despues = {c.carton_id: c.marcado for c in motor_nuevo.cartones}
    assert marcado_despues == marcado_antes
    assert motor_nuevo.bombo.extraidas == list(range(1, n + 1))
    assert motor_nuevo.bombo.restantes == 75 - n


def test_reanudar_ronda_pendiente_falla(con: sqlite3.Connection, escenario) -> None:
    ronda, *_ = escenario
    motor = MotorSorteo(rng=_RngSecuencial())
    with pytest.raises(ErrorValidacion):
        motor.reanudar_ronda(con, ronda.id)


def test_anular_ganador_y_reanudar_no_declara_incoherencia_ni_reaparece(
    con: sqlite3.Connection, escenario
) -> None:
    """Pruebas obligatorias de la decisión D13 (hallazgos V1/C2/C3): anular
    un ganador, "matar el proceso", reanudar, y verificar que no reaparece y
    que la reanudación no se declara incoherente."""
    ronda, c1, c2 = escenario
    numero_ganador = _numero_de_la_esquina(c1)
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(numero_ganador):
        motor.extraer(con)

    ganador = repo_ganador.listar_por_ronda(con, ronda.id)[0]
    repo_ganador.anular(con, ganador.id, "2026-01-01T00:00:00Z")

    detectados_tras_reanudar: list[list] = []
    motor_nuevo = MotorSorteo(
        rng=_RngSecuencial(), al_detectar_ganadores=detectados_tras_reanudar.append
    )
    resultado = motor_nuevo.reanudar_ronda(con, ronda.id)

    assert resultado.coherente
    assert c1.id not in resultado.detectados
    assert c1.id in resultado.persistidos  # sigue estando, solo que anulado

    for _ in range(75 - numero_ganador):
        motor_nuevo.extraer(con)

    assert detectados_tras_reanudar == []
    ganador_recargado = repo_ganador.obtener(con, ganador.id)
    assert ganador_recargado.anulado_en is not None
    assert len(repo_ganador.listar_por_ronda(con, ronda.id)) == 1  # no reapareció ni se duplicó


def test_reanudacion_incoherente_lanza_y_forzar_la_adopta(
    con: sqlite3.Connection, escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Una incoherencia real (no explicada por anulación/rechazo) es un
    modal terminal: `ErrorReanudacion`. `forzar=True` la adopta igual,
    registrando `sorteo.reanudacion_incoherente` en auditoría."""
    ronda, c1, c2 = escenario
    numero_ganador = _numero_de_la_esquina(c1)
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(numero_ganador):
        motor.extraer(con)

    # Corrompe el registro a mano: borra la fila de ganador sin anularla,
    # simulando un fallo real (no una decisión del operador).
    con.execute("DELETE FROM ganador WHERE ronda_id = ?", (ronda.id,))

    motor_nuevo = MotorSorteo(rng=_RngSecuencial())
    with pytest.raises(ErrorReanudacion):
        motor_nuevo.reanudar_ronda(con, ronda.id)
    assert not motor_nuevo.hay_ronda_en_juego

    resultado = motor_nuevo.reanudar_ronda(con, ronda.id, forzar=True)
    assert not resultado.coherente
    assert motor_nuevo.hay_ronda_en_juego

    from bingo.persistencia import repo_auditoria

    registros = repo_auditoria.listar_por_evento(con, ronda.evento_id)
    assert any(r.accion == "sorteo.reanudacion_incoherente" for r in registros)


@pytest.mark.lento
def test_extraer_con_mil_cartones_es_rapido(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """Contrato §5.3: el commit de una bola ocurre antes de que la interfaz
    la muestre — con 1.000 cartones en juego tiene que seguir siendo una
    operación de milisegundos, no de segundos, o el sorteo se siente
    congelado en directo."""
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    cartones_bd: list[Carton] = []
    compradores_bd: list[Comprador] = []
    for i in range(1000):
        matriz = generar_carton(Random(i))
        creado = Carton(
            evento_id=evento_creado.id,
            lote_id=lote_creado.id,
            codigo=f"MIL-{i:06d}",
            numeros=orden_canonico(matriz),
            firma=firma(matriz),
            estado="vendido",
        )
        cartones_bd.append(creado)
    repo_carton.crear_varios(con, cartones_bd)
    for carton in repo_carton.listar_por_evento(con, evento_creado.id, estado="vendido"):
        compradores_bd.append(Comprador(carton_id=carton.id, nombre=f"Comprador {carton.id}"))
    repo_comprador.crear_varios(con, compradores_bd)

    ronda = crear_ronda(con, evento_creado.id, patron.id)
    motor = MotorSorteo(rng=_RngSecuencial())
    motor.iniciar_ronda(con, ronda.id)
    assert len(motor.cartones) == 1000

    inicio = time.perf_counter()
    motor.extraer(con)
    transcurrido = time.perf_counter() - inicio

    assert transcurrido < 0.5
