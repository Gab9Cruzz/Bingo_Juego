"""G33: `SQLITE_READONLY` y condiciones similares salen como `ErrorPersistencia`
traducido, y NO por el manejador global — matar el proceso por un directorio
de solo lectura es exactamente el modo de fallo que no se puede permitir en
un portátil de evento.
"""

from __future__ import annotations

import os
import stat

import pytest

from bingo.persistencia.conexion import abrir_conexion
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.persistencia.migraciones import aplicar_migraciones
from bingo.utilidades.errores import ErrorPersistencia


def test_base_de_solo_lectura_da_error_persistencia_traducido(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    aplicar_migraciones(con)
    con.close()

    ruta = bingo_home / "datos" / "bingo.db"
    os.chmod(ruta, stat.S_IREAD)
    try:
        con2 = abrir_conexion(synchronous="OFF")
        try:
            with pytest.raises(ErrorPersistencia), traducir_errores_sqlite():
                con2.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
        finally:
            con2.close()
    finally:
        os.chmod(ruta, stat.S_IWRITE)
