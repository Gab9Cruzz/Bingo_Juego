import logging
import sys
import threading

from bingo.utilidades.errores import (
    ErrorBingo,
    ErrorImagen,
    ErrorIntegridad,
    ErrorTransicionInvalida,
    ErrorValidacion,
    instalar_manejador_global,
)


def test_jerarquia() -> None:
    assert issubclass(ErrorImagen, ErrorValidacion)
    assert issubclass(ErrorTransicionInvalida, Exception)
    assert not issubclass(ErrorTransicionInvalida, ErrorValidacion)


def test_constructor_guarda_clave_y_parametros() -> None:
    error = ErrorBingo("clave.x", detalle="tecnico", parametros={"a": 1})
    assert error.clave_i18n == "clave.x"
    assert error.parametros == {"a": 1}
    assert error.detalle == "tecnico"


def test_error_integridad_guarda_tipo_y_restriccion() -> None:
    error = ErrorIntegridad("error.integridad.unique", tipo="unique", restriccion="carton.firma")
    assert error.tipo == "unique"
    assert error.restriccion == "carton.firma"


def test_error_validacion_guarda_campo() -> None:
    error = ErrorValidacion("eventos.error.nombre_vacio", campo="nombre")
    assert error.campo == "nombre"


def test_manejador_hilo_trabajador_solo_registra(caplog) -> None:
    """G11: una excepción de un hilo que NO es el principal solo se registra,
    nunca intenta construir un diálogo (comportamiento indefinido fuera del
    hilo de la interfaz).
    """
    instalar_manejador_global(mostrar_dialogo=lambda e: (_ for _ in ()).throw(AssertionError()))

    def _hilo() -> None:
        raise RuntimeError("boom en hilo trabajador")

    hilo = threading.Thread(target=_hilo)
    with caplog.at_level(logging.CRITICAL, logger="bingo"):
        hilo.start()
        hilo.join()

    assert any(
        r.exc_info is not None and "boom en hilo trabajador" in str(r.exc_info[1])
        for r in caplog.records
    )


def test_manejador_hilo_principal_llama_dialogo() -> None:
    llamado = []
    instalar_manejador_global(mostrar_dialogo=lambda e: llamado.append(e))
    try:
        raise ValueError("boom en hilo principal")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert len(llamado) == 1
