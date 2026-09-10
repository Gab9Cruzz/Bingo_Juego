"""Motor de render de PDF de cartones (contrato de la fase 3, §3.2; documento
técnico §5.2).

`MotorRenderCarton` es la única unidad de dibujo: `servicios/servicio_impresion.py`
(el PDF de producción) y `ui/vistas/vista_plantilla.py` (la vista previa,
decisión D4 de `docs/Fase_3/Plan_Implementacion_Fase3.md`) lo instancian igual
y llaman los mismos métodos sobre un `reportlab.pdfgen.canvas.Canvas` real —
nunca hay una segunda ruta de dibujo "aproximada" para la vista previa, que es
justo lo que el contrato prohíbe.

Cachea logos y marca de agua como `ImageReader` una sola vez por instancia
(requisito §5.2.4 del contrato): pasar el mismo objeto `ImageReader` a
`canvas.drawImage` en todas las páginas es lo que evita incrustar el mismo
logo miles de veces en el PDF.
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, A5, landscape, letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from bingo.dominio.carton import BIT_LIBRE, MatrizCarton, indice_bit
from bingo.dominio.firma import contenido_qr
from bingo.dominio.modelos import Organizacion
from bingo.impresion.plantilla import PlantillaCarton

logger = logging.getLogger("bingo.impresion")

_LETRAS_DEFECTO = ("B", "I", "N", "G", "O")

_TAMANOS_HOJA: dict[str, tuple[float, float]] = {
    "A4": A4,
    "Carta": letter,
    "A5": A5,
}

# (filas, columnas) de la rejilla de cartones por hoja, en orientación vertical.
# En horizontal se transponen (ver `_disposicion_grilla`).
_GRILLA_VERTICAL: dict[int, tuple[int, int]] = {
    1: (1, 1),
    2: (2, 1),
    4: (2, 2),
    6: (3, 2),
}

_PAQUETE_FUENTES = "bingo.recursos.fuentes"
_ARCHIVOS_FUENTE = {
    "Merriweather": "Merriweather/Merriweather-Variable.ttf",
    "Open Sans": "OpenSans/OpenSans-Variable.ttf",
}
_fuentes_registradas: set[str] = set()


def _asegurar_fuente_registrada(nombre: str) -> str:
    """Registra `nombre` en ReportLab la primera vez que se pide y devuelve el
    nombre a usar en `canvas.setFont`. Si no es una de las empaquetadas o el
    registro falla, cae a Helvetica/Helvetica-Bold sin lanzar: un logo o una
    tipografía rota no debe tumbar el lote completo de impresión.
    """
    if nombre in ("Helvetica", "Helvetica-Bold", "Courier", "Times-Roman"):
        return nombre
    if nombre not in _ARCHIVOS_FUENTE:
        return "Helvetica"
    if nombre in _fuentes_registradas:
        return nombre
    try:
        ruta = resources.files(_PAQUETE_FUENTES).joinpath(_ARCHIVOS_FUENTE[nombre])
        with resources.as_file(ruta) as ruta_local:
            pdfmetrics.registerFont(TTFont(nombre, str(ruta_local)))
        _fuentes_registradas.add(nombre)
        return nombre
    except Exception:  # noqa: BLE001 - una fuente rota no debe tumbar el render
        logger.warning("No se pudo registrar la fuente %r; usando Helvetica", nombre, exc_info=True)
        return "Helvetica"


def _tamano_hoja(plantilla: PlantillaCarton) -> tuple[float, float]:
    base = _TAMANOS_HOJA.get(plantilla.hoja.tamano, A4)
    return landscape(base) if plantilla.hoja.orientacion == "horizontal" else base


def _disposicion_grilla(plantilla: PlantillaCarton) -> tuple[int, int]:
    filas, columnas = _GRILLA_VERTICAL.get(plantilla.hoja.cartones_por_hoja, (1, 1))
    if plantilla.hoja.orientacion == "horizontal":
        filas, columnas = columnas, filas
    return filas, columnas


class MotorRenderCarton:
    """Dibuja cartones sobre un `Canvas` de ReportLab según una `PlantillaCarton`.

    Se construye una vez por operación de render (un lote completo, o una
    sola vista previa): el `__init__` carga y cachea todas las imágenes que
    la plantilla necesita, para que ningún método de dibujo vuelva a tocar
    el disco.
    """

    def __init__(
        self,
        plantilla: PlantillaCarton,
        organizacion: Organizacion,
        clave_evento: str,
    ) -> None:
        self._plantilla = plantilla
        self._organizacion = organizacion
        self._clave_evento = clave_evento
        self._cache_imagenes: dict[str, ImageReader | None] = {}
        self._fuente_numeros = _asegurar_fuente_registrada(plantilla.numeros.fuente)
        # Precarga: logo principal, secundario, fondo, marca de agua. Cachear
        # aquí y no en `dibujar_carton` es lo que evita releer/recodificar la
        # misma imagen miles de veces (contrato §5.2.4).
        for ruta in (
            plantilla.marca.logo,
            plantilla.marca.logo_secundario,
            plantilla.marca.fondo,
        ):
            self._imagen(ruta)

    def _imagen(self, ruta: str | None) -> ImageReader | None:
        if not ruta:
            return None
        if ruta in self._cache_imagenes:
            return self._cache_imagenes[ruta]
        lector: ImageReader | None
        try:
            lector = None if not Path(ruta).exists() else ImageReader(ruta)
        except Exception:  # noqa: BLE001 - una imagen rota no debe tumbar el render
            logger.warning("No se pudo cargar la imagen %r", ruta, exc_info=True)
            lector = None
        self._cache_imagenes[ruta] = lector
        return lector

    # --- Disposición de la hoja -------------------------------------------------

    def tamano_hoja(self) -> tuple[float, float]:
        return _tamano_hoja(self._plantilla)

    def calcular_disposicion(self) -> list[tuple[float, float, float, float]]:
        """Posiciones `(x, y, ancho, alto)` en puntos, origen abajo-izquierda
        (convención de ReportLab), una por cartón de la hoja. Una tabla fija
        por `cartones_por_hoja` (1/2/4/6 son los únicos valores soportados,
        ver `config/ajustes.CARTONES_POR_HOJA_SOPORTADOS`) es más simple y más
        fácil de verificar a mano contra una hoja impresa que un algoritmo de
        empaquetado genérico — nota de riesgo del propio contrato.
        """
        ancho_hoja, alto_hoja = self.tamano_hoja()
        margen = self._plantilla.hoja.margen_mm * mm
        filas, columnas = _disposicion_grilla(self._plantilla)

        ancho_usable = ancho_hoja - 2 * margen
        alto_usable = alto_hoja - 2 * margen
        ancho_celda = ancho_usable / columnas
        alto_celda = alto_usable / filas

        posiciones: list[tuple[float, float, float, float]] = []
        for fila in range(filas):
            for columna in range(columnas):
                x = margen + columna * ancho_celda
                # fila 0 = arriba de la hoja; el origen de ReportLab es abajo.
                y = alto_hoja - margen - (fila + 1) * alto_celda
                posiciones.append((x, y, ancho_celda, alto_celda))
        return posiciones

    def dibujar_marcas_corte(
        self, canvas: Canvas, posiciones: list[tuple[float, float, float, float]]
    ) -> None:
        """Solo tiene sentido con más de un cartón por hoja (contrato §3.2)."""
        if len(posiciones) <= 1:
            return
        largo = 4 * mm
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#888888"))
        canvas.setLineWidth(0.4)
        for x, y, ancho, alto in posiciones:
            for esquina_x in (x, x + ancho):
                for esquina_y in (y, y + alto):
                    canvas.line(esquina_x - largo, esquina_y, esquina_x + largo, esquina_y)
                    canvas.line(esquina_x, esquina_y - largo, esquina_x, esquina_y + largo)
        canvas.restoreState()

    # --- Dibujo de un cartón -----------------------------------------------

    def dibujar_carton(
        self,
        canvas: Canvas,
        codigo: str,
        matriz: MatrizCarton,
        x: float,
        y: float,
        ancho: float,
        alto: float,
    ) -> None:
        """La unidad básica que pide el contrato: un cartón, en una posición y
        tamaño dados. Todo lo que dibuja está controlado por `self._plantilla`.
        """
        marca = self._plantilla.marca
        canvas.saveState()

        fondo = self._imagen(marca.fondo)
        if fondo is not None:
            canvas.saveState()
            canvas.setFillAlpha(marca.opacidad_fondo)
            canvas.drawImage(fondo, x, y, width=ancho, height=alto, mask="auto")
            canvas.restoreState()

        reservado_arriba = self._dibujar_marca(canvas, x, y, ancho, alto)
        reservado_abajo = self._dibujar_textos_pie(canvas, x, y, ancho)

        area_y = y + reservado_abajo
        area_alto = alto - reservado_arriba - reservado_abajo
        self._dibujar_grilla(canvas, matriz, x, area_y, ancho, area_alto)

        self._dibujar_identificacion(canvas, codigo, x, y, ancho, alto)

        if self._plantilla.identificacion.marca_agua and self._organizacion.logo_path:
            self._dibujar_marca_agua(canvas, x, y, ancho, alto)

        canvas.restoreState()

    def _dibujar_marca(
        self, canvas: Canvas, x: float, y: float, ancho: float, alto: float
    ) -> float:
        """Logo + título + subtítulo + texto superior. Devuelve la altura
        reservada en la parte superior del cartón para que la grilla no se
        dibuje encima.
        """
        marca = self._plantilla.marca
        texto_superior = self._plantilla.textos.superior
        alto_logo = marca.logo_alto_mm * mm if marca.logo else 0.0
        alto_titulo = 5 * mm if marca.titulo else 0.0
        alto_subtitulo = 3.5 * mm if marca.subtitulo else 0.0
        alto_texto_superior = 3 * mm if texto_superior else 0.0
        margen_superior = 2 * mm if marca.logo or marca.titulo else 0
        reservado = (
            max(alto_logo, alto_titulo + alto_subtitulo) + alto_texto_superior + margen_superior
        )

        techo_logo = y + alto - alto_texto_superior  # debajo del texto superior, si lo hay

        logo = self._imagen(marca.logo)
        if logo is not None:
            ancho_logo, alto_original = logo.getSize()
            proporcion = alto_logo / alto_original if alto_original else 1
            ancho_dibujo = ancho_logo * proporcion
            pos_x = {
                "superior_izquierda": x + 2 * mm,
                "superior_centro": x + (ancho - ancho_dibujo) / 2,
                "superior_derecha": x + ancho - ancho_dibujo - 2 * mm,
            }.get(marca.logo_pos, x + 2 * mm)
            canvas.drawImage(
                logo,
                pos_x,
                techo_logo - alto_logo,
                width=ancho_dibujo,
                height=alto_logo,
                mask="auto",
                preserveAspectRatio=True,
            )

        texto_y = techo_logo - 4 * mm
        if marca.titulo:
            canvas.setFillColor(HexColor(marca.color_encabezado))
            canvas.setFont(self._fuente_numeros, 11)
            canvas.drawCentredString(x + ancho / 2, texto_y, marca.titulo)
            texto_y -= 4.5 * mm
        if marca.subtitulo:
            canvas.setFillColor(HexColor(marca.color_encabezado))
            canvas.setFont(self._fuente_numeros, 8)
            canvas.drawCentredString(x + ancho / 2, texto_y, marca.subtitulo)

        if texto_superior:
            canvas.setFont("Helvetica", 6)
            canvas.setFillColor(HexColor("#555555"))
            canvas.drawCentredString(x + ancho / 2, y + alto - 2.5 * mm, texto_superior[:140])

        return reservado

    def _dibujar_textos_pie(self, canvas: Canvas, x: float, y: float, ancho: float) -> float:
        """Texto inferior y contacto (el texto superior lo dibuja `_dibujar_marca`,
        junto al logo/título — 'superior' e 'inferior' son posiciones en el
        cartón, no dos líneas del mismo bloque)."""
        textos = self._plantilla.textos
        lineas = [t for t in (textos.inferior, textos.contacto) if t]
        if not lineas:
            return 0.0
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(HexColor("#555555"))
        reservado = 3 * mm * len(lineas) + 1 * mm
        texto_y = y + reservado - 3 * mm
        for linea in lineas:
            canvas.drawCentredString(x + ancho / 2, texto_y, linea[:140])
            texto_y -= 3 * mm
        return reservado

    def _dibujar_grilla(
        self, canvas: Canvas, matriz: MatrizCarton, x: float, y: float, ancho: float, alto: float
    ) -> None:
        encabezado = self._plantilla.encabezado
        alto_encabezado = 6 * mm if encabezado.mostrar else 0.0
        alto_grilla = alto - alto_encabezado
        lado_celda = min(ancho / 5, alto_grilla / 5)
        ancho_total = lado_celda * 5
        alto_total = lado_celda * 5
        origen_x = x + (ancho - ancho_total) / 2
        origen_y = y + (alto - alto_encabezado - alto_total) / 2

        letras = encabezado.letras if len(encabezado.letras) == 5 else list(_LETRAS_DEFECTO)
        if encabezado.mostrar:
            canvas.setFillColor(HexColor(self._plantilla.marca.color_encabezado))
            canvas.rect(
                origen_x, origen_y + alto_total, ancho_total, alto_encabezado, stroke=0, fill=1
            )
            canvas.setFont(self._fuente_numeros, min(alto_encabezado * 0.6, 12))
            canvas.setFillColor(HexColor("#ffffff"))
            for columna, letra in enumerate(letras):
                canvas.drawCentredString(
                    origen_x + (columna + 0.5) * lado_celda,
                    origen_y + alto_total + alto_encabezado * 0.28,
                    letra,
                )

        canvas.setStrokeColor(HexColor(self._plantilla.marca.color_grilla))
        canvas.setLineWidth(0.6)
        tamano_numero = min(self._plantilla.numeros.tamano_pt, lado_celda * 0.6)
        canvas.setFont(self._fuente_numeros, tamano_numero)
        canvas.setFillColor(HexColor("#000000"))

        for fila in range(5):
            for columna in range(5):
                celda_x = origen_x + columna * lado_celda
                # fila 0 del dominio es la de arriba; ReportLab dibuja desde abajo.
                celda_y = origen_y + (4 - fila) * lado_celda
                canvas.rect(celda_x, celda_y, lado_celda, lado_celda, stroke=1, fill=0)

                valor = matriz[fila][columna]
                centro_x = celda_x + lado_celda / 2
                centro_y = celda_y + lado_celda * 0.35
                if indice_bit(fila, columna) == BIT_LIBRE and valor is None:
                    self._dibujar_libre(canvas, centro_x, centro_y, lado_celda)
                else:
                    canvas.drawCentredString(centro_x, centro_y, str(valor))

    def _dibujar_libre(
        self, canvas: Canvas, centro_x: float, centro_y: float, lado_celda: float
    ) -> None:
        libre = self._plantilla.libre
        if libre.tipo == "logo" and self._imagen(self._plantilla.marca.logo) is not None:
            logo = self._imagen(self._plantilla.marca.logo)
            lado = lado_celda * 0.7
            canvas.drawImage(
                logo,
                centro_x - lado / 2,
                centro_y - lado * 0.2,
                width=lado,
                height=lado,
                mask="auto",
                preserveAspectRatio=True,
            )
        elif libre.tipo == "estrella":
            canvas.setFont(self._fuente_numeros, lado_celda * 0.5)
            canvas.drawCentredString(centro_x, centro_y, "★")
        else:
            tamano = min(8, lado_celda * 0.22)
            canvas.setFont("Helvetica", tamano)
            canvas.drawCentredString(centro_x, centro_y, libre.texto or "LIBRE")

    def _dibujar_identificacion(
        self, canvas: Canvas, codigo: str, x: float, y: float, ancho: float, alto: float
    ) -> None:
        identificacion = self._plantilla.identificacion
        lado_qr = 14 * mm if identificacion.qr else 0.0
        margen_interno = 2 * mm

        pos_x, pos_y = {
            "inferior_izquierda": (x + margen_interno, y + margen_interno),
            "inferior_centro": (x + (ancho - lado_qr) / 2, y + margen_interno),
            "inferior_derecha": (x + ancho - lado_qr - margen_interno, y + margen_interno),
        }.get(identificacion.pos, (x + ancho - lado_qr - margen_interno, y + margen_interno))

        if identificacion.qr:
            texto_qr = contenido_qr(self._clave_evento, codigo)
            _dibujar_qr(canvas, texto_qr, pos_x, pos_y, lado_qr)

        if identificacion.mostrar_codigo:
            canvas.setFont("Helvetica", 6)
            canvas.setFillColor(HexColor("#000000"))
            texto_x = pos_x + lado_qr / 2 if identificacion.qr else x + ancho - margen_interno
            ancla = canvas.drawCentredString if identificacion.qr else canvas.drawRightString
            ancla(texto_x, pos_y - 2.5 * mm if identificacion.qr else y + margen_interno, codigo)

    def _dibujar_marca_agua(
        self, canvas: Canvas, x: float, y: float, ancho: float, alto: float
    ) -> None:
        logo = self._imagen(self._organizacion.logo_path)
        if logo is None:
            return
        lado = min(ancho, alto) * 0.6
        canvas.saveState()
        canvas.setFillAlpha(self._plantilla.identificacion.opacidad_marca_agua)
        canvas.drawImage(
            logo,
            x + (ancho - lado) / 2,
            y + (alto - lado) / 2,
            width=lado,
            height=lado,
            mask="auto",
            preserveAspectRatio=True,
        )
        canvas.restoreState()

    # --- Página completa ----------------------------------------------------

    def renderizar_pagina(self, canvas: Canvas, cartones: list[tuple[str, MatrizCarton]]) -> None:
        """Coloca hasta `cartones_por_hoja` cartones y hace `showPage()`. Una
        llamada = una hoja física. `cartones` es `[(codigo, matriz), ...]`.
        """
        posiciones = self.calcular_disposicion()
        for (codigo, matriz), (x, y, ancho, alto) in zip(cartones, posiciones, strict=False):
            self.dibujar_carton(canvas, codigo, matriz, x, y, ancho, alto)
        if self._plantilla.hoja.marcas_corte:
            self.dibujar_marcas_corte(canvas, posiciones[: len(cartones)])
        canvas.showPage()


def _dibujar_qr(canvas: Canvas, texto: str, x: float, y: float, lado: float) -> None:
    """Dibuja un QR de `lado` puntos con esquina inferior-izquierda en `(x, y)`.

    Receta estándar de ReportLab: el widget de barcode no se dibuja
    directamente sobre un `Canvas`, se envuelve en un `Drawing` escalado al
    tamaño deseado y se pinta con `renderPDF.draw`.
    """
    if lado <= 0:
        return
    widget = QrCodeWidget(texto)
    x0, y0, x1, y1 = widget.getBounds()
    ancho_natural = x1 - x0
    alto_natural = y1 - y0
    dibujo = Drawing(
        lado,
        lado,
        transform=[lado / ancho_natural, 0, 0, lado / alto_natural, 0, 0],
    )
    dibujo.add(widget)
    renderPDF.draw(dibujo, canvas, x, y)
