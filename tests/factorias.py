"""Fábricas de entidades de dominio para pruebas. Cada fase amplía este archivo."""

from __future__ import annotations

import sqlite3
from random import Random

import pytest

from bingo.dominio.carton import firma, generar_carton, orden_canonico
from bingo.dominio.modelos import Carton, Evento, Lote, Organizacion
from bingo.persistencia import repo_carton, repo_evento, repo_lote, repo_organizacion


def crear_organizacion(con: sqlite3.Connection, **overrides: object) -> Organizacion:
    datos = {"nombre": "Fundación de prueba"} | overrides
    return repo_organizacion.crear(con, Organizacion(**datos))


def crear_evento(con: sqlite3.Connection, organizacion_id: int, **overrides: object) -> Evento:
    datos = {"organizacion_id": organizacion_id, "nombre": "Bingo de prueba"} | overrides
    return repo_evento.crear(con, Evento(**datos))


def crear_lote(con: sqlite3.Connection, evento_id: int, **overrides: object) -> Lote:
    datos = {
        "evento_id": evento_id,
        "cantidad": 10,
        "prefijo_codigo": "TEST",
        "semilla": "semilla-de-prueba",
    } | overrides
    return repo_lote.crear(con, Lote(**datos))


def crear_carton(
    con: sqlite3.Connection, evento_id: int, lote_id: int, *, semilla: int = 0, **overrides: object
) -> Carton:
    """`semilla` distingue cartones dentro de la misma prueba (cada valor genera
    un cartón distinto vía `Random(semilla)`); `codigo` por defecto usa la misma
    semilla para no colisionar con `UNIQUE(evento_id, codigo)`.
    """
    matriz = generar_carton(Random(semilla))
    datos = {
        "evento_id": evento_id,
        "lote_id": lote_id,
        "codigo": f"TEST-{semilla:06d}",
        "numeros": orden_canonico(matriz),
        "firma": firma(matriz),
    } | overrides
    repo_carton.crear_varios(con, [Carton(**datos)])
    return repo_carton.obtener_por_codigo(con, evento_id, datos["codigo"])


@pytest.fixture
def organizacion_creada(con: sqlite3.Connection) -> Organizacion:
    return crear_organizacion(con)


@pytest.fixture
def evento_creado(con: sqlite3.Connection, organizacion_creada: Organizacion) -> Evento:
    return crear_evento(con, organizacion_creada.id)


@pytest.fixture
def lote_creado(con: sqlite3.Connection, evento_creado: Evento) -> Lote:
    return crear_lote(con, evento_creado.id)
