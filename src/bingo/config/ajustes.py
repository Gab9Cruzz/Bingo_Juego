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

# impresion/plantilla.py, impresion/render_pdf.py, servicios/servicio_impresion.py
TAMANOS_HOJA_SOPORTADOS = ("A4", "Carta", "A5")
CARTONES_POR_HOJA_SOPORTADOS = (1, 2, 4, 6)
HOJAS_POR_ARCHIVO_DEFECTO = 500
RETARDO_VISTA_PREVIA_MS = 500

# servicios/servicio_compradores.py — importación de Excel (fase 4).
# LIMITE_FILAS_IMPORTACION no es la única defensa: A6 (Fase_4) muestra que
# `ws.max_row` lo controla quien manda el archivo y que `sharedStrings.xml`
# se descomprime entero antes de iterar, así que el tope de tamaño
# descomprimido del .zip se comprueba primero, sin abrir el libro.
LIMITE_FILAS_IMPORTACION = 20_000
LIMITE_TAMANO_XLSX_MB = 15
LIMITE_TAMANO_XLSX_DESCOMPRIMIDO_MB = 200
TAMANO_BLOQUE_IMPORTACION = 500  # filas por transacción (decisión TD-3: trocear)
COMPROBAR_CANCELAR_CADA_FILAS_IMPORTACION = 200

# servicios/servicio_patrones.py
VERSION_SEMILLA_PATRONES_SISTEMA = 1
