# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller (tarea 4.14, contrato §5.11): `--onedir`, no
`--onefile` — un solo binario metería toda la app en un directorio temporal
que Windows Defender reescanea en cada arranque, y en un equipo de evento
sin internet eso es un arranque de varios segundos que `--onedir` evita.

Genera la carpeta `dist/bingo/` con `bingo.exe` y todo lo que necesita al
lado — es lo que `instalador.iss` empaqueta.

Construir desde la raíz del repo:
    .venv\\Scripts\\pyinstaller.exe empaquetado\\bingo.spec --noconfirm

`hiddenimports` explícitos para los módulos de PySide6 que se cargan por
nombre en tiempo de ejecución, no por `import` estático — PyInstaller no los
ve analizando el árbol de imports, y sin ellos el `.exe` arranca pero
`QtMultimedia`/`QtTextToSpeech` fallan en silencio la noche del evento
(riesgo señalado en la tabla de riesgos del plan de la fase 5). Por eso
`empaquetado/humo.py` los importa explícitamente **dentro** del binario ya
construido, en la semana 1, no al final.
"""

from pathlib import Path

# `SPECPATH` lo define PyInstaller en el espacio de nombres del propio
# archivo .spec al ejecutarlo — no es una variable de Python normal, así
# que `noqa` para que ruff no se queje si este archivo llega a lintarse.
RAIZ = Path(SPECPATH).resolve().parent  # noqa: F821
SRC = RAIZ / "src"

datas = [
    (str(SRC / "bingo" / "persistencia" / "migraciones" / "*.sql"), "bingo/persistencia/migraciones"),
    (str(SRC / "bingo" / "i18n" / "*.json"), "bingo/i18n"),
    (str(SRC / "bingo" / "recursos" / "fuentes" / "Merriweather" / "*"), "bingo/recursos/fuentes/Merriweather"),
    (str(SRC / "bingo" / "recursos" / "fuentes" / "OpenSans" / "*"), "bingo/recursos/fuentes/OpenSans"),
    (str(SRC / "bingo" / "recursos" / "sonidos" / "*.wav"), "bingo/recursos/sonidos"),
]

hiddenimports = [
    # Cargados por nombre desde `ui/sonido.py` (D5/D6, tarea 4.10) —
    # nunca aparecen en un `import` de nivel de módulo que PyInstaller
    # pueda seguir estáticamente.
    "PySide6.QtMultimedia",
    "PySide6.QtTextToSpeech",
    # `impresion/acta.py`/`impresion/reporte.py` generan PDF con
    # reportlab, pero la vista previa de PDF (si el operador la abre desde
    # el explorador) pasa por QtPdf en algunos flujos de Windows.
    "PySide6.QtPdf",
]

analisis = Analysis(  # noqa: F821
    [str(SRC / "bingo" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analisis.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    analisis.scripts,
    [],
    exclude_binaries=True,
    name="bingo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

coleccion = COLLECT(  # noqa: F821
    exe,
    analisis.binaries,
    analisis.zipfiles,
    analisis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="bingo",
)
