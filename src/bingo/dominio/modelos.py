"""Entidades de dominio sin comportamiento propio (solo registro).

`dominio/` no importa nada del proyecto salvo `utilidades/errores`; nunca
PySide6 ni sqlite3 (verificado por `tests/arquitectura/test_arquitectura.py`).
Los repositorios devuelven estos objetos, nunca `sqlite3.Row`: si la UI
recibiera `Row`, terminaría indexando por nombre de columna y el acoplamiento
al esquema se filtraría igual que si el SQL viviera fuera de `persistencia/`.

Entidades con comportamiento propio (generación de cartones, evaluación de
patrones, extracción de bolas) viven en su propio módulo de `dominio/`
(`carton.py`, `patron.py`, `bombo.py`, fases siguientes), no aquí. `Lote` y
`Carton` (fase 2) son solo registro — el álgebra del cartón opera sobre
`list[list[int | None]]`, no sobre `Carton` de este módulo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Organizacion:
    nombre: str
    id: int | None = None
    logo_path: str | None = None
    logo_secundario: str | None = None
    color_primario: str = "#1a1a2e"
    color_secundario: str = "#e94560"
    color_texto: str = "#ffffff"
    tipografia: str | None = None
    contacto: str | None = None
    eslogan: str | None = None
    pie_pagina: str | None = None
    condiciones: str | None = None
    aviso_legal: str | None = None
    creada_en: str = ""


@dataclass(slots=True)
class Evento:
    organizacion_id: int
    nombre: str
    id: int | None = None
    fecha: str | None = None
    hora: str | None = None
    lugar: str | None = None
    precio_tabla_centavos: int = 0
    estado: str = "borrador"
    plantilla_json: str | None = None
    tema_json: str | None = None
    creado_en: str = ""


@dataclass(slots=True)
class RegistroAuditoria:
    accion: str
    id: int | None = None
    evento_id: int | None = None
    momento: str = ""
    detalle: str | None = None


@dataclass(slots=True)
class Lote:
    evento_id: int
    cantidad: int
    prefijo_codigo: str
    semilla: str
    id: int | None = None
    generado_en: str = ""
    completado_en: str | None = None  # NULL = en curso o huérfano (fase 2)


@dataclass(slots=True)
class Carton:
    evento_id: int
    lote_id: int
    codigo: str
    numeros: str  # 24 números, orden canónico, coma-separado (dominio/carton.py)
    firma: str
    id: int | None = None
    estado: str = "generado"
