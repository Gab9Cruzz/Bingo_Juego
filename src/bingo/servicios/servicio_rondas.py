"""Casos de uso de `ronda` (contrato de la fase 4, §4.7).

`validar_evento_listo` es el criterio de aceptación "un evento con rondas
incompletas no deja iniciar el sorteo, y dice exactamente qué falta"
(contrato §4.7). Devuelve `list[PendienteEvento]` con claves i18n y
parámetros — nunca un `bool` ni un texto ya formateado, que sería una cadena
visible fuera de `t()`. La fase 5 la llama antes de permitir
`preparado -> en_curso`; `servicio_eventos.marcar_preparado` ya la aplica
para el criterio equivalente al pasar de `borrador` a `preparado`.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from bingo.config.ajustes import LADO_MAX_LOGO
from bingo.config.rutas import dir_medios_evento
from bingo.dominio.modelos import Ronda
from bingo.persistencia import repo_auditoria, repo_carton, repo_patron, repo_ronda
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorValidacion
from bingo.utilidades.imagenes import validar_y_normalizar

_TIPOS_PREMIO = ("efectivo", "bien")


@dataclass(slots=True, frozen=True)
class PendienteEvento:
    """Un ítem de lo que falta para que el evento pueda jugarse (hallazgo A8
    del plan de la fase 4). `bloqueante=False` es un aviso, no un impedimento
    — "al menos un cartón vendido" no puede bloquear un evento que se vende
    entero en la puerta la misma noche."""

    clave_i18n: str
    parametros: dict[str, object] = field(default_factory=dict)
    bloqueante: bool = True


def _validar_datos_ronda(ronda: Ronda) -> None:
    if not ronda.nombre.strip():
        raise ErrorValidacion("rondas.error.nombre_vacio", campo="nombre")
    if ronda.premio_tipo is not None and ronda.premio_tipo not in _TIPOS_PREMIO:
        raise ErrorValidacion(
            "rondas.error.premio_tipo_invalido",
            campo="premio_tipo",
            parametros={"valor": ronda.premio_tipo},
        )
    if ronda.premio_tipo == "efectivo" and (
        ronda.premio_valor_centavos is None or ronda.premio_valor_centavos <= 0
    ):
        raise ErrorValidacion("rondas.error.premio_valor_invalido", campo="premio_valor_centavos")


def crear_ronda(con: sqlite3.Connection, ronda: Ronda) -> Ronda:
    _validar_datos_ronda(ronda)
    if repo_patron.obtener(con, ronda.patron_id) is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda.patron_id})
    orden = repo_ronda.orden_maximo(con, ronda.evento_id) + 1
    a_crear = dataclasses.replace(ronda, orden=orden)
    with transaccion(con):
        creada = repo_ronda.crear(con, a_crear)
        repo_auditoria.registrar(con, ronda.evento_id, "ronda.creada", detalle=creada.nombre)
    return creada


def actualizar_ronda(con: sqlite3.Connection, ronda: Ronda) -> None:
    if ronda.id is None:
        raise ValueError("No se puede actualizar una ronda sin id")
    _validar_datos_ronda(ronda)
    if repo_patron.obtener(con, ronda.patron_id) is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda.patron_id})
    with transaccion(con):
        repo_ronda.actualizar(con, ronda)
        repo_auditoria.registrar(con, ronda.evento_id, "ronda.actualizada", detalle=ronda.nombre)


def eliminar_ronda(con: sqlite3.Connection, ronda_id: int) -> None:
    ronda = repo_ronda.obtener(con, ronda_id)
    if ronda is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
    with transaccion(con):
        repo_ronda.eliminar(con, ronda_id)
        repo_auditoria.registrar(con, ronda.evento_id, "ronda.eliminada", detalle=ronda.nombre)
    if ronda.premio_imagen:
        Path(ronda.premio_imagen).unlink(missing_ok=True)


def reordenar(con: sqlite3.Connection, evento_id: int, ids_en_orden: list[int]) -> None:
    """Dos pasadas en una sola transacción (decisión D5, corregida por el
    hallazgo C1): `UNIQUE(evento_id, orden)` se comprueba por sentencia, así
    que un intercambio directo colisiona a mitad de camino. `ids_en_orden`
    debe ser el conjunto **completo** de rondas del evento, ni una de menos
    ni una de más — de lo contrario alguna quedaría en el rango negativo.
    """
    actuales = repo_ronda.listar_por_evento(con, evento_id)
    ids_actuales = {r.id for r in actuales}
    if set(ids_en_orden) != ids_actuales or len(ids_en_orden) != len(ids_actuales):
        raise ErrorValidacion("rondas.error.orden_incompleto", campo="ids_en_orden")
    with transaccion(con):
        repo_ronda.desplazar_ordenes_a_negativo(con, evento_id)
        for posicion, ronda_id in enumerate(ids_en_orden, start=1):
            repo_ronda.actualizar_orden(con, ronda_id, posicion)
        repo_auditoria.registrar(con, evento_id, "rondas.reordenadas")


def guardar_imagen_premio(
    con: sqlite3.Connection, evento_id: int, ronda_id: int, origen: Path
) -> str:
    """Normaliza la imagen del premio con el mismo camino que el logo
    (`utilidades/imagenes.validar_y_normalizar`) y la persiste en
    `ronda.premio_imagen`. Nombre de archivo por `ronda_id` (no por evento)
    para no acumular huérfanos al reemplazarla."""
    ronda = repo_ronda.obtener(con, ronda_id)
    if ronda is None or ronda.evento_id != evento_id:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
    destino = dir_medios_evento(evento_id) / f"premio_{ronda_id}.png"
    ruta = validar_y_normalizar(origen, destino, lado_max=LADO_MAX_LOGO)
    with transaccion(con):
        repo_ronda.actualizar(con, dataclasses.replace(ronda, premio_imagen=str(ruta)))
    return str(ruta)


def validar_evento_listo(con: sqlite3.Connection, evento_id: int) -> list[PendienteEvento]:
    pendientes: list[PendienteEvento] = []
    rondas = repo_ronda.listar_por_evento(con, evento_id)
    if not rondas:
        pendientes.append(PendienteEvento("rondas.pendiente.sin_rondas"))
        return pendientes

    sin_premio = [r for r in rondas if not (r.premio_nombre or "").strip()]
    if sin_premio:
        pendientes.append(
            PendienteEvento("rondas.pendiente.sin_premio", {"cantidad": len(sin_premio)})
        )

    sin_valor = [
        r
        for r in rondas
        if r.premio_tipo == "efectivo"
        and not (r.premio_valor_centavos and r.premio_valor_centavos > 0)
    ]
    if sin_valor:
        pendientes.append(
            PendienteEvento("rondas.pendiente.sin_valor_efectivo", {"cantidad": len(sin_valor)})
        )

    # `patron_id` es NOT NULL en el esquema (001_inicial.sql): el formulario
    # de ronda ya exige un patrón antes de poder guardar, así que no hace
    # falta (ni es posible) una ronda sin patrón que reportar aquí
    # (hallazgo A9 del plan de la fase 4).

    conteo = repo_carton.contar_por_estado(con, evento_id)
    if conteo.get("vendido", 0) == 0:
        # Aviso, no bloqueo (hallazgo A8): un evento que se vende entero en
        # la puerta la misma noche debe poder arrancar igual.
        pendientes.append(PendienteEvento("rondas.pendiente.sin_vendidos", bloqueante=False))

    return pendientes
