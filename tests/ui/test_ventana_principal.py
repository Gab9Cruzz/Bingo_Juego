"""Pruebas offscreen de `VentanaPrincipal` (tarea 4.12: gancho de "Restaurar",
bloqueado mientras hay un espacio de evento abierto)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from factorias import crear_evento, crear_organizacion

from bingo import i18n
from bingo.ui.ventana_principal import VentanaPrincipal


def test_gancho_restaurar_se_llama_sin_evento_abierto(
    qapp, con: sqlite3.Connection, tmp_path: Path
) -> None:
    i18n.cargar("es")
    ventana = VentanaPrincipal(con)

    recibido: list[Path] = []
    ventana.establecer_gancho_restaurar(recibido.append)

    ruta = tmp_path / "respaldo.zip"
    ventana._vista_ajustes._gancho_restaurar(ruta)  # noqa: SLF001

    assert recibido == [ruta]


def test_gancho_restaurar_bloqueado_con_evento_abierto(
    qapp, con: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)

    ventana = VentanaPrincipal(con)
    ventana.abrir_evento(evento)

    avisos: list[str] = []
    monkeypatch.setattr(
        "bingo.ui.ventana_principal.QMessageBox.warning",
        lambda *a, **k: avisos.append(a[1] if len(a) > 1 else ""),
    )

    recibido: list[Path] = []
    ventana.establecer_gancho_restaurar(recibido.append)
    ruta = tmp_path / "respaldo.zip"
    ventana._vista_ajustes._gancho_restaurar(ruta)  # noqa: SLF001

    assert recibido == []  # nunca llegó a la restauración de verdad
    assert len(avisos) == 1


def test_gancho_restaurar_no_referencia_la_ventana_con_fuerza(
    qapp, con: sqlite3.Connection
) -> None:
    """`establecer_gancho_restaurar` usa `weakref.ref(self)` a propósito: un
    método ligado (`self._al_pedir_restaurar`) capturado a secas cerraría un
    ciclo ventana -> `VistaAjustes` (hija) -> gancho -> ventana. La prueba de
    que el ciclo entero se rompe requeriría que `VentanaPrincipal` sea
    recolectable, y no lo es por una razón completamente aparte
    (`i18n.registrar_para_retraduccion` conecta `destroyed` a un método
    propio — un ciclo del lado de Qt que ni `gc.collect()` rompe); lo que sí
    se puede comprobar aquí, sin depender de eso, es que el propio gancho no
    guarda una referencia fuerte directa a la ventana."""
    import weakref

    i18n.cargar("es")
    ventana = VentanaPrincipal(con)
    ventana.establecer_gancho_restaurar(lambda _ruta: None)

    gancho = ventana._vista_ajustes._gancho_restaurar  # noqa: SLF001
    referentes_directos = gancho.__closure__ or ()
    valores = [celda.cell_contents for celda in referentes_directos]
    assert not any(v is ventana for v in valores)
    assert any(isinstance(v, weakref.ReferenceType) and v() is ventana for v in valores)
