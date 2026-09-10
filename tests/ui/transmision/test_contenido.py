from bingo import i18n
from bingo.ui.transmision import contenido


def test_hay_carton_ganador_nunca_lleva_codigo_ni_nombre() -> None:
    """Regla que no se negocia del contrato §5.4: el aviso de "hay
    ganador" no revela código ni nombre. Se verifica sobre el texto, no
    sobre píxeles (tarea 4.9)."""
    texto = contenido.texto_hay_carton_ganador("es", "WhatsApp 099-000-0000", 45)
    assert "A-" not in texto  # ningún código de cartón por accidente
    assert "099-000-0000" in texto  # el canal SÍ se anuncia
    assert "45" in texto


def test_hay_carton_ganador_sin_limite_no_muestra_segundos() -> None:
    texto = contenido.texto_hay_carton_ganador("es", "el escenario", None)
    assert "None" not in texto


def test_ganador_confirmado_es_el_unico_que_lleva_codigo_y_nombre() -> None:
    texto = contenido.texto_ganador_confirmado("es", "A-0142", "María Chávez")
    assert "A-0142" in texto
    assert "María Chávez" in texto


def test_idioma_publico_independiente_del_idioma_de_interfaz() -> None:
    """Decisión DU-13: aunque la interfaz esté en inglés, el texto de
    transmisión sigue el idioma configurado en el tema del evento."""
    i18n.cargar("en")
    texto_es = contenido.texto_pausa("es")
    texto_en = contenido.texto_pausa("en")
    assert texto_es != texto_en
    assert texto_es == "EN PAUSA"
    assert texto_en == "PAUSED"


def test_bienvenida_usa_texto_configurado_si_existe() -> None:
    assert contenido.texto_bienvenida("es", "Bienvenidos al Bingo de la Fundación") == (
        "Bienvenidos al Bingo de la Fundación"
    )


def test_bienvenida_cae_al_texto_por_defecto_si_vacio() -> None:
    assert contenido.texto_bienvenida("es", "") != ""


def test_a_una_bola_incluye_la_cantidad() -> None:
    assert "7" in contenido.texto_a_una_bola("es", 7)
