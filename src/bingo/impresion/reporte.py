"""Reportes tabulares en Excel y PDF de la fase 4 (contrato §4.1, §4.2, §4.4;
decisión D8 del plan de la fase 4): plantilla de compradores, informe de
importación y conciliación. Único módulo que escribe `.xlsx` de la fase
(hallazgo A4) — ni `servicio_compradores` ni `servicio_conciliacion` abren
`openpyxl.Workbook()` directamente; `render_pdf.py` es el motor del cartón
(`MotorRenderCarton`) y no comparte nada con esto salvo la librería.

No importa PySide6 ni sqlite3 (verificado por
`tests/arquitectura/test_arquitectura.py`); tampoco i18n — todo texto visible
llega ya traducido en el diccionario `textos` que pasa la vista.

`_escribir_seguro` es la única vía para poner en una celda una cadena que
viene de un dato de comprador (nombre, código): una cadena que empieza por
`=` se guarda con `data_type` explícito de texto (`set_explicit_value`), para
que Excel nunca la interprete como fórmula al abrir el archivo (hallazgo A5:
el vector real de inyección en `.xlsx` es `Cell.value` con `=`; un prefijo
`'` no existe como tal en el modelo de `openpyxl` — sería un no-op).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, Protection
from openpyxl.worksheet.worksheet import Worksheet

_FORMATO_TEXTO = "@"
_LONGITUD_MAXIMA_NOMBRE_HOJA = 31


def _escribir_seguro(hoja: Worksheet, fila: int, columna: int, valor: object) -> None:
    celda = hoja.cell(row=fila, column=columna)
    if isinstance(valor, str) and valor.startswith("="):
        celda.set_explicit_value(valor, data_type="s")
    else:
        celda.value = valor


# ── Plantilla de compradores (contrato §4.1) ──


def escribir_plantilla_compradores(
    codigos: Sequence[str], ruta_destino: Path, textos: Mapping[str, str]
) -> Path:
    """Hoja `Ventas` con una fila por cartón (código bloqueado, resto
    editable) más hoja `Instrucciones`. Protección de hoja + celda bloqueada
    es lo único que hace que Excel respete `locked` (sin `sheet.protection
    .sheet = True`, `locked` no hace nada). Teléfono y cédula llevan
    `number_format = "@"` en toda la columna, no solo el encabezado, para
    que Excel no se coma el cero inicial de un número de teléfono."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Ventas"

    encabezados = [
        textos.get("columna_codigo", "Código"),
        textos.get("columna_nombre", "Nombre"),
        textos.get("columna_telefono", "Teléfono"),
        textos.get("columna_cedula", "Cédula"),
        textos.get("columna_correo", "Correo"),
    ]
    for columna, texto in enumerate(encabezados, start=1):
        celda = hoja.cell(row=1, column=columna, value=texto)
        celda.font = Font(bold=True)
        celda.protection = Protection(locked=True)

    for fila, codigo in enumerate(codigos, start=2):
        celda_codigo = hoja.cell(row=fila, column=1, value=codigo)
        celda_codigo.protection = Protection(locked=True)
        for columna in (2, 3, 4, 5):
            celda = hoja.cell(row=fila, column=columna)
            celda.protection = Protection(locked=False)
            if columna in (3, 4):  # teléfono, cédula
                celda.number_format = _FORMATO_TEXTO

    hoja.column_dimensions["A"].width = 18
    hoja.column_dimensions["B"].width = 28
    hoja.column_dimensions["C"].width = 16
    hoja.column_dimensions["D"].width = 16
    hoja.column_dimensions["E"].width = 26
    hoja.freeze_panes = "A2"
    hoja.protection.sheet = True

    instrucciones = libro.create_sheet(textos.get("hoja_instrucciones", "Instrucciones")[:31])
    for fila, texto in enumerate(_texto_instrucciones(textos), start=1):
        instrucciones.cell(row=fila, column=1, value=texto)
    instrucciones.column_dimensions["A"].width = 100

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta_destino)
    return ruta_destino


def _texto_instrucciones(textos: Mapping[str, str]) -> list[str]:
    # Decisión D.3 (plan de la fase 4): la hoja de instrucciones es el único
    # punto del sistema donde se informa al titular del dato de la finalidad,
    # el plazo de conservación y el responsable del tratamiento — es gratis
    # y cierra parte de la brecha LOPDP que `TODOS.md` P1 sigue dejando
    # pendiente como política.
    claves = (
        "instrucciones_titulo",
        "instrucciones_no_mover_codigo",
        "instrucciones_columnas_reconocidas",
        "instrucciones_cedula_opcional",
        "instrucciones_finalidad",
        "instrucciones_plazo",
        "instrucciones_responsable",
    )
    return [textos[c] for c in claves if c in textos]


# ── Informe de importación (contrato §4.2) ──


def escribir_informe_importacion(
    categorias: Mapping[str, Sequence[Any]], ruta_destino: Path, textos: Mapping[str, str]
) -> Path:
    """Una hoja por categoría con filas (solo las que tengan al menos una
    fila — coherente con la vista, que tampoco pinta categorías vacías)."""
    libro = Workbook()
    libro.remove(libro.active)

    columnas_campo = ("numero_fila", "codigo", "nombre", "telefono", "cedula", "correo")
    for clave, filas in categorias.items():
        if not filas:
            continue
        nombre_hoja = textos.get(f"categoria_{clave}", clave)[:_LONGITUD_MAXIMA_NOMBRE_HOJA]
        hoja = libro.create_sheet(nombre_hoja)
        for columna, campo in enumerate(columnas_campo, start=1):
            texto = textos.get(f"columna_{campo}", campo)
            hoja.cell(row=1, column=columna, value=texto).font = Font(bold=True)
        for fila_indice, item in enumerate(filas, start=2):
            for columna_indice, campo in enumerate(columnas_campo, start=1):
                _escribir_seguro(hoja, fila_indice, columna_indice, getattr(item, campo, None))
        hoja.freeze_panes = "A2"

    if not libro.sheetnames:
        libro.create_sheet(textos.get("hoja_sin_problemas", "Sin problemas"))

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta_destino)
    return ruta_destino


# ── Conciliación (contrato §4.4) ──


def reporte_conciliacion_excel(
    resumen: Mapping[str, object],
    filas_detalle: Sequence[Mapping[str, object]],
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    advertencia: str | None = None,
) -> Path:
    """Hoja `Resumen` (contadores + recaudación) y hoja `Detalle`
    (cartón, estado, comprador...). Qué columnas trae cada fila de
    `filas_detalle` lo decide el llamador (`servicio_conciliacion`), no este
    módulo — la casilla "incluir datos de contacto" (decisión D.3) filtra en
    el origen de los datos, nunca aquí (hallazgo E-M11): si `impresion/`
    recibiera siempre todas las columnas, un futuro llamador podría saltarse
    la casilla."""
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = textos.get("hoja_resumen", "Resumen")[:_LONGITUD_MAXIMA_NOMBRE_HOJA]

    fila = 1
    for clave, valor in resumen.items():
        hoja_resumen.cell(row=fila, column=1, value=textos.get(f"etiqueta_{clave}", clave))
        _escribir_seguro(hoja_resumen, fila, 2, valor)
        fila += 1
    if advertencia:
        fila += 1
        celda = hoja_resumen.cell(row=fila, column=1, value=advertencia)
        celda.font = Font(bold=True, color="C0392B")
    hoja_resumen.column_dimensions["A"].width = 34
    hoja_resumen.column_dimensions["B"].width = 20

    nombre_hoja_detalle = textos.get("hoja_detalle", "Detalle")[:_LONGITUD_MAXIMA_NOMBRE_HOJA]
    hoja_detalle = libro.create_sheet(nombre_hoja_detalle)
    if filas_detalle:
        columnas = list(filas_detalle[0].keys())
        for columna_indice, clave in enumerate(columnas, start=1):
            texto = textos.get(f"columna_{clave}", clave)
            hoja_detalle.cell(row=1, column=columna_indice, value=texto).font = Font(bold=True)
        for fila_indice, datos in enumerate(filas_detalle, start=2):
            for columna_indice, clave in enumerate(columnas, start=1):
                _escribir_seguro(hoja_detalle, fila_indice, columna_indice, datos.get(clave))
    hoja_detalle.freeze_panes = "A2"

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta_destino)
    return ruta_destino


def reporte_conciliacion_pdf(
    resumen: Mapping[str, object],
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    advertencia: str | None = None,
) -> Path:
    """PDF de una página con el resumen — el comprobante que se entrega a la
    organización o al tesorero. No comparte motor con `render_pdf.py`
    (decisión D8): es un `Canvas` de ReportLab plano, sin caché de imágenes
    ni disposición por hoja."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo = pdf_canvas.Canvas(str(ruta_destino), pagesize=A4)
    _, alto = A4
    y = alto - 60

    lienzo.setFont("Helvetica-Bold", 16)
    lienzo.drawString(40, y, textos.get("titulo", "Conciliación"))
    y -= 30

    lienzo.setFont("Helvetica", 11)
    for clave, valor in resumen.items():
        etiqueta = textos.get(f"etiqueta_{clave}", clave)
        lienzo.drawString(40, y, f"{etiqueta}: {valor}")
        y -= 18

    if advertencia:
        y -= 12
        lienzo.setFillColorRGB(0.75, 0.1, 0.1)
        lienzo.setFont("Helvetica-Bold", 11)
        lienzo.drawString(40, y, advertencia)
        lienzo.setFillColorRGB(0, 0, 0)

    lienzo.showPage()
    lienzo.save()
    return ruta_destino


# ── Reporte de evento (contrato de la fase 5, §5.9) ──
#
# Extiende el reporte de conciliación de la fase 4 con una hoja de rondas y
# ganadores — lo que la organización recibe al cerrar el evento. Mismo
# `_escribir_seguro` para nombres de comprador/código (hallazgo A5): el
# reporte del evento lleva nombres de personas tanto como el de
# conciliación.


def reporte_evento_excel(
    resumen: Mapping[str, object],
    filas_cartones: Sequence[Mapping[str, object]],
    filas_rondas: Sequence[Mapping[str, object]],
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    advertencia: str | None = None,
) -> Path:
    """Tres hojas: `Resumen`, `Detalle` (cartones) y `Rondas` (una fila por
    ganador — `servicio_conciliacion` decide qué columnas trae cada fila,
    igual que en `reporte_conciliacion_excel`, hallazgo E-M11)."""
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = textos.get("hoja_resumen", "Resumen")[:_LONGITUD_MAXIMA_NOMBRE_HOJA]

    fila = 1
    for clave, valor in resumen.items():
        hoja_resumen.cell(row=fila, column=1, value=textos.get(f"etiqueta_{clave}", clave))
        _escribir_seguro(hoja_resumen, fila, 2, valor)
        fila += 1
    if advertencia:
        fila += 1
        celda = hoja_resumen.cell(row=fila, column=1, value=advertencia)
        celda.font = Font(bold=True, color="C0392B")
    hoja_resumen.column_dimensions["A"].width = 34
    hoja_resumen.column_dimensions["B"].width = 20

    _agregar_hoja_de_filas(libro, "hoja_detalle", "Detalle", filas_cartones, textos)
    _agregar_hoja_de_filas(libro, "hoja_rondas", "Rondas", filas_rondas, textos)

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta_destino)
    return ruta_destino


def _agregar_hoja_de_filas(
    libro: Workbook,
    clave_titulo: str,
    titulo_defecto: str,
    filas: Sequence[Mapping[str, object]],
    textos: Mapping[str, str],
) -> None:
    nombre_hoja = textos.get(clave_titulo, titulo_defecto)[:_LONGITUD_MAXIMA_NOMBRE_HOJA]
    hoja = libro.create_sheet(nombre_hoja)
    if filas:
        columnas = list(filas[0].keys())
        for columna_indice, clave in enumerate(columnas, start=1):
            texto = textos.get(f"columna_{clave}", clave)
            hoja.cell(row=1, column=columna_indice, value=texto).font = Font(bold=True)
        for fila_indice, datos in enumerate(filas, start=2):
            for columna_indice, clave in enumerate(columnas, start=1):
                _escribir_seguro(hoja, fila_indice, columna_indice, datos.get(clave))
    hoja.freeze_panes = "A2"


def reporte_evento_pdf(
    resumen: Mapping[str, object],
    filas_rondas: Sequence[Mapping[str, object]],
    ruta_destino: Path,
    textos: Mapping[str, str],
    *,
    advertencia: str | None = None,
) -> Path:
    """Resumen de una página + una fila por ganador — nunca datos de
    contacto (decisión UC-3 de la fase 4): el PDF es lo que puede circular
    fuera del control del operador."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo = pdf_canvas.Canvas(str(ruta_destino), pagesize=A4)
    ancho, alto = A4
    y = alto - 60

    lienzo.setFont("Helvetica-Bold", 16)
    lienzo.drawString(40, y, textos.get("titulo", "Reporte del evento"))
    y -= 30

    lienzo.setFont("Helvetica", 11)
    for clave, valor in resumen.items():
        etiqueta = textos.get(f"etiqueta_{clave}", clave)
        lienzo.drawString(40, y, f"{etiqueta}: {valor}")
        y -= 18

    if advertencia:
        y -= 12
        lienzo.setFillColorRGB(0.75, 0.1, 0.1)
        lienzo.setFont("Helvetica-Bold", 11)
        lienzo.drawString(40, y, advertencia)
        lienzo.setFillColorRGB(0, 0, 0)
        y -= 18

    y -= 12
    lienzo.setFont("Helvetica-Bold", 13)
    lienzo.drawString(40, y, textos.get("titulo_rondas", "Rondas y ganadores"))
    y -= 20
    lienzo.setFont("Helvetica", 10)
    if not filas_rondas:
        lienzo.drawString(40, y, textos.get("sin_rondas", "Sin rondas jugadas"))
    for datos in filas_rondas:
        texto = " · ".join(str(v) for v in datos.values() if v not in (None, ""))
        lienzo.drawString(40, y, texto)
        y -= 16
        if y < 60:
            lienzo.showPage()
            y = alto - 60
            lienzo.setFont("Helvetica", 10)

    lienzo.showPage()
    lienzo.save()
    return ruta_destino


# ── Auditoría del evento (tarea 4.19, expansión E3) ──


def reporte_auditoria_excel(
    filas: Sequence[Mapping[str, object]],
    ruta_destino: Path,
    textos: Mapping[str, str],
) -> Path:
    """Una sola hoja (momento, acción, detalle) — sin resumen: el panel de
    auditoría es una tabla, no un tablero. `_escribir_seguro` es igual de
    necesario aquí que en cualquier otro reporte: `detalle` puede llevar
    texto libre de otra fase (p. ej. un motivo de anulación) que empiece
    por `=`."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = textos.get("hoja", "Auditoría")[:_LONGITUD_MAXIMA_NOMBRE_HOJA]
    columnas = ("momento", "accion", "detalle")
    for columna_indice, clave in enumerate(columnas, start=1):
        texto = textos.get(f"columna_{clave}", clave)
        hoja.cell(row=1, column=columna_indice, value=texto).font = Font(bold=True)
    for fila_indice, datos in enumerate(filas, start=2):
        for columna_indice, clave in enumerate(columnas, start=1):
            _escribir_seguro(hoja, fila_indice, columna_indice, datos.get(clave))
    hoja.freeze_panes = "A2"
    hoja.column_dimensions["A"].width = 20
    hoja.column_dimensions["B"].width = 28
    hoja.column_dimensions["C"].width = 50

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta_destino)
    return ruta_destino
