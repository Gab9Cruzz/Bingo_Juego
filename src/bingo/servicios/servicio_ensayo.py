"""Modo ensayo (tarea 4.17 de la fase 5, expansión E1, criterio de
aceptación §5.12): `python -m bingo --ensayo` monta en un minuto lo que el
ensayo completo (`docs/Fase_5/Ensayo.md`) necesita a mano — un evento con
200 cartones vendidos y tres rondas con patrones distintos. Sin esto, cada
práctica exigía recrear todo desde cero, y el riesgo que el propio plan
señala ("el ensayo se salta por falta de tiempo") se vuelve más probable
cada vez que montarlo cuesta media hora.

Reutiliza servicios existentes de punta a punta — ni una consulta SQL
propia (mandato explícito del plan): `servicio_organizaciones.
crear_organizacion`, `servicio_eventos.crear_evento`,
`servicio_cartones.generar_lote`, `servicio_compradores.
marcar_vendidos_por_rango`, `servicio_rondas.crear_ronda`.
"""

from __future__ import annotations

import sqlite3

from bingo.dominio.modelos import Evento, Organizacion, Ronda
from bingo.persistencia import repo_carton, repo_evento, repo_organizacion, repo_patron
from bingo.servicios import (
    servicio_cartones,
    servicio_compradores,
    servicio_eventos,
    servicio_organizaciones,
    servicio_patrones,
    servicio_rondas,
)

NOMBRE_ORGANIZACION = "Organización de ensayo"
NOMBRE_EVENTO = "Bingo de ensayo"
CANTIDAD_CARTONES = 200
PREFIJO_CODIGO = "ENSAYO"
CANTIDAD_RONDAS = 3


def ejecutar(con: sqlite3.Connection) -> Evento:
    """Idempotente (prueba exigida por el plan: correr `--ensayo` dos veces
    deja exactamente un evento de prueba): si el evento de ensayo ya
    existe, no vuelve a generar nada — lo devuelve tal cual."""
    organizacion = next(
        (o for o in repo_organizacion.listar(con) if o.nombre == NOMBRE_ORGANIZACION), None
    )
    if organizacion is None:
        organizacion = servicio_organizaciones.crear_organizacion(
            con, Organizacion(nombre=NOMBRE_ORGANIZACION), None
        )

    evento_existente = next(
        (
            e
            for e in repo_evento.listar_por_organizacion(con, organizacion.id)
            if e.nombre == NOMBRE_EVENTO
        ),
        None,
    )
    if evento_existente is not None:
        return evento_existente

    evento = servicio_eventos.crear_evento(
        con,
        Evento(
            organizacion_id=organizacion.id,
            nombre=NOMBRE_EVENTO,
            precio_tabla_centavos=100,
        ),
    )

    servicio_cartones.generar_lote(con, evento.id, CANTIDAD_CARTONES, PREFIJO_CODIGO)

    cartones = repo_carton.listar_por_evento(con, evento.id, limite=None)
    # "Marcar vendidos por rango" solo acepta cartones ya impresos/entregados
    # (`_ESTADOS_VENDIBLES`) — recién generados están en "generado", el
    # ensayo se salta el paso real de imprimir.
    for carton in cartones:
        servicio_cartones.cambiar_estado_carton(con, carton.id, "impreso")

    codigos = sorted(c.codigo for c in cartones)
    servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, codigos[0], codigos[-1], nombre_generico="Comprador de ensayo"
    )

    # Idempotente y barato (fase 4): no depender de que `__main__.principal`
    # ya la haya corrido — este servicio no asume nada de quién lo llama.
    servicio_patrones.asegurar_patrones_sistema(con)
    patrones_sistema = [p for p in repo_patron.listar(con) if p.es_sistema]
    for indice, patron in enumerate(patrones_sistema[:CANTIDAD_RONDAS], start=1):
        servicio_rondas.crear_ronda(
            con,
            Ronda(evento_id=evento.id, nombre=f"Ronda de ensayo {indice}", patron_id=patron.id),
        )

    return evento
