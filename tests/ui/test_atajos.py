import pytest

from bingo.ui.atajos import ATAJOS, RegistroAtajos


def test_getitem_resuelve_ambito_global() -> None:
    assert ATAJOS["nuevo"] == "Ctrl+N"


def test_secuencia_por_ambito() -> None:
    assert ATAJOS.secuencia("sorteo.extraer", "sorteo") == "Space"


def test_mismo_nombre_en_dos_ambitos_no_colisiona() -> None:
    registro = RegistroAtajos()
    registro.registrar("buscar", "Ctrl+F", "global")
    registro.registrar("buscar", "Ctrl+Shift+F", "sorteo")
    assert registro.secuencia("buscar", "global") == "Ctrl+F"
    assert registro.secuencia("buscar", "sorteo") == "Ctrl+Shift+F"


def test_atajo_sin_registrar_falla() -> None:
    registro = RegistroAtajos()
    with pytest.raises(KeyError):
        registro.secuencia("no_existe")


def test_extraer_tiene_alterno_que_no_colisiona() -> None:
    """DU-5: `F5` existe precisamente para no competir nunca con un campo de
    texto que tenga el foco."""
    assert ATAJOS.secuencia("sorteo.extraer_alterno", "sorteo") == "F5"
