"""Activos empaquetados con la aplicación (fuentes, iconos, sonidos).

Paquete real (no solo una carpeta) por la misma razón que
`persistencia/migraciones/`: `importlib.resources.files()` necesita que el
paquete que ancla la búsqueda tenga `__init__.py` para resolver
consistentemente en modo `onedir` y `onefile` de PyInstaller.
"""
