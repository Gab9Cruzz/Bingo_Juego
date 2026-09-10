from pathlib import Path

import pytest

from bingo.persistencia import migraciones
from bingo.persistencia.conexion import abrir_conexion
from bingo.utilidades.errores import ErrorMigracion


def test_primera_aplicacion_crea_esquema(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        aplicadas = migraciones.aplicar_migraciones(con)
        # 002_fase3.sql (columna evento.clave_evento) desde que la fase 3
        # dejó de editar 001_inicial.sql (decisión D1, Plan_Implementacion_Fase3.md §3).
        # 003_fase4.sql reconstruye patron/comprador y añade columnas de premio.
        assert aplicadas == [1, 2, 3]
        assert migraciones.version_actual(con) == 3
        tablas = {
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert {"organizacion", "evento", "carton", "schema_version"} <= tablas
    finally:
        con.close()


def test_segunda_aplicacion_no_reaplica(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        aplicadas = migraciones.aplicar_migraciones(con)
        assert migraciones.aplicar_migraciones(con) == []
        filas = con.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert filas == len(aplicadas)
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
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "b" not in tablas, "la tabla de la migración fallida no debería sobrevivir"
        assert migraciones.version_actual(con) == 1, "schema_version no debió ganar fila"
    finally:
        con.close()


def test_migracion_003_sobre_base_poblada_por_002(bingo_home, tmp_path: Path, monkeypatch) -> None:
    """Hueco señalado en el ANEXO C.5 del plan de la fase 4: `conftest.py`
    migra desde cero una vez por sesión, así que nadie más ejerce la ruta de
    actualización real sobre una base que ya tenía filas en `comprador` y
    `patron` bajo el esquema de la 001/002. Verifica que la reconstrucción de
    ambas tablas conserva las filas existentes con los valores por defecto
    correctos de las columnas nuevas."""
    con = abrir_conexion(synchronous="OFF")
    try:
        carpeta = tmp_path / "solo_001_002"
        carpeta.mkdir()
        migraciones_reales = migraciones._resolver_directorio()
        for numero in ("001_inicial.sql", "002_fase3.sql"):
            (carpeta / numero).write_bytes((migraciones_reales / numero).read_bytes())
        _apuntar_a_directorio_temporal(monkeypatch, carpeta)
        migraciones.aplicar_migraciones(con)
        assert migraciones.version_actual(con) == 2

        con.execute(
            "INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', '2026-01-01T00:00:00Z')"
        )
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, creado_en) "
            "VALUES (1, 'Ev', '2026-01-01T00:00:00Z')"
        )
        con.execute(
            "INSERT INTO lote (evento_id, cantidad, prefijo_codigo, semilla, generado_en) "
            "VALUES (1, 1, 'A', 's', '2026-01-01T00:00:00Z')"
        )
        numeros = ",".join(str(n) for n in range(1, 25))
        con.execute(
            "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma, estado) "
            "VALUES (1, 1, 'A-1', ?, 'f', 'vendido')",
            (numeros,),
        )
        con.execute(
            "INSERT INTO comprador (carton_id, nombre, registrado_en) "
            "VALUES (1, 'Juan', '2026-01-01T00:00:00Z')"
        )
        con.execute("INSERT INTO patron (nombre, mascara, organizacion_id) VALUES ('P', 5, 1)")

        # Apuntar de vuelta a las migraciones reales (incluida la 003) para la segunda pasada:
        monkeypatch.setattr(migraciones, "_resolver_directorio", lambda: migraciones_reales)
        aplicadas = migraciones.aplicar_migraciones(con)
        assert aplicadas == [3]
        assert migraciones.version_actual(con) == 3

        fila_comprador = con.execute(
            "SELECT provisional, anulado_en, estado_carton_previo, nombre "
            "FROM comprador WHERE id = 1"
        ).fetchone()
        assert fila_comprador["provisional"] == 0
        assert fila_comprador["anulado_en"] is None
        assert fila_comprador["nombre"] == "Juan"

        info_comprador = con.execute("PRAGMA table_info(comprador)").fetchall()
        columna_provisional = next(c for c in info_comprador if c["name"] == "provisional")
        assert columna_provisional["notnull"] == 1
        assert columna_provisional["dflt_value"] == "0"

        fila_patron = con.execute(
            "SELECT mascaras, usa_libre, es_sistema FROM patron WHERE id = 1"
        ).fetchone()
        assert fila_patron["mascaras"] == "[5]"
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
