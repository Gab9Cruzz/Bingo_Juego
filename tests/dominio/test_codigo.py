from bingo.dominio.codigo import normalizar, normalizar_texto

_CODIGOS_EVENTO = ["A-2026-000001", "A-2026-000002", "A-2026-000010"]


def test_normalizar_texto_colapsa_espacios_y_mayusculas() -> None:
    assert normalizar_texto("  a-2026-000001  ") == "A-2026-000001"
    assert normalizar_texto("a-2026   000001") == "A-2026 000001"


def test_caso_1_coincidencia_exacta() -> None:
    resultado = normalizar("A-2026-000001", _CODIGOS_EVENTO)
    assert resultado.es_unico
    assert resultado.codigo_unico == "A-2026-000001"


def test_caso_2_coincidencia_con_espacios_y_minusculas() -> None:
    resultado = normalizar("  a-2026-000002  ", _CODIGOS_EVENTO)
    assert resultado.codigo_unico == "A-2026-000002"


def test_caso_3_sufijo_numerico_unico() -> None:
    resultado = normalizar("10", _CODIGOS_EVENTO)
    assert resultado.codigo_unico == "A-2026-000010"


def test_caso_4_sufijo_numerico_ambiguo() -> None:
    resultado = normalizar("1", ["A-2026-000001", "B-2026-000001"])
    assert resultado.es_ambiguo
    assert not resultado.es_unico


def test_caso_5_texto_no_numerico_sin_coincidencia() -> None:
    resultado = normalizar("NO-EXISTE", _CODIGOS_EVENTO)
    assert resultado.codigos == ()


def test_caso_6_cadena_vacia_no_reconocible() -> None:
    resultado = normalizar("   ", _CODIGOS_EVENTO)
    assert resultado.codigos == ()


def test_sufijo_numerico_sin_coincidencia_no_es_ambiguo() -> None:
    resultado = normalizar("999", _CODIGOS_EVENTO)
    assert resultado.codigos == ()
    assert not resultado.es_ambiguo
