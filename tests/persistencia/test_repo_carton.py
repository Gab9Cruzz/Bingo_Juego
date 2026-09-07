from __future__ import annotations

import sqlite3
from random import Random

import pytest
from factorias import crear_carton, crear_evento, crear_lote, crear_organizacion

from bingo.dominio.carton import firma, generar_carton, orden_canonico
from bingo.dominio.modelos import Carton
from bingo.persistencia import repo_carton
from bingo.utilidades.errores import ErrorIntegridad


def _carton_de_prueba(evento_id: int, lote_id: int, semilla: int, **overrides: object) -> Carton:
    matriz = generar_carton(Random(semilla))
    datos = {
        "evento_id": evento_id,
        "lote_id": lote_id,
        "codigo": f"T-{semilla:06d}",
        "numeros": orden_canonico(matriz),
        "firma": firma(matriz),
    } | overrides
    return Carton(**datos)


def test_crear_varios_inserta_en_un_solo_executemany(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    cartones = [_carton_de_prueba(ev.id, lote.id, i) for i in range(5)]
    insertados = repo_carton.crear_varios(con, cartones)
    assert insertados == 5
    assert len(repo_carton.listar_por_evento(con, ev.id)) == 5


def test_crear_varios_con_lista_vacia_no_hace_nada(con: sqlite3.Connection) -> None:
    assert repo_carton.crear_varios(con, []) == 0


def test_unique_firma_lanza_error_integridad(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    carton = _carton_de_prueba(ev.id, lote.id, 1)
    repo_carton.crear_varios(con, [carton])
    duplicado = _carton_de_prueba(ev.id, lote.id, 1, codigo="OTRO-CODIGO")
    with pytest.raises(ErrorIntegridad) as excinfo:
        repo_carton.crear_varios(con, [duplicado])
    assert excinfo.value.tipo == "unique"


def test_unique_codigo_lanza_error_integridad(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    repo_carton.crear_varios(con, [_carton_de_prueba(ev.id, lote.id, 1, codigo="X-1")])
    otro = _carton_de_prueba(ev.id, lote.id, 2, codigo="X-1")
    with pytest.raises(ErrorIntegridad) as excinfo:
        repo_carton.crear_varios(con, [otro])
    assert excinfo.value.tipo == "unique"


def test_obtener_por_codigo(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    carton = crear_carton(con, ev.id, lote.id, semilla=1)
    encontrado = repo_carton.obtener_por_codigo(con, ev.id, carton.codigo)
    assert encontrado is not None
    assert encontrado.id == carton.id
    assert repo_carton.obtener_por_codigo(con, ev.id, "NO-EXISTE") is None


def test_explain_query_plan_usa_indice_de_codigo(con: sqlite3.Connection) -> None:
    plan = con.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM carton WHERE evento_id = 1 AND codigo = 'X'"
    ).fetchall()
    texto_plan = " ".join(str(fila["detail"]) for fila in plan)
    assert "carton" in texto_plan.lower()
    assert "SCAN" not in texto_plan.upper() or "USING" in texto_plan.upper()


def test_listar_por_evento_filtra_por_estado(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    a = crear_carton(con, ev.id, lote.id, semilla=1)
    crear_carton(con, ev.id, lote.id, semilla=2)
    repo_carton.actualizar_estado(con, a.id, "impreso")

    generados = repo_carton.listar_por_evento(con, ev.id, estado="generado")
    impresos = repo_carton.listar_por_evento(con, ev.id, estado="impreso")
    assert len(generados) == 1
    assert len(impresos) == 1
    assert impresos[0].id == a.id


def test_listar_por_evento_busca_por_codigo(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    crear_carton(con, ev.id, lote.id, semilla=1, codigo="ABC-001")
    crear_carton(con, ev.id, lote.id, semilla=2, codigo="ABC-002")
    crear_carton(con, ev.id, lote.id, semilla=3, codigo="XYZ-001")

    resultado = repo_carton.listar_por_evento(con, ev.id, texto_busqueda="ABC")
    assert {c.codigo for c in resultado} == {"ABC-001", "ABC-002"}


def test_listar_por_evento_paginacion(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    for i in range(10):
        crear_carton(con, ev.id, lote.id, semilla=i)

    pagina_1 = repo_carton.listar_por_evento(con, ev.id, limite=4, desplazamiento=0)
    pagina_2 = repo_carton.listar_por_evento(con, ev.id, limite=4, desplazamiento=4)
    assert len(pagina_1) == 4
    assert len(pagina_2) == 4
    assert {c.id for c in pagina_1}.isdisjoint({c.id for c in pagina_2})


def test_contar_por_estado(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    a = crear_carton(con, ev.id, lote.id, semilla=1)
    crear_carton(con, ev.id, lote.id, semilla=2)
    repo_carton.actualizar_estado(con, a.id, "impreso")

    conteo = repo_carton.contar_por_estado(con, ev.id)
    assert conteo == {"generado": 1, "impreso": 1}


def test_listar_firmas_por_evento(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    a = crear_carton(con, ev.id, lote.id, semilla=1)
    b = crear_carton(con, ev.id, lote.id, semilla=2)
    assert repo_carton.listar_firmas_por_evento(con, ev.id) == {a.firma, b.firma}


def test_actualizar_estado_por_lote(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    crear_carton(con, ev.id, lote.id, semilla=1)
    crear_carton(con, ev.id, lote.id, semilla=2)

    actualizados = repo_carton.actualizar_estado_por_lote(con, lote.id, "impreso")
    assert actualizados == 2
    assert repo_carton.contar_por_estado(con, ev.id) == {"impreso": 2}


def test_eliminar_por_lote(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    crear_carton(con, ev.id, lote.id, semilla=1)
    crear_carton(con, ev.id, lote.id, semilla=2)

    eliminados = repo_carton.eliminar_por_lote(con, lote.id)
    assert eliminados == 2
    assert repo_carton.listar_por_evento(con, ev.id) == []
