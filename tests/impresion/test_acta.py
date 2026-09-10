from pathlib import Path

from pypdf import PdfReader

from bingo.impresion.acta import escribir_acta_pdf


def _escribir(ruta: Path, **overrides) -> Path:
    base = {
        "organizacion_nombre": "Fundación X",
        "evento_nombre": "Bingo 2026",
        "ronda_nombre": "Ronda 1",
        "patron_nombre": "Línea horizontal",
        "premio_texto": "Televisor",
        "numeros": list(range(1, 76)),
        "ganadores": [{"codigo": "A-0001", "decision": "unico"}],
        "hash_acta": "abc123",
        "textos": {},
    }
    base.update(overrides)
    return escribir_acta_pdf(ruta, **base)


def test_genera_un_pdf_que_abre(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "acta.pdf")
    lector = PdfReader(str(ruta))
    assert len(lector.pages) >= 1


def test_incluye_el_hash_en_el_texto(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "acta.pdf", hash_acta="deadbeef" * 8)
    lector = PdfReader(str(ruta))
    texto = "".join(pagina.extract_text() or "" for pagina in lector.pages)
    assert "deadbeef" in texto


def test_sin_ganadores_no_lanza(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "acta.pdf", ganadores=[])
    lector = PdfReader(str(ruta))
    assert len(lector.pages) >= 1


def test_muchos_ganadores_agrega_paginas(tmp_path: Path) -> None:
    ganadores = [{"codigo": f"A-{i:04d}", "decision": "rechazado"} for i in range(80)]
    ruta = _escribir(tmp_path / "acta.pdf", ganadores=ganadores)
    lector = PdfReader(str(ruta))
    assert len(lector.pages) >= 2


def test_crea_carpetas_intermedias(tmp_path: Path) -> None:
    ruta = _escribir(tmp_path / "no_existe" / "acta.pdf")
    assert ruta.exists()
