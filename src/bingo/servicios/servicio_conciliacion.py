"""Casos de uso de conciliación (contrato de la fase 4, §4.4).

`calcular` se apoya en `repo_carton.contar_por_estado` (ya existe desde la
fase 2) y `repo_comprador.contar_por_evento`. La recaudación teórica es
multiplicación de enteros — cero coma flotante en el camino de un
comprobante que se entrega a la organización (`dominio/dinero.py`).

**Discrepancia (hallazgo E-C1 del plan de la fase 4):** se compara
`vendidos` contra el total de compradores vivos (provisionales +
registrados), no solo contra los registrados. Con la venta por rango
(decisión D.1) un evento con ventas de puerta tiene compradores
provisionales de sobra y legítimos; compararlos aparte los convertiría en
una falsa alarma permanente en vez de la discrepancia real que el reporte
debe hacer visible (un `vendido` sin ninguna fila `comprador`, viva o
provisional — el invariante que `servicio_cartones.cambiar_estado_carton`
ya impide crear por la vía genérica).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bingo.dominio.dinero import formatear
from bingo.impresion import reporte
from bingo.persistencia import repo_carton, repo_comprador, repo_evento, repo_ganador, repo_ronda
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorValidacion


@dataclass(slots=True, frozen=True)
class Conciliacion:
    generados: int
    impresos: int
    entregados: int
    vendidos: int
    anulados: int
    total_cartones: int
    precio_tabla_centavos: int
    recaudacion_teorica_centavos: int
    compradores_registrados: int
    compradores_provisionales: int
    recaudado_real_centavos: int | None
    diferencia_centavos: int | None
    discrepancia: bool


def calcular(con: sqlite3.Connection, evento_id: int) -> Conciliacion:
    evento = repo_evento.obtener(con, evento_id)
    if evento is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})

    conteo = repo_carton.contar_por_estado(con, evento_id)
    vendidos = conteo.get("vendido", 0)
    registrados = repo_comprador.contar_por_evento(con, evento_id, provisional=False)
    provisionales = repo_comprador.contar_por_evento(con, evento_id, provisional=True)
    teorica = vendidos * evento.precio_tabla_centavos
    real = evento.recaudado_real_centavos
    diferencia = (real - teorica) if real is not None else None

    return Conciliacion(
        generados=conteo.get("generado", 0),
        impresos=conteo.get("impreso", 0),
        entregados=conteo.get("entregado", 0),
        vendidos=vendidos,
        anulados=conteo.get("anulado", 0),
        total_cartones=sum(conteo.values()),
        precio_tabla_centavos=evento.precio_tabla_centavos,
        recaudacion_teorica_centavos=teorica,
        compradores_registrados=registrados,
        compradores_provisionales=provisionales,
        recaudado_real_centavos=real,
        diferencia_centavos=diferencia,
        discrepancia=vendidos != (registrados + provisionales),
    )


def declarar_recaudado_real(con: sqlite3.Connection, evento_id: int, centavos: int | None) -> None:
    if centavos is not None and centavos < 0:
        raise ErrorValidacion("conciliacion.error.recaudado_negativo", campo="recaudado_real")
    with transaccion(con):
        repo_evento.actualizar_recaudado_real(con, evento_id, centavos)


def _resumen(conciliacion: Conciliacion, idioma: str) -> dict[str, object]:
    resumen: dict[str, object] = {
        "generados": conciliacion.generados,
        "impresos": conciliacion.impresos,
        "entregados": conciliacion.entregados,
        "vendidos": conciliacion.vendidos,
        "anulados": conciliacion.anulados,
        "total_cartones": conciliacion.total_cartones,
        "compradores_registrados": conciliacion.compradores_registrados,
        "compradores_provisionales": conciliacion.compradores_provisionales,
        "recaudacion_teorica": formatear(conciliacion.recaudacion_teorica_centavos, idioma),
    }
    if conciliacion.recaudado_real_centavos is not None:
        resumen["recaudado_real"] = formatear(conciliacion.recaudado_real_centavos, idioma)
    if conciliacion.diferencia_centavos is not None:
        resumen["diferencia"] = formatear(conciliacion.diferencia_centavos, idioma)
    return resumen


def _filas_detalle(
    con: sqlite3.Connection, evento_id: int, *, incluir_contacto: bool
) -> list[dict[str, object]]:
    cartones = repo_carton.listar_por_evento(con, evento_id, limite=None)
    compradores = repo_comprador.mapa_por_evento(con, evento_id)
    filas: list[dict[str, object]] = []
    for carton in cartones:
        comprador = compradores.get(carton.id)
        fila: dict[str, object] = {
            "codigo": carton.codigo,
            "estado": carton.estado,
            "comprador": comprador.nombre if comprador else "",
        }
        if incluir_contacto:
            fila["telefono"] = comprador.telefono if comprador else ""
            fila["cedula"] = comprador.cedula if comprador else ""
            fila["correo"] = comprador.correo if comprador else ""
        filas.append(fila)
    return filas


def generar_reporte_excel(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    idioma: str = "es",
    incluir_contacto: bool = False,
) -> Path:
    """`incluir_contacto=False` por defecto (decisión D.3): el `.xlsx` de
    conciliación viaja por WhatsApp; sin la casilla explícita marcada, la
    hoja `Detalle` no lleva teléfono, cédula ni correo — la decisión de qué
    columnas pedir se toma aquí, no en `impresion/reporte.py` (hallazgo
    E-M11)."""
    conciliacion = calcular(con, evento_id)
    resumen = _resumen(conciliacion, idioma)
    advertencia = textos.get("advertencia_discrepancia") if conciliacion.discrepancia else None
    filas = _filas_detalle(con, evento_id, incluir_contacto=incluir_contacto)
    return reporte.reporte_conciliacion_excel(
        resumen, filas, ruta_destino, textos, advertencia=advertencia
    )


def generar_reporte_pdf(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    idioma: str = "es",
) -> Path:
    """El PDF nunca lleva datos de contacto (decisión D.3): es el resumen,
    no el detalle cartón por cartón."""
    conciliacion = calcular(con, evento_id)
    resumen = _resumen(conciliacion, idioma)
    advertencia = textos.get("advertencia_discrepancia") if conciliacion.discrepancia else None
    return reporte.reporte_conciliacion_pdf(resumen, ruta_destino, textos, advertencia=advertencia)


def _filas_rondas(
    con: sqlite3.Connection, evento_id: int, *, incluir_contacto: bool
) -> list[dict[str, object]]:
    """Una fila por ganador **no anulado** (tarea 4.11): un ganador anulado
    es un hecho descartado por el operador, no algo que la organización
    necesite ver en el reporte que se le entrega. Datos de contacto solo
    con la casilla marcada (decisión UC-3 de la fase 4) — el reporte del
    evento lleva nombres de personas tanto como el de conciliación."""
    filas: list[dict[str, object]] = []
    for ronda in repo_ronda.listar_por_evento(con, evento_id):
        ganadores = [
            g for g in repo_ganador.listar_por_ronda(con, ronda.id) if g.anulado_en is None
        ]
        if not ganadores:
            filas.append(
                {
                    "ronda": ronda.nombre,
                    "premio": ronda.premio_nombre or "",
                    "codigo": "",
                    "comprador": "",
                    "decision": "",
                }
            )
            continue
        for ganador in ganadores:
            carton = repo_carton.obtener(con, ganador.carton_id)
            comprador = (
                repo_comprador.obtener_por_carton(con, ganador.carton_id, incluir_anulados=True)
                if carton is not None
                else None
            )
            fila: dict[str, object] = {
                "ronda": ronda.nombre,
                "premio": ronda.premio_nombre or "",
                "codigo": carton.codigo if carton is not None else "?",
                "comprador": comprador.nombre if comprador is not None else "",
                "decision": ganador.decision or "",
            }
            if incluir_contacto and comprador is not None:
                fila["telefono"] = comprador.telefono
                fila["cedula"] = comprador.cedula
                fila["correo"] = comprador.correo
            filas.append(fila)
    return filas


def generar_reporte_evento_excel(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    idioma: str = "es",
    incluir_contacto: bool = False,
) -> Path:
    """El reporte del evento (contrato de la fase 5, §5.9): lo mismo que
    `generar_reporte_excel`, más una hoja `Rondas` con los ganadores."""
    conciliacion = calcular(con, evento_id)
    resumen = _resumen(conciliacion, idioma)
    advertencia = textos.get("advertencia_discrepancia") if conciliacion.discrepancia else None
    filas_cartones = _filas_detalle(con, evento_id, incluir_contacto=incluir_contacto)
    filas_rondas = _filas_rondas(con, evento_id, incluir_contacto=incluir_contacto)
    return reporte.reporte_evento_excel(
        resumen, filas_cartones, filas_rondas, ruta_destino, textos, advertencia=advertencia
    )


def generar_reporte_evento_pdf(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    idioma: str = "es",
) -> Path:
    """Nunca datos de contacto (decisión UC-3): es el resumen que puede
    circular fuera del control del operador."""
    conciliacion = calcular(con, evento_id)
    resumen = _resumen(conciliacion, idioma)
    advertencia = textos.get("advertencia_discrepancia") if conciliacion.discrepancia else None
    filas_rondas = _filas_rondas(con, evento_id, incluir_contacto=False)
    return reporte.reporte_evento_pdf(
        resumen, filas_rondas, ruta_destino, textos, advertencia=advertencia
    )
