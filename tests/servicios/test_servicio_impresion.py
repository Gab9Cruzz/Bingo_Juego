from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from factorias import crear_evento, crear_organizacion
from pypdf import PdfReader

from bingo.dominio.modelos import Lote
from bingo.persistencia import repo_carton, repo_evento, repo_lote
from bingo.servicios import servicio_cartones, servicio_impresion
from bingo.utilidades.errores import ErrorDominio, ErrorNoEncontrado


def _evento(con: sqlite3.Connection):
    org = crear_organizacion(con)
    return crear_evento(con, org.id)


def _lote_con_cartones(con: sqlite3.Connection, cantidad: int, prefijo: str = "P"):
    ev = _evento(con)
    lote = servicio_cartones.generar_lote(con, ev.id, cantidad, prefijo, semilla=f"s-{prefijo}")
    return ev, lote


def test_generar_pdf_lote_produce_archivos_que_abren(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    ev, lote = _lote_con_cartones(con, 20, "ABRE")
    rutas = servicio_impresion.generar_pdf_lote(con, ev.id, lote.id, tmp_path, hojas_por_archivo=3)

    assert rutas
    for ruta in rutas:
        assert ruta.exists()
        lector = PdfReader(str(ruta))
        assert len(lector.pages) > 0


def test_generar_pdf_lote_particiona_segun_hojas_por_archivo(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    # 20 cartones, 4 por hoja (defecto) = 5 hojas; hojas_por_archivo=2 -> 3 archivos (2+2+1).
    ev, lote = _lote_con_cartones(con, 20, "PART")
    rutas = servicio_impresion.generar_pdf_lote(con, ev.id, lote.id, tmp_path, hojas_por_archivo=2)

    assert len(rutas) == 3
    paginas_totales = sum(len(PdfReader(str(r)).pages) for r in rutas)
    assert paginas_totales == 5  # 20 cartones / 4 por hoja


def test_generar_pdf_lote_nombra_archivos_con_prefijo_y_numero(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    ev, lote = _lote_con_cartones(con, 10, "NOM")
    rutas = servicio_impresion.generar_pdf_lote(
        con, ev.id, lote.id, tmp_path, hojas_por_archivo=100
    )
    assert rutas[0].name == "NOM_parte_01.pdf"


def test_generar_pdf_lote_progreso_llega_al_total(con: sqlite3.Connection, tmp_path: Path) -> None:
    ev, lote = _lote_con_cartones(con, 12, "PROG")
    llamadas: list[tuple[int, int]] = []
    servicio_impresion.generar_pdf_lote(
        con, ev.id, lote.id, tmp_path, al_progresar=lambda he, t: llamadas.append((he, t))
    )
    assert llamadas
    assert llamadas[-1] == (12, 12)


def test_generar_pdf_lote_cancelacion_a_mitad_produce_archivo_valido(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    ev, lote = _lote_con_cartones(con, 40, "CANC")
    contador = {"n": 0}

    def _cancelar_tras_dos_hojas() -> bool:
        contador["n"] += 1
        return contador["n"] > 2

    rutas = servicio_impresion.generar_pdf_lote(
        con, ev.id, lote.id, tmp_path, debe_cancelar=_cancelar_tras_dos_hojas
    )
    assert rutas
    lector = PdfReader(str(rutas[-1]))
    assert len(lector.pages) >= 1  # PDF parcial pero válido, no corrupto


def test_generar_pdf_lote_vacio_lanza(con: sqlite3.Connection, tmp_path: Path) -> None:
    ev = _evento(con)
    lote_vacio = repo_lote.crear(
        con, Lote(evento_id=ev.id, cantidad=0, prefijo_codigo="VACIO", semilla="s")
    )
    with pytest.raises(ErrorDominio):
        servicio_impresion.generar_pdf_lote(con, ev.id, lote_vacio.id, tmp_path)


def test_generar_pdf_lote_evento_inexistente(con: sqlite3.Connection, tmp_path: Path) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_impresion.generar_pdf_lote(con, 999_999, 1, tmp_path)


def test_generar_pdf_lote_lote_de_otro_evento(con: sqlite3.Connection, tmp_path: Path) -> None:
    ev_a, lote_a = _lote_con_cartones(con, 5, "A")
    ev_b = _evento(con)
    with pytest.raises(ErrorNoEncontrado):
        servicio_impresion.generar_pdf_lote(con, ev_b.id, lote_a.id, tmp_path)


def test_generar_pdf_lote_asegura_clave_evento(con: sqlite3.Connection, tmp_path: Path) -> None:
    ev, lote = _lote_con_cartones(con, 4, "CLAVE")
    assert repo_evento.obtener(con, ev.id).clave_evento is None
    servicio_impresion.generar_pdf_lote(con, ev.id, lote.id, tmp_path)
    assert repo_evento.obtener(con, ev.id).clave_evento is not None


def test_marcar_lote_impreso(con: sqlite3.Connection) -> None:
    ev, lote = _lote_con_cartones(con, 3, "MARK")
    cambiados = servicio_impresion.marcar_lote_impreso(con, lote.id)
    assert cambiados == 3
    assert repo_carton.contar_por_estado(con, ev.id) == {"impreso": 3}


def test_marcar_lote_impreso_no_toca_anulados(con: sqlite3.Connection) -> None:
    ev, lote = _lote_con_cartones(con, 3, "MARK2")
    carton = repo_carton.listar_por_lote(con, lote.id)[0]
    repo_carton.actualizar_estado(con, carton.id, "anulado")

    cambiados = servicio_impresion.marcar_lote_impreso(con, lote.id)
    assert cambiados == 2
    assert repo_carton.obtener(con, carton.id).estado == "anulado"


def test_marcar_lote_impreso_lote_inexistente(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_impresion.marcar_lote_impreso(con, 999_999)


@pytest.mark.lento
def test_tamano_de_archivo_crece_linealmente_no_cuadraticamente(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    """Confirma que el caché de `ImageReader` de `MotorRenderCarton` funciona:
    generar 4x cartones con el mismo logo debe pesar ~4x, no explotar.
    """
    from PIL import Image

    from bingo.persistencia import repo_organizacion

    org = crear_organizacion(con)
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (400, 400), (10, 20, 30, 255)).save(logo)
    org.logo_path = str(logo)
    repo_organizacion.actualizar(con, org)

    ev_chico = crear_evento(con, org.id, nombre="Chico")
    lote_chico = servicio_cartones.generar_lote(con, ev_chico.id, 200, "CHICO", semilla="s-chico")
    carpeta_chica = tmp_path / "chico"
    rutas_chicas = servicio_impresion.generar_pdf_lote(
        con, ev_chico.id, lote_chico.id, carpeta_chica, hojas_por_archivo=1000
    )
    tamano_chico = sum(r.stat().st_size for r in rutas_chicas)

    ev_grande = crear_evento(con, org.id, nombre="Grande")
    lote_grande = servicio_cartones.generar_lote(
        con, ev_grande.id, 800, "GRANDE", semilla="s-grande"
    )
    carpeta_grande = tmp_path / "grande"
    rutas_grandes = servicio_impresion.generar_pdf_lote(
        con, ev_grande.id, lote_grande.id, carpeta_grande, hojas_por_archivo=1000
    )
    tamano_grande = sum(r.stat().st_size for r in rutas_grandes)

    razon = tamano_grande / tamano_chico
    # 4x los cartones -> se espera ~4x el tamaño, con margen generoso para el
    # overhead fijo del PDF (metadata, fuentes incrustadas una sola vez).
    assert razon < 6.0, f"Creció {razon:.1f}x con 4x los cartones: el caché de imagen no funciona"


@pytest.mark.lento
def test_generar_10000_cartones_sin_congelar(con: sqlite3.Connection, tmp_path: Path) -> None:
    import time

    ev, lote = _lote_con_cartones(con, 10_000, "VOL")
    inicio = time.perf_counter()
    rutas = servicio_impresion.generar_pdf_lote(
        con, ev.id, lote.id, tmp_path, hojas_por_archivo=500
    )
    duracion = time.perf_counter() - inicio

    assert rutas
    for ruta in rutas:
        lector = PdfReader(str(ruta))
        assert len(lector.pages) > 0
    # Medido en esta máquina: ~380s para 10.000 cartones (~38ms/cartón). Con
    # perfilado manual, el QR (`reportlab.graphics.barcode.qr`, codificador
    # Reed-Solomon puro Python) es ~93% de ese tiempo — sin QR baja a ~1.6ms/
    # cartón. El criterio de aceptación del contrato es "no se congela, con
    # progreso y cancelación" (cumplido: corre en `Tarea`/`QThread`), no un
    # tiempo límite — el margen aquí es generoso a propósito, para detectar
    # una regresión grosera, no para exigir una cifra que el contrato no pide.
    # Ver TODOS.md ("Acelerar la generación de QR...") si algún evento real
    # necesita lotes de 10.000+ más rápido que ~6-7 minutos.
    assert duracion < 600.0, f"Tardó {duracion:.1f}s para 10.000 cartones"
