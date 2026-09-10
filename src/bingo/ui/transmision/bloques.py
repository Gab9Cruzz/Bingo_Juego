"""Pintores de la ventana de transmisión (contrato §5.4, decisión D14).

Lienzo lógico 1920x1080: cada función pinta en esas coordenadas — la
ventana aplica la escala una sola vez (`ui/transmision/escala.py`) antes de
invocar a estas, nunca al revés.

Reusa `dominio.tema.BLOQUES` para el tamaño de cada bloque (decisión
DU-4/tarea 4.21): es la misma tabla que `vista_tema.py::_LienzoPrevia`
consulta para la vista previa de preparación — lo que se configura es
literalmente lo que sale. La posición real de cada bloque (editable) vive
en la instancia de `ConfigBloque` del tema, no en `BLOQUES`.

El texto de cada bloque de estado vive en `contenido.py`, no aquí: la regla
que no se negocia (nunca código ni nombre antes de `ganador_confirmado`) se
prueba sobre el texto, no sobre píxeles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from bingo.dominio.patron import celdas_desde_mascara
from bingo.dominio.tema import BLOQUES, ConfigBloque, TemaDashboard
from bingo.ui.transmision import contenido
from bingo.ui.transmision.estado_transmision import EstadoTransmision

ANCHO_LOGICO = 1920
ALTO_LOGICO = 1080

_FORMA_POR_CLAVE: dict[str, tuple[float, float]] = {
    clave: (ancho_frac, alto_frac) for clave, _ci, _px, _py, ancho_frac, alto_frac in BLOQUES
}


@dataclass(slots=True)
class ContextoTransmision:
    """Todo lo que un fotograma necesita. Se reconstruye antes de cada
    `paintEvent` a partir del estado en memoria — no guarda nada que no
    venga de otro lado, para que un `paintEvent` repetido nunca desincronice
    lo que se ve de lo que de verdad pasó."""

    tema: TemaDashboard
    estado: EstadoTransmision
    idioma: str
    numero_actual: int | None = None
    numeros_extraidos: frozenset[int] = frozenset()
    restantes_bombo: int = 75
    patron_mascara: int | None = None
    nombre_patron: str = ""
    premio_texto: str = ""
    canal_reclamo: str = ""
    segundos_restantes_reclamo: int | None = None
    a_una_bola_cantidad: int = 0
    codigo_ganador: str = ""
    nombre_ganador: str = ""
    texto_bienvenida: str = ""
    texto_cierre: str = ""
    ganadores_recientes: list = field(default_factory=list)


def _rect_bloque(clave: str, bloque: ConfigBloque) -> QRectF:
    ancho_frac, alto_frac = _FORMA_POR_CLAVE[clave]
    ancho = ANCHO_LOGICO * ancho_frac * bloque.escala
    alto = ALTO_LOGICO * alto_frac * bloque.escala
    x = bloque.pos_x * ANCHO_LOGICO
    y = bloque.pos_y * ALTO_LOGICO
    return QRectF(x, y, ancho, alto)


def _fuente(tamano: float, *, negrita: bool = False) -> QFont:
    fuente = QFont()
    fuente.setPointSizeF(max(tamano, 6.0))
    fuente.setBold(negrita)
    return fuente


def pintar_fondo(painter: QPainter, tema: TemaDashboard) -> None:
    painter.fillRect(QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO), QColor(tema.colores.fondo))


def pintar_numero_actual(painter: QPainter, tema: TemaDashboard, numero: int | None) -> None:
    bloque = tema.numero_actual
    if not bloque.visible:
        return
    rect = _rect_bloque("numero_actual", bloque)
    painter.fillRect(rect, QColor(tema.colores.fondo).darker(115))
    painter.setFont(_fuente(rect.height() * 0.55, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.numero_actual)))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(numero) if numero else "—")


def pintar_contador_bolas(painter: QPainter, tema: TemaDashboard, extraidas: int) -> None:
    bloque = tema.contador_bolas
    if not bloque.visible:
        return
    rect = _rect_bloque("contador_bolas", bloque)
    painter.setFont(_fuente(rect.height() * 0.5))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{extraidas} / 75")


def pintar_reloj(painter: QPainter, tema: TemaDashboard, texto_hora: str) -> None:
    bloque = tema.reloj
    if not bloque.visible:
        return
    rect = _rect_bloque("reloj", bloque)
    painter.setFont(_fuente(rect.height() * 0.5))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto_hora)


def pintar_bombo(painter: QPainter, tema: TemaDashboard, restantes: int) -> None:
    bloque = tema.bombo
    if not bloque.visible:
        return
    rect = _rect_bloque("bombo", bloque)
    painter.setPen(QPen(QColor(tema.colores.acento)))
    painter.drawEllipse(rect)
    painter.setFont(_fuente(rect.height() * 0.25))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(restantes))


def pintar_tablero_75(
    painter: QPainter, tema: TemaDashboard, numeros_extraidos: frozenset[int], ultima: int | None
) -> None:
    bloque = tema.tablero_75
    if not bloque.visible:
        return
    rect = _rect_bloque("tablero_75", bloque)
    ancho_celda = rect.width() / 5
    alto_celda = rect.height() / 15
    painter.setFont(_fuente(alto_celda * 0.5))
    numero = 1
    for columna in range(5):
        for fila in range(15):
            celda = QRectF(
                rect.x() + columna * ancho_celda,
                rect.y() + fila * alto_celda,
                ancho_celda,
                alto_celda,
            )
            marcado = numero in numeros_extraidos
            if marcado:
                painter.fillRect(celda, QColor(tema.colores.tablero_marcado))
                color_texto = "#ffffff"
            else:
                color_texto = tema.colores.texto
            if numero == ultima:
                lapiz = QPen(QColor(tema.colores.numero_actual))
                lapiz.setWidth(4)
                painter.setPen(lapiz)
                painter.drawRect(celda.adjusted(1, 1, -1, -1))
            painter.setPen(QPen(QColor(color_texto)))
            fuente_celda = painter.font()
            fuente_celda.setBold(marcado)
            painter.setFont(fuente_celda)
            painter.drawText(celda, Qt.AlignmentFlag.AlignCenter, str(numero))
            numero += 1


def pintar_patron_activo(painter: QPainter, tema: TemaDashboard, mascara: int | None) -> None:
    bloque = tema.patron_activo
    if not bloque.visible or mascara is None:
        return
    rect = _rect_bloque("patron_activo", bloque)
    lado = min(rect.width(), rect.height()) / 5
    origen_x = rect.x() + (rect.width() - lado * 5) / 2
    origen_y = rect.y() + (rect.height() - lado * 5) / 2
    celdas_encendidas = set(celdas_desde_mascara(mascara))
    for fila in range(5):
        for columna in range(5):
            celda = QRectF(origen_x + columna * lado, origen_y + fila * lado, lado, lado)
            if (fila, columna) in celdas_encendidas:
                painter.fillRect(celda, QColor(tema.colores.acento))
            painter.setPen(QPen(QColor(tema.colores.texto)))
            painter.drawRect(celda)


def pintar_logo(painter: QPainter, tema: TemaDashboard) -> None:
    bloque = tema.logo
    if not bloque.visible:
        return
    rect = _rect_bloque("logo", bloque)
    painter.setPen(QPen(QColor(tema.colores.texto)))
    painter.drawRect(rect)


def pintar_imagen_premio(painter: QPainter, tema: TemaDashboard) -> None:
    bloque = tema.imagen_premio
    if not bloque.visible:
        return
    rect = _rect_bloque("imagen_premio", bloque)
    painter.setPen(QPen(QColor(tema.colores.texto)))
    painter.drawRect(rect)


def pintar_banner_texto(painter: QPainter, tema: TemaDashboard) -> None:
    if not tema.banner_texto.visible or not tema.banner_texto.texto:
        return
    alto = ALTO_LOGICO * 0.03
    rect = QRectF(0, ALTO_LOGICO - alto, ANCHO_LOGICO, alto)
    painter.fillRect(rect, QColor(tema.colores.acento))
    painter.setPen(QPen(QColor("#ffffff")))
    painter.setFont(_fuente(alto * 0.5))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, tema.banner_texto.texto)


def _pintar_overlay_fondo(painter: QPainter, tema: TemaDashboard, opacidad: float = 0.85) -> None:
    color = QColor(tema.colores.fondo)
    color.setAlphaF(opacidad)
    painter.fillRect(QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO), color)


def pintar_overlay_bienvenida(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    _pintar_overlay_fondo(painter, tema, opacidad=1.0)
    painter.setFont(_fuente(90, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    texto = contenido.texto_bienvenida(ctx.idioma, ctx.texto_bienvenida)
    painter.drawText(QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO), Qt.AlignmentFlag.AlignCenter, texto)


def pintar_overlay_hay_carton_ganador(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    """**Regla que no se negocia (contrato §5.4):** el patrón completado, y
    nada más. Ni código ni nombre — eso es exclusivo de
    `pintar_overlay_ganador_confirmado`."""
    _pintar_overlay_fondo(painter, tema)
    pintar_patron_activo(painter, tema, ctx.patron_mascara)
    texto = contenido.texto_hay_carton_ganador(
        ctx.idioma, ctx.canal_reclamo, ctx.segundos_restantes_reclamo
    )
    rect_texto = QRectF(0, ALTO_LOGICO * 0.75, ANCHO_LOGICO, ALTO_LOGICO * 0.2)
    painter.setFont(_fuente(48, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.numero_actual)))
    painter.drawText(rect_texto, Qt.AlignmentFlag.AlignCenter, texto)


def pintar_overlay_reclamo_vencido(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    _pintar_overlay_fondo(painter, tema)
    painter.setFont(_fuente(56, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    painter.drawText(
        QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO),
        Qt.AlignmentFlag.AlignCenter,
        contenido.texto_reclamo_vencido(ctx.idioma),
    )


def pintar_overlay_ganador_confirmado(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    """El único lugar de toda la transmisión donde se pintan código y
    nombre juntos."""
    _pintar_overlay_fondo(painter, tema, opacidad=1.0)
    painter.setFont(_fuente(96, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.numero_actual)))
    texto = contenido.texto_ganador_confirmado(ctx.idioma, ctx.codigo_ganador, ctx.nombre_ganador)
    painter.drawText(QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO), Qt.AlignmentFlag.AlignCenter, texto)


def pintar_overlay_entre_rondas(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    _pintar_overlay_fondo(painter, tema, opacidad=1.0)
    pintar_patron_activo(painter, tema, ctx.patron_mascara)
    painter.setFont(_fuente(56, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    texto = contenido.texto_entre_rondas(ctx.idioma, ctx.nombre_patron, ctx.premio_texto)
    painter.drawText(
        QRectF(0, ALTO_LOGICO * 0.7, ANCHO_LOGICO, ALTO_LOGICO * 0.2),
        Qt.AlignmentFlag.AlignCenter,
        texto,
    )


def pintar_overlay_a_una_bola(
    painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision
) -> None:
    """DU-10: mismo bloque siempre visible con la cantidad; tratamiento
    dramático (color de número actual, no de acento) cuando quedan tres o
    menos — ahí es donde vive la tensión del juego."""
    rect = QRectF(ANCHO_LOGICO * 0.55, ALTO_LOGICO * 0.02, ANCHO_LOGICO * 0.4, ALTO_LOGICO * 0.08)
    dramatico = ctx.a_una_bola_cantidad <= 3
    color_fondo = tema.colores.numero_actual if dramatico else tema.colores.acento
    painter.fillRect(rect, QColor(color_fondo))
    painter.setPen(QPen(QColor("#0b0b14" if dramatico else "#ffffff")))
    painter.setFont(_fuente(rect.height() * 0.5, negrita=True))
    texto = contenido.texto_a_una_bola(ctx.idioma, ctx.a_una_bola_cantidad)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, texto)


def pintar_overlay_pausa(painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision) -> None:
    rect = QRectF(ANCHO_LOGICO * 0.35, 0, ANCHO_LOGICO * 0.3, ALTO_LOGICO * 0.08)
    painter.fillRect(rect, QColor(tema.colores.acento))
    painter.setPen(QPen(QColor("#ffffff")))
    painter.setFont(_fuente(rect.height() * 0.5, negrita=True))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, contenido.texto_pausa(ctx.idioma))


def pintar_overlay_cierre(painter: QPainter, tema: TemaDashboard, ctx: ContextoTransmision) -> None:
    _pintar_overlay_fondo(painter, tema, opacidad=1.0)
    painter.setFont(_fuente(80, negrita=True))
    painter.setPen(QPen(QColor(tema.colores.texto)))
    texto = contenido.texto_cierre(ctx.idioma, ctx.texto_cierre)
    painter.drawText(QRectF(0, 0, ANCHO_LOGICO, ALTO_LOGICO), Qt.AlignmentFlag.AlignCenter, texto)


_OVERLAYS_POR_ESTADO = {
    EstadoTransmision.BIENVENIDA: pintar_overlay_bienvenida,
    EstadoTransmision.A_UNA_BOLA_CRITICA: pintar_overlay_a_una_bola,
    EstadoTransmision.HAY_CARTON_GANADOR: pintar_overlay_hay_carton_ganador,
    EstadoTransmision.RECLAMO_VENCIDO: pintar_overlay_reclamo_vencido,
    EstadoTransmision.GANADOR_CONFIRMADO: pintar_overlay_ganador_confirmado,
    EstadoTransmision.ENTRE_RONDAS: pintar_overlay_entre_rondas,
    EstadoTransmision.PAUSA: pintar_overlay_pausa,
    EstadoTransmision.CIERRE: pintar_overlay_cierre,
}

# Estados de pantalla completa (sin los bloques persistentes debajo).
_ESTADOS_EXCLUSIVOS = frozenset(
    {
        EstadoTransmision.BIENVENIDA,
        EstadoTransmision.GANADOR_CONFIRMADO,
        EstadoTransmision.ENTRE_RONDAS,
        EstadoTransmision.CIERRE,
    }
)


def pintar_fotograma(painter: QPainter, ctx: ContextoTransmision, texto_hora: str = "") -> None:
    """Un fotograma completo, en coordenadas lógicas 1920x1080. El llamante
    (`ventana_transmision.py`) ya aplicó la escala real antes de esto."""
    pintar_fondo(painter, ctx.tema)

    if ctx.estado not in _ESTADOS_EXCLUSIVOS:
        pintar_numero_actual(painter, ctx.tema, ctx.numero_actual)
        pintar_bombo(painter, ctx.tema, ctx.restantes_bombo)
        pintar_tablero_75(painter, ctx.tema, ctx.numeros_extraidos, ctx.numero_actual)
        pintar_contador_bolas(painter, ctx.tema, len(ctx.numeros_extraidos))
        pintar_reloj(painter, ctx.tema, texto_hora)
        pintar_patron_activo(painter, ctx.tema, ctx.patron_mascara)
        pintar_logo(painter, ctx.tema)
        pintar_imagen_premio(painter, ctx.tema)
        pintar_banner_texto(painter, ctx.tema)

    pintor_overlay = _OVERLAYS_POR_ESTADO.get(ctx.estado)
    if pintor_overlay is not None:
        pintor_overlay(painter, ctx.tema, ctx)
