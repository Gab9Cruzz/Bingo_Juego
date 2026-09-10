from bingo.ui.widgets.tablero_setenta_cinco import TableroSetentaYCinco


def test_marcar_agrega_a_marcadas(qapp) -> None:
    tablero = TableroSetentaYCinco()
    tablero.marcar(7)
    assert 7 in tablero.marcadas()
    assert 8 not in tablero.marcadas()


def test_marcar_numero_fuera_de_rango_no_falla(qapp) -> None:
    tablero = TableroSetentaYCinco()
    tablero.marcar(999)  # no debe lanzar


def test_ultima_se_mueve_de_celda_en_celda(qapp) -> None:
    tablero = TableroSetentaYCinco()
    tablero.marcar(7, es_ultima=True)
    tablero.marcar(42, es_ultima=True)
    assert tablero._celdas[7].property("ultima") is False  # noqa: SLF001
    assert tablero._celdas[42].property("ultima") is True  # noqa: SLF001


def test_reiniciar_limpia_todo(qapp) -> None:
    tablero = TableroSetentaYCinco()
    tablero.marcar(7, es_ultima=True)
    tablero.reiniciar()
    assert tablero.marcadas() == set()
    assert tablero._celdas[7].property("ultima") is False  # noqa: SLF001
