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
