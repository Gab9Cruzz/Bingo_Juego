from bingo.ui.transmision.pantallas import elegir_pantalla


def test_ninguna_pantalla_disponible() -> None:
    decision = elegir_pantalla([], None)
    assert decision.pantalla is None
    assert decision.modo_ventana is True
    assert decision.motivo == "transmision.pantalla.ninguna"


def test_una_sola_pantalla_fuerza_modo_ventana() -> None:
    """Decisión DU-17: nunca pantalla completa sobre la única pantalla."""
    decision = elegir_pantalla(["\\\\.\\DISPLAY1"], None)
    assert decision.pantalla == "\\\\.\\DISPLAY1"
    assert decision.modo_ventana is True
    assert decision.motivo == "transmision.pantalla.una_sola"


def test_una_sola_pantalla_ignora_el_guardado() -> None:
    decision = elegir_pantalla(["\\\\.\\DISPLAY1"], "\\\\.\\DISPLAY2")
    assert decision.modo_ventana is True


def test_monitor_guardado_disponible_se_usa_sin_avisar() -> None:
    decision = elegir_pantalla(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"], "\\\\.\\DISPLAY2")
    assert decision.pantalla == "\\\\.\\DISPLAY2"
    assert decision.modo_ventana is False
    assert decision.motivo == "transmision.pantalla.guardada"


def test_monitor_guardado_ya_no_existe_cae_al_segundo() -> None:
    decision = elegir_pantalla(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"], "\\\\.\\DISPLAY9")
    assert decision.pantalla == "\\\\.\\DISPLAY2"
    assert decision.modo_ventana is False
    assert decision.motivo == "transmision.pantalla.no_encontrada"


def test_sin_monitor_guardado_usa_el_segundo_y_avisa() -> None:
    decision = elegir_pantalla(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"], None)
    assert decision.pantalla == "\\\\.\\DISPLAY2"
    assert decision.modo_ventana is False
    assert decision.motivo == "transmision.pantalla.sin_elegir"


def test_tres_pantallas_sin_guardado_usa_la_segunda() -> None:
    decision = elegir_pantalla(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2", "\\\\.\\DISPLAY3"], None)
    assert decision.pantalla == "\\\\.\\DISPLAY2"
