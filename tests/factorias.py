"""Fábricas de entidades de dominio para pruebas. Cada fase amplía este archivo."""

from __future__ import annotations

import sqlite3

import pytest

from bingo.dominio.modelos import Evento, Organizacion
from bingo.persistencia import repo_evento, repo_organizacion


def crear_organizacion(con: sqlite3.Connection, **overrides: object) -> Organizacion:
    datos = {"nombre": "Fundación de prueba"} | overrides
    return repo_organizacion.crear(con, Organizacion(**datos))


def crear_evento(con: sqlite3.Connection, organizacion_id: int, **overrides: object) -> Evento:
    datos = {"organizacion_id": organizacion_id, "nombre": "Bingo de prueba"} | overrides
    return repo_evento.crear(con, Evento(**datos))


@pytest.fixture
def organizacion_creada(con: sqlite3.Connection) -> Organizacion:
    return crear_organizacion(con)


@pytest.fixture
def evento_creado(con: sqlite3.Connection, organizacion_creada: Organizacion) -> Evento:
    return crear_evento(con, organizacion_creada.id)
