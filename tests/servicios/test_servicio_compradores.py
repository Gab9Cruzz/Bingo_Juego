"""El corazón de la fase 4 (contrato §4.9): archivos deliberadamente sucios,
construidos con `openpyxl` en la propia prueba — nunca ficheros binarios en
el repositorio."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl
import pytest
from factorias import crear_carton, crear_evento, crear_lote, crear_organizacion

from bingo.dominio.modelos import Comprador
from bingo.persistencia import repo_carton, repo_comprador
from bingo.servicios import servicio_cartones, servicio_compradores
from bingo.utilidades.errores import ErrorTransicionInvalida, ErrorValidacion

_TEXTOS_PLANTILLA = {
    "columna_codigo": "Codigo",
    "columna_nombre": "Nombre",
    "columna_telefono": "Telefono",
    "columna_cedula": "Cedula",
    "columna_correo": "Correo",
    "hoja_instrucciones": "Instrucciones",
    "instrucciones_titulo": "Instrucciones",
}


def _evento_con_cartones_impresos(con: sqlite3.Connection, cantidad: int = 10):
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    lote = crear_lote(con, evento.id)
    cartones = []
    for i in range(cantidad):
        c = crear_carton(con, evento.id, lote.id, semilla=i)
        servicio_cartones.cambiar_estado_carton(con, c.id, "impreso")
        cartones.append(c)
    return evento, cartones


def _libro_vacio_con_hoja_ventas() -> openpyxl.Workbook:
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    return libro


def test_exportar_plantilla_produce_hoja_ventas_e_instrucciones(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    evento, _cartones = _evento_con_cartones_impresos(con)
    ruta = servicio_compradores.exportar_plantilla(
        con, evento.id, tmp_path / "p.xlsx", _TEXTOS_PLANTILLA
    )
    libro = openpyxl.load_workbook(ruta)
    assert "Ventas" in libro.sheetnames
    assert "Instrucciones" in libro.sheetnames
    libro.close()


def test_exportar_plantilla_sin_cartones_falla(con: sqlite3.Connection, tmp_path: Path) -> None:
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    with pytest.raises(ErrorValidacion):
        servicio_compradores.exportar_plantilla(
            con, evento.id, tmp_path / "p.xlsx", _TEXTOS_PLANTILLA
        )


def test_validar_importacion_rechaza_xls(con: sqlite3.Connection, tmp_path: Path) -> None:
    evento, _c = _evento_con_cartones_impresos(con)
    ruta = tmp_path / "viejo.xls"
    ruta.write_bytes(b"no es realmente un xls, solo se prueba la extension")
    with pytest.raises(ErrorValidacion) as exc:
        servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert exc.value.clave_i18n == "compradores.error.formato_xls_legado"


def test_validar_importacion_rechaza_archivo_inexistente(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    evento, _c = _evento_con_cartones_impresos(con)
    with pytest.raises(ErrorValidacion):
        servicio_compradores.validar_importacion(con, evento.id, tmp_path / "no_existe.xlsx")


def test_validar_importacion_reporta_columnas_faltantes(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    evento, _c = _evento_con_cartones_impresos(con)
    libro = _libro_vacio_con_hoja_ventas()
    hoja = libro.active
    hoja.cell(row=1, column=1, value="algo")
    hoja.cell(row=1, column=2, value="otra_cosa")
    ruta = tmp_path / "malo.xlsx"
    libro.save(ruta)
    libro.close()

    informe = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert set(informe.columnas_faltantes) == {"codigo", "nombre"}


def test_validar_importacion_archivo_sucio_completo(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    """Un solo archivo que combina todos los casos sucios del contrato §4.9:
    encabezados reordenados/renombrados/con acentos y mayúsculas, fila vacía
    en medio, código duplicado, cartón ya asignado, fila sin nombre, teléfono
    con cero inicial, y una columna extra desconocida."""
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=10)

    # el cartón 5 ya tiene comprador vivo, sin pasar por "vendido" a propósito
    # (probar el camino "ya_asignado" no requiere que el cartón esté vendido)
    ya_asignado = repo_comprador.crear(
        con, Comprador(carton_id=cartones[5].id, nombre="Comprador previo")
    )
    assert ya_asignado.id is not None

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    # Encabezados reordenados, con alias, acentos y mayúsculas.
    hoja.cell(row=1, column=1, value="NOMBRE")
    hoja.cell(row=1, column=2, value="Código")
    hoja.cell(row=1, column=3, value="Teléfono")
    hoja.cell(row=1, column=4, value="Correo Electronico")

    hoja.cell(row=2, column=1, value="Ana Lopez")
    hoja.cell(row=2, column=2, value=cartones[0].codigo)
    hoja.cell(row=2, column=3, value="0987654321")  # cero inicial: no debe perderse
    hoja.cell(row=2, column=4, value="ana@example.com")

    # fila totalmente vacía en medio
    for columna in range(1, 5):
        hoja.cell(row=3, column=columna, value=None)

    # duplicado en archivo (mismo cartón que la fila 2)
    hoja.cell(row=4, column=1, value="Ana Duplicada")
    hoja.cell(row=4, column=2, value=cartones[0].codigo)

    # código inventado
    hoja.cell(row=5, column=1, value="Nadie")
    hoja.cell(row=5, column=2, value="NO-EXISTE-999")

    # cartón ya asignado a otro comprador
    hoja.cell(row=6, column=1, value="Otro Nombre")
    hoja.cell(row=6, column=2, value=cartones[5].codigo)

    # fila sin nombre (pero con teléfono: sí cuenta como problema real)
    hoja.cell(row=7, column=1, value=None)
    hoja.cell(row=7, column=2, value=cartones[1].codigo)
    hoja.cell(row=7, column=3, value="099")

    # columna extra desconocida, se ignora en silencio
    hoja.cell(row=1, column=5, value="Columna rara que nadie pidió")
    hoja.cell(row=2, column=5, value="dato irrelevante")

    ruta = tmp_path / "sucio.xlsx"
    libro.save(ruta)
    libro.close()

    informe = servicio_compradores.validar_importacion(con, evento.id, ruta)

    assert len(informe.correctas) == 1
    assert informe.correctas[0].telefono == "0987654321"
    assert len(informe.duplicado_en_archivo) == 1
    assert len(informe.codigo_inexistente) == 1
    assert len(informe.ya_asignado) == 1
    assert len(informe.sin_nombre) == 1
    assert informe.columnas_faltantes == []


def test_reimportacion_no_reporta_las_ya_cargadas_como_error(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    """800 repetidas + 200 nuevas -> 200 correctas, 800 `ya_registrado_igual`
    (contrato §4.2). Se reduce la escala para que la prueba corra rápido en
    el bucle interno; `test_importacion_de_mil_filas_marcada_lento` cubre el
    volumen real del criterio de aceptación."""
    total = 20
    ya_cargadas = 12
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=total)

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    hoja.cell(row=1, column=1, value="codigo")
    hoja.cell(row=1, column=2, value="nombre")
    for i, carton in enumerate(cartones):
        hoja.cell(row=i + 2, column=1, value=carton.codigo)
        hoja.cell(row=i + 2, column=2, value=f"Comprador {i}")
    ruta = tmp_path / "completo.xlsx"
    libro.save(ruta)
    libro.close()

    informe_1 = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert len(informe_1.correctas) == total

    # Solo se aplican las primeras `ya_cargadas`.
    informe_1.correctas = informe_1.correctas[:ya_cargadas]
    resultado_1 = servicio_compradores.aplicar_importacion(con, evento.id, informe_1)
    assert resultado_1.aplicadas == ya_cargadas

    informe_2 = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert len(informe_2.correctas) == total - ya_cargadas
    assert len(informe_2.ya_registrado_igual) == ya_cargadas


def test_aplicar_importacion_es_atomica_por_bloque(
    con: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decisión TD-3: la escritura ya no es una sola transacción para todo
    el archivo (se trocea para no sostener el lock de escritor). Cada
    bloque, sin embargo, sigue siendo atómico: si `repo_carton.
    actualizar_estado` falla a mitad de un bloque, ninguna fila de *ese*
    bloque queda aplicada, y el resultado informa dónde se detuvo."""
    from bingo.config import ajustes

    monkeypatch.setattr(ajustes, "TAMANO_BLOQUE_IMPORTACION", 2)
    monkeypatch.setattr(servicio_compradores, "TAMANO_BLOQUE_IMPORTACION", 2)

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=4)
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    hoja.cell(row=1, column=1, value="codigo")
    hoja.cell(row=1, column=2, value="nombre")
    for i, carton in enumerate(cartones):
        hoja.cell(row=i + 2, column=1, value=carton.codigo)
        hoja.cell(row=i + 2, column=2, value=f"Comprador {i}")
    ruta = tmp_path / "cuatro.xlsx"
    libro.save(ruta)
    libro.close()

    informe = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert len(informe.correctas) == 4

    llamadas = {"n": 0}
    original = repo_comprador.crear

    def _crear_que_falla_en_el_tercero(con_, comprador):
        llamadas["n"] += 1
        if llamadas["n"] == 3:
            raise ErrorTransicionInvalida("error.transicion_invalida", parametros={})
        return original(con_, comprador)

    monkeypatch.setattr(repo_comprador, "crear", _crear_que_falla_en_el_tercero)

    resultado = servicio_compradores.aplicar_importacion(con, evento.id, informe)

    # El primer bloque (2 filas) se aplicó completo; el segundo bloque
    # (donde cae la tercera llamada) no dejó ninguna fila a medias.
    assert resultado.aplicadas == 2
    assert resultado.error is not None
    conteo = repo_carton.contar_por_estado(con, evento.id)
    assert conteo.get("vendido", 0) == 2
    assert repo_comprador.contar_por_evento(con, evento.id) == 2


def test_importacion_completa_comprador_provisional(
    con: sqlite3.Connection, tmp_path: Path
) -> None:
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=3)
    resultado_rango = servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, cartones[0].codigo, cartones[0].codigo, nombre_generico="Venta en puerta"
    )
    assert resultado_rango.marcados == 1

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    hoja.cell(row=1, column=1, value="codigo")
    hoja.cell(row=1, column=2, value="nombre")
    hoja.cell(row=1, column=3, value="telefono")
    hoja.cell(row=2, column=1, value=cartones[0].codigo)
    hoja.cell(row=2, column=2, value="Nombre Real")
    hoja.cell(row=2, column=3, value="0999999999")
    ruta = tmp_path / "completa.xlsx"
    libro.save(ruta)
    libro.close()

    informe = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert len(informe.completa_provisional) == 1
    assert len(informe.correctas) == 0

    resultado = servicio_compradores.aplicar_importacion(con, evento.id, informe)
    assert resultado.completadas_provisionales == 1

    comprador = repo_comprador.obtener_por_carton(con, cartones[0].id)
    assert comprador.nombre == "Nombre Real"
    assert comprador.provisional is False
    assert repo_carton.obtener(con, cartones[0].id).estado == "vendido"


def test_registrar_manual_feliz(con: sqlite3.Connection) -> None:
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    creado = servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    assert creado.id is not None
    assert repo_carton.obtener(con, cartones[0].id).estado == "vendido"


def test_registrar_manual_codigo_inexistente(con: sqlite3.Connection) -> None:
    from bingo.dominio.modelos import Comprador

    evento, _cartones = _evento_con_cartones_impresos(con, cantidad=1)
    with pytest.raises(ErrorValidacion):
        servicio_compradores.registrar_manual(
            con, evento.id, "NO-EXISTE", Comprador(carton_id=0, nombre="Juan")
        )


def test_registrar_manual_ya_asignado(con: sqlite3.Connection) -> None:
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Primero")
    )
    with pytest.raises(ErrorValidacion):
        servicio_compradores.registrar_manual(
            con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Segundo")
        )


def test_anular_venta_devuelve_al_estado_previo(con: sqlite3.Connection) -> None:
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    creado = servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    servicio_compradores.anular_venta(con, creado.id, motivo="se arrepintió")

    carton = repo_carton.obtener(con, cartones[0].id)
    assert carton.estado == "impreso"  # el estado que tenía antes de venderse
    assert repo_comprador.obtener_por_carton(con, cartones[0].id) is None
    assert repo_comprador.obtener(con, creado.id).anulado_en is not None


def test_anular_venta_no_deja_datos_personales_en_auditoria(con: sqlite3.Connection) -> None:
    from bingo.dominio.modelos import Comprador
    from bingo.persistencia import repo_auditoria

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    creado = servicio_compradores.registrar_manual(
        con,
        evento.id,
        cartones[0].codigo,
        Comprador(carton_id=0, nombre="Nombre Secreto", telefono="0999999999"),
    )
    servicio_compradores.anular_venta(con, creado.id)

    registros = repo_auditoria.listar_por_evento(con, evento.id)
    detalles = " ".join(r.detalle or "" for r in registros)
    assert "Nombre Secreto" not in detalles
    assert "0999999999" not in detalles


def test_anular_venta_permite_revender_el_carton(con: sqlite3.Connection) -> None:
    """Hallazgo E-C3: el índice único de `comprador.carton_id` es parcial —
    anular no debe inutilizar el cartón."""
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    primero = servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Primero")
    )
    servicio_compradores.anular_venta(con, primero.id)
    segundo = servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Segundo")
    )
    assert segundo.id is not None
    assert repo_carton.obtener(con, cartones[0].id).estado == "vendido"


def test_marcar_vendidos_por_rango_filtra_no_aborta(con: sqlite3.Connection) -> None:
    """Hallazgo E-C2: un cartón ya vendido dentro del rango no tira el rango
    entero."""
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=5)
    servicio_cartones.cambiar_estado_carton(con, cartones[4].id, "anulado")
    repo_comprador.crear(con, Comprador(carton_id=cartones[2].id, nombre="Ya vendido"))
    # Escritura directa por repositorio para el montaje de la prueba: el
    # servicio bloquea a propósito la ruta genérica hacia "vendido"
    # (hallazgo E-A5, ver test_cambiar_estado_carton_generico_no_permite_vendido).
    repo_carton.actualizar_estado(con, cartones[2].id, "vendido")

    resultado = servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, cartones[0].codigo, cartones[4].codigo, nombre_generico="Venta en puerta"
    )
    assert resultado.marcados == 3  # 0, 1, 3
    assert resultado.ya_vendidos == 1
    assert resultado.omitidos_anulados == 1


def test_marcar_vendidos_por_rango_es_idempotente(con: sqlite3.Connection) -> None:
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=3)
    r1 = servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, cartones[0].codigo, cartones[2].codigo, nombre_generico="Venta en puerta"
    )
    r2 = servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, cartones[0].codigo, cartones[2].codigo, nombre_generico="Venta en puerta"
    )
    assert r1.marcados == 3
    assert r2.marcados == 0
    assert r2.ya_vendidos == 3


def test_invariante_ningun_vendido_sin_comprador_vivo(con: sqlite3.Connection) -> None:
    """El invariante que sostiene toda la regla de elegibilidad estricta
    (UC-1): tras cualquier operación de escritura de este módulo, ningún
    cartón `vendido` debe carecer de una fila `comprador` viva."""
    from bingo.dominio.modelos import Comprador

    evento, cartones = _evento_con_cartones_impresos(con, cantidad=3)
    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="A")
    )
    servicio_compradores.marcar_vendidos_por_rango(
        con, evento.id, cartones[1].codigo, cartones[1].codigo, nombre_generico="Puerta"
    )

    todos = repo_carton.listar_por_evento(con, evento.id, limite=None)
    vendidos = [c for c in todos if c.estado == "vendido"]
    for carton in vendidos:
        assert repo_comprador.obtener_por_carton(con, carton.id) is not None


def test_cambiar_estado_carton_generico_no_permite_vendido(con: sqlite3.Connection) -> None:
    """`servicio_cartones.cambiar_estado_carton` (fase 2) no puede ser la
    puerta trasera que rompa el invariante de arriba (hallazgo E-A5)."""
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1)
    with pytest.raises(ErrorTransicionInvalida):
        servicio_cartones.cambiar_estado_carton(con, cartones[0].id, "vendido")


@pytest.mark.lento
def test_importacion_de_mil_filas_marcada_lento(con: sqlite3.Connection, tmp_path: Path) -> None:
    """Criterio de aceptación del contrato: un Excel de 1.000 compradores.
    Corre en `Tarea` en producción; aquí se valida y se aplica en línea."""
    evento, cartones = _evento_con_cartones_impresos(con, cantidad=1000)
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    hoja.cell(row=1, column=1, value="codigo")
    hoja.cell(row=1, column=2, value="nombre")
    for i, carton in enumerate(cartones):
        hoja.cell(row=i + 2, column=1, value=carton.codigo)
        hoja.cell(row=i + 2, column=2, value=f"Comprador {i}")
    ruta = tmp_path / "mil.xlsx"
    libro.save(ruta)
    libro.close()

    informe = servicio_compradores.validar_importacion(con, evento.id, ruta)
    assert len(informe.correctas) == 1000
    resultado = servicio_compradores.aplicar_importacion(con, evento.id, informe)
    assert resultado.aplicadas == 1000
    assert repo_comprador.contar_por_evento(con, evento.id) == 1000
