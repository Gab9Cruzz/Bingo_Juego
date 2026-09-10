from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from factorias import crear_evento, crear_organizacion, crear_patron, crear_ronda

from bingo.dominio.modelos import Ronda
from bingo.persistencia import repo_auditoria, repo_ronda
from bingo.servicios import servicio_rondas
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorTransicionInvalida, ErrorValidacion


def _evento(con: sqlite3.Connection):
    org = crear_organizacion(con)
    return crear_evento(con, org.id)


def test_crear_ronda_asigna_orden_siguiente(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    r1 = servicio_rondas.crear_ronda(
        con, Ronda(evento_id=evento.id, nombre="R1", patron_id=patron.id)
    )
    r2 = servicio_rondas.crear_ronda(
        con, Ronda(evento_id=evento.id, nombre="R2", patron_id=patron.id)
    )
    assert r1.orden == 1
    assert r2.orden == 2


def test_crear_ronda_rechaza_efectivo_sin_valor(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    with pytest.raises(ErrorValidacion):
        servicio_rondas.crear_ronda(
            con,
            Ronda(evento_id=evento.id, nombre="R1", patron_id=patron.id, premio_tipo="efectivo"),
        )


def test_reordenar_permutacion_completa(con: sqlite3.Connection) -> None:
    """Invertir el orden de 5 rondas de una vez (hallazgo C1): la
    implementación ingenua de un intercambio directo choca con
    `UNIQUE(evento_id, orden)`."""
    evento = _evento(con)
    patron = crear_patron(con)
    rondas = [crear_ronda(con, evento.id, patron.id, nombre=f"R{i}", orden=i) for i in range(1, 6)]
    invertido = list(reversed([r.id for r in rondas]))
    servicio_rondas.reordenar(con, evento.id, invertido)

    resultado = repo_ronda.listar_por_evento(con, evento.id)
    assert [r.id for r in resultado] == invertido


def test_reordenar_rechaza_lista_incompleta(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    r1 = crear_ronda(con, evento.id, patron.id, orden=1)
    crear_ronda(con, evento.id, patron.id, orden=2)
    with pytest.raises(ErrorValidacion):
        servicio_rondas.reordenar(con, evento.id, [r1.id])


def test_reordenar_rechaza_id_ajeno_al_evento(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    otro_evento = _evento(con)
    patron = crear_patron(con)
    r1 = crear_ronda(con, evento.id, patron.id, orden=1)
    ajena = crear_ronda(con, otro_evento.id, patron.id, orden=1)
    with pytest.raises(ErrorValidacion):
        servicio_rondas.reordenar(con, evento.id, [r1.id, ajena.id])


def test_validar_evento_listo_sin_rondas(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    pendientes = servicio_rondas.validar_evento_listo(con, evento.id)
    assert any(p.clave_i18n == "rondas.pendiente.sin_rondas" for p in pendientes)


def test_validar_evento_listo_reporta_sin_premio_y_sin_valor(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    crear_ronda(con, evento.id, patron.id, orden=1, premio_nombre=None)
    crear_ronda(
        con, evento.id, patron.id, orden=2, premio_nombre="Efectivo", premio_tipo="efectivo"
    )
    pendientes = servicio_rondas.validar_evento_listo(con, evento.id)
    claves = {p.clave_i18n for p in pendientes}
    assert "rondas.pendiente.sin_premio" in claves
    assert "rondas.pendiente.sin_valor_efectivo" in claves


def test_validar_evento_listo_cartones_vendidos_es_solo_aviso(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    crear_ronda(con, evento.id, patron.id, orden=1, premio_nombre="Premio")
    pendientes = servicio_rondas.validar_evento_listo(con, evento.id)
    pendiente_vendidos = next(
        p for p in pendientes if p.clave_i18n == "rondas.pendiente.sin_vendidos"
    )
    assert pendiente_vendidos.bloqueante is False


def test_validar_evento_listo_vacio_cuando_todo_esta_completo(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    crear_ronda(con, evento.id, patron.id, orden=1, premio_nombre="Premio", premio_tipo="bien")
    pendientes = servicio_rondas.validar_evento_listo(con, evento.id)
    bloqueantes = [p for p in pendientes if p.bloqueante]
    assert bloqueantes == []


def test_guardar_imagen_premio(con: sqlite3.Connection, tmp_path: Path) -> None:
    from PIL import Image

    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1)

    origen = tmp_path / "premio.png"
    Image.new("RGB", (10, 10), color="red").save(origen)

    ruta = servicio_rondas.guardar_imagen_premio(con, evento.id, ronda.id, origen)
    assert Path(ruta).exists()
    actualizada = repo_ronda.obtener(con, ronda.id)
    assert actualizada.premio_imagen == ruta


def test_eliminar_ronda_borra_imagen_huerfana(con: sqlite3.Connection, tmp_path: Path) -> None:
    from PIL import Image

    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1)
    origen = tmp_path / "premio.png"
    Image.new("RGB", (10, 10), color="blue").save(origen)
    ruta = servicio_rondas.guardar_imagen_premio(con, evento.id, ronda.id, origen)

    servicio_rondas.eliminar_ronda(con, ronda.id)
    assert not Path(ruta).exists()


def test_reabrir_ronda_pasa_a_en_curso_y_limpia_cerrada_en(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1, estado="cerrada")
    repo_ronda.actualizar_cierre(con, ronda.id, estado="cerrada", cerrada_en="2026-01-01T00:00:00Z")

    servicio_rondas.reabrir_ronda(con, ronda.id)

    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.estado == "en_curso"
    assert recargada.cerrada_en is None


def test_reabrir_ronda_invalida_el_acta_si_tenia(con: sqlite3.Connection) -> None:
    """Hallazgo E-16/C6: un acta ya en manos de la organización no puede
    seguir pareciendo válida sobre una ronda que se sigue jugando."""
    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1, estado="cerrada")
    repo_ronda.actualizar_acta(
        con, ronda.id, acta_hash="abc123", acta_generada_en="2026-01-01T00:00:00Z"
    )

    servicio_rondas.reabrir_ronda(con, ronda.id)

    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.acta_hash is None
    assert recargada.acta_generada_en is None
    acciones = [r.accion for r in repo_auditoria.listar_por_evento(con, evento.id)]
    assert "sorteo.ronda_reabierta" in acciones
    assert "sorteo.acta_invalidada" in acciones


def test_reabrir_ronda_sin_acta_no_registra_invalidacion(con: sqlite3.Connection) -> None:
    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1, estado="cerrada")

    servicio_rondas.reabrir_ronda(con, ronda.id)

    acciones = [r.accion for r in repo_auditoria.listar_por_evento(con, evento.id)]
    assert "sorteo.acta_invalidada" not in acciones


def test_reabrir_ronda_en_curso_falla(con: sqlite3.Connection) -> None:
    """`TRANSICIONES_RONDA` no permite `en_curso -> en_curso`: reabrir solo
    tiene sentido sobre una ronda de verdad cerrada."""
    evento = _evento(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1, estado="en_curso")
    with pytest.raises(ErrorTransicionInvalida):
        servicio_rondas.reabrir_ronda(con, ronda.id)


def test_reabrir_ronda_inexistente_falla(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_rondas.reabrir_ronda(con, 999)
