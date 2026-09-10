"""La prueba que sostiene la regla del repositorio y el principio rector del
documento técnico ("el dominio no importa PySide6 ni sqlite3"). Dos
comprobaciones deliberadamente estrechas (enmienda E6): imports por AST, y SQL
fuera de `persistencia/` por literales de cadena anclados al inicio. Se evita
a propósito cualquier heurística sobre "texto visible", que es una máquina de
falsos positivos (enmienda E6).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

RAIZ_SRC = Path(__file__).resolve().parents[2] / "src" / "bingo"

_PREFIJOS_SQL = ("SELECT ", "INSERT INTO ", "UPDATE ", "DELETE FROM ", "CREATE TABLE ")
_METODOS_EJECUCION_SQL = {"execute", "executemany", "executescript"}


def _archivos_python(carpeta: Path) -> list[Path]:
    return sorted((carpeta).rglob("*.py"))


def _nombres_importados(arbol: ast.AST) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def test_dominio_no_importa_pyside6_ni_sqlite3() -> None:
    for archivo in _archivos_python(RAIZ_SRC / "dominio"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        importados = _nombres_importados(arbol)
        assert "PySide6" not in importados, f"{archivo} importa PySide6"
        assert "sqlite3" not in importados, f"{archivo} importa sqlite3"


def test_ui_no_importa_sqlite3() -> None:
    for archivo in _archivos_python(RAIZ_SRC / "ui"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        importados = _nombres_importados(arbol)
        assert "sqlite3" not in importados, f"{archivo} importa sqlite3"


def test_servicios_no_importan_pyside6() -> None:
    for archivo in _archivos_python(RAIZ_SRC / "servicios"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        importados = _nombres_importados(arbol)
        assert "PySide6" not in importados, f"{archivo} importa PySide6"


def test_impresion_no_importa_pyside6_ni_sqlite3() -> None:
    """`impresion/` (fase 3) importa ReportLab, no PySide6 ni sqlite3: el
    motor de render se usa igual desde un `QThread` (servicio_impresion) que
    desde la vista previa de la interfaz, sin acoplarse a ninguno de los dos.
    """
    for archivo in _archivos_python(RAIZ_SRC / "impresion"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        importados = _nombres_importados(arbol)
        assert "PySide6" not in importados, f"{archivo} importa PySide6"
        assert "sqlite3" not in importados, f"{archivo} importa sqlite3"


def _literales_de_cadena(arbol: ast.AST) -> list[str]:
    return [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
    ]


def test_sql_no_se_filtra_fuera_de_persistencia() -> None:
    for carpeta in ("config", "dominio", "impresion", "servicios", "ui", "utilidades", "i18n"):
        for archivo in _archivos_python(RAIZ_SRC / carpeta):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for literal in _literales_de_cadena(arbol):
                for prefijo in _PREFIJOS_SQL:
                    assert not literal.startswith(prefijo), (
                        f"{archivo} contiene un literal SQL fuera de persistencia/: {literal!r}"
                    )


def test_execute_no_se_llama_fuera_de_persistencia() -> None:
    """La valla de verdad (enmienda E27): nadie fuera de `persistencia/` llama
    a `.execute(`, `.executemany(` ni `.executescript(`.
    """
    for carpeta in ("config", "dominio", "impresion", "servicios", "ui", "utilidades", "i18n"):
        for archivo in _archivos_python(RAIZ_SRC / carpeta):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for nodo in ast.walk(arbol):
                if (
                    isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr in _METODOS_EJECUCION_SQL
                ):
                    raise AssertionError(
                        f"{archivo}:{nodo.lineno} llama a .{nodo.func.attr}() "
                        "fuera de persistencia/"
                    )


def _claves_i18n_en_constructores_error(arbol: ast.AST) -> list[str]:
    claves = []
    for nodo in ast.walk(arbol):
        es_constructor_error = (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id.startswith("Error")
            and nodo.args
        )
        if es_constructor_error:
            primer_arg = nodo.args[0]
            if isinstance(primer_arg, ast.Constant) and isinstance(primer_arg.value, str):
                claves.append(primer_arg.value)
    return claves


def test_claves_i18n_de_errores_existen_en_es_json() -> None:
    ruta_es = RAIZ_SRC / "i18n" / "es.json"
    claves_es = set(json.loads(ruta_es.read_text(encoding="utf-8")).keys())

    faltantes: list[tuple[Path, str]] = []
    for archivo in _archivos_python(RAIZ_SRC):
        if archivo.name == "errores.py":
            continue  # define la jerarquía, no la usa con claves reales
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for clave in _claves_i18n_en_constructores_error(arbol):
            # las claves con parámetros de formato ({...}) no aplican aquí;
            # todas las usadas en el código son literales fijos.
            if clave not in claves_es:
                faltantes.append((archivo, clave))

    assert not faltantes, f"Claves i18n de Error* ausentes en es.json: {faltantes}"
