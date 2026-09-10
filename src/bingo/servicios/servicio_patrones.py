"""Casos de uso de `patron` (contrato de la fase 4, §4.5, §4.6).

`asegurar_patrones_sistema` resuelve `TODOS.md` P2 ("carga de los patrones
del sistema... se difiere a la fase 4"). Se llama desde `__main__.py` justo
después de las migraciones, en su propia `transaccion()` por patrón (una
fila con datos corruptos no debe bloquear la precarga del resto).
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.config.ajustes import VERSION_SEMILLA_PATRONES_SISTEMA
from bingo.dominio.modelos import Patron
from bingo.dominio.patron import PATRONES_SISTEMA, usa_libre_incoherente
from bingo.persistencia import repo_auditoria, repo_patron, repo_ronda
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorDominio, ErrorNoEncontrado, ErrorValidacion


def asegurar_patrones_sistema(con: sqlite3.Connection) -> int:
    """Idempotente por `clave_i18n`: crea los patrones del sistema que
    falten y actualiza (máscaras, descripción, `usa_libre`) los que están en
    una `version_semilla` anterior a `VERSION_SEMILLA_PATRONES_SISTEMA` —
    salvo que una ronda de un evento que ya no esté en `borrador` los use
    (decisión DS16 del plan de la fase 4): cambiar en silencio la definición
    de quién gana un premio en un evento activo no es aceptable. Devuelve
    cuántos patrones creó o actualizó.
    """
    afectados = 0
    for spec in PATRONES_SISTEMA:
        existente = repo_patron.obtener_por_clave_i18n(con, spec.clave_i18n)
        if existente is None:
            with transaccion(con):
                repo_patron.crear(
                    con,
                    Patron(
                        nombre=spec.nombre_es,
                        mascaras=list(spec.mascaras),
                        clave_i18n=spec.clave_i18n,
                        descripcion=spec.descripcion_i18n,
                        usa_libre=spec.usa_libre,
                        es_sistema=True,
                        version_semilla=VERSION_SEMILLA_PATRONES_SISTEMA,
                        organizacion_id=None,
                    ),
                )
            afectados += 1
            continue

        if existente.version_semilla >= VERSION_SEMILLA_PATRONES_SISTEMA:
            continue

        if repo_ronda.contar_por_patron_en_eventos_no_borrador(con, existente.id) > 0:
            with transaccion(con):
                repo_auditoria.registrar(
                    con,
                    None,
                    "patron.actualizacion_omitida",
                    detalle=f"{spec.clave_i18n}: en uso por rondas de eventos activos",
                )
            continue

        with transaccion(con):
            repo_patron.actualizar(
                con,
                dataclasses.replace(
                    existente,
                    mascaras=list(spec.mascaras),
                    descripcion=spec.descripcion_i18n,
                    usa_libre=spec.usa_libre,
                    version_semilla=VERSION_SEMILLA_PATRONES_SISTEMA,
                ),
            )
        afectados += 1
    return afectados


def validar_patron(con: sqlite3.Connection, patron: Patron) -> None:
    if not patron.nombre.strip():
        raise ErrorValidacion("patrones.error.nombre_vacio", campo="nombre")
    if not patron.mascaras:
        raise ErrorValidacion("patrones.error.sin_mascaras", campo="mascaras")
    limite = (1 << 25) - 1
    for m in patron.mascaras:
        if not (1 <= m <= limite):
            raise ErrorValidacion(
                "patrones.error.mascara_invalida", campo="mascaras", parametros={"valor": m}
            )
    if usa_libre_incoherente(patron.mascaras, patron.usa_libre):
        raise ErrorValidacion("patrones.error.libre_incoherente", campo="usa_libre")
    if repo_patron.existe_nombre(con, patron.organizacion_id, patron.nombre, excluir_id=patron.id):
        raise ErrorValidacion(
            "patrones.error.nombre_repetido", campo="nombre", parametros={"nombre": patron.nombre}
        )


def crear_patron(con: sqlite3.Connection, patron: Patron) -> Patron:
    a_crear = dataclasses.replace(patron, es_sistema=False, clave_i18n=None, version_semilla=0)
    validar_patron(con, a_crear)
    with transaccion(con):
        creado = repo_patron.crear(con, a_crear)
        repo_auditoria.registrar(con, None, "patron.creado", detalle=creado.nombre)
    return creado


def duplicar_patron(
    con: sqlite3.Connection, patron_id: int, nombre_nuevo: str, organizacion_id: int
) -> Patron:
    """Copia un patrón (del sistema o propio) como patrón editable de
    `organizacion_id`. Es la única vía para "editar" un patrón del sistema
    (contrato §4.6: no se borran, solo se duplican)."""
    original = repo_patron.obtener(con, patron_id)
    if original is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": patron_id})
    copia = dataclasses.replace(
        original,
        id=None,
        nombre=nombre_nuevo,
        clave_i18n=None,
        es_sistema=False,
        version_semilla=0,
        organizacion_id=organizacion_id,
    )
    return crear_patron(con, copia)


def eliminar_patron(con: sqlite3.Connection, patron_id: int) -> None:
    patron = repo_patron.obtener(con, patron_id)
    if patron is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": patron_id})
    if patron.es_sistema:
        raise ErrorDominio("patrones.error.es_sistema")
    en_uso = repo_ronda.contar_por_patron(con, patron_id)
    if en_uso > 0:
        raise ErrorDominio("patrones.error.en_uso", parametros={"cantidad": en_uso})
    with transaccion(con):
        repo_patron.eliminar(con, patron_id)
        repo_auditoria.registrar(con, None, "patron.eliminado", detalle=patron.nombre)
