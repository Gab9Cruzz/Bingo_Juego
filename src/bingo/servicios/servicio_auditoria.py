"""Casos de uso del panel de auditoría del evento (tarea 4.19 de la fase 5,
expansión E3 — cierra una deuda de la fase 4).

`repo_auditoria.listar_por_evento` ya existía; este servicio no añade SQL
nuevo, solo el filtro por prefijo de acción (en memoria: el volumen por
evento no lo justifica) y la exportación a `.xlsx`, delegada en
`impresion/reporte.py` (único módulo que escribe Excel, hallazgo A4 de la
fase 4).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path

from bingo.dominio.modelos import RegistroAuditoria
from bingo.impresion import reporte
from bingo.persistencia import repo_auditoria

# Tope generoso: la fase 5 multiplica por diez lo que se escribe en
# auditoría por evento (extracción de cada bola, cada extracción de
# reclamo, etc.), y `listar_por_evento` ya trae `LIMIT` propio (200 por
# defecto) pensado para un vistazo rápido, no para el panel dedicado.
LIMITE_PANEL = 5000


def listar(
    con: sqlite3.Connection, evento_id: int, *, prefijo: str | None = None
) -> list[RegistroAuditoria]:
    """Más reciente primero (mismo orden que `repo_auditoria.
    listar_por_evento`). `prefijo` filtra por el inicio de `accion`
    (p. ej. "venta." o "sorteo.") — vacío o `None` no filtra."""
    registros = repo_auditoria.listar_por_evento(con, evento_id, limite=LIMITE_PANEL)
    if prefijo:
        registros = [r for r in registros if r.accion.startswith(prefijo)]
    return registros


def generar_reporte_excel(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    prefijo: str | None = None,
) -> Path:
    """Exporta exactamente lo que el panel está mostrando — mismo filtro de
    prefijo, para que "exportar" nunca traiga más filas de las que el
    operador vio en pantalla."""
    registros = listar(con, evento_id, prefijo=prefijo)
    filas = [
        {"momento": r.momento, "accion": r.accion, "detalle": r.detalle or ""} for r in registros
    ]
    return reporte.reporte_auditoria_excel(filas, ruta_destino, textos)
