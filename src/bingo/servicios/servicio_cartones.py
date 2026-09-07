"""Casos de uso de generación de cartones (documento técnico §4.3, contrato
de la fase 2, revisión `/autoplan` en `docs/Fase_2/Plan_Implementacion_Fase2.md`).

Convenio del trabajador `QThread` (`docs/convenciones-codigo.md`): este módulo
nunca importa PySide6. `generar_lote` acepta `al_progresar` y `debe_cancelar`
como invocables simples; es `ui/tarea.py::Tarea` quien los conecta a señales de
Qt desde el hilo de la interfaz.

Nota de implementación sobre la "semilla" (resuelve una tensión del propio
contrato): el documento técnico dice que `generar_carton` recibe
`secrets.SystemRandom()` en producción, pero `secrets.SystemRandom` no admite
semilla — no se puede "registrar la semilla para reproducirlo" de algo que no
se puede volver a sembrar. La resolución: en producción se genera una semilla
criptográficamente aleatoria (`secrets.token_hex(16)`, 128 bits de entropía
del sistema operativo) y se siembra un `random.Random` determinista con ella.
Un cartón de bingo no tiene el mismo requisito de imprevisibilidad frente a un
adversario que una bola de sorteo en vivo (fase 5, donde sí se usa
`secrets.SystemRandom()` sin semilla): aquí la garantía que importa es
"nadie puede predecir cuál es tu cartón antes de comprarlo", que 128 bits de
semilla ya cubren de sobra, y a cambio se obtiene reproducibilidad real.
"""

from __future__ import annotations

import re
import secrets
import sqlite3
from collections.abc import Callable
from random import Random

from bingo.config.ajustes import (
    LIMITE_CARTONES_POR_LOTE,
    LONGITUD_MAXIMA_PREFIJO_CODIGO,
    TAMANO_BLOQUE_INSERCION_CARTONES,
    TOPE_COLISIONES_FIRMA_CONSECUTIVAS,
)
from bingo.dominio import carton as dominio_carton
from bingo.dominio.estados import TRANSICIONES_CARTON, puede_transicionar
from bingo.dominio.modelos import Carton, Lote
from bingo.persistencia import repo_auditoria, repo_carton, repo_lote
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import (
    ErrorDominio,
    ErrorNoEncontrado,
    ErrorTransicionInvalida,
    ErrorValidacion,
)
from bingo.utilidades.fechas import ahora_iso

PATRON_PREFIJO_CODIGO = re.compile(r"^[A-Za-z0-9-]+$")
_COMPROBAR_CANCELAR_CADA = 50


def _validar_cantidad(cantidad: int) -> None:
    if cantidad <= 0:
        raise ErrorValidacion("cartones.error.cantidad_invalida", campo="cantidad")
    if cantidad > LIMITE_CARTONES_POR_LOTE:
        raise ErrorValidacion(
            "cartones.error.cantidad_excede_maximo",
            campo="cantidad",
            parametros={"limite": LIMITE_CARTONES_POR_LOTE},
        )


def _validar_prefijo(con: sqlite3.Connection, evento_id: int, prefijo_codigo: str) -> str:
    prefijo = prefijo_codigo.strip()
    if not prefijo:
        raise ErrorValidacion("cartones.error.prefijo_vacio", campo="prefijo_codigo")
    if len(prefijo) > LONGITUD_MAXIMA_PREFIJO_CODIGO or not PATRON_PREFIJO_CODIGO.match(prefijo):
        raise ErrorValidacion(
            "cartones.error.prefijo_invalido",
            campo="prefijo_codigo",
            parametros={"limite": LONGITUD_MAXIMA_PREFIJO_CODIGO},
        )
    if repo_lote.existe_prefijo(con, evento_id, prefijo):
        raise ErrorValidacion(
            "cartones.error.prefijo_repetido",
            campo="prefijo_codigo",
            parametros={"prefijo": prefijo},
        )
    return prefijo


def _codigo_correlativo(prefijo: str, anio: int, secuencia: int, ancho: int) -> str:
    return f"{prefijo}-{anio}-{secuencia:0{ancho}d}"


def generar_lote(
    con: sqlite3.Connection,
    evento_id: int,
    cantidad: int,
    prefijo_codigo: str,
    *,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
    rng: Random | None = None,
    semilla: str | None = None,
) -> Lote:
    """Genera un lote de `cantidad` cartones únicos para `evento_id`.

    `rng`/`semilla` son el punto de inyección para pruebas: sin ellos, produce
    una semilla nueva de `secrets.token_hex(16)` y siembra su propio
    `random.Random`. Con `rng` inyectado y sin `semilla` explícita, se
    registra `"personalizada"` en `lote.semilla` — ese camino es solo para
    pruebas que necesitan un generador fabricado a mano (p. ej. uno que
    siempre repite la misma firma, para ejercitar el tope de colisiones).
    """
    _validar_cantidad(cantidad)
    prefijo = _validar_prefijo(con, evento_id, prefijo_codigo)

    if rng is None:
        semilla = semilla or secrets.token_hex(16)
        rng = Random(semilla)
    elif semilla is None:
        semilla = "personalizada"

    with transaccion(con):
        lote = repo_lote.crear(
            con,
            Lote(evento_id=evento_id, cantidad=cantidad, prefijo_codigo=prefijo, semilla=semilla),
        )
        repo_auditoria.registrar(con, evento_id, "lote.creado", detalle=f"{prefijo}, {cantidad}")

    firmas_vistas = repo_carton.listar_firmas_por_evento(con, evento_id)
    anio = int(ahora_iso()[:4])
    ancho = len(str(cantidad))

    generados = 0
    cancelado = False
    bloque: list[Carton] = []

    while generados < cantidad:
        if (
            debe_cancelar is not None
            and generados % _COMPROBAR_CANCELAR_CADA == 0
            and debe_cancelar()
        ):
            cancelado = True
            break

        intentos_consecutivos = 0
        while True:
            matriz = dominio_carton.generar_carton(rng)
            firma = dominio_carton.firma(matriz)
            if firma not in firmas_vistas:
                break
            intentos_consecutivos += 1
            if intentos_consecutivos >= TOPE_COLISIONES_FIRMA_CONSECUTIVAS:
                raise ErrorDominio(
                    "cartones.error.generacion_bloqueada",
                    parametros={"intentos": TOPE_COLISIONES_FIRMA_CONSECUTIVAS},
                )
        firmas_vistas.add(firma)

        codigo = _codigo_correlativo(prefijo, anio, generados + 1, ancho)
        bloque.append(
            Carton(
                evento_id=evento_id,
                lote_id=lote.id,
                codigo=codigo,
                numeros=dominio_carton.orden_canonico(matriz),
                firma=firma,
            )
        )
        generados += 1

        if len(bloque) >= TAMANO_BLOQUE_INSERCION_CARTONES or generados == cantidad:
            with transaccion(con):
                repo_carton.crear_varios(con, bloque)
            bloque = []
            if al_progresar is not None:
                al_progresar(generados, cantidad)

    if cancelado:
        with transaccion(con):
            repo_carton.eliminar_por_lote(con, lote.id)
            repo_lote.eliminar(con, lote.id)
            repo_auditoria.registrar(
                con, evento_id, "lote.cancelado", detalle=f"{generados}/{cantidad} generados"
            )
        return lote

    with transaccion(con):
        repo_lote.marcar_completado(con, lote.id)
        repo_auditoria.registrar(con, evento_id, "lote.completado", detalle=f"{cantidad} cartones")

    return repo_lote.obtener(con, lote.id) or lote


def limpiar_lotes_huerfanos(con: sqlite3.Connection) -> int:
    """Corre al arrancar la app (antes de mostrar cualquier ventana). Cada
    lote huérfano se limpia en su propia transacción — una fila corrupta no
    debe bloquear la limpieza del resto (revisión Eng de la fase 2).
    """
    huerfanos = repo_lote.listar_huerfanos(con)
    limpiados = 0
    for lote in huerfanos:
        with transaccion(con):
            cartones_eliminados = repo_carton.eliminar_por_lote(con, lote.id)
            repo_lote.eliminar(con, lote.id)
            repo_auditoria.registrar(
                con,
                lote.evento_id,
                "lote.huerfano_limpiado",
                detalle=f"lote {lote.id}, {cartones_eliminados} cartones",
            )
        limpiados += 1
    return limpiados


def cambiar_estado_carton(con: sqlite3.Connection, carton_id: int, nuevo_estado: str) -> None:
    """Valida la transición contra `dominio.estados` antes de escribir, igual
    que `servicio_eventos.cambiar_estado`.
    """
    actual = repo_carton.obtener(con, carton_id)
    if actual is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": carton_id})

    if not puede_transicionar(TRANSICIONES_CARTON, actual.estado, nuevo_estado):
        raise ErrorTransicionInvalida(
            "error.transicion_invalida", parametros={"actual": actual.estado, "nuevo": nuevo_estado}
        )

    with transaccion(con):
        repo_carton.actualizar_estado(con, carton_id, nuevo_estado)
        repo_auditoria.registrar(
            con,
            actual.evento_id,
            "carton.cambio_estado",
            detalle=f"{actual.estado} -> {nuevo_estado}",
        )
