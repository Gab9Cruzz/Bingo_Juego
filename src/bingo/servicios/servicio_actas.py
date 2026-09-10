"""Orquesta el acta de una ronda (contrato §5.9, decisión D7).

Construye la carga canónica desde la base, la sella con SHA-256, escribe el
PDF y guarda `acta_hash`/`acta_generada_en` — la única vía para que esas dos
columnas cambien fuera de la invalidación por reapertura
(`servicio_rondas.reabrir_ronda`, hallazgo E-16/C6).

**El nombre del archivo va por `ronda_id`, no por `orden` (hallazgo C6).**
`orden` es mutable (`repo_ronda.actualizar_orden`,
`servicio_rondas.reordenar`): con `acta-ronda-<orden>.pdf`, reordenar rondas
haría que el acta de una sobrescriba la de otra. Formato:
`acta-<ronda_id>-<AAAAMMDD-HHMMSS>.pdf`, y nunca se borra la anterior — dos
actas de la misma ronda (por ejemplo, tras reabrir y volver a cerrar) dejan
las dos en disco, con hashes distintos si el sorteo cambió de verdad.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from bingo.config.rutas import dir_impresos_evento
from bingo.dominio.acta import GanadorActa, carga_canonica, hash_acta
from bingo.impresion.acta import escribir_acta_pdf
from bingo.persistencia import (
    repo_auditoria,
    repo_carton,
    repo_evento,
    repo_extraccion,
    repo_ganador,
    repo_organizacion,
    repo_patron,
    repo_ronda,
)
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorNoEncontrado
from bingo.utilidades.fechas import ahora_iso


def _nombres_org_evento(con: sqlite3.Connection, ronda) -> tuple[str, str]:
    evento = repo_evento.obtener(con, ronda.evento_id)
    if evento is None:
        return "", ""
    organizacion = repo_organizacion.obtener(con, evento.organizacion_id)
    return (organizacion.nombre if organizacion is not None else ""), evento.nombre


def _datos_de_la_ronda(con: sqlite3.Connection, ronda_id: int):
    """Todo lo que hace falta para construir la carga canónica y el PDF, en
    una sola pasada: `(ronda, patron, numeros, ganadores_activos)`. Los
    ganadores anulados no entran al acta — son un hecho que el operador ya
    descartó, no algo que la organización necesite ver impreso."""
    ronda = repo_ronda.obtener(con, ronda_id)
    if ronda is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
    patron = repo_patron.obtener(con, ronda.patron_id)
    numeros = repo_extraccion.numeros_por_ronda(con, ronda_id)
    ganadores_activos = [
        g for g in repo_ganador.listar_por_ronda(con, ronda_id) if g.anulado_en is None
    ]
    return ronda, patron, numeros, ganadores_activos


def _construir_carga(con: sqlite3.Connection, ronda_id: int) -> str:
    ronda, patron, numeros, ganadores_activos = _datos_de_la_ronda(con, ronda_id)
    organizacion_nombre, evento_nombre = _nombres_org_evento(con, ronda)
    ganadores_acta = []
    for g in ganadores_activos:
        carton = repo_carton.obtener(con, g.carton_id)
        ganadores_acta.append(
            GanadorActa(codigo=carton.codigo if carton is not None else "?", decision=g.decision)
        )
    return carga_canonica(
        organizacion_nombre=organizacion_nombre,
        evento_nombre=evento_nombre,
        ronda_nombre=ronda.nombre,
        patron_nombre=patron.nombre if patron is not None else "",
        premio_texto=ronda.premio_nombre or "",
        numeros=numeros,
        ganadores=ganadores_acta,
    )


def generar_acta(con: sqlite3.Connection, ronda_id: int) -> Path:
    ronda, patron, numeros, ganadores_activos = _datos_de_la_ronda(con, ronda_id)
    organizacion_nombre, evento_nombre = _nombres_org_evento(con, ronda)
    carga = _construir_carga(con, ronda_id)
    hash_valor = hash_acta(carga)

    ganadores_para_pdf = []
    for g in ganadores_activos:
        carton = repo_carton.obtener(con, g.carton_id)
        ganadores_para_pdf.append(
            {"codigo": carton.codigo if carton is not None else "?", "decision": g.decision}
        )

    momento = ahora_iso()
    fecha, _, hora = momento.partition("T")
    sello = f"{fecha.replace('-', '')}-{hora.rstrip('Z').replace(':', '')}"
    ruta = dir_impresos_evento(ronda.evento_id) / f"acta-{ronda_id}-{sello}.pdf"

    escribir_acta_pdf(
        ruta,
        organizacion_nombre=organizacion_nombre,
        evento_nombre=evento_nombre,
        ronda_nombre=ronda.nombre,
        patron_nombre=patron.nombre if patron is not None else "",
        premio_texto=ronda.premio_nombre or "",
        numeros=numeros,
        ganadores=ganadores_para_pdf,
        hash_acta=hash_valor,
        textos={},
    )

    with transaccion(con):
        repo_ronda.actualizar_acta(con, ronda_id, acta_hash=hash_valor, acta_generada_en=momento)
        repo_auditoria.registrar(
            con,
            ronda.evento_id,
            "sorteo.acta_generada",
            detalle=f"ronda_id={ronda_id} hash={hash_valor} ruta={ruta}",
        )

    return ruta


def verificar_acta(con: sqlite3.Connection, ronda_id: int) -> str:
    """Tarea 4.20 (verificador). Devuelve `"coincide"`, `"no_coincide"` o
    `"sin_acta"` — nunca lanza por una discrepancia, que es un resultado
    válido de verificar, no un error de programa."""
    ronda = repo_ronda.obtener(con, ronda_id)
    if ronda is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
    if ronda.acta_hash is None:
        return "sin_acta"
    carga_actual = _construir_carga(con, ronda_id)
    return "coincide" if hash_acta(carga_actual) == ronda.acta_hash else "no_coincide"
