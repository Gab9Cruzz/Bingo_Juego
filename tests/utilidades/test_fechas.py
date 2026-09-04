from datetime import UTC, datetime

from bingo.utilidades.fechas import a_iso, ahora_iso, desde_iso, formatear_para_ui


def test_ahora_iso_termina_en_z() -> None:
    assert ahora_iso().endswith("Z")


def test_ida_y_vuelta() -> None:
    momento = datetime(2026, 12, 24, 20, 30, 0, tzinfo=UTC)
    texto = a_iso(momento)
    assert texto == "2026-12-24T20:30:00Z"
    assert desde_iso(texto) == momento


def test_fecha_de_calendario_sin_zona() -> None:
    # evento.fecha se guarda como YYYY-MM-DD, sin componente de hora ni zona.
    fecha = "2026-12-24"
    assert len(fecha) == 10
    assert "T" not in fecha


def test_formatear_para_ui_es() -> None:
    texto = a_iso(datetime(2026, 1, 5, 14, 30, tzinfo=UTC))
    assert "/" in formatear_para_ui(texto, "es")


def test_formatear_para_ui_en() -> None:
    texto = a_iso(datetime(2026, 1, 5, 14, 30, tzinfo=UTC))
    assert "-" in formatear_para_ui(texto, "en")
