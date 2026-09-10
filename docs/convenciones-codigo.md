# Convenciones de código — Proyecto BINGO

Este documento existe porque un convenio que no está escrito aquí no existe: el
plan de cada fase se archiva al cerrar la fase. Lo que sigue son reglas de
implementación, no de alcance. Se amplía en cada fase, nunca se recorta sin razón
escrita.

## Conexiones e hilos

- **Una conexión por hilo. Nunca se comparte.** `check_same_thread=True` se
  mantiene siempre. Un trabajador (`QThread`, hilo de `threading`) abre su propia
  conexión con `abrir_conexion()` y la cierra en un `finally`.
- En WAL conviven un escritor y N lectores. **La interfaz no mantiene nunca una
  transacción abierta entre dos vueltas del bucle de eventos.**
- `abrir_conexion(":memory:")` se salta la comprobación de `journal_mode` (no
  aplica a bases en memoria).

## Transacciones

- **Los repositorios nunca abren transacciones y nunca hacen commit.** Solo los
  servicios y `__main__` abren `transaccion()`.
- `transaccion()` no es reentrante: anidarla lanza `ErrorPersistencia`, nunca un
  `OperationalError` crudo de SQLite.
- Con `isolation_level=None`, una llamada a repositorio fuera de `transaccion()`
  hace autocommit; dentro, participa de la transacción abierta.

## Tabla de verbos de repositorio

| Verbo | Forma de la firma | Devuelve |
|---|---|---|
| `crear` | `(con, modelo)` | el modelo persistido (con `id` asignado) |
| `crear_varios` | `(con, list[modelo])` | `int` insertados; usa `executemany` |
| `obtener` | `(con, id)` | `Modelo \| None` — siempre por clave primaria |
| `obtener_por_<campo>` | `(con, valor)` | `Modelo \| None` |
| `listar` / `listar_por_<campo>` | `(con, ..., limite=None, desplazamiento=0)` | `list[Modelo]` |
| `contar` / `contar_por_<campo>` | `(con, ...)` | `int` |
| `existe_<campo>` | `(con, valor, excluir_id=None)` | `bool` |
| `actualizar` / `actualizar_<campo>` | `(con, modelo)` / `(con, id, valor)` | `None` |
| `eliminar` / `eliminar_por_<campo>` | `(con, id)` | `None` |

- Nombres de archivo: `repo_<entidad en singular>`, `servicio_<lo que gestiona,
  en plural>`.
- Paginación: siempre `limite` y `desplazamiento`, en ese orden.
- `con` va **siempre primero**, en repositorios y en servicios.
- `repo_auditoria.registrar` es la única excepción a la tabla (nombre fijado por
  el contrato de la fase 1): no generalizar ese nombre a otros repositorios.

## Mapeo fila → modelo

Cada repositorio termina con dos funciones privadas, plantilla para los que
falten:

```python
def _desde_fila(fila: sqlite3.Row) -> Modelo: ...
def _a_parametros(modelo: Modelo) -> dict[str, object]: ...
```

## Quién captura qué

- La vista captura `ErrorValidacion` → mensaje en línea sobre `e.campo`.
- La vista captura `ErrorBingo` (el resto de subclases) → franja no modal o modal
  según la tabla de canales de `ui/dialogos.py`.
- **La vista no captura nunca `Exception`.** Lo que no sea `ErrorBingo` es un
  fallo de programa y pertenece al manejador global (`utilidades/errores.py`).
- Los repositorios devuelven `None` cuando no encuentran algo por clave.
  **Los servicios lanzan `ErrorNoEncontrado`** cuando lo necesitan existente.

## Canales de error (`ui/dialogos.py`)

| Canal | Cuándo | Forma |
|---|---|---|
| En línea, junto al campo | `ErrorValidacion` | Texto bajo el campo, foco al campo |
| Franja de vista, no modal | `ErrorPersistencia`, `ErrorIntegridad`, `ErrorBaseBloqueada` | Barra en la cabecera de la vista con acción de reintentar |
| Modal | Solo condiciones terminales: migración fallida, base corrupta, sin permisos | Diálogo con detalle copiable y ruta del log |

## Errores (`utilidades/errores.py`)

Constructor fijo, no se improvisa por fase:

```python
class ErrorBingo(Exception):
    def __init__(self, clave_i18n, *, detalle="", parametros=None):
        ...
        self.clave_i18n = clave_i18n
        self.parametros = parametros or {}
        self.detalle = detalle  # técnico: va al log, nunca a la vista
```

**Regla asociada:** la vista pinta `t(e.clave_i18n, **e.parametros)`; el log
escribe `e.detalle` y la traza; `str(e)` no se le enseña nunca a un usuario.
Toda `clave_i18n` pasada a un constructor `Error*` debe existir en `es.json`
(verificado por `test_arquitectura.py`).

## Traducción de errores de `sqlite3`

Único punto de traducción: `persistencia/errores_sqlite.py::traducir_errores_sqlite()`,
un context manager aplicado en la frontera de cada repositorio. Conserva
`tipo` (`"unique" | "foreign_key" | "check" | "not_null"`) y `restriccion`
(p. ej. `"carton.evento_id, carton.firma"`) en `ErrorIntegridad`. El error
original de `sqlite3` se conserva siempre como `__cause__`.

## Migraciones

- Los archivos de migración **nunca** contienen su propio `BEGIN` ni `COMMIT`:
  el runner los añade envolviendo el script completo antes de pasarlo a
  `executescript()` (única forma de que el `COMMIT` implícito de
  `executescript()` no destruya la atomicidad).
- Nombre de archivo: tres dígitos, guion bajo, nombre en minúsculas, `.sql`.
- **Política de edición de la 001: es editable hasta el primer evento con datos
  reales.** A partir de ese momento, "nunca se edita una migración publicada" y
  todo cambio va en `002_*.sql`. *Si editas la 001 durante el desarrollo, corre
  `python -m bingo --reiniciar-datos` para no trabajar contra un esquema viejo.*

## Dominio

- `dominio/` no importa nada del proyecto salvo `utilidades/errores`. Nunca
  PySide6 ni sqlite3.
- Entidades con comportamiento propio van en su propio módulo
  (`dominio/carton.py`, `dominio/patron.py`, `dominio/bombo.py`, fases
  siguientes). Las que son solo registro van en `dominio/modelos.py`.
- `puede_transicionar(transiciones: Mapping[str, set[str]], actual, nuevo) -> bool`
  es genérica: cada fase pasa su propia tabla (`TRANSICIONES_EVENTO`,
  `TRANSICIONES_CARTON`, `TRANSICIONES_RONDA`), nunca se renombra la función.

## Dinero

Conversión centralizada en `dominio/dinero.py` (`a_centavos`, `formatear`).
Prohibida la conversión ad hoc en vistas o servicios: alimenta un comprobante
que se entrega a la organización.

## Trabajador `QThread` (`ui/tarea.py`)

- Señales `progreso(int, int)`, `terminado(object)`, `fallado(ErrorBingo)`;
  `cancelar()` cooperativo. Abre y cierra su propia conexión dentro de `run()`.
- Convenio del lado del servicio: los servicios aceptan
  `al_progresar: Callable[[int, int], None] | None = None` y
  `debe_cancelar: Callable[[], bool] | None = None`, y **nunca** importan Qt.

## Guardado: autoguardado vs. explícito (decisión DS14, fase 4)

- **Autoguardado con retardo** (`QTimer` de un solo disparo,
  `RETARDO_VISTA_PREVIA_MS`) solo en editores de **configuración visual de un
  registro único** por evento: la plantilla del cartón (`vista_plantilla.py`)
  y el tema del dashboard (`vista_tema.py`). No hay "cancelar" que tenga
  sentido — el registro siempre existe, solo se edita.
- **Guardar/Cancelar explícito** en toda vista que edita una **entidad de una
  colección** (un comprador, una ronda, un patrón): el operador puede abrir el
  formulario, arrepentirse y cerrar sin que nada se escriba. Corolario:
  cambiar de fila/selección con cambios sin guardar debería pedir
  confirmación de descarte — pendiente en `vista_rondas.py` (`TODOS.md`), que
  hoy guarda cada cambio de campo al vuelo en vez de por un botón explícito;
  no se corrigió por tiempo, no por estar de acuerdo con el atajo.

## i18n

- Ninguna cadena visible se escribe directamente en el código: todo pasa por
  `t(clave, **parametros)`.
- Clave faltante → `⟦clave⟧` (constante `MARCA_FALTANTE`), nunca cadena vacía ni
  excepción. Parámetro faltante dentro de una plantilla → se pinta
  `⟦nombre_parametro⟧`, no revienta. Plantilla mal formada (llave suelta) → se
  registra y se devuelve la plantilla cruda.
- Cada vista/widget propio implementa `retraducir(self) -> None`; los textos se
  asignan **únicamente** ahí, y el constructor la invoca al final.
  `retraducir()` toca solo textos estáticos (etiquetas, botones, títulos),
  **nunca** el contenido de un campo editable.
- El registro de widgets para la retraducción es un `weakref.WeakSet` a nivel de
  módulo de `i18n/`, con baja explícita en la señal `destroyed` del widget.

## Pruebas

- `tests/conftest.py` fija `QT_QPA_PLATFORM=offscreen` antes de cualquier otro
  import.
- `bingo_home` (autouse, función) hace estructuralmente imposible escribir en el
  `%LOCALAPPDATA%` real.
- `raiz_datos()` (en `config/rutas.py`) lee `os.environ` **en cada llamada**, sin
  cachear en una constante de módulo: si se cachea, `monkeypatch.setenv` deja de
  tener efecto y las pruebas escriben en el perfil real del desarrollador.
- Marcador `lento` para pruebas de volumen; bucle interno con
  `pytest -m "not lento"`.

## Otros

- `con` (la conexión) va siempre primero en cualquier función de repositorio o
  servicio.
- Punto de entrada probable: `def principal(argv: list[str] | None = None) -> int`.
- Todo módulo de `persistencia/`, `servicios/` y `utilidades/` abre con un
  docstring que declara su contrato.
- `docs/decisiones.md`: una entrada corta por decisión relevante, añadida al
  cerrar cada fase.
