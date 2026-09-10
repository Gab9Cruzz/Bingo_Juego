import json
import re

from bingo import i18n
from bingo.i18n import MARCA_FALTANTE

_RUTA_ES = None
_RUTA_EN = None


def _cargar_json(idioma: str) -> dict[str, str]:
    from pathlib import Path

    ruta = Path(i18n.__file__).parent / f"{idioma}.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def _marcadores(texto: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", texto))


def test_paridad_de_claves() -> None:
    es = _cargar_json("es")
    en = _cargar_json("en")
    assert set(es.keys()) == set(en.keys())


def test_paridad_de_marcadores() -> None:
    es = _cargar_json("es")
    en = _cargar_json("en")
    for clave in es:
        assert _marcadores(es[clave]) == _marcadores(en[clave]), clave


def test_clave_faltante_devuelve_marca_visible() -> None:
    i18n.cargar("es")
    resultado = i18n.t("clave.que.no.existe")
    assert resultado == MARCA_FALTANTE.format(clave="clave.que.no.existe")


def test_parametro_faltante_no_rompe() -> None:
    i18n.cargar("es")
    # organizaciones.eventos_contador usa {cantidad}
    resultado = i18n.t("organizaciones.eventos_contador")
    assert "⟦cantidad⟧" in resultado


def test_respaldo_a_espanol_si_falta_en_ingles(monkeypatch) -> None:
    i18n.cargar("es")
    i18n.cargar("en")
    i18n._traducciones["en"]["clave.solo.es"] = None  # type: ignore[index]
    del i18n._traducciones["en"]["clave.solo.es"]
    i18n._traducciones["es"]["clave.solo.es"] = "Solo en español"
    resultado = i18n.t("clave.solo.es")
    assert resultado == "Solo en español"


def test_cambiar_idioma() -> None:
    i18n.cargar("es")
    assert i18n.t("comun.guardar") == "Guardar"
    i18n.cargar("en")
    assert i18n.t("comun.guardar") == "Save"


def test_t_en_no_depende_del_idioma_activo() -> None:
    """Decisión DU-13: la ventana de transmisión resuelve contra un idioma
    explícito, no el de la interfaz — si el operador prueba la app en
    inglés, `t_en("es", ...)` sigue devolviendo español."""
    i18n.cargar("en")
    assert i18n.t("comun.guardar") == "Save"
    assert i18n.t_en("es", "comun.guardar") == "Guardar"
    assert i18n.t_en("en", "comun.guardar") == "Save"


def test_t_en_clave_faltante_devuelve_marca() -> None:
    i18n.cargar("es")
    assert i18n.t_en("en", "clave.que.no.existe") == MARCA_FALTANTE.format(
        clave="clave.que.no.existe"
    )
