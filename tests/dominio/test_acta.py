from bingo.dominio.acta import GanadorActa, carga_canonica, hash_acta


def _carga(**overrides) -> str:
    base = {
        "organizacion_nombre": "Fundación X",
        "evento_nombre": "Bingo 2026",
        "ronda_nombre": "Ronda 1",
        "patron_nombre": "Línea horizontal",
        "premio_texto": "Televisor",
        "numeros": [7, 42, 13],
        "ganadores": [GanadorActa(codigo="A-0001", decision="unico")],
    }
    base.update(overrides)
    return carga_canonica(**base)


def test_carga_empieza_por_version() -> None:
    assert _carga().startswith("acta/v1\n")


def test_misma_ronda_da_la_misma_carga_y_el_mismo_hash() -> None:
    """Es la razón de existir de esta función: regenerar el acta del mismo
    sorteo tiene que dar el mismo hash — de lo contrario no es un
    comprobante."""
    carga_a = _carga()
    carga_b = _carga()
    assert carga_a == carga_b
    assert hash_acta(carga_a) == hash_acta(carga_b)


def test_orden_de_lectura_de_ganadores_no_cambia_la_carga() -> None:
    g1 = GanadorActa(codigo="A-0002", decision="rechazado")
    g2 = GanadorActa(codigo="A-0001", decision="unico")
    carga_orden_1 = _carga(ganadores=[g1, g2])
    carga_orden_2 = _carga(ganadores=[g2, g1])
    assert carga_orden_1 == carga_orden_2


def test_una_bola_distinta_cambia_el_hash() -> None:
    assert hash_acta(_carga(numeros=[7, 42, 13])) != hash_acta(_carga(numeros=[7, 42, 14]))


def test_una_decision_distinta_cambia_el_hash() -> None:
    original = _carga()
    modificada = _carga(ganadores=[GanadorActa(codigo="A-0001", decision="rechazado")])
    assert hash_acta(original) != hash_acta(modificada)


def test_sin_ganadores_es_una_carga_valida() -> None:
    carga = _carga(ganadores=[])
    assert carga.endswith("\n")  # la última línea (ganadores) queda vacía
    hash_acta(carga)  # no lanza


def test_hash_es_sha256_hexadecimal() -> None:
    resultado = hash_acta(_carga())
    assert len(resultado) == 64
    int(resultado, 16)  # no lanza si es hexadecimal válido
