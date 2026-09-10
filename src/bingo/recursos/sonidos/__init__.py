"""Tres efectos generados con la biblioteca estándar (decisión D6, plan de
la fase 5): `bola.wav`, `ganador.wav`, `alerta.wav`. Se regeneran con
`scripts/generar_sonidos.py`; `ui/sonido.py` los carga con
`importlib.resources` (mismo convenio que `recursos/fuentes/`), no con una
ruta relativa a `__file__`, para que viajen igual en modo `onedir` y
`onefile` de PyInstaller.
"""
