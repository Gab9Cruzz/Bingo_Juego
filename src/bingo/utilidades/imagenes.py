"""Validación y normalización de imágenes (logos) con Pillow.

`Image.verify()` comprueba la estructura del contenedor, no descodifica los
píxeles: un JPEG truncado por el final pasa `verify()` limpio las tres veces
probadas y solo `load()` lo rechaza. Por eso `verify()` no basta solo:
`es_imagen_valida` reabre la imagen (`verify()` deja el objeto inutilizable
para cualquier otra operación) y llama a `load()` dentro del mismo `try`.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from bingo.config.ajustes import LIMITE_PIXELES_IMAGEN, LIMITE_TAMANO_IMAGEN_MB
from bingo.utilidades.errores import ErrorImagen

_LIMITE_BYTES = LIMITE_TAMANO_IMAGEN_MB * 1024 * 1024


def es_imagen_valida(ruta: Path) -> bool:
    try:
        with Image.open(ruta) as img:
            img.verify()
        with Image.open(ruta) as img:
            img.load()
        return True
    except (OSError, DecompressionBombError, UnidentifiedImageError):
        return False


def validar_y_normalizar(origen: Path, destino: Path, *, lado_max: int = 1600) -> Path:
    """Convierte `origen` a PNG en `destino`, redimensionando si excede `lado_max`.

    Escritura atómica: se escribe primero a un archivo temporal junto a
    `destino` y se reemplaza con `os.replace`, para no dejar un PNG a medias
    si la aplicación muere a mitad de la copia.
    """
    if not origen.exists():
        raise ErrorImagen("error.imagen.no_existe", campo="logo")

    try:
        tamano = origen.stat().st_size
    except OSError as error:
        raise ErrorImagen("error.imagen.no_existe", campo="logo", detalle=str(error)) from error
    if tamano > _LIMITE_BYTES:
        raise ErrorImagen(
            "error.imagen.muy_grande",
            campo="logo",
            parametros={"limite_mb": LIMITE_TAMANO_IMAGEN_MB},
        )

    try:
        with Image.open(origen) as img:
            img.verify()
    except (OSError, UnidentifiedImageError) as error:
        raise ErrorImagen(
            "error.imagen.formato_no_soportado", campo="logo", detalle=str(error)
        ) from error

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(origen) as img:
                ancho, alto = img.size
                if ancho * alto > LIMITE_PIXELES_IMAGEN:
                    raise ErrorImagen("error.imagen.bomba_descompresion", campo="logo")
                img.load()
                imagen = img.convert("RGBA")
    except DecompressionBombError as error:
        raise ErrorImagen(
            "error.imagen.bomba_descompresion", campo="logo", detalle=str(error)
        ) from error
    except OSError as error:
        raise ErrorImagen("error.imagen.corrupta", campo="logo", detalle=str(error)) from error

    if max(imagen.size) > lado_max:
        proporcion = lado_max / max(imagen.size)
        nuevo_tamano = (round(imagen.width * proporcion), round(imagen.height * proporcion))
        imagen = imagen.resize(nuevo_tamano, Image.LANCZOS)

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    imagen.save(temporal, format="PNG")
    os.replace(temporal, destino)
    return destino
