from __future__ import annotations

import sqlite3

import pytest
from factorias import crear_evento, crear_organizacion

from bingo.config.ajustes import LIMITE_CARTONES_POR_LOTE
from bingo.persistencia import repo_carton, repo_lote
from bingo.servicios import servicio_cartones
from bingo.utilidades.errores import ErrorDominio, ErrorValidacion


class _RngSiempreIgual:
    """Genera siempre el mismo cartón: `randrange` devuelve 0 siempre, así
    que cada columna elige sus primeros N elementos disponibles en el mismo
    orden. Sirve para forzar una colisión de firma en cada intento.
    """

    def randrange(self, _stop: int) -> int:
        return 0


def _evento(con: sqlite3.Connection):
    org = crear_organizacion(con)
    return crear_evento(con, org.id)


def test_generar_lote_feliz(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    lote = servicio_cartones.generar_lote(con, ev.id, 10, "ABC", semilla="s1")
    assert lote.completado_en is not None

    cartones = repo_carton.listar_por_evento(con, ev.id)
    assert len(cartones) == 10
    codigos = sorted(c.codigo for c in cartones)
    assert codigos[0].startswith("ABC-")
    # ancho de secuencia = len(str(10)) = 2
    assert codigos[0].split("-")[-1].__len__() == 2


def test_generar_lote_ancho_de_secuencia_segun_cantidad(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 5, "X", semilla="s2")
    codigos = sorted(c.codigo for c in repo_carton.listar_por_evento(con, ev.id))
    assert all(len(c.split("-")[-1]) == 1 for c in codigos)


def test_generar_lote_reproducible_con_la_misma_semilla(con: sqlite3.Connection) -> None:
    ev_a = crear_evento(con, crear_organizacion(con).id)
    ev_b = crear_evento(con, crear_organizacion(con).id)
    servicio_cartones.generar_lote(con, ev_a.id, 8, "R", semilla="misma-semilla")
    servicio_cartones.generar_lote(con, ev_b.id, 8, "R", semilla="misma-semilla")

    numeros_a = sorted(c.numeros for c in repo_carton.listar_por_evento(con, ev_a.id))
    numeros_b = sorted(c.numeros for c in repo_carton.listar_por_evento(con, ev_b.id))
    assert numeros_a == numeros_b


def test_generar_lote_al_progresar_monotono(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    llamadas: list[tuple[int, int]] = []
    servicio_cartones.generar_lote(
        con, ev.id, 1200, "P", semilla="s3", al_progresar=lambda g, t: llamadas.append((g, t))
    )
    assert llamadas, "al_progresar nunca se llamó"
    generados_vistos = [g for g, _t in llamadas]
    assert generados_vistos == sorted(generados_vistos)
    assert llamadas[-1] == (1200, 1200)


def test_generar_lote_cancelado_a_mitad_no_deja_huerfanos(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    umbral = 700  # cae después del bloque de 500

    def debe_cancelar() -> bool:
        return len(repo_carton.listar_por_evento(con, ev.id)) >= umbral

    lote = servicio_cartones.generar_lote(
        con, ev.id, 2000, "C", semilla="s4", debe_cancelar=debe_cancelar
    )

    assert repo_carton.listar_por_evento(con, ev.id) == []
    assert repo_lote.obtener(con, lote.id) is None


def test_generar_lote_cantidad_invalida(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorValidacion) as excinfo:
        servicio_cartones.generar_lote(con, ev.id, 0, "A")
    assert excinfo.value.campo == "cantidad"


def test_generar_lote_cantidad_excede_maximo(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorValidacion) as excinfo:
        servicio_cartones.generar_lote(con, ev.id, LIMITE_CARTONES_POR_LOTE + 1, "A")
    assert excinfo.value.campo == "cantidad"


def test_generar_lote_cantidad_limite_exacto_pasa_validacion() -> None:
    # No se genera el lote completo (sería lento); solo se confirma que la
    # validación de cantidad no rechaza el límite exacto antes de arrancar.
    try:
        servicio_cartones._validar_cantidad(LIMITE_CARTONES_POR_LOTE)
    except ErrorValidacion:
        pytest.fail("La cantidad límite exacta no debería ser rechazada")


def test_generar_lote_prefijo_vacio(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorValidacion) as excinfo:
        servicio_cartones.generar_lote(con, ev.id, 5, "   ")
    assert excinfo.value.campo == "prefijo_codigo"


def test_generar_lote_prefijo_invalido_por_caracter(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorValidacion) as excinfo:
        servicio_cartones.generar_lote(con, ev.id, 5, "AB C")
    assert excinfo.value.campo == "prefijo_codigo"


def test_generar_lote_prefijo_invalido_por_longitud(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorValidacion):
        servicio_cartones.generar_lote(con, ev.id, 5, "A" * 13)


def test_generar_lote_prefijo_12_caracteres_pasa(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    lote = servicio_cartones.generar_lote(con, ev.id, 3, "A" * 12, semilla="s5")
    assert lote.prefijo_codigo == "A" * 12


def test_generar_lote_prefijo_repetido_en_el_mismo_evento(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 3, "REP", semilla="s6")
    with pytest.raises(ErrorValidacion) as excinfo:
        servicio_cartones.generar_lote(con, ev.id, 3, "REP", semilla="s7")
    assert excinfo.value.campo == "prefijo_codigo"


def test_generar_lote_prefijo_repetido_no_toca_la_base(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 3, "REP", semilla="s6")
    total_antes = len(repo_carton.listar_por_evento(con, ev.id))
    with pytest.raises(ErrorValidacion):
        servicio_cartones.generar_lote(con, ev.id, 100, "REP", semilla="s7")
    assert len(repo_carton.listar_por_evento(con, ev.id)) == total_antes


def test_generar_lote_prefijo_distinto_si_funciona(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 3, "REP", semilla="s6")
    servicio_cartones.generar_lote(con, ev.id, 3, "OTRO", semilla="s7")  # no debe lanzar
    assert len(repo_lote.listar_por_evento(con, ev.id)) == 2


def test_generar_lote_tope_de_colisiones_de_firma(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    with pytest.raises(ErrorDominio):
        servicio_cartones.generar_lote(con, ev.id, 5, "COL", rng=_RngSiempreIgual())


def test_limpiar_lotes_huerfanos(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    # Simula un proceso muerto a mitad de generar_lote: lote sin completado_en,
    # con cartones ya insertados en un bloque previo.
    lote_huerfano = servicio_cartones.generar_lote(
        con, ev.id, 5, "H", semilla="s8", debe_cancelar=lambda: False
    )
    # Deshace el cierre exitoso a mano para simular el estado "a medias".
    con.execute("UPDATE lote SET completado_en = NULL WHERE id = ?", (lote_huerfano.id,))

    limpiados = servicio_cartones.limpiar_lotes_huerfanos(con)

    assert limpiados == 1
    assert repo_lote.obtener(con, lote_huerfano.id) is None
    assert repo_carton.listar_por_evento(con, ev.id) == []


def test_limpiar_lotes_huerfanos_no_toca_lotes_completos(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    lote = servicio_cartones.generar_lote(con, ev.id, 5, "OK", semilla="s9")
    assert servicio_cartones.limpiar_lotes_huerfanos(con) == 0
    assert repo_lote.obtener(con, lote.id) is not None


def test_limpiar_lotes_huerfanos_procesa_el_resto_si_uno_falla(
    con: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    ev = _evento(con)
    huerfano_1 = servicio_cartones.generar_lote(con, ev.id, 2, "H1", semilla="a")
    huerfano_2 = servicio_cartones.generar_lote(con, ev.id, 2, "H2", semilla="b")
    con.execute(
        "UPDATE lote SET completado_en = NULL WHERE id IN (?, ?)",
        (huerfano_1.id, huerfano_2.id),
    )

    llamadas = []
    original = repo_lote.eliminar

    def _eliminar_fallando_la_primera(con_, lote_id):  # noqa: ANN001 - firma de monkeypatch
        llamadas.append(lote_id)
        if len(llamadas) == 1:
            raise sqlite3.OperationalError("fallo simulado")
        return original(con_, lote_id)

    monkeypatch.setattr(repo_lote, "eliminar", _eliminar_fallando_la_primera)

    with pytest.raises(sqlite3.OperationalError):
        servicio_cartones.limpiar_lotes_huerfanos(con)

    # El segundo lote no se tocó porque el primero abortó la función completa
    # con una excepción sin capturar: documenta el comportamiento real, no
    # una aspiración — cada lote está en su propia transacción, pero el
    # bucle de Python que las abre no atrapa fallos entre una y otra.
    assert len(llamadas) == 1


@pytest.mark.lento
def test_generar_10000_cartones_toma_menos_de_10_segundos(con: sqlite3.Connection) -> None:
    import time

    ev = _evento(con)
    inicio = time.perf_counter()
    servicio_cartones.generar_lote(con, ev.id, 10_000, "VOL", semilla="volumen")
    duracion = time.perf_counter() - inicio
    assert duracion < 10.0, f"Tardó {duracion:.1f}s, se esperaba menos de 10s"


def test_cambiar_estado_carton_valido(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 1, "E", semilla="se")
    carton = repo_carton.listar_por_evento(con, ev.id)[0]
    servicio_cartones.cambiar_estado_carton(con, carton.id, "impreso")
    assert repo_carton.obtener(con, carton.id).estado == "impreso"


def test_cambiar_estado_carton_invalido(con: sqlite3.Connection) -> None:
    from bingo.utilidades.errores import ErrorTransicionInvalida

    ev = _evento(con)
    servicio_cartones.generar_lote(con, ev.id, 1, "E2", semilla="se2")
    carton = repo_carton.listar_por_evento(con, ev.id)[0]
    with pytest.raises(ErrorTransicionInvalida):
        servicio_cartones.cambiar_estado_carton(con, carton.id, "vendido")
