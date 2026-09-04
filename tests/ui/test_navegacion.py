"""Enmienda E14: navegación de dos niveles, eje evento."""

from __future__ import annotations

from bingo import i18n
from bingo.config import preferencias
from bingo.dominio.modelos import Evento, Organizacion
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.ui.ventana_principal import VentanaPrincipal


def test_sin_organizaciones_estado_vacio_correcto(qapp, con, bingo_home) -> None:
    i18n.cargar("es")
    ventana = VentanaPrincipal(con)
    etiqueta = ventana._vista_eventos._etiqueta_vacio
    # `isHidden()` refleja la bandera explícita del propio widget, a
    # diferencia de `isVisible()`, que en una ventana nunca mostrada
    # (`.show()`) es siempre False sin importar `setVisible(True)`.
    assert not etiqueta.isHidden()
    assert etiqueta.text() == "Primero crea una organización"


def test_abrir_evento_entra_al_espacio_y_guarda_preferencia(qapp, con, bingo_home) -> None:
    i18n.cargar("es")
    org = repo_organizacion.crear(con, Organizacion(nombre="X"))
    evento = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))

    ventana = VentanaPrincipal(con)
    ventana.abrir_evento(evento)

    assert ventana._pila_principal.currentWidget() is ventana._espacio_evento
    assert ventana._espacio_evento.evento.id == evento.id
    assert preferencias.cargar().ultimo_evento_abierto_id == evento.id


def test_cerrar_evento_vuelve_al_inicio(qapp, con, bingo_home) -> None:
    i18n.cargar("es")
    org = repo_organizacion.crear(con, Organizacion(nombre="X"))
    evento = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))

    ventana = VentanaPrincipal(con)
    ventana.abrir_evento(evento)
    ventana.cerrar_evento()

    assert ventana._pila_principal.currentIndex() == 0
    assert ventana._espacio_evento is None
