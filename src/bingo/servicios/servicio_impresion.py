"""Casos de uso de generación de PDF de cartones (contrato de la fase 3, §3.5;
documento técnico §5.2).

Convenio del trabajador `QThread` (`docs/convenciones-codigo.md`): este
módulo nunca importa PySide6. `generar_pdf_lote` acepta `al_progresar` y
`debe_cancelar` como invocables simples, igual que
`servicios/servicio_cartones.py::generar_lote`; es `ui/tarea.py::Tarea` quien
los conecta a señales de Qt desde el hilo de la interfaz.

Memoria acotada (contrato §5.2.3-4, riesgo anotado en
`docs/Fase_3/Plan_Implementacion_Fase3.md` §5): un `Canvas` de ReportLab
retiene todo su documento en memoria hasta `.save()`, así que lo que evita un
PDF de 10.000 cartones de cientos de MB es la combinación de dos cosas, no
una — (a) abrir un `Canvas`/archivo nuevo cada `hojas_por_archivo` hojas
acota cuánto retiene en memoria un único documento abierto, y (b) el caché de
`ImageReader` de `MotorRenderCarton` evita recodificar el mismo logo en cada
página.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from bingo.config.ajustes import HOJAS_POR_ARCHIVO_DEFECTO
from bingo.dominio import carton as dominio_carton
from bingo.dominio.estados import TRANSICIONES_CARTON, puede_transicionar
from bingo.dominio.modelos import Lote, Organizacion
from bingo.impresion.plantilla import PlantillaCarton, validar
from bingo.impresion.render_pdf import MotorRenderCarton
from bingo.persistencia import (
    repo_auditoria,
    repo_carton,
    repo_evento,
    repo_lote,
    repo_organizacion,
)
from bingo.persistencia.conexion import transaccion
from bingo.servicios import servicio_eventos
from bingo.utilidades.errores import ErrorDominio, ErrorNoEncontrado, ErrorTransicionInvalida


def _cargar_contexto(
    con: sqlite3.Connection, evento_id: int, lote_id: int
) -> tuple[PlantillaCarton, str, Organizacion, Lote]:
    """Lee evento, lote, organización y clave; construye y valida la plantilla.
    Reutilizado por `generar_pdf_lote` y por la vista previa (`vista_plantilla`).
    """
    evento = repo_evento.obtener(con, evento_id)
    if evento is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})
    lote = repo_lote.obtener(con, lote_id)
    if lote is None or lote.evento_id != evento_id:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": lote_id})
    organizacion = repo_organizacion.obtener(con, evento.organizacion_id)
    if organizacion is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento.organizacion_id})

    clave_evento = servicio_eventos.asegurar_clave_evento(con, evento_id)
    plantilla = (
        PlantillaCarton.desde_json(evento.plantilla_json)
        if evento.plantilla_json
        else PlantillaCarton.por_defecto(organizacion)
    )
    validar(plantilla)
    return plantilla, clave_evento, organizacion, lote


def generar_pdf_lote(
    con: sqlite3.Connection,
    evento_id: int,
    lote_id: int,
    carpeta_destino: Path,
    *,
    hojas_por_archivo: int = HOJAS_POR_ARCHIVO_DEFECTO,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
) -> list[Path]:
    """Genera el/los PDF de un lote. Devuelve las rutas escritas, en orden.

    Un archivo nuevo cada `hojas_por_archivo` hojas — nombres numerados
    (`<prefijo_lote>_parte_NN.pdf`), lo que además facilita mandar a imprenta
    por tandas (contrato §3.5.5). Cancelable: al detectarse `debe_cancelar()`,
    se cierra el `Canvas` en curso (un PDF parcial es una impresión más
    corta, no un archivo corrupto) y se detiene sin seguir con el resto.
    """
    plantilla, clave_evento, organizacion, lote = _cargar_contexto(con, evento_id, lote_id)

    cartones = repo_carton.listar_por_lote(con, lote_id)
    if not cartones:
        raise ErrorDominio("impresion.error.lote_vacio", parametros={"id": lote_id})

    motor = MotorRenderCarton(plantilla, organizacion, clave_evento)
    por_hoja = plantilla.hoja.cartones_por_hoja

    carpeta_destino.mkdir(parents=True, exist_ok=True)
    rutas_generadas: list[Path] = []
    canvas_actual: Canvas | None = None
    hojas_en_archivo = 0
    indice_archivo = 0
    total = len(cartones)
    procesados = 0

    def _abrir_archivo() -> Canvas:
        nonlocal indice_archivo
        indice_archivo += 1
        ruta = carpeta_destino / f"{lote.prefijo_codigo}_parte_{indice_archivo:02d}.pdf"
        rutas_generadas.append(ruta)
        return Canvas(str(ruta), pagesize=motor.tamano_hoja())

    for inicio in range(0, total, por_hoja):
        if debe_cancelar is not None and debe_cancelar():
            break

        if canvas_actual is None or hojas_en_archivo >= hojas_por_archivo:
            if canvas_actual is not None:
                canvas_actual.save()
            canvas_actual = _abrir_archivo()
            hojas_en_archivo = 0

        grupo = cartones[inicio : inicio + por_hoja]
        cartones_hoja = [
            (carton.codigo, dominio_carton.carton_desde_orden_canonico(carton.numeros))
            for carton in grupo
        ]
        motor.renderizar_pagina(canvas_actual, cartones_hoja)
        hojas_en_archivo += 1
        procesados += len(grupo)
        if al_progresar is not None:
            al_progresar(procesados, total)

    if canvas_actual is not None:
        canvas_actual.save()

    return rutas_generadas


def marcar_lote_impreso(con: sqlite3.Connection, lote_id: int) -> int:
    """Pasa a `impreso` solo los cartones del lote que siguen en `generado`
    (contrato §3.5.6: "al terminar, ofrecer marcar el lote como impreso").
    Devuelve cuántos cambiaron. Acción explícita del operador, no automática
    al final de `generar_pdf_lote` — puede querer revisar el PDF primero.
    """
    lote = repo_lote.obtener(con, lote_id)
    if lote is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": lote_id})
    if not puede_transicionar(TRANSICIONES_CARTON, "generado", "impreso"):
        raise ErrorTransicionInvalida(
            "error.transicion_invalida", parametros={"actual": "generado", "nuevo": "impreso"}
        )

    with transaccion(con):
        cambiados = repo_carton.actualizar_estado_por_lote(con, lote_id, "generado", "impreso")
        repo_auditoria.registrar(
            con, lote.evento_id, "lote.marcado_impreso", detalle=f"{cambiados} cartones"
        )
    return cambiados
