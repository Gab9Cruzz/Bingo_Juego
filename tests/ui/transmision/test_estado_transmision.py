from bingo.ui.transmision.estado_transmision import EstadoTransmision, MaquinaEstadoTransmision


def test_arranca_en_bienvenida() -> None:
    assert MaquinaEstadoTransmision().estado == EstadoTransmision.BIENVENIDA


def test_bola_extraida_pasa_a_en_juego() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    assert maquina.estado == EstadoTransmision.EN_JUEGO


def test_a_una_bola_con_cantidad_positiva() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.cartones_a_una_bola(3)
    assert maquina.estado == EstadoTransmision.A_UNA_BOLA_CRITICA


def test_a_una_bola_con_cantidad_cero_vuelve_a_en_juego() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.cartones_a_una_bola(3)
    maquina.cartones_a_una_bola(0)
    assert maquina.estado == EstadoTransmision.EN_JUEGO


def test_ganadores_detectados_pasa_a_hay_carton_ganador() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    assert maquina.estado == EstadoTransmision.HAY_CARTON_GANADOR


def test_bola_extraida_no_interrumpe_hay_carton_ganador() -> None:
    """El hallazgo central de DU-3: la ronda sigue extrayendo bolas
    (`sin_reclamo="continuar"`) sin que la pantalla vuelva a EN_JUEGO por su
    cuenta — solo `reclamo_vencido()` o `ganador_confirmado()` sacan de aquí."""
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    maquina.bola_extraida()
    assert maquina.estado == EstadoTransmision.HAY_CARTON_GANADOR


def test_cartones_a_una_bola_no_interrumpe_hay_carton_ganador() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    maquina.cartones_a_una_bola(5)
    assert maquina.estado == EstadoTransmision.HAY_CARTON_GANADOR


def test_reclamo_vencido_desde_hay_carton_ganador() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    maquina.reclamo_vencido()
    assert maquina.estado == EstadoTransmision.RECLAMO_VENCIDO


def test_reclamo_vencido_ignorado_fuera_de_hay_carton_ganador() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.reclamo_vencido()
    assert maquina.estado == EstadoTransmision.EN_JUEGO


def test_continuar_tras_reclamo_vencido_vuelve_a_en_juego() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    maquina.reclamo_vencido()
    maquina.continuar_tras_reclamo_vencido()
    assert maquina.estado == EstadoTransmision.EN_JUEGO


def test_continuar_tras_reclamo_vencido_respeta_a_una_bola_activo() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.cartones_a_una_bola(2)
    maquina.ganadores_detectados()
    maquina.reclamo_vencido()
    maquina.continuar_tras_reclamo_vencido()
    assert maquina.estado == EstadoTransmision.A_UNA_BOLA_CRITICA


def test_ganador_confirmado_desde_cualquier_estado() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ganadores_detectados()
    maquina.ganador_confirmado()
    assert maquina.estado == EstadoTransmision.GANADOR_CONFIRMADO


def test_ronda_cerrada_pasa_a_entre_rondas() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.ronda_cerrada()
    assert maquina.estado == EstadoTransmision.ENTRE_RONDAS


def test_ronda_iniciada_desde_entre_rondas() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.ronda_cerrada()
    maquina.ronda_iniciada()
    assert maquina.estado == EstadoTransmision.EN_JUEGO


def test_pausa_y_reanudacion_restauran_el_estado_anterior() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.cartones_a_una_bola(2)
    maquina.ronda_pausada()
    assert maquina.estado == EstadoTransmision.PAUSA

    maquina.ronda_reanudada()
    assert maquina.estado == EstadoTransmision.A_UNA_BOLA_CRITICA


def test_finalizar_evento_pasa_a_cierre_desde_cualquier_estado() -> None:
    maquina = MaquinaEstadoTransmision()
    maquina.bola_extraida()
    maquina.finalizar_evento()
    assert maquina.estado == EstadoTransmision.CIERRE
