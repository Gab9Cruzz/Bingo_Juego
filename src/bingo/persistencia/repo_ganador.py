"""Repositorio de `ganador`. Toda consulta SQL de esta entidad vive aquí.

`crear()` es el verbo normal de la tabla de convenciones — **no**
`crear_si_no_existe` con `INSERT OR IGNORE` (corrección del hallazgo C3,
plan de la fase 5, que sustituye lo que decía la tarea 4.4 original). Con la
reanudación en solo lectura (decisión D13) nadie vuelve a insertar un
ganador ya persistido: si `idx_ganador_ronda_carton` (índice único **total**,
hallazgo V1) salta, es un error de programa, y debe llegar como
`ErrorIntegridad` normal a la franja, no tragárselo en silencio.

`anular` es un borrado lógico (`anulado_en`), igual que `Comprador` — pero a
diferencia de ese índice, el de esta tabla es total: un ganador anulado
sigue contando para "ese cartón ya ganó esa ronda" y no se puede reinsertar
vivo.
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Ganador
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = (
    "ronda_id",
    "carton_id",
    "bola_numero",
    "confirmado",
    "reparte_premio",
    "registrado_en",
    "confirmado_en",
    "decision",
    "anulado_en",
    "nota",
)


def _desde_fila(fila: sqlite3.Row) -> Ganador:
    return Ganador(
        id=fila["id"],
        ronda_id=fila["ronda_id"],
        carton_id=fila["carton_id"],
        bola_numero=fila["bola_numero"],
        confirmado=bool(fila["confirmado"]),
        reparte_premio=bool(fila["reparte_premio"]),
        registrado_en=fila["registrado_en"],
        confirmado_en=fila["confirmado_en"],
        decision=fila["decision"],
        anulado_en=fila["anulado_en"],
        nota=fila["nota"],
    )


def _a_parametros(ganador: Ganador) -> dict[str, object]:
    return {
        "ronda_id": ganador.ronda_id,
        "carton_id": ganador.carton_id,
        "bola_numero": ganador.bola_numero,
        "confirmado": int(ganador.confirmado),
        "reparte_premio": int(ganador.reparte_premio),
        "registrado_en": ganador.registrado_en or ahora_iso(),
        "confirmado_en": ganador.confirmado_en,
        "decision": ganador.decision,
        "anulado_en": ganador.anulado_en,
        "nota": ganador.nota,
    }


def crear(con: sqlite3.Connection, ganador: Ganador) -> Ganador:
    parametros = _a_parametros(ganador)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(f"INSERT INTO ganador ({columnas}) VALUES ({marcadores})", parametros)
    return dataclasses.replace(
        ganador, id=cursor.lastrowid, registrado_en=parametros["registrado_en"]
    )


def obtener(con: sqlite3.Connection, ganador_id: int) -> Ganador | None:
    fila = con.execute("SELECT * FROM ganador WHERE id = ?", (ganador_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_ronda(con: sqlite3.Connection, ronda_id: int) -> list[Ganador]:
    filas = con.execute(
        "SELECT * FROM ganador WHERE ronda_id = ? ORDER BY bola_numero, id", (ronda_id,)
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def listar_por_evento(con: sqlite3.Connection, evento_id: int) -> list[Ganador]:
    """Une con `ronda` porque `ganador` no lleva `evento_id` propio — el
    reporte del evento (tarea 4.11) y el panel de auditoría necesitan la
    lista completa sin recorrer ronda por ronda."""
    filas = con.execute(
        "SELECT ganador.* FROM ganador "
        "JOIN ronda ON ronda.id = ganador.ronda_id "
        "WHERE ronda.evento_id = ? "
        "ORDER BY ronda.orden, ganador.bola_numero, ganador.id",
        (evento_id,),
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def actualizar_decision(
    con: sqlite3.Connection,
    ganador_id: int,
    *,
    confirmado: bool,
    confirmado_en: str,
    decision: str,
    reparte_premio: bool,
    nota: str | None = None,
) -> None:
    """Verbo puntual de `servicio_ganadores.confirmar` (contrato §5.6)."""
    with traducir_errores_sqlite():
        con.execute(
            "UPDATE ganador SET confirmado = :confirmado, confirmado_en = :confirmado_en, "
            "decision = :decision, reparte_premio = :reparte_premio, nota = :nota "
            "WHERE id = :id",
            {
                "confirmado": int(confirmado),
                "confirmado_en": confirmado_en,
                "decision": decision,
                "reparte_premio": int(reparte_premio),
                "nota": nota,
                "id": ganador_id,
            },
        )


def anular(con: sqlite3.Connection, ganador_id: int, anulado_en: str) -> None:
    with traducir_errores_sqlite():
        con.execute("UPDATE ganador SET anulado_en = ? WHERE id = ?", (anulado_en, ganador_id))


def contar_confirmados_por_ronda(con: sqlite3.Connection, ronda_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM ganador WHERE ronda_id = ? AND confirmado = 1", (ronda_id,)
    ).fetchone()
    return fila["n"] if fila else 0
