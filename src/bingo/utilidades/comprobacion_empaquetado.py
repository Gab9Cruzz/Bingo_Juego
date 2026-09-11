"""Autocomprobación de empaquetado (tarea 4.14, hallazgo E-12): sin QApplication
ni ventana, solo importa los módulos de PySide6 que el resto de la app carga
por nombre (`ui/sonido.py`, D5/D6) y verifica que los recursos embebidos
(migraciones, i18n, sonidos) existen donde el paquete los busca.

`__main__.py --comprobar-empaquetado` la invoca antes de construir cualquier
cosa; es lo que `empaquetado/humo.py` ejerce contra el `.exe` real que
PyInstaller produce, en la SEMANA 1 del plan de empaquetado — PyInstaller con
`QtMultimedia`/`QtTextToSpeech` es célebre por fallar tarde, y descubrirlo en
la última semana antes de un evento real no es una opción.
"""

from __future__ import annotations

import importlib
import importlib.resources

_MODULOS_QT_POR_NOMBRE = (
    "PySide6.QtMultimedia",
    "PySide6.QtTextToSpeech",
    "PySide6.QtPdf",
)
_SONIDOS_ESPERADOS = ("bola.wav", "ganador.wav", "alerta.wav")
_IDIOMAS_ESPERADOS = ("es", "en")


def comprobar() -> list[str]:
    """Devuelve la lista de problemas encontrados — vacía si el empaquetado
    está completo. Nunca lanza: un módulo que falta es exactamente lo que
    esto existe para reportar, no para tumbar el proceso que lo pregunta."""
    problemas: list[str] = []

    for nombre_modulo in _MODULOS_QT_POR_NOMBRE:
        try:
            importlib.import_module(nombre_modulo)
        except ImportError as error:
            problemas.append(f"no se pudo importar {nombre_modulo}: {error}")

    try:
        from bingo.persistencia.migraciones import _resolver_directorio

        directorio = _resolver_directorio()
        if not any(p.name.endswith(".sql") for p in directorio.iterdir()):
            problemas.append("no se encontró ningún archivo .sql de migraciones")
    except Exception as error:  # noqa: BLE001 - autocomprobación: se reporta, no se relanza
        problemas.append(f"no se pudo listar las migraciones: {error}")

    try:
        import bingo.i18n as paquete_i18n

        for idioma in _IDIOMAS_ESPERADOS:
            ruta = importlib.resources.files(paquete_i18n) / f"{idioma}.json"
            if not ruta.is_file():
                problemas.append(f"no se encontró i18n/{idioma}.json")
    except Exception as error:  # noqa: BLE001
        problemas.append(f"no se pudo verificar i18n: {error}")

    try:
        import bingo.recursos.sonidos as paquete_sonidos

        for nombre in _SONIDOS_ESPERADOS:
            ruta = importlib.resources.files(paquete_sonidos) / nombre
            if not ruta.is_file():
                problemas.append(f"no se encontró recursos/sonidos/{nombre}")
    except Exception as error:  # noqa: BLE001
        problemas.append(f"no se pudo verificar recursos/sonidos: {error}")

    try:
        import bingo.recursos.fuentes as paquete_fuentes

        for subcarpeta, nombre_archivo in (
            ("Merriweather", "Merriweather-Variable.ttf"),
            ("OpenSans", "OpenSans-Variable.ttf"),
        ):
            ruta = importlib.resources.files(paquete_fuentes) / subcarpeta / nombre_archivo
            if not ruta.is_file():
                problemas.append(f"no se encontró recursos/fuentes/{subcarpeta}/{nombre_archivo}")
    except Exception as error:  # noqa: BLE001
        problemas.append(f"no se pudo verificar recursos/fuentes: {error}")

    return problemas
