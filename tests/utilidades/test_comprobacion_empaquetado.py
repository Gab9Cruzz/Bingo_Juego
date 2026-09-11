from bingo.utilidades.comprobacion_empaquetado import comprobar


def test_comprobar_no_encuentra_problemas_en_el_arbol_de_fuentes() -> None:
    """No prueba PyInstaller (eso es `empaquetado/humo.py`, contra el `.exe`
    real): prueba que la lógica de la propia comprobación no tiene falsos
    positivos sobre el árbol de fuentes, donde los tres recursos que mira
    (migraciones, i18n, sonidos/fuentes) sí existen."""
    assert comprobar() == []
