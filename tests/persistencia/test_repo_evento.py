import sqlite3

import pytest

from bingo.dominio.modelos import Evento, Organizacion
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.utilidades.errores import ErrorValidacion


def _crear_org(con: sqlite3.Connection) -> Organizacion:
    return repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))


def test_crear_devuelve_modelo_persistido(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo 2026"))
    assert ev.id is not None
    assert ev.estado == "borrador"


def test_precio_en_centavos_sin_perdida(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(
        con, Evento(organizacion_id=org.id, nombre="Bingo", precio_tabla_centavos=1999)
    )
    recuperado = repo_evento.obtener(con, ev.id)
    assert recuperado.precio_tabla_centavos == 1999


def test_listar_por_organizacion(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    otra_org = repo_organizacion.crear(con, Organizacion(nombre="Otra"))
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="A"))
    repo_evento.crear(con, Evento(organizacion_id=otra_org.id, nombre="B"))
    resultado = repo_evento.listar_por_organizacion(con, org.id)
    assert len(resultado) == 1
    assert resultado[0].nombre == "A"


def test_listar_todos(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="A"))
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="B"))
    assert len(repo_evento.listar_todos(con)) == 2


def test_actualizar_estado_solo_escribe(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_estado(con, ev.id, "preparado")
    assert repo_evento.obtener(con, ev.id).estado == "preparado"


def test_actualizar_plantilla_json_invalido_rechazado(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    with pytest.raises(ErrorValidacion):
        repo_evento.actualizar_plantilla(con, ev.id, "{no es json}")


def test_actualizar_plantilla_json_valido(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_plantilla(con, ev.id, '{"color": "#fff"}')
    assert repo_evento.obtener(con, ev.id).plantilla_json == '{"color": "#fff"}'


def test_existe_nombre_por_organizacion(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo Anual"))
    assert repo_evento.existe_nombre(con, org.id, "bingo anual")
    assert not repo_evento.existe_nombre(con, org.id, "otro")


def test_clave_evento_nula_por_defecto(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    assert ev.clave_evento is None
    assert repo_evento.obtener(con, ev.id).clave_evento is None


def test_actualizar_clave(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_clave(con, ev.id, "clave-secreta")
    assert repo_evento.obtener(con, ev.id).clave_evento == "clave-secreta"


def test_actualizar_juego_con_tema_json_nulo_no_lo_pierde(con: sqlite3.Connection) -> None:
    """Hallazgo E-13: un evento que nunca abrió la sección Tema tiene
    `tema_json` en NULL. `json_set(NULL, ...)` devolvería NULL sin el
    `COALESCE`, y el ajuste se perdería en silencio."""
    import json

    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    assert ev.tema_json is None

    repo_evento.actualizar_juego(con, ev.id, "intervalo_seg", 6)

    tema = json.loads(repo_evento.obtener(con, ev.id).tema_json)
    assert tema == {"juego": {"intervalo_seg": 6}}


def test_actualizar_juego_conserva_otras_claves_del_tema(con: sqlite3.Connection) -> None:
    import json

    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_tema(con, ev.id, json.dumps({"colores": {"fondo": "#000000"}}))

    repo_evento.actualizar_juego(con, ev.id, "modo", "automatico")

    tema = json.loads(repo_evento.obtener(con, ev.id).tema_json)
    assert tema == {"colores": {"fondo": "#000000"}, "juego": {"modo": "automatico"}}


def test_actualizar_juego_guarda_booleano_como_json_bool_no_entero(con: sqlite3.Connection) -> None:
    """Un `bool` de Python no debe quedar como `0`/`1` en el JSON: eso
    rompería la reconstrucción de `ConfigJuego` la próxima vez que
    `dominio/tema.py` la lea."""
    import json

    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_juego(con, ev.id, "sonido_bola", False)

    crudo = repo_evento.obtener(con, ev.id).tema_json
    assert '"sonido_bola": false' in crudo or '"sonido_bola":false' in crudo
    assert json.loads(crudo)["juego"]["sonido_bola"] is False
