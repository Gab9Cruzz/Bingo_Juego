"""PDF del acta de una ronda (contrato §5.9). Cabecera con organización y
evento, patrón y premio, secuencia completa de bolas extraídas en
cuadrícula, ganadores con código y decisión, hash al pie en monoespaciada.

Mismo patrón que `impresion/reporte.py::reporte_conciliacion_pdf` (decisión
D8 de la fase 4): un `Canvas` de ReportLab plano, sin el motor de
`render_pdf.py` (que es del cartón). No importa PySide6 ni sqlite3, ni
i18n — todo texto visible llega ya traducido en `textos`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

_MARGEN = 40
_ALTO_LINEA = 15


def escribir_acta_pdf(
    ruta_destino: Path,
    *,
    organizacion_nombre: str,
    evento_nombre: str,
    ronda_nombre: str,
    patron_nombre: str,
    premio_texto: str,
    numeros: Sequence[int],
    ganadores: Sequence[Mapping[str, object]],
    hash_acta: str,
    textos: Mapping[str, str],
) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo = pdf_canvas.Canvas(str(ruta_destino), pagesize=A4)
    ancho, alto = A4
    y = alto - 50

    lienzo.setFont("Helvetica-Bold", 16)
    lienzo.drawString(_MARGEN, y, textos.get("titulo", "Acta de ronda"))
    y -= 28

    lienzo.setFont("Helvetica", 11)
    for etiqueta, valor in (
        (textos.get("organizacion", "Organización"), organizacion_nombre),
        (textos.get("evento", "Evento"), evento_nombre),
        (textos.get("ronda", "Ronda"), ronda_nombre),
        (textos.get("patron", "Patrón"), patron_nombre),
        (textos.get("premio", "Premio"), premio_texto or "—"),
    ):
        lienzo.drawString(_MARGEN, y, f"{etiqueta}: {valor}")
        y -= _ALTO_LINEA

    y -= 10
    lienzo.setFont("Helvetica-Bold", 12)
    lienzo.drawString(_MARGEN, y, textos.get("bolas", "Bolas extraídas, en orden"))
    y -= 18
    y = _dibujar_bolas(lienzo, numeros, ancho, y)

    y -= 12
    lienzo.setFont("Helvetica-Bold", 12)
    lienzo.drawString(_MARGEN, y, textos.get("ganadores", "Ganadores"))
    y -= 18
    y = _dibujar_ganadores(lienzo, ganadores, textos, alto, y)

    lienzo.setFont("Courier", 8)
    lienzo.drawString(_MARGEN, 40, f"SHA-256: {hash_acta}")

    lienzo.showPage()
    lienzo.save()
    return ruta_destino


def _dibujar_bolas(lienzo, numeros: Sequence[int], ancho: float, y: float) -> float:
    columnas = 15
    ancho_celda = (ancho - 2 * _MARGEN) / columnas
    lienzo.setFont("Helvetica", 9)
    for indice, numero in enumerate(numeros):
        fila, columna = divmod(indice, columnas)
        x = _MARGEN + columna * ancho_celda
        lienzo.drawString(x, y - fila * _ALTO_LINEA, str(numero))
    filas_usadas = (len(numeros) + columnas - 1) // columnas if numeros else 0
    return y - filas_usadas * _ALTO_LINEA


def _dibujar_ganadores(
    lienzo,
    ganadores: Sequence[Mapping[str, object]],
    textos: Mapping[str, str],
    alto: float,
    y: float,
) -> float:
    lienzo.setFont("Helvetica", 10)
    if not ganadores:
        lienzo.drawString(_MARGEN, y, textos.get("sin_ganadores", "Sin ganadores registrados"))
        return y - _ALTO_LINEA
    for ganador in ganadores:
        codigo = ganador.get("codigo", "")
        decision = ganador.get("decision") or textos.get("decision_pendiente", "pendiente")
        lienzo.drawString(_MARGEN, y, f"{codigo} — {decision}")
        y -= _ALTO_LINEA
        if y < 80:
            lienzo.showPage()
            y = alto - 50
            lienzo.setFont("Helvetica", 10)
    return y
