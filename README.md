# BINGO

Aplicación de escritorio (Python 3.12+ / PySide6 / SQLite) para montar y
ejecutar bingos de 75 bolas: organizaciones, eventos, cartones, plantillas
imprimibles, compradores, rondas y transmisión en vivo.

Ver `docs/Proyecto_Alcance.md` (qué construye) y `docs/Documento_Tecnico.md`
(cómo). Reglas de implementación en `docs/convenciones-codigo.md`.

## Requisitos

- Windows 10/11 de 64 bits (multiplataforma en el código, probado solo en
  Windows).
- **Python 3.12** exacto para desarrollar — no una versión más nueva que pueda
  haber instalada en la máquina. Verificar con `py -0p`; instalar con
  `winget install Python.Python.3.12` si falta.

## Instalación

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Ejecución

```bash
python -m bingo
```

`--reiniciar-datos` borra la base de datos local y vuelve a aplicar las
migraciones desde cero (para desarrollo; ver política de la 001 editable en
`docs/convenciones-codigo.md`). `--forzar-instancia` ignora un bloqueo de
instancia única que haya quedado rancio.

Variable de entorno `BINGO_HOME` sobreescribe dónde vive todo (por defecto
`%LOCALAPPDATA%\Bingo`); las pruebas la usan para no tocar nunca el perfil real.
`BINGO_DEBUG=1` sube la consola a nivel `DEBUG` (el archivo de log queda
siempre en `INFO`).

## Dónde guarda sus datos

| Contenido | Ruta |
|---|---|
| Base de datos | `%LOCALAPPDATA%\Bingo\datos\bingo.db` |
| Logs de aplicación | `%LOCALAPPDATA%\Bingo\logs\aplicacion.log` |
| Respaldos | `%LOCALAPPDATA%\Bingo\respaldos\` |
| Imágenes y logos | `%LOCALAPPDATA%\Bingo\medios\<id organización>\` |
| Preferencias | `%LOCALAPPDATA%\Bingo\preferencias.json` |

**El archivo `.db` no debe vivir en una carpeta sincronizada** (OneDrive,
Dropbox, Google Drive, iCloud) ni en una unidad de red: es la causa más
frecuente de corrupción en SQLite. La aplicación avisa si detecta esa
situación.

## Pruebas

```bash
pytest                    # suite completa
pytest -m "not lento"     # bucle interno de desarrollo, sin pruebas de volumen
pytest tests/persistencia/test_conexion.py -v   # un solo archivo
```

Las pruebas nunca tocan el `%LOCALAPPDATA%` real: `tests/conftest.py` fija
`BINGO_HOME` a una carpeta temporal en cada prueba.

## Lint

```bash
ruff check .
ruff format --check .
```

## Reiniciar la base de desarrollo

Mientras se desarrolla, es normal acumular datos de prueba o editar el esquema
de la migración `001_inicial.sql` (ver política en
`docs/convenciones-codigo.md`). Para empezar de cero sin desinstalar nada:

```bash
python -m bingo --reiniciar-datos
```

## Versionado

Semántico (`MAJOR.MINOR.PATCH`), visible en Ajustes › Diagnóstico. Ver
`CHANGELOG.md`.
