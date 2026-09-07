"""Constantes de configuración que no cambian en tiempo de ejecución."""

from __future__ import annotations

NOMBRE_APP = "Bingo"

# Segmentos de ruta que delatan una carpeta sincronizada (config/rutas.py).
SEGMENTOS_SINCRONIZADOS = ("OneDrive", "Dropbox", "Google Drive", "iCloudDrive")

# utilidades/imagenes.py
LADO_MAX_LOGO = 1600
LIMITE_TAMANO_IMAGEN_MB = 20
LIMITE_PIXELES_IMAGEN = 40_000_000  # ancho * alto

# persistencia/conexion.py
BUSY_TIMEOUT_MS = 5000

# servicios/servicio_cartones.py — hallazgo Eng de la fase 2: sin tope, una
# cantidad arbitrariamente grande no está cubierta por ningún criterio de
# aceptación ni prueba, y el set de firmas en memoria crecería sin límite
# operable. 50.000 cubre con margen el volumen real de un bingo de una
# organización (docs/Proyecto_Alcance.md).
LIMITE_CARTONES_POR_LOTE = 50_000
TAMANO_BLOQUE_INSERCION_CARTONES = 500
TOPE_COLISIONES_FIRMA_CONSECUTIVAS = 1_000
LONGITUD_MAXIMA_PREFIJO_CODIGO = 12
