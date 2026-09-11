import sqlite3
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
        # 004_fase5.sql añade columnas de sorteo/acta a ronda y ganador (decisión D3).
        assert aplicadas == [1, 2, 3, 4]
        assert migraciones.version_actual(con) == 4
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

        # Apuntar de vuelta a las migraciones reales (incluidas la 003 y la
        # 004) para la segunda pasada:
        monkeypatch.setattr(migraciones, "_resolver_directorio", lambda: migraciones_reales)
        aplicadas = migraciones.aplicar_migraciones(con)
        assert aplicadas == [3, 4]
        assert migraciones.version_actual(con) == 4

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


def test_migracion_004_sobre_base_poblada_por_003(bingo_home, tmp_path: Path, monkeypatch) -> None:
    """`test_migraciones` sube a la 004 sobre una base con datos de la 003
    (tarea 4.1 del plan de la fase 5): una ronda y un ganador ya insertados
    bajo el esquema anterior deben sobrevivir con las columnas nuevas en
    NULL, y el índice único de `ganador` debe ser total, no parcial
    (hallazgo V1)."""
    con = abrir_conexion(synchronous="OFF")
    try:
        carpeta = tmp_path / "solo_001_002_003"
        carpeta.mkdir()
        migraciones_reales = migraciones._resolver_directorio()
        for numero in ("001_inicial.sql", "002_fase3.sql", "003_fase4.sql"):
            (carpeta / numero).write_bytes((migraciones_reales / numero).read_bytes())
        _apuntar_a_directorio_temporal(monkeypatch, carpeta)
        migraciones.aplicar_migraciones(con)
        assert migraciones.version_actual(con) == 3

        con.execute(
            "INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', '2026-01-01T00:00:00Z')"
        )
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, creado_en) "
            "VALUES (1, 'Ev', '2026-01-01T00:00:00Z')"
        )
        con.execute("INSERT INTO patron (nombre, mascaras, organizacion_id) VALUES ('P', '[5]', 1)")
        con.execute(
            "INSERT INTO ronda (evento_id, orden, nombre, patron_id, estado) "
            "VALUES (1, 1, 'Ronda 1', 1, 'cerrada')"
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
            "INSERT INTO ganador (ronda_id, carton_id, bola_numero, registrado_en) "
            "VALUES (1, 1, 42, '2026-01-01T00:00:00Z')"
        )

        monkeypatch.setattr(migraciones, "_resolver_directorio", lambda: migraciones_reales)
        aplicadas = migraciones.aplicar_migraciones(con)
        assert aplicadas == [4]
        assert migraciones.version_actual(con) == 4

        fila_ronda = con.execute(
            "SELECT iniciada_en, cerrada_en, acta_hash, acta_generada_en FROM ronda WHERE id = 1"
        ).fetchone()
        assert tuple(fila_ronda) == (None, None, None, None)

        fila_ganador = con.execute(
            "SELECT confirmado_en, decision, anulado_en, nota FROM ganador WHERE id = 1"
        ).fetchone()
        assert tuple(fila_ganador) == (None, None, None, None)

        # Índice único TOTAL (hallazgo V1): insertar el mismo (ronda_id,
        # carton_id) de nuevo debe fallar aunque la fila original estuviera
        # "anulada" (aquí no lo está, pero el índice no lleva WHERE).
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO ganador (ronda_id, carton_id, bola_numero, registrado_en) "
                "VALUES (1, 1, 50, '2026-01-01T00:00:00Z')"
            )
    finally:
        con.close()


def test_copia_previa_conserva_filas_sin_cerrar(tmp_path: Path) -> None:
    """Tarea 4.22, hallazgo B5 (crítico): la copia debe incluir las filas ya
    confirmadas aunque la conexión de origen siga abierta — por eso el
    checkpoint de WAL antes de copiar no es opcional (en WAL, los datos
    confirmados pueden vivir solo en `bingo.db-wal`)."""
    ruta_bd_prueba = tmp_path / "bingo.db"
    con = sqlite3.connect(ruta_bd_prueba)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE t (x INTEGER)")
        con.executemany("INSERT INTO t (x) VALUES (?)", [(1,), (2,), (3,)])
        con.commit()

        migraciones._copia_previa_a_migrar(con, 3)

        copia = ruta_bd_prueba.with_name("bingo.db.pre-3")
        assert copia.exists()
        con_copia = sqlite3.connect(copia)
        try:
            filas = con_copia.execute("SELECT x FROM t ORDER BY x").fetchall()
            assert [f[0] for f in filas] == [1, 2, 3]
        finally:
            con_copia.close()
    finally:
        con.close()


def test_copia_previa_no_se_pisa_si_ya_existe(tmp_path: Path) -> None:
    """Una sola copia por versión: no tiene sentido pisar con datos más
    nuevos lo que debía ser la foto de la versión anterior."""
    ruta_bd_prueba = tmp_path / "bingo.db"
    con = sqlite3.connect(ruta_bd_prueba)
    con.row_factory = sqlite3.Row
    try:
        con.execute("CREATE TABLE t (x INTEGER)")
        con.commit()
        migraciones._copia_previa_a_migrar(con, 3)
        copia = ruta_bd_prueba.with_name("bingo.db.pre-3")
        contenido_original = copia.read_bytes()

        con.execute("INSERT INTO t (x) VALUES (99)")
        con.commit()
        migraciones._copia_previa_a_migrar(con, 3)

        assert copia.read_bytes() == contenido_original
    finally:
        con.close()


def test_copia_previa_sin_archivo_real_no_falla() -> None:
    """`:memory:` (o cualquier base sin archivo en `PRAGMA database_list`):
    no hay nada que copiar, y eso no es un error."""
    con = sqlite3.connect(":memory:")
    try:
        migraciones._copia_previa_a_migrar(con, 1)
    finally:
        con.close()


def test_aplicar_004_sobre_base_de_la_003_deja_copia_pre_3(
    bingo_home, tmp_path: Path, monkeypatch
) -> None:
    """Tarea 4.22 (corrección S5-14, hallazgo B5 crítico): aplicar la 004
    sobre una base con datos de la 003 debe dejar `bingo.db.pre-3` con el
    contenido íntegro anterior a la migración."""
    from bingo.config.rutas import ruta_bd

    con = abrir_conexion(synchronous="OFF")
    try:
        carpeta = tmp_path / "solo_001_002_003"
        carpeta.mkdir()
        migraciones_reales = migraciones._resolver_directorio()
        for numero in ("001_inicial.sql", "002_fase3.sql", "003_fase4.sql"):
            (carpeta / numero).write_bytes((migraciones_reales / numero).read_bytes())
        _apuntar_a_directorio_temporal(monkeypatch, carpeta)
        migraciones.aplicar_migraciones(con)
        assert migraciones.version_actual(con) == 3

        con.execute(
            "INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', '2026-01-01T00:00:00Z')"
        )
        con.commit()

        monkeypatch.setattr(migraciones, "_resolver_directorio", lambda: migraciones_reales)
        aplicadas = migraciones.aplicar_migraciones(con)
        assert aplicadas == [4]

        copia = ruta_bd().with_name("bingo.db.pre-3")
        assert copia.exists()
        con_copia = sqlite3.connect(copia)
        con_copia.row_factory = sqlite3.Row
        try:
            assert migraciones.version_actual(con_copia) == 3
            nombre = con_copia.execute(
                "SELECT nombre FROM organizacion WHERE id = 1"
            ).fetchone()[0]
            assert nombre == "Org"
        finally:
            con_copia.close()
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
