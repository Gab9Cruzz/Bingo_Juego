import dataclasses
import sqlite3

from factorias import crear_carton, crear_comprador

from bingo.dominio.modelos import Comprador
from bingo.persistencia import repo_comprador


def test_crear_y_obtener_por_carton(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    creado = crear_comprador(con, carton.id, nombre="Ana")
    obtenido = repo_comprador.obtener_por_carton(con, carton.id)
    assert obtenido is not None
    assert obtenido.id == creado.id
    assert obtenido.nombre == "Ana"


def test_obtener_por_carton_ignora_anulados_por_defecto(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    creado = crear_comprador(con, carton.id)
    repo_comprador.anular(con, creado.id)
    assert repo_comprador.obtener_por_carton(con, carton.id) is None
    assert repo_comprador.obtener_por_carton(con, carton.id, incluir_anulados=True) is not None


def test_indice_unico_parcial_permite_recrear_tras_anular(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """El hallazgo E-C3 del plan de la fase 4: anular una venta no debe dejar
    el cartón inutilizable para siempre — el índice único es parcial
    (`WHERE anulado_en IS NULL`)."""
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    primero = crear_comprador(con, carton.id, nombre="Primero")
    repo_comprador.anular(con, primero.id)
    segundo = crear_comprador(con, carton.id, nombre="Segundo")  # no lanza
    assert repo_comprador.obtener_por_carton(con, carton.id).id == segundo.id


def test_crear_varios(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2)
    n = repo_comprador.crear_varios(
        con,
        [
            Comprador(carton_id=c1.id, nombre="A"),
            Comprador(carton_id=c2.id, nombre="B"),
        ],
    )
    assert n == 2
    assert repo_comprador.contar_por_evento(con, evento_creado.id) == 2


def test_listar_por_evento_busca_por_codigo_y_nombre(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    crear_comprador(con, c1.id, nombre="Beto Ruiz")
    resultado = repo_comprador.listar_por_evento(con, evento_creado.id, texto_busqueda="Beto")
    assert len(resultado) == 1
    resultado_codigo = repo_comprador.listar_por_evento(
        con, evento_creado.id, texto_busqueda=c1.codigo
    )
    assert len(resultado_codigo) == 1


def test_listar_por_evento_filtra_provisional(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2)
    crear_comprador(con, c1.id, provisional=True)
    crear_comprador(con, c2.id, provisional=False)
    assert len(repo_comprador.listar_por_evento(con, evento_creado.id, provisional=True)) == 1
    assert len(repo_comprador.listar_por_evento(con, evento_creado.id, provisional=False)) == 1


def test_mapa_por_evento(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    crear_comprador(con, carton.id)
    mapa = repo_comprador.mapa_por_evento(con, evento_creado.id)
    assert carton.id in mapa


def test_contar_por_evento(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    crear_comprador(con, c1.id)
    assert repo_comprador.contar_por_evento(con, evento_creado.id) == 1


def test_actualizar(con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    creado = crear_comprador(con, carton.id, nombre="Antes")
    repo_comprador.actualizar(con, dataclasses.replace(creado, nombre="Después"))
    assert repo_comprador.obtener(con, creado.id).nombre == "Después"


def test_eliminar_por_evento_borra_vivos_y_anulados(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2)
    vivo = crear_comprador(con, c1.id)
    anulado = crear_comprador(con, c2.id)
    repo_comprador.anular(con, anulado.id)

    eliminados = repo_comprador.eliminar_por_evento(con, evento_creado.id)
    assert eliminados == 2
    assert repo_comprador.obtener(con, vivo.id) is None
    assert repo_comprador.obtener(con, anulado.id) is None


def test_provisional_persiste_como_booleano(
    con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    carton = crear_carton(con, evento_creado.id, lote_creado.id)
    creado = crear_comprador(con, carton.id, provisional=True)
    assert repo_comprador.obtener(con, creado.id).provisional is True
