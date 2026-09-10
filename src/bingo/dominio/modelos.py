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
    clave_evento: str | None = None  # HMAC del QR de los cartones (fase 3, dominio/firma.py)
    recaudado_real_centavos: int | None = None  # declarado por el operador (fase 4)
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


@dataclass(slots=True)
class Comprador:
    """Fase 4. `provisional=True` marca las filas que crea
    `servicio_compradores.marcar_vendidos_por_rango` sin datos de contacto
    (venta de puerta): el cartón participa bajo la regla de elegibilidad
    estricta sin que nadie haya tecleado un nombre real todavía (decisión
    UC-1 + D4, `docs/Fase_4/Plan_Implementacion_Fase4.md` ANEXO D.1).

    `anulado_en` es un borrado lógico, no `None` en un `DELETE` (decisión
    A3): la auditoría de una venta anulada necesita seguir apuntando a una
    fila que existe. `estado_carton_previo` es el estado al que
    `anular_venta` devuelve el cartón (hallazgo C2: no siempre es
    `entregado`).
    """

    carton_id: int
    nombre: str
    id: int | None = None
    telefono: str | None = None
    cedula: str | None = None
    correo: str | None = None
    provisional: bool = False
    estado_carton_previo: str | None = None
    anulado_en: str | None = None
    registrado_en: str = ""


@dataclass(slots=True)
class Patron:
    """Fase 4. `mascaras` es una lista de enteros de 25 bits: un patrón gana
    con que se cumpla cualquiera de ellas (decisión D1, doc técnico §16.1).
    `clave_i18n` identifica un patrón del sistema para la retraducción y la
    idempotencia de `servicio_patrones.asegurar_patrones_sistema`; es `None`
    en un patrón propio de una organización. `nombre` guarda el texto en
    español como respaldo si `clave_i18n` no resuelve (decisión M9) — la
    vista siempre prioriza `t(clave_i18n)`.
    """

    nombre: str
    mascaras: list[int]
    id: int | None = None
    clave_i18n: str | None = None
    descripcion: str | None = None
    usa_libre: bool = True
    es_sistema: bool = False
    version_semilla: int = 0
    organizacion_id: int | None = None


@dataclass(slots=True)
class Ronda:
    """Fase 4. `orden` lo asigna `servicio_rondas.crear_ronda`
    (`MAX(orden) + 1` del evento); el valor que traiga el objeto al crear se
    ignora. `estado` sigue la máquina de `dominio/estados.py::TRANSICIONES_RONDA`
    (fase 5).

    `iniciada_en`, `cerrada_en`, `acta_hash` y `acta_generada_en` (fase 5,
    migración 004) **nunca** se escriben con `repo_ronda.actualizar()`
    (hallazgo A1, crítico, plan de la fase 5): ese verbo reescribe *todas*
    las columnas de `_COLUMNAS` desde el objeto en memoria, y una `Ronda`
    cargada al abrir una vista de preparación no lleva el `acta_hash` que
    otra pantalla acaba de escribir — el último que guarde borraría el del
    otro. Se escriben solo con los verbos puntuales `actualizar_inicio`,
    `actualizar_cierre` y `actualizar_acta`.
    """

    evento_id: int
    nombre: str
    patron_id: int
    id: int | None = None
    orden: int = 0
    premio_nombre: str | None = None
    premio_tipo: str | None = None  # 'efectivo' | 'bien' | None
    premio_valor_centavos: int | None = None
    premio_descripcion: str | None = None
    premio_imagen: str | None = None
    estado: str = "pendiente"
    iniciada_en: str | None = None
    cerrada_en: str | None = None
    acta_hash: str | None = None
    acta_generada_en: str | None = None


@dataclass(slots=True)
class Extraccion:
    """Fase 5. Una bola extraída de una ronda. `orden` es la posición dentro
    de la ronda (1, 2, 3...), asignada por `servicio_sorteo.MotorSorteo`, no
    por el repositorio: el bombo es quien sabe cuántas bolas van salidas."""

    ronda_id: int
    orden: int
    numero: int
    id: int | None = None
    extraida_en: str = ""


@dataclass(slots=True)
class Ganador:
    """Fase 5. Una fila por cartón detectado ganador de una ronda —
    detección y registro son dos cosas distintas (decisión D8): el motor
    solo persiste las detecciones de la primera bola que produjo ganador
    (`bola_numero`), y a partir de ahí `decision` la fija
    `servicio_ganadores.confirmar`.

    `decision`: `None` mientras está pendiente; luego `"unico"`,
    `"reparto"`, `"desempate_externo"`, `"no_reclamado"` o `"rechazado"`.
    `anulado_en` es un borrado lógico (mismo patrón que `Comprador`, fase 4):
    la fila no se borra nunca, porque `idx_ganador_ronda_carton` es total
    (hallazgo V1) y una reanudación no debe poder reinsertarla viva.
    """

    ronda_id: int
    carton_id: int
    bola_numero: int
    id: int | None = None
    confirmado: bool = False
    reparte_premio: bool = False
    registrado_en: str = ""
    confirmado_en: str | None = None
    decision: str | None = None
    anulado_en: str | None = None
    nota: str | None = None
