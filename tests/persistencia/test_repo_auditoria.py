import sqlite3

from bingo.dominio.modelos import Organizacion
from bingo.persistencia import repo_auditoria, repo_organizacion


def test_registrar_con_evento_id(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="X"))
    repo_auditoria.registrar(con, None, "org.creada", detalle=f"id={org.id}")
    registros = repo_auditoria.listar_por_evento(con, 1)
    assert registros == []  # evento_id=None no aparece al filtrar por evento 1


def test_registrar_y_listar_por_evento(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'E', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]

    repo_auditoria.registrar(con, evento_id, "evento.creado")
    repo_auditoria.registrar(con, evento_id, "evento.editado", detalle="nombre cambiado")

    registros = repo_auditoria.listar_por_evento(con, evento_id)
    assert len(registros) == 2
    assert registros[0].accion == "evento.editado"  # orden descendente por momento


def test_registrar_con_evento_id_none(con: sqlite3.Connection) -> None:
    repo_auditoria.registrar(con, None, "app.arranque")
    fila = con.execute("SELECT evento_id FROM auditoria WHERE accion = 'app.arranque'").fetchone()
    assert fila["evento_id"] is None


def test_limite_de_lectura(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'E', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in range(5):
        repo_auditoria.registrar(con, evento_id, f"accion.{i}")
    assert len(repo_auditoria.listar_por_evento(con, evento_id, limite=2)) == 2
