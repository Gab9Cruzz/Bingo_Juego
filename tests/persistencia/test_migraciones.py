from pathlib import Path

import pytest

from bingo.persistencia import migraciones
from bingo.persistencia.conexion import abrir_conexion
from bingo.utilidades.errores import ErrorMigracion


def test_primera_aplicacion_crea_esquema(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        aplicadas = migraciones.aplicar_migraciones(con)
        assert aplicadas == [1]
        assert migraciones.version_actual(con) == 1
        tablas = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"organizacion", "evento", "carton", "schema_version"} <= tablas
    finally:
        con.close()


def test_segunda_aplicacion_no_reaplica(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        migraciones.aplicar_migraciones(con)
        assert migraciones.aplicar_migraciones(con) == []
        filas = con.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert filas == 1
    finally:
        con.close()


def _apuntar_a_directorio_temporal(monkeypatch: pytest.MonkeyPatch, carpeta: Path) -> None:
    monkeypatch.setattr(migraciones, "_resolver_directorio", lambda: carpeta)


def test_numeracion_con_hueco_falla(bingo_home, tmp_path: Path, monkeypatch) -> None:
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    (carpeta / "001_inicial.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    (carpeta / "003_otra.sql").write_text("CREATE TABLE b (x INTEGER);", encoding="utf-8")
    _apuntar_a_directorio_temporal(monkeypatch, carpeta)

    con = abrir_conexion(synchronous="OFF")
    try:
        with pytest.raises(ErrorMigracion):
            migraciones.aplicar_migraciones(con)
    finally:
        con.close()


def test_archivo_mal_nombrado_falla(bingo_home, tmp_path: Path, monkeypatch) -> None:
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    (carpeta / "Inicial.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    _apuntar_a_directorio_temporal(monkeypatch, carpeta)

    con = abrir_conexion(synchronous="OFF")
    try:
        with pytest.raises(ErrorMigracion):
            migraciones.aplicar_migraciones(con)
    finally:
        con.close()


def test_version_futura_aborta(bingo_home, tmp_path: Path, monkeypatch) -> None:
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    (carpeta / "001_inicial.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    _apuntar_a_directorio_temporal(monkeypatch, carpeta)

    con = abrir_conexion(synchronous="OFF")
    try:
        migraciones.aplicar_migraciones(con)
        con.execute(
            "INSERT INTO schema_version (version, aplicada_en, archivo) VALUES (99, 'x', 'y')"
        )
        with pytest.raises(ErrorMigracion):
            migraciones.aplicar_migraciones(con)
    finally:
        con.close()


def test_atomicidad_real_migracion_a_medias_no_sobrevive(
    bingo_home, tmp_path: Path, monkeypatch
) -> None:
    """La prueba central de la enmienda G1: `executescript()` emite un COMMIT
    implícito antes de correr el script. Si el `BEGIN`/`COMMIT` no viven
    DENTRO del texto ejecutado, un fallo a mitad de camino deja el esquema a
    medio construir y sin fila en `schema_version` — el peor estado posible.
    """
    carpeta = tmp_path / "migraciones"
    carpeta.mkdir()
    (carpeta / "001_inicial.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    (carpeta / "002_falla.sql").write_text(
        "CREATE TABLE b (x INTEGER);\nESTO NO ES SQL VALIDO;", encoding="utf-8"
    )
    _apuntar_a_directorio_temporal(monkeypatch, carpeta)

    con = abrir_conexion(synchronous="OFF")
    try:
        # aplicar_migraciones aplica TODAS las pendientes en una sola llamada:
        # la 001 se confirma y la 002 falla a mitad, dentro de la misma llamada.
        with pytest.raises(ErrorMigracion):
            migraciones.aplicar_migraciones(con)

        tablas = {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "b" not in tablas, "la tabla de la migración fallida no debería sobrevivir"
        assert migraciones.version_actual(con) == 1, "schema_version no debió ganar fila"
    finally:
        con.close()


def test_base_a_medias_detectada(bingo_home) -> None:
    """G34: tablas creadas pero `schema_version` vacía -> error accionable, no reintento ciego."""
    con = abrir_conexion(synchronous="OFF")
    try:
        con.execute("CREATE TABLE organizacion (id INTEGER PRIMARY KEY)")
        with pytest.raises(ErrorMigracion):
            migraciones.aplicar_migraciones(con)
    finally:
        con.close()
