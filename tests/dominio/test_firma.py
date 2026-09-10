from bingo.dominio import firma


def test_generar_clave_evento_produce_hex_de_longitud_esperada() -> None:
    clave = firma.generar_clave_evento()
    assert len(clave) == firma.LONGITUD_CLAVE_EVENTO_BYTES * 2
    int(clave, 16)  # no lanza: es hexadecimal válido


def test_generar_clave_evento_no_repite() -> None:
    assert firma.generar_clave_evento() != firma.generar_clave_evento()


def test_firmar_codigo_es_determinista() -> None:
    assert firma.firmar_codigo("clave", "ORG-2026-000001") == firma.firmar_codigo(
        "clave", "ORG-2026-000001"
    )


def test_firmar_codigo_depende_de_la_clave() -> None:
    assert firma.firmar_codigo("clave-a", "C1") != firma.firmar_codigo("clave-b", "C1")


def test_contenido_qr_formato() -> None:
    texto = firma.contenido_qr("clave", "ORG-2026-000001")
    codigo, hmac_hex = texto.split("|")
    assert codigo == "ORG-2026-000001"
    assert len(hmac_hex) == firma.LONGITUD_HMAC


def test_verificar_qr_acepta_codigo_generado() -> None:
    texto = firma.contenido_qr("clave-evento", "ORG-2026-000042")
    assert firma.verificar_qr("clave-evento", texto) == "ORG-2026-000042"


def test_verificar_qr_rechaza_codigo_alterado() -> None:
    texto = firma.contenido_qr("clave-evento", "ORG-2026-000042")
    codigo, hmac_hex = texto.split("|")
    alterado = f"ORG-2026-999999|{hmac_hex}"
    assert firma.verificar_qr("clave-evento", alterado) is None


def test_verificar_qr_rechaza_hmac_alterado() -> None:
    texto = firma.contenido_qr("clave-evento", "ORG-2026-000042")
    codigo, hmac_hex = texto.split("|")
    alterado = f"{codigo}|{'0' * len(hmac_hex)}"
    assert firma.verificar_qr("clave-evento", alterado) is None


def test_verificar_qr_rechaza_clave_distinta() -> None:
    texto = firma.contenido_qr("clave-a", "ORG-2026-000042")
    assert firma.verificar_qr("clave-b", texto) is None


def test_verificar_qr_rechaza_texto_sin_separador() -> None:
    assert firma.verificar_qr("clave", "sin-separador") is None


def test_verificar_qr_rechaza_codigo_vacio() -> None:
    assert firma.verificar_qr("clave", "|abcdef12") is None
