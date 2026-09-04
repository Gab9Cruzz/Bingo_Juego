<!-- /autoplan restore point: C:\Users\Gabo\.gstack\projects\Bingo_App\no-branch-autoplan-restore-20260904-134945.md -->

# Plan de implementación — FASE 1 · Cimientos

**Proyecto:** BINGO · **Autor del plan:** Gabriel + Claude Code
**Fecha:** 2026-09-04 · **Entregable:** etiqueta `v0.1.0`
**Fuentes:** `docs/Fase_1/Contrato_Fase1.md` (contrato de la fase), `docs/Documento_Tecnico.md`
(arquitectura, esquema, convenciones), `docs/Proyecto_Alcance.md` (alcance funcional),
`docs/Plan_Fases_Bingo.md` (vista general).

**Regla rectora del plan:** este documento cumple **todo** lo establecido en
`docs/Fase_1/Contrato_Fase1.md`. Cada tarea 1.1–1.6 del contrato original aparece aquí
íntegra y ampliada. Lo que se añade sobre el contrato está marcado con `[+]` y
justificado; nada del contrato se recorta.

---

## 0. Punto de partida y objetivo

**Punto de partida:** carpeta con cuatro documentos markdown y nada más. Sin
repositorio Git, sin código, sin entorno virtual.

**Objetivo de la fase:** una aplicación de escritorio que abre, crea su propia
estructura de datos en el equipo, aplica migraciones, y permite dar de alta
organizaciones (con logo y colores) y eventos en borrador, todo persistido. Al
cerrar y reabrir, la información sigue ahí. La interfaz cambia de idioma
completo. `ruff check` pasa limpio.

**Lo que NO hay al terminar la fase 1:** cartones, patrones, PDF, Excel, sorteo.
El esqueleto existe; el bingo llega en fases 2–5.

---

## 1. Entorno verificado (probes ejecutados)

| Comprobación | Resultado | Implicación |
|---|---|---|
| `python --version` | 3.14.2 (64-bit) | Supera el mínimo 3.12 del documento técnico |
| `git --version` | 2.49.0.windows.1 | Disponible |
| `pip index versions PySide6` | 6.11.2, rueda `cp310-abi3-win_amd64` | Instala en 3.14 sin compilar |
| `pip install --dry-run` deps | openpyxl 3.1.5, pillow 12.3.0, reportlab 5.0.1, ruff 0.16.6 | Todas resuelven |
| `codex` | no instalado | Las voces externas de esta revisión corren solo con subagente Claude |

**Decisión de versión de Python (enmendada, ver E1):** se fija
`requires-python = ">=3.12"` **y se desarrolla sobre 3.12**, no sobre la 3.14.2
que hay instalada. Motivo: la fase 5 empaqueta con PyInstaller e Inno Setup, y
3.12 es la versión con más kilometraje en esa cadena. Nada de la fase 1 necesita
3.14, y desarrollar sobre el piso que se promete evita descubrir en la fase 5 que
un hook de PyInstaller no soporta 3.14. Primera tarea de 1.1: instalar Python
3.12 y crear el entorno virtual con él.

**Decisión de pines de dependencia `[+]`:** `reportlab` acaba de saltar a 5.0.x,
un cambio de versión mayor cuya API de posicionamiento se usa intensivamente en
la fase 3. Se pinea `reportlab>=4.2,<6` y se deja anotado que la fase 3 debe
verificar el comportamiento real de la 5.x antes de escribir el motor de render.
El resto se pinea por rango menor.

---

## 2. Enfoque elegido

### Alternativas consideradas

**APPROACH A — Vertical mínimo primero**
Levantar el arranque de la app + una tabla + una vista, y luego ir engordando.
Se ve algo funcionando en la primera hora, pero el esquema completo y las
migraciones llegan tarde y hay que retocar la vista tres veces.

**APPROACH B — Capas de abajo hacia arriba (elegido)**
Orden: entorno → rutas y conexión → migraciones → esquema completo → repositorios
→ i18n → utilidades → servicios → UI. Cada capa se cierra con sus pruebas antes
de subir a la siguiente. La UI se escribe última, contra repositorios ya probados.

**APPROACH C — UI primero con datos falsos**
Maquetar las tres vistas con datos en memoria y enchufar la base después. Rápido
para ver pantallas, pero obliga a reescribir la capa de datos de la UI y contradice
el objetivo declarado de la fase.

**Elegido: B.** El riesgo declarado de la fase es exactamente que los cimientos
queden mal. B es el único orden en que cada capa se prueba sin interfaz, que es
además el principio rector del documento técnico ("el dominio no importa PySide6
ni sqlite3"). A y C invierten ese orden.

### Secuencia de trabajo

`[!]` **Enmienda G20 — el orden de construcción NO es el orden de los números de
sección.** Las secciones están numeradas siguiendo el contrato de la fase, que
agrupa por tema. El contrato no es un orden de ejecución, y seguirlo al pie
violaría el propio principio de "de abajo hacia arriba" que este plan eligió:
§1.2 (conexión, migraciones) levanta `ErrorPersistencia` y escribe en el log, y
tanto `utilidades/errores.py` (§1.5.1) como `utilidades/log.py` (§1.5.2) e `i18n`
(§1.4) están numerados **después**. Lo mismo con §1.8: las fixtures hacen falta
para escribir las pruebas de §1.2, y la tabla de verbos y la plantilla de mapeo
tienen que existir antes de escribir el primer repositorio, que es —dice el propio
plan— el que decide cómo se escriben los otros siete.

**Este es el orden de ejecución. Manda sobre la numeración:**

```
  PASO  QUÉ SE CONSTRUYE                                    SECCIÓN
  ────  ─────────────────────────────────────────────────   ───────
   0    Esqueleto que camina (desechable)                    §1.0
   1    Repositorio, entorno, pyproject, ruff, .gitignore    §1.1
   2    Convenciones escritas ANTES de codificar             §1.8 (todo)
        docs/convenciones-codigo.md + CLAUDE.md
   3    utilidades/: errores, log, fechas                    §1.5.1-1.5.3
   4    i18n + preferencias                                  §1.4
   5    config/rutas + conexión + migraciones + 001          §1.2
        tests/conftest.py y factorias.py a la vez            §1.8.8
   6    repositorios (organizacion, evento, auditoria)       §1.3
   7    dominio/: modelos, estados, dinero                   §1.3.4, §1.8.6
   8    utilidades/imagenes                                  §1.5.4
   9    servicios/                                           §1.6
  10    interfaz                                             §1.7
  11    pruebas restantes, guion de aceptación, cierre       §1.9
```

```
  1.0 ──▶ 1.1 ──▶ 1.8 convenciones ──▶ 1.5 utilidades ──▶ 1.4 i18n
                                                             │
                        ┌────────────────────────────────────┘
                        ▼
  1.2 persistencia + conftest ──▶ 1.3 repos ──▶ dominio ──▶ 1.6 servicios
                                                                │
                        ┌───────────────────────────────────────┘
                        ▼
  1.7 interfaz ──▶ 1.9 pruebas y cierre ──▶ tag v0.1.0
```

---

## 3. Tareas

### 1.0 `[+]` Esqueleto que camina (primera hora)

`[!]` **Enmienda E8.** El orden de abajo hacia arriba deja todo lo ambiental para
el final: el propio riesgo "PySide6 sobre este Python" se mitigaba con una prueba
de humo en el paso 1.8, o sea, después de escribir treinta módulos. Se antepone un
esqueleto mínimo, desechable en su forma pero no en su información:

- Una ventana PySide6 vacía que abre y cierra.
- Un `sqlite3.connect` a un archivo temporal, un `CREATE TABLE`, un `INSERT`, un
  `SELECT`, y el resultado pintado en un `QLabel`.
- Ejecutado también con `QT_QPA_PLATFORM=offscreen` para confirmar que las
  pruebas van a poder correr sin pantalla.

Objetivo: en menos de una hora saber que Python, PySide6 y SQLite conviven en esta
máquina. Si algo de eso falla, falla ahora y no al final. El código se tira; lo
que queda es la certeza.

No confundir con la tarea 1.7: esto no es la ventana principal, es un cable
pelado para comprobar que hay corriente.

---

### 1.1 Preparación del entorno

**Del contrato:** repositorio Git con `main` y `dev`; estructura de carpetas
según §2.2 del documento técnico; `pyproject.toml` con PySide6, reportlab,
pillow, openpyxl, pytest, ruff; entorno virtual y `.gitignore`; ruff con línea de
100; `README.md`.

**Detalle de ejecución:**

1. `git init`, primer commit en `main`, rama `dev` creada desde `main`.
   `main` queda estable; se trabaja en `feature/fase-1-*` y se integra a `dev`.
2. Instalar **Python 3.12** (enmienda E1) y crear el entorno virtual en `.venv/` con él.
   El 3.14.2 que hay instalado no se usa para este proyecto.
3. Estructura de carpetas exacta de §2.2, con `__init__.py` en cada paquete y un
   `.gitkeep` en `migraciones/`, `recursos/`, `docs/`.
4. `pyproject.toml`:
   - `[project]`: nombre `bingo`, versión `0.1.0`, `requires-python = ">=3.12"`.
   - dependencias: PySide6, reportlab, pillow, openpyxl. (`qrcode[pil]` entra en
     la fase 3, no ahora.)
   - `[project.optional-dependencies] dev`: pytest, pytest-qt, ruff.
   - `[build-system]`: setuptools con layout `src/`.
   - `[tool.ruff]`: `line-length = 100`, `target-version = "py312"`.
   - `[tool.ruff.lint]`: `select = ["E","F","I","UP","B","SIM"]`. `[+]` El
     contrato pide solo la línea de 100; añadir `I` (orden de imports) y `B`
     (bugbear) cuesta cero y evita ruido de revisión más adelante.
   - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`.
5. `.gitignore`: `.venv/`, `__pycache__/`, `*.py[cod]`, `*.db`, `*.db-wal`,
   `*.db-shm`, `dist/`, `build/`, `*.spec`, `medios/`, `.pytest_cache/`,
   `.ruff_cache/`, `*.log`.
   `[+]` Se añaden `*.db-wal` y `*.db-shm`: WAL genera esos dos archivos junto al
   `.db` y el contrato solo menciona `.db`.
6. `README.md`: qué es, requisitos, instalación (`python -m venv .venv`,
   `pip install -e ".[dev]"`), ejecución (`python -m bingo`), pruebas (`pytest`),
   lint (`ruff check .`), y dónde guarda sus datos la aplicación.
7. `[+]` `CHANGELOG.md` con la entrada `0.1.0`. Cuesta dos minutos y la fase 5
   pide versionado semántico visible en Ajustes.

**Archivos:** `.gitignore`, `pyproject.toml`, `README.md`, `CHANGELOG.md`,
`TODOS.md`, `CLAUDE.md` (ya creado), árbol de `src/bingo/` y `tests/`.

**Verificación:** `ruff check .` sin errores; `pip install -e ".[dev]"` termina;
`python -c "import bingo"` funciona.

---

### 1.2 Capa de persistencia

**Del contrato:** `conexion.py` con `journal_mode=WAL`, `foreign_keys=ON`,
`synchronous=FULL` y `row_factory` por nombre; resolución de rutas creando
`%LOCALAPPDATA%\Bingo\` con `datos`, `logs`, `respaldos`, `medios`; sistema de
migraciones con tabla `schema_version`, lector de `NNN_*.sql` ordenados,
aplicación transaccional y registro de versión; migración `001_inicial.sql` con
el esquema completo de §3.1.

#### 1.2.1 `config/rutas.py`

Un único módulo responsable de decir dónde está cada cosa. Nadie más construye
rutas a mano.

```python
def raiz_datos() -> Path          # %LOCALAPPDATA%\Bingo  (override por env BINGO_HOME)
def dir_datos() -> Path           # raiz/datos
def dir_logs() -> Path            # raiz/logs
def dir_respaldos() -> Path       # raiz/respaldos
def dir_medios() -> Path          # raiz/medios
def dir_medios_organizacion(organizacion_id: int) -> Path
def ruta_bd() -> Path             # raiz/datos/bingo.db
def ruta_preferencias() -> Path   # raiz/preferencias.json
def asegurar_estructura() -> None # crea todo lo anterior si falta
```

- `[+] BINGO_HOME`: variable de entorno que sobreescribe la raíz. Sin esto las
  pruebas escriben en el `%LOCALAPPDATA%` real del desarrollador. Es el requisito
  que hace testeable toda la capa de persistencia.
- `[+] dir_medios_organizacion(id)` recibe **id, no nombre**. El contrato dice
  `medios/<organizacion>/`; usar el nombre rompe con barras, dos puntos o acentos,
  y deja carpetas huérfanas al renombrar. Se usa `medios/<id>/` y el nombre queda
  solo en la base.
- Fuera de Windows se cae a `~/.local/share/Bingo`. El código es multiplataforma
  aunque solo se pruebe en Windows.

#### 1.2.2 `[+]` Guardia de ubicación de la base

El documento técnico marca como **regla crítica** que el `.db` no viva en carpeta
sincronizada ni unidad de red, y llama a eso "la causa más frecuente de corrupción
en SQLite". El contrato de la fase no incluye ninguna comprobación. Se añade:

`config/rutas.py::advertencia_ubicacion_bd() -> str | None`

Devuelve una clave de aviso si la ruta resuelta contiene un segmento `OneDrive`,
`Dropbox`, `Google Drive` o `iCloudDrive`, o si es una ruta UNC (`\\servidor\...`).
La ventana principal muestra el aviso una vez al arrancar, con opción de no volver
a mostrarlo. No bloquea: avisa.
`[!]` **Enmienda E3.** El borrador llamaba a `GetDriveTypeW` por `ctypes` para
detectar unidades de red mapeadas. Se descarta: es código Win32 específico, sin
prueba posible fuera de Windows, para cubrir un caso (letra de unidad mapeada a un
recurso de red) que la comprobación de ruta UNC ya cubre en su forma común. Cinco
líneas de comparación de cadenas hacen el 95% del trabajo.

#### 1.2.3 `persistencia/conexion.py`

```python
Sincronizacion = Literal["FULL", "NORMAL", "OFF"]

def abrir_conexion(ruta=None, *, synchronous: Sincronizacion = "FULL") -> sqlite3.Connection
def cerrar_conexion(con) -> None

@contextmanager
def transaccion(con) -> Iterator[sqlite3.Connection]
```

- `row_factory = sqlite3.Row` (acceso por nombre de columna, como pide el contrato).
- PRAGMAs aplicados **fuera de cualquier transacción**, en este orden:
  `busy_timeout` → `journal_mode=WAL` → `foreign_keys=ON` → `synchronous`.
  `[!]` **Enmienda G2 — se corrige el orden y, sobre todo, la justificación.**
  El borrador decía que el orden entre `journal_mode`, `foreign_keys` y
  `synchronous` "no es cosmético". Entre esos tres **sí lo es**: ninguno depende
  de otro. Lo que no es cosmético es (a) estar fuera de transacción y (b) que
  `busy_timeout` se fije **antes** que `journal_mode=WAL`, porque pasar a WAL
  toma un bloqueo exclusivo y devuelve `SQLITE_BUSY` si otra conexión tiene la
  base abierta; sin `busy_timeout` ya en vigor, el cambio falla en el acto en vez
  de reintentar. El borrador listaba `busy_timeout` como una viñeta suelta
  *después* de la lista ordenada: la única restricción de orden real era
  justamente la que tenía mal.
  `[!]` Y una asimetría que conviene tener escrita, porque solo una de las dos es
  detectable: dentro de una transacción abierta, `PRAGMA foreign_keys` es un
  **no-op silencioso** (verificado: relee `0`), mientras que `journal_mode`
  **lanza** (`cannot change out of wal mode from within a transaction`).
  `[!]` `journal_mode=WAL` **se persiste en la cabecera del archivo** y sobrevive
  a las conexiones; `foreign_keys`, `busy_timeout` y `synchronous` son por
  conexión. La fase 5 lo necesita para el camino de respaldo y restauración.
- `synchronous` **por defecto `FULL`**, exactamente como pide el contrato. El
  parámetro existe para que la fase 2 pueda pasar `NORMAL` durante la carga
  masiva de cartones, no para cambiar el comportamiento por defecto.
  `[!]` **Enmienda E2.** El borrador de este plan invertía el valor por defecto
  con la justificación de que FULL haría de cuello de botella al insertar 10.000
  cartones. La justificación era falsa y nadie la había medido: la fase 2 inserta
  en bloques de 500 por transacción, o sea 20 commits y 20 fsync para el lote
  entero. El contrato manda FULL; FULL queda de serie. Si en la fase 2 se mide un
  problema real, ahí está el parámetro, y ahí estará la medición que lo respalde.
- `isolation_level = None` (autocommit) más `transaccion()` explícita con
  `BEGIN IMMEDIATE`. Evita el manejo implícito de transacciones de `sqlite3`,
  fuente clásica de confusión sobre cuándo hay commit.
- `[+] PRAGMA busy_timeout = 5000`: sin esto, dos accesos concurrentes
  (aplicación más respaldo en línea de la fase 5) dan `database is locked` al instante.
- `[+]` Al abrir, se releen **dos** PRAGMA y se verifican:
  `foreign_keys` tiene que ser `1` y `journal_mode` tiene que ser `wal` (salvo con
  `":memory:"`, donde WAL no aplica y la comprobación se salta). Si alguno no
  cuadra, `ErrorPersistencia`.
  `[!]` **Enmienda G3b.** El borrador solo verificaba `foreign_keys`, y el §1.8.1
  hablaba de "saltarse la comprobación de WAL" para `":memory:"` — una
  comprobación que en realidad no estaba especificada en ningún sitio. Importa:
  `journal_mode=WAL` puede quedarse en `delete` en silencio si la base está en un
  recurso de red, que es exactamente el escenario para el que existe el §1.2.2.
- `[!]` **Enmienda G3c — `synchronous` es un conjunto cerrado**, no una cadena
  libre que se interpola en `PRAGMA synchronous = {}`. Se valida la pertenencia
  antes de interpolar. El plan usa los tres valores en sitios distintos: `FULL`
  por defecto, `NORMAL` en el trabajador de la fase 2, `OFF` en las pruebas.

#### 1.2.4 `persistencia/migraciones.py`

```python
def version_actual(con) -> int
def migraciones_pendientes(version: int) -> list[Migracion]
def aplicar_migraciones(con) -> list[int]   # devuelve versiones aplicadas
```

- La tabla de control se crea aparte, antes de leer nada:

  ```sql
  CREATE TABLE IF NOT EXISTS schema_version (
      version     INTEGER PRIMARY KEY,
      aplicada_en TEXT NOT NULL,
      archivo     TEXT NOT NULL
  );
  ```

  `[!]` `schema_version` **no está** en el esquema de §3.1 del documento técnico.
  No puede vivir dentro de `001_inicial.sql`, porque el runner necesita leerla
  antes de aplicar la 001. Va en código, con `IF NOT EXISTS`.
- Los archivos se descubren con `importlib.resources` sobre el paquete
  `bingo.persistencia.migraciones`, **no** con rutas relativas a `__file__`.
  `[!]` **Enmienda G14 — se conserva `importlib.resources` pero se corrige la
  justificación, que era falsa en las dos direcciones.** En PyInstaller **onedir**
  (el modo que fija el §12 del documento técnico) `__file__` *sí* resuelve bien:
  los módulos quedan como archivos reales bajo `_internal`. Y al revés,
  `importlib.resources` no puede encontrar un archivo que nunca se empaquetó:
  PyInstaller no recoge archivos de datos por su cuenta. La mitigación real de ese
  riesgo es una entrada `datas=` en el `.spec`, y eso es trabajo de la fase 5.
  `importlib.resources` se queda porque es la API correcta igualmente (y la única
  que funciona también en modo `onefile`), no porque resuelva el empaquetado.
  **Lo que sí debe la fase 1** es que los `.sql` viajen en una instalación normal:
  `[tool.setuptools.package-data]` en `pyproject.toml`. Sin eso, un
  `pip install .` (sin `-e`) produce una aplicación con cero migraciones. Y se
  zanja una ambigüedad del §1.1: `persistencia/migraciones/` **lleva
  `__init__.py`** (no un `.gitkeep`), porque `importlib.resources.files()` se
  comporta distinto con un paquete de espacio de nombres.
- Nombre de archivo válido: tres dígitos, guion bajo, nombre en minúsculas, `.sql`.
  Un archivo que no calce produce error explícito, no se ignora en silencio.
- Números duplicados o huecos (001, 003 sin 002) producen `ErrorMigracion` con
  detalle. Aplicar migraciones salteadas en silencio es peor que fallar.
- `[!]` **Enmienda G1 (crítica) — cómo se ejecuta el archivo `.sql`, porque la
  forma obvia no funciona.** El borrador decía "`BEGIN`, SQL del archivo,
  `INSERT INTO schema_version`, `COMMIT`" sin decir *con qué*. La implementación
  natural —`con.execute("BEGIN IMMEDIATE")` y después `con.executescript(sql)`—
  **no puede funcionar**: `executescript()` emite un `COMMIT` implícito antes de
  correr el script. Verificado en esta máquina:

  ```
  in_transaction antes de executescript:  True
  in_transaction después de executescript: False
  COMMIT -> ERROR: cannot commit - no transaction is active
  ```

  Y lo peor no es el error del camino feliz. Con un `.sql` que falla a mitad, el
  resultado medido es:

  ```
  ROLLBACK -> cannot rollback - no transaction is active
  ¿sobrevivió el esquema a medias?  tabla 'ok' presente: True   ← desastre
  ```

  Esquema a medio construir, sin fila en `schema_version`, que es el peor estado
  posible y justo el que `test_migraciones.py` afirmaba cubrir.

  **Mecanismo obligatorio:** el `BEGIN` y el `COMMIT` van **dentro** del script
  que se pasa a `executescript`:

  ```python
  con.executescript(
      "BEGIN IMMEDIATE;\n" + sql + "\nINSERT INTO schema_version(...) VALUES(...);\nCOMMIT;"
  )
  ```

  con `con.rollback()` en el `except`. Verificado: con el `BEGIN` dentro del
  script, un fallo a mitad revierte entero y la tabla no sobrevive.
  **Regla asociada, que va a `docs/convenciones-codigo.md`: los archivos de
  migración no contienen nunca su propio `BEGIN` ni `COMMIT`.**
- Si algo falla, se propaga con el número de migración y el nombre del archivo.
- Cada aplicación se registra en el log de aplicación.
- `[+]` Guardia de versión futura: si `version_actual` supera la migración más
  alta disponible, la base viene de una versión más nueva de la aplicación. Se
  aborta con mensaje claro en vez de arrancar contra un esquema desconocido.
- `[!]` **Enmienda G34 — base migrada a medias.** Aunque G1 cierra la causa
  principal, un corte de luz en el momento justo puede dejar tablas creadas y
  `schema_version` vacía. Al arrancar, `version_actual` devuelve 0, el runner
  reaplica la 001 y `CREATE TABLE organizacion` falla con "table already exists",
  saliendo con código 4 y sin salida posible para el usuario. El borrador cubría
  "versión futura" y "hueco en la numeración" pero no este. **Detección:**
  `version_actual == 0` y `sqlite_master` no vacío → `ErrorMigracion` con clave
  propia y mensaje accionable ("la base quedó a medias; ciérrala y usa
  `--reiniciar-datos`, o restaura un respaldo"). Va también a `docs/runbook.md`.

#### 1.2.5 `migraciones/001_inicial.sql`

El esquema **completo** de §3.1 del documento técnico, tal cual: `organizacion`,
`evento`, `lote`, `carton` (con sus dos `UNIQUE` y sus dos índices), `comprador`,
`patron`, `ronda`, `extraccion`, `ganador`, `auditoria`. Se crean todas desde ya,
aunque rondas y extracciones no se usen hasta las fases 4 y 5 — es lo que pide
explícitamente el contrato.

Ajustes sobre el SQL literal del documento, todos justificados:

- **Sin líneas `PRAGMA` dentro del archivo.** Los PRAGMA que encabezan §3.1 son
  de conexión, no de esquema; dentro de una migración transaccional no aplican y
  `journal_mode` directamente falla. Viven en `conexion.py`.
- `[+] CHECK` en los campos de estado, hoy `TEXT` libre:
  - `evento.estado` en (`borrador`, `preparado`, `en_curso`, `finalizado`)
  - `carton.estado` en (`generado`, `impreso`, `entregado`, `vendido`, `anulado`)
  - `ronda.estado` en (`pendiente`, `en_curso`, `pausada`, `cerrada`)
  - `ronda.premio_tipo` en (`efectivo`, `bien`), permitiendo NULL

  El documento ya enumera esos valores como comentario; convertirlos en `CHECK`
  hace que la base rechace un typo en vez de dejar un evento en estado `borrado`
  que ninguna consulta vuelve a encontrar.
- `[!]` **Enmienda E4a — se retira el `UNIQUE (organizacion_id, nombre)` en
  `evento`** que proponía el borrador. Una organización repite el mismo nombre de
  evento cada año ("Bingo Solidario") con toda naturalidad. El duplicado accidental
  se ataca donde corresponde: `repo_organizacion.existe_nombre` ya planificado,
  como aviso en el formulario, no como restricción de la base.
  `[!]` **Enmienda G5 — se corrige el argumento, no la decisión.** El borrador
  añadía que "en SQLite no se puede quitar un `UNIQUE` sin reconstruir la tabla".
  Eso vale solo para un `UNIQUE` declarado dentro de la tabla; declarado como
  `CREATE UNIQUE INDEX`, se quita con un `DROP INDEX` y ya está. La decisión se
  sostiene sola con el argumento de negocio; el técnico era falso y se habría
  citado en fases posteriores como si fuera una ley general.
- `[+]` **Enmienda E4b — dinero en enteros.** `evento.precio_tabla` pasa de
  `REAL` a `precio_tabla_centavos INTEGER`. El documento técnico especifica
  `REAL`, pero ese número alimenta la "recaudación teórica" del reporte de la
  fase 5 y el acta que se entrega a la organización como comprobante. Coma
  flotante en un documento con el nombre del operador encima es un error que se
  descubre sumando mil cartones. Cambiarlo ahora, con la 001 sin escribir, cuesta
  una línea; en la fase 5 cuesta una migración y un recálculo.
- `[+]` **Enmienda E4c — columnas de texto de la organización que faltan.** El
  alcance (§4.1 y §5.1) pide textos legales, eslogan, pie de página y condiciones
  en el perfil de la organización, y ninguna columna del §3.1 los recoge. Si la
  tesis del contrato es "el esquema completo desde ya", el esquema completo los
  incluye: `eslogan TEXT`, `pie_pagina TEXT`, `condiciones TEXT`,
  `aviso_legal TEXT` en `organizacion`.
- `[+]` **Enmienda E4d — `evento.fecha` con hora.** El alcance §5.1 imprime
  "fecha y hora del evento" en el cartón. Se guardan dos columnas separadas:
  `fecha TEXT` (`YYYY-MM-DD`, día del bingo) y `hora TEXT` (`HH:MM`, opcional).
  Separadas y no un instante, porque la hora del evento es hora local del lugar y
  no tiene sentido convertirla a UTC.
- `[+]` Índices `idx_evento_organizacion` sobre `evento(organizacion_id)` e
  `idx_auditoria_evento` sobre `auditoria(evento_id, momento)`. Son las dos
  consultas que esta fase deja escritas.
- Se respeta la ausencia de `ON DELETE CASCADE` (decisión explícita del §3.2).
- `[!]` **Enmienda G4 — se retira el `CHECK` sobre `ronda.estado`, revirtiendo una
  decisión tomada antes en esta misma revisión.** Al revisar las secciones 1 y 2
  de este plan se descartó el consejo de quitarlo, con el argumento de que los
  valores de `ronda.estado` estaban cerrados en el §6.1 del documento técnico. Ese
  argumento era falso, y la prueba está en el propio documento: la **decisión
  pendiente número 2 del §16** dice, con todas sus letras, que qué hacer si nadie
  reclama el premio *"impacta la máquina de estados de la sección 6.1"*. O sea que
  el documento declara abierta esa máquina de estados en el mismo texto que se
  citó para darla por cerrada.

  Y no es un `CHECK` cualquiera: **en SQLite un `CHECK` no se puede añadir ni
  quitar sin reconstruir la tabla entera** (el procedimiento de doce pasos). Sería
  congelar detrás de la restricción menos alterable que hay una máquina de estados
  que la fase 5 va a tener que ampliar.

  Se mantienen los `CHECK` de `evento.estado` y `carton.estado`, cuyos conjuntos de
  valores sí están cerrados, y el de `ronda.premio_tipo`, que el §4.5 del alcance
  fija en efectivo/bien. `ronda.estado` queda como `TEXT` libre y lo valida el
  dominio, como el resto de las transiciones.
- `[!]` **Enmienda E4e — política de edición de la 001.** El documento técnico
  §3.3 dice "nunca se edita una migración ya publicada", y a la vez §16 deja
  abierta la modelación de los patrones con variantes hasta la fase 4. Las dos
  cosas juntas congelarían hoy un `patron`/`ronda` que todavía no está diseñado.
  Se escribe la política explícita en el `README`: **la 001 es editable y la base
  de desarrollo es desechable hasta el primer evento con datos reales.** A partir
  de ese momento, y solo entonces, empieza a regir "nunca se edita una migración
  publicada" y todo cambio va en `002_*.sql`. Cuesta una frase y descongela la
  fase 4.
- Los `CHECK` sobre `ronda.estado` y `ronda.premio_tipo` **se mantienen**: sus
  valores están cerrados en el documento técnico (§6.1 fija la máquina de estados
  de la ronda; §4.5 del alcance fija efectivo/bien). Lo que está abierto en §16
  es cómo se modelan los patrones con varias máscaras, que afecta a `patron`, no
  a esas dos columnas.

#### 1.2.6 Carga de patrones del sistema — **NO en esta fase**

El documento técnico dice que los patrones del sistema "se cargan en la tabla
`patron` en la primera ejecución". Es tentador meterlo aquí porque la tabla ya
existe. Se deja para la fase 4, donde están el catálogo y el editor. Anotado en
`TODOS.md` para que no se pierda.

**Verificación de 1.2:** pruebas con `BINGO_HOME` sobre `tmp_path`; primera
apertura crea carpetas y aplica 001; segunda apertura no reaplica; `PRAGMA
foreign_keys` devuelve 1; `PRAGMA synchronous` devuelve 2 (FULL) por defecto;
insertar evento con `organizacion_id` inexistente falla; insertar `evento.estado`
inválido falla por CHECK.

---

### 1.3 Repositorios base

**Del contrato:** `repo_organizacion.py` (crear, obtener por id, listar,
actualizar, eliminar con validación de que no tenga eventos); `repo_evento.py`
(crear, obtener, listar por organización, actualizar estado, actualizar JSON de
plantilla y tema); patrón repositorio estricto, ningún SQL fuera de estos
archivos; `repo_auditoria.py` con `registrar(evento_id, accion, detalle)`.

#### 1.3.1 `persistencia/repo_organizacion.py`

```python
def crear(con, org: Organizacion) -> Organizacion     # [E26] devuelve la copia persistida
def obtener(con, organizacion_id: int) -> Organizacion | None
def listar(con) -> list[Organizacion]
def actualizar(con, org: Organizacion) -> None
def eliminar(con, organizacion_id: int) -> None      # ErrorIntegridad si tiene dependencias
def contar_eventos(con, organizacion_id: int) -> int
def existe_nombre(con, nombre: str, excluir_id: int | None = None) -> bool   # [+]
```

- `[!]` **Enmienda E26 — `crear` devuelve el modelo persistido**, no el `id`
  suelto. Con `-> int`, el objeto que pasó el llamante se queda con `id=None` y
  cada llamante tiene que acordarse de `org.id = repo.crear(con, org)`, en cada
  repositorio y en cada fase. Se devuelve
  `dataclasses.replace(org, id=cur.lastrowid)` y el `id` de entrada se ignora.
- `eliminar` comprueba eventos **y** `[+]` patrones propios de la organización
  (`patron.organizacion_id`), que también apuntan a ella. El contrato solo
  menciona eventos; el esquema tiene dos claves foráneas entrantes.
- `[+] existe_nombre` para avisar de duplicados en el formulario antes de guardar.

#### 1.3.2 `persistencia/repo_evento.py`

```python
def crear(con, evento: Evento) -> Evento        # [G7] el modelo persistido, como en E26
def obtener(con, evento_id: int) -> Evento | None
def listar_por_organizacion(con, organizacion_id: int) -> list[Evento]
def actualizar(con, evento: Evento) -> None
def actualizar_estado(con, evento_id: int, estado: str) -> None
def actualizar_plantilla(con, evento_id: int, plantilla_json: str) -> None
def actualizar_tema(con, evento_id: int, tema_json: str) -> None
```

- `actualizar_estado` **escribe y nada más**: recibe un estado ya validado.
  `[!]` **Enmienda E5.** El borrador ponía la validación de la máquina de estados
  dentro del repositorio. Eso es lógica de dominio dentro de la capa de SQL, o sea
  justo la erosión que vuelve decorativa la regla del repositorio que este mismo
  plan defiende. La tabla de transiciones vive en `dominio/estados.py`
  (`TRANSICIONES_EVENTO` y la función genérica
  `puede_transicionar(transiciones, actual, nuevo) -> bool` de §1.8.11 — el borrador
  la publicaba aquí sin el primer argumento y con él tres páginas más abajo) y la
  aplica `servicios/servicio_eventos.cambiar_estado`, que lanza
  `ErrorTransicionInvalida`. De paso, le da a ese servicio la razón de existir
  que le faltaba.
- `actualizar_plantilla` y `actualizar_tema` verifican que la cadena sea JSON
  válido antes de escribir (`json.loads` y descartar el resultado). Guardar JSON
  corrupto en la fase 1 se descubre en la fase 3, con el editor ya escrito.

#### 1.3.3 `persistencia/repo_auditoria.py`

```python
def registrar(con, evento_id: int | None, accion: str, detalle: str | None = None) -> None
def listar_por_evento(con, evento_id: int, limite: int = 200) -> list[RegistroAuditoria]  # [+]
```

- `evento_id` acepta `None` para acciones de nivel organización o aplicación
  (el esquema lo permite: la clave foránea es nullable).
- `momento` en ISO 8601 UTC vía `utilidades/fechas.py`.
- `[+] listar_por_evento` para que la auditoría sea consultable, no solo
  escribible. Sin lector, la tabla es un pozo.

#### 1.3.4 Modelos de dominio ligeros

`dominio/modelos.py` con dataclasses `Organizacion`, `Evento`,
`RegistroAuditoria`. Sin lógica de bingo (eso es la fase 2), solo estructura.
Los repositorios devuelven estos objetos, nunca `sqlite3.Row`.
`[!]` Esto es lo que hace real la regla "ninguna consulta SQL fuera de los
repositorios": si la UI recibe `Row`, termina indexando por nombre de columna y
el acoplamiento al esquema se filtra igual.

#### 1.3.5 `[+]` Prueba automatizada de la regla del repositorio

`tests/test_arquitectura.py`, en dos comprobaciones deliberadamente estrechas:

1. **Importaciones (con `ast`, cero falsos positivos).** `dominio/` no importa
   `PySide6` ni `sqlite3`; `ui/` no importa `sqlite3`; `servicios/` no importa
   `PySide6`. Esto es exactamente el principio rector del documento técnico y se
   verifica leyendo nodos `Import`/`ImportFrom`, no texto.
2. **SQL fuera de `persistencia/` (con `ast`, sobre literales de cadena).** Falla
   si un literal de cadena en cualquier módulo fuera de `persistencia/` empieza
   por `SELECT `, `INSERT INTO `, `UPDATE `, `DELETE FROM ` o `CREATE TABLE `.
   Anclado al inicio de la cadena, no búsqueda de palabra suelta.

`[!]` **Enmienda E6.** El borrador añadía una tercera comprobación: detectar
"literales de texto visible" en `ui/` fuera de `retraducir()`. Se descarta. Es una
máquina de falsos positivos (`setObjectName`, nombres de widget, cadenas de
formato, rutas de icono, una clave i18n que contenga la palabra "select") y un
linter casero que se pelea tres veces y a la cuarta se desactiva, llevándose por
delante las dos comprobaciones que sí valen. La regla "ninguna cadena visible en
el código" se sostiene con el patrón `retraducir()` (§1.4.3) y con revisión, no
con un detector heurístico.

**Verificación de 1.3:** CRUD completo de organización y evento contra base
temporal; borrar organización con evento asociado falla; transición de estado
inválida falla; `test_arquitectura.py` pasa.

---

### 1.4 Sistema de idiomas

**Del contrato:** `i18n/es.json` y `i18n/en.json`; función `t(clave,
**parametros)`; idioma persistido en preferencias locales; ninguna cadena visible
escrita directamente en el código.

#### 1.4.1 `i18n/__init__.py`

```python
def cargar(idioma: str) -> None
def idioma_actual() -> str
def idiomas_disponibles() -> list[str]
def t(clave: str, **parametros: object) -> str
```

- Archivos JSON planos con claves con punto (`org.titulo`,
  `evento.estado.borrador`), siguiendo el ejemplo del documento técnico
  (`"sorteo.bola_actual": "Bola {numero}"`).
- Sustitución con `str.format_map` sobre un diccionario tolerante.
  `[!]` `str.format` explota con `KeyError` si falta un parámetro y con
  `ValueError` si el texto traducido trae una llave suelta. En una aplicación que
  corre en vivo frente a cámara, un texto mal formado no puede tumbar la ventana:
  se registra el fallo y se devuelve la plantilla cruda.
- **Clave faltante:** devuelve `⟦clave⟧` (constante de módulo `MARCA_FALTANTE`,
  fijada para que `test_i18n.py` pueda afirmar sobre ella) y escribe una
  advertencia en el log. Nunca cadena vacía (invisible) ni excepción (tumba la
  vista).
  `[!]` **Enmienda G17 — se fija la marca y se resuelve una contradicción.** El
  borrador decía "entre marcas visibles" sin decir cuáles, y `test_i18n.py`
  afirmaba sobre ellas. Además el borrador se contradecía en un solo punto:
  "`str.format_map` sobre un diccionario **tolerante**" (que por construcción no
  lanza nunca) y a la vez "se registra el fallo y se devuelve la **plantilla
  cruda**" (que es lo que se hace cuando *sí* lanza). Son dos resultados distintos
  para `t("sorteo.bola_actual")` sin `numero`. **Política única:**
  1. Diccionario tolerante: un parámetro que falta se pinta `⟦numero⟧`, no revienta.
  2. `try/except ValueError` alrededor de `format_map` para plantillas mal formadas
     (una llave suelta en el JSON traducido): se registra y se devuelve la
     plantilla cruda.
- **Respaldo:** si la clave falta en `en.json` pero existe en `es.json`, se usa el
  español. El español es el idioma de referencia.

#### 1.4.2 `[+]` Prueba de paridad de claves

`tests/test_i18n.py`: el conjunto de claves de `es.json` y `en.json` es idéntico,
y los marcadores de cada clave coinciden entre idiomas. El criterio de aceptación
"cambiar el idioma cambia todos los textos visibles" es imposible de cumplir si un
archivo va por detrás del otro, e imposible de vigilar a ojo cuando haya 300
claves en la fase 5.

#### 1.4.3 `[+]` Retraducción en caliente

`[!]` **Hueco real del contrato.** Qt no vuelve a llamar a `t()` solo. Si las
vistas fijan sus textos en el constructor, cambiar el idioma en Ajustes no cambia
nada hasta reiniciar, y el criterio de aceptación dice explícitamente que cambiar
el idioma cambia *todos* los textos visibles.

Solución: cada vista y cada widget propio implementa `retraducir(self) -> None`,
que reasigna todos sus textos desde `t()`. Los textos se asignan **únicamente**
dentro de `retraducir()`, que el constructor invoca al final. Así hay un solo lugar
por vista donde viven las cadenas.

`[!]` **Enmienda E20 — el disparo es de aplicación, no de ventana.** El borrador
ponía el registro de vistas en `ventana_principal`. La fase 5 añade
`ventana_transmision`, que es una **segunda ventana de nivel superior**, más
diálogos, más widgets creados al vuelo (el tablero de 75 bolas, las filas de
ganadores, las celdas del cartón). Un registro que vive en la ventana principal no
alcanza a ninguno de ellos. Se pone la señal en un objeto de módulo dentro de
`bingo/i18n/`, al que cualquier widget se suscribe en su constructor. Mismo
código, funciona para la segunda ventana.

`[!]` **Enmienda G18 — cómo se da de baja, que el borrador no decía.** Es el
choque clásico de PySide6: una lista de módulo que guarda envoltorios Python de
widgets de C++ ya destruidos, y el siguiente `cargar("en")` lanza
`RuntimeError: Internal C++ object (QLabel) already deleted` — en mitad de un
evento en vivo, porque la fase 5 crea al vuelo las 75 celdas del tablero y las
filas de ganadores. **El registro es un `weakref.WeakSet` y además se conecta a la
señal `destroyed` de cada widget para darlo de baja explícitamente.** Se prueba:
crear una segunda ventana de nivel superior, destruirla, y volver a disparar el
cambio de idioma sin que reviente.

`[!]` **Enmienda E20b — `retraducir()` toca etiquetas, nunca valores.** Solo
textos estáticos: etiquetas, botones, encabezados, marcadores de posición y
títulos. Jamás el contenido de un campo. Cambiar de idioma con un formulario a
medio llenar no puede borrar lo escrito.

#### 1.4.4 `config/preferencias.py` `[+ no estaba nombrado]`

El contrato pide "ajuste de idioma persistido en preferencias locales" sin decir
dónde. Se define: `%LOCALAPPDATA%\Bingo\preferencias.json`, no la base de datos.

```python
def cargar() -> Preferencias
def guardar(prefs: Preferencias) -> None
```

`Preferencias`: `idioma` (por defecto `es`), `ultimo_evento_abierto_id` (`None`,
enmienda E14 — sustituye a `organizacion_activa_id`), `ultima_carpeta_exportacion`
(`None`), `avisos_descartados` (lista), y `[+ E23]` un bloque `ventana` con
`geometria` y `maximizada`, reservando `monitor_transmision` para la fase 5.
Reabrir siempre con el tamaño por defecto es una molestia menor hoy y una real la
noche del evento.

- Escritura atómica: archivo temporal más `os.replace`. Un corte de luz durante el
  guardado no puede dejar un JSON truncado que impida arrancar.
- JSON ilegible o corrupto: se usan los valores por defecto, se registra en el log
  y se renombra el archivo malo a `preferencias.json.corrupto`. La aplicación
  **nunca** deja de arrancar por un archivo de preferencias.
- **Fuera de la base de datos a propósito:** el idioma debe leerse antes de abrir
  la base (los mensajes de error de migración también van traducidos), y las
  preferencias deben sobrevivir a restaurar un respaldo hecho en otro equipo.

---

### 1.5 Utilidades transversales

**Del contrato:** módulo de manejo de errores con captura de excepciones no
controladas, diálogo legible y log de aplicación; módulo de fechas con ISO 8601
en texto; validación y normalización de imágenes con Pillow (convertir a PNG,
limitar dimensiones, rechazar corruptos).

#### 1.5.1 `utilidades/errores.py`

Jerarquía explícita, **sin captura genérica de `Exception`** en la capa de negocio:

```
ErrorBingo (base)
├── ErrorPersistencia
│   ├── ErrorMigracion
│   ├── ErrorIntegridad          (FK, UNIQUE, CHECK, NOT NULL)
│   ├── ErrorBaseBloqueada       (SQLITE_BUSY / SQLITE_LOCKED)
│   └── ErrorBaseCorrupta        [+ E25] (SQLITE_CORRUPT / SQLITE_NOTADB)
├── ErrorValidacion              (error del usuario: se pinta junto al campo)
│   └── ErrorImagen
├── ErrorDominio                 [+ E25] (regla de negocio, no entrada del usuario)
│   ├── ErrorTransicionInvalida
│   └── ErrorNoEncontrado
└── ErrorConfiguracion
```

`[!]` **Enmienda E25 — el constructor se fija aquí, no se deja a la
imaginación.** El borrador decía que los errores "llevan `clave_i18n` y
`parametros`" sin enseñar la firma. Cada fase, y cada sesión del asistente, habría
inventado una distinta.

```python
class ErrorBingo(Exception):
    def __init__(self, clave_i18n: str, *, detalle: str = "",
                 parametros: dict[str, object] | None = None) -> None:
        super().__init__(detalle or clave_i18n)
        self.clave_i18n = clave_i18n
        self.parametros = parametros or {}
        self.detalle = detalle      # técnico: va al log, nunca a la vista
```

Regla asociada: **la vista pinta `t(e.clave_i18n, **e.parametros)`; el log escribe
`e.detalle` y la traza; `str(e)` no se le enseña nunca a un usuario.**

`[!]` **Enmienda G19 — `parametros` es un diccionario explícito, no `**kwargs`.**
Con `**parametros`, un mensaje que necesitara un marcador llamado literalmente
`detalle` o `clave_i18n` sería irrepresentable. Y las subclases se escriben con
constructor completo, no solo con anotaciones de clase:

```python
class ErrorIntegridad(ErrorPersistencia):
    def __init__(self, clave_i18n, *, tipo, restriccion=None, detalle="", parametros=None):
        super().__init__(clave_i18n, detalle=detalle, parametros=parametros)
        self.tipo = tipo                # "unique" | "foreign_key" | "check" | "not_null"
        self.restriccion = restriccion  # "carton.evento_id, carton.firma"
```

El borrador dejaba a la imaginación cómo se poblaban esos dos campos, justo en el
sitio del que E25d dice que depende la fase 2.

`[!]` **Enmienda E25b — `ErrorValidacion` lleva `campo: str | None`.** El §1.7.3
exige que los errores de validación se pinten "junto al campo, no en un diálogo
modal". Sin saber *qué* campo, eso no se puede implementar.

`[!]` **Enmienda E25c — `ErrorTransicionInvalida` no es validación.** Una
transición imposible es un fallo de programa o una condición de carrera, no un
error de tecleo. Bajo la política de canales del §1.7.8 habría intentado pintarse
junto a un campo inexistente. Pasa a `ErrorDominio`, que va a la franja no modal.

`[!]` **Enmienda E25d — un único punto de traducción de `sqlite3`.** El borrador
tenía `ErrorIntegridad` y `ErrorBaseBloqueada` en el árbol **sin nadie que los
produjera**. Se define un contextmanager en `persistencia/errores_sqlite.py`,
aplicado en la frontera del repositorio:

```python
@contextmanager
def traducir_errores_sqlite() -> Iterator[None]: ...
```

Distingue por `sqlite3.Error.sqlite_errorname` y por el texto del mensaje, y
**conserva la información de qué restricción falló**:

```python
class ErrorIntegridad(ErrorPersistencia):
    tipo: Literal["unique", "foreign_key", "check", "not_null"]
    restriccion: str | None     # p. ej. "carton.evento_id, carton.firma"
```

`[!]` Esto no es pulcritud: **la fase 2 depende de ello**. Su contrato dice que al
insertar un cartón con firma repetida la inserción falla y se genera otro. Para
eso hay que distinguir `UNIQUE(evento_id, firma)` de `UNIQUE(evento_id, codigo)` y
de un fallo de clave foránea, y SQLite solo lo dice en el texto del mensaje. Si la
fase 1 envuelve a ciegas y tira el mensaje, la fase 2 se queda sin la información
que necesita y tiene que ir a rebuscar en `__cause__`. El original se conserva
siempre como `__cause__`.

`test_errores.py` cubre los cuatro tipos de restricción contra el esquema real de
la 001, más `SQLITE_BUSY` y `SQLITE_CORRUPT`.

`instalar_manejador_global()`:
- `sys.excepthook` para el hilo principal.
- `threading.excepthook` para hilos de `threading`.
- `[!]` **Enmienda G11 (alta) — `threading.excepthook` NO cubre `QThread`.**
  El borrador instalaba `threading.excepthook` justificándolo precisamente en que
  "las fases 2 y 3 usan `QThread`". Pero `threading.excepthook` solo se dispara
  para objetos `threading.Thread`; un `QThread` de PySide6 no lo es. Una excepción
  que se escapa de `QThread.run()` va a `sys.excepthook` y **se ejecuta en el hilo
  trabajador**. O sea que el manejador, tal como estaba especificado, intentaría
  construir un `QMessageBox` fuera del hilo de la interfaz: comportamiento
  indefinido en Qt y, en la práctica, un cierre en seco.
  **Regla:** el manejador comprueba
  `threading.current_thread() is threading.main_thread()`; si no lo es, **solo
  registra** y traslada el aviso al hilo de la interfaz por una señal en cola.
  `threading.excepthook` se conserva por completitud, sin la justificación falsa.
- `[!]` **Enmienda G12 — qué pasa después del diálogo.** PySide6 llama a
  `sys.excepthook` ante una excepción no capturada en un *slot* invocado desde el
  bucle de eventos de C++ y **a continuación el proceso muere**. El borrador
  describía el diálogo como si la aplicación siguiera viva, y el criterio de
  aceptación 7 lo daba por hecho. Se escribe la secuencia real: registrar →
  volcar a disco → mostrar el modal → **el proceso termina**. El texto del diálogo
  dice que se pierde el trabajo sin guardar, y el criterio 7 comprueba también la
  salida.
- `[!]` PySide6 invoca `sys.excepthook` ante una excepción no capturada dentro de
  un *slot* y a continuación **aborta el proceso**. El manejador debe escribir el
  log y mostrar el diálogo *antes* de retornar, y se prueba explícitamente que el
  registro llega a disco. Confiar en que "Qt lo maneja" es exactamente cómo se
  pierden los datos de la última bola en la fase 5.
- Diálogo: mensaje traducido, botón "copiar detalle", ruta del log.

#### 1.5.2 `utilidades/log.py`

- `logging` estándar con `RotatingFileHandler` sobre
  `%LOCALAPPDATA%\Bingo\logs\aplicacion.log` (5 MB por 3 archivos).
- Formato con hora ISO 8601 UTC, nivel, módulo y mensaje.
- Consola en `DEBUG` cuando `BINGO_DEBUG=1`; archivo siempre en `INFO`.
- Se escribe la versión de la aplicación, la versión de Python y la ruta de la
  base en la primera línea de cada arranque. Sin eso, un reporte de error a tres
  semanas vista no se puede reconstruir.
- `[!]` El log de aplicación de esta fase es distinto del log de partida de la
  fase 5 (uno por ronda, con `flush()` forzado tras cada bola). Se nombran
  distinto desde ya para que nadie los mezcle.

#### 1.5.3 `utilidades/fechas.py`

```python
def ahora_iso() -> str                    # UTC, con sufijo Z
def a_iso(dt: datetime) -> str
def desde_iso(texto: str) -> datetime
def formatear_para_ui(texto_iso: str, idioma: str) -> str
```

- Todo lo que va a la base es ISO 8601 en texto, como pide el contrato.
- **Todo se guarda en UTC**; la conversión a hora local ocurre solo al mostrar.
  `[+]` El contrato dice ISO 8601 pero no fija zona. Sin fijarla, un acta de
  sorteo de la fase 5 podría llevar horas locales sin desfase declarado, y el acta
  es un comprobante ante la organización.
- `evento.fecha` es una **fecha de calendario** (`YYYY-MM-DD`), no un instante: es
  el día del bingo, no un momento con zona. Se documenta la diferencia en el
  módulo para que la fase 5 no la reinterprete.

#### 1.5.4 `utilidades/imagenes.py`

```python
def validar_y_normalizar(origen: Path, destino: Path, *, lado_max: int = 1600) -> Path
def es_imagen_valida(ruta: Path) -> bool
```

- Abre con Pillow, fuerza `img.verify()`, **reabre** para operar (`verify()` deja
  el objeto inutilizable) y **llama a `img.load()`** dentro del mismo `try`.
  `[!]` **Enmienda G13 (alta) — `verify()` solo no basta.** `verify()` comprueba
  la estructura del contenedor, no descodifica los píxeles. Medido en esta máquina
  con un JPEG truncado por el final:

  ```
  jpeg -200 bytes   PASSED verify()   load() RECHAZADO: OSError
  jpeg -600 bytes   PASSED verify()   load() RECHAZADO: OSError
  jpeg -1000 bytes  PASSED verify()   load() RECHAZADO: OSError
  ```

  Con PNG truncado por la cola sí lo caza `verify()` (los CRC de chunk lo delatan),
  pero con JPEG pasa limpio las tres veces. O sea que `es_imagen_valida()` habría
  devuelto `True` para un archivo dañado, y el criterio de aceptación 9 habría
  pasado sin probar nada. `load()` (o el `convert()`/`resize()` que viene después)
  es lo que de verdad valida.
- Convierte a PNG preservando el canal alfa, redimensiona si excede `lado_max`
  manteniendo la proporción.
- Rechaza con `ErrorImagen` (traducido): archivo inexistente, formato no
  soportado, archivo corrupto, `[+]` archivo mayor a 20 MB, `[+]` imagen cuyo
  producto ancho por alto supere el límite de bomba de descompresión de Pillow
  `[!]` **Enmienda G13b — la bomba de descompresión, con precisión.** Pillow emite
  `DecompressionBombWarning` por encima de `MAX_IMAGE_PIXELS` y **lanza
  `DecompressionBombError` por encima del doble**; no es "solo un aviso" como decía
  el borrador. Convertir el aviso en error exige un `warnings.simplefilter` de
  proceso entero desde un módulo de utilidades, que es un efecto global
  desagradable. Se hace lo barato y comprobable: una comprobación explícita de
  `ancho * alto > LIMITE_PIXELES` antes de descodificar, más capturar
  `DecompressionBombError` por si acaso.
- `[+]` Escritura atómica al destino (temporal más `os.replace`) para no dejar un
  PNG a medias si la aplicación muere copiando.
- `[+]` Nombre de archivo destino determinista: `logo_principal.png` y
  `logo_secundario.png` dentro de `medios/<id_org>/`. Sin nombre fijo, cambiar el
  logo tres veces deja tres archivos y ninguna forma de saber cuál está en uso.

---

### 1.6 `[+]` Capa de servicios (mínima)

El documento técnico define tres capas y coloca los servicios entre la UI y los
repositorios. El contrato de la fase 1 salta de repositorios a interfaz. Si la
vista llama al repositorio directamente, la fase 2 tiene que reescribir esas
llamadas cuando aparezca `servicio_cartones`.

Se crean dos servicios finos, ahora, con lo justo:

`servicios/servicio_organizaciones.py`

```python
def crear_organizacion(con, datos: Organizacion, logo_origen: Path | None) -> Organizacion
def actualizar_organizacion(con, datos: Organizacion, logo_origen: Path | None) -> Organizacion
def eliminar_organizacion(con, organizacion_id: int) -> None
```

`[!]` **Enmienda G8 — el orden del borrador era imposible en el alta.** Decía
"archivo copiado **antes** del commit", pero la carpeta destino es
`medios/<id>/` y el `id` no existe hasta después del `INSERT`. El orden real, todo
dentro de la misma transacción:

```
  BEGIN IMMEDIATE
    ├─ validar
    ├─ normalizar la imagen a un temporal      (fuera de medios/)
    ├─ INSERT organizacion            ──▶ id = lastrowid
    ├─ copiar el temporal a medios/<id>/logo_principal.png
    ├─ UPDATE organizacion SET logo_path = ...
    ├─ registrar en auditoria
  COMMIT
    └─ si algo falla: ROLLBACK + borrar el PNG ya copiado
```

En la edición, donde el `id` ya existe, el orden es el mismo menos el `INSERT`.
`[!]` Este es el único punto de la fase donde el sistema de archivos y la base de
datos tienen que quedar consistentes entre sí. Merece un lugar con nombre **y una
prueba**: `test_servicio_organizaciones.py` (enmienda G14).

`servicios/servicio_eventos.py`

```python
def crear_evento(con, evento: Evento) -> Evento
def cambiar_estado(con, evento_id: int, nuevo: str) -> None   # valida la transición
```

`cambiar_estado` consulta el estado actual, pregunta a
`dominio.estados.puede_transicionar(actual, nuevo)`, lanza
`ErrorTransicionInvalida` si no procede, y solo entonces llama al repositorio y
registra en auditoría. Es la enmienda E5 aterrizada: la regla vive en el dominio,
el servicio la aplica, el repositorio escribe.

**Alcance deliberadamente mínimo.** No se inventan servicios para las fases 2 a 5.

---

### 1.7 Interfaz base

**Del contrato:** ventana principal con barra lateral o menú (Organizaciones,
Eventos, Ajustes); vista de organizaciones con lista, formulario de alta y
edición, carga de logo copiado a medios, selectores de color, campo de contacto;
vista de eventos con lista filtrada por organización y formulario de nombre,
fecha, lugar y precio; vista de ajustes con idioma, rutas y versión; `ui/tema.py`
mínimo aplicando los colores de la organización activa.
`[!]` Las dos últimas cláusulas del contrato — "organización activa" y "colores
aplicados a la interfaz" — son las que enmiendan **E14** (el eje pasa a ser el
evento) y **E15** (la marca no pinta el cromo del operador). E15 está sujeta al
desafío **DU-1**: la decide Gabriel en la puerta final, no el plan.

#### 1.7.1 `__main__.py` — secuencia de arranque

```
  inicio
    │
    ├─▶ construir QApplication            ◀── PRIMERO. Sin esto no hay diálogos.
    ├─▶ instalar manejador global de excepciones
    ├─▶ asegurar estructura de carpetas ──(sin permisos)──▶ diálogo + salida 2
    │       ◀── ANTES del log: RotatingFileHandler abre el archivo al construirse
    ├─▶ configurar log de aplicación
    ├─▶ cargar preferencias  ──(corrupto)──▶ valores por defecto + aviso en log
    ├─▶ cargar idioma
    ├─▶ comprobar ubicación de la BD ──(sincronizada/red)──▶ aviso no bloqueante
    ├─▶ tomar bloqueo de instancia única ──(ocupado)──▶ aviso + salida 0
    ├─▶ abrir conexión + PRAGMAs ──(BD corrupta)──▶ diálogo + salida 3
    ├─▶ aplicar migraciones pendientes ──(falla)──▶ diálogo + salida 4
    ├─▶ escribir línea de arranque en aplicacion.log
    ├─▶ construir ventana principal
    └─▶ app.exec()
```

`[!]` **Enmienda G9 — crear las carpetas antes de configurar el log.** El
borrador ordenaba: manejador global → **log** → preferencias → idioma → **crear
carpetas**. `RotatingFileHandler` abre `%LOCALAPPDATA%\Bingo\logs\aplicacion.log`
al construirse, y en un equipo limpio esa carpeta todavía no existe: la
configuración del log reventaba antes de que `asegurar_estructura()` llegara a
correr. Justo en el criterio de aceptación número 1. `asegurar_estructura()` no
necesita ni preferencias ni idioma para su propio camino de fallo (un diálogo de
permisos), así que sube. Alternativa equivalente: abrir el manejador con
`delay=True`.

`[!]` **Enmienda G10 — la segunda instancia no puede salir con código 0.** Cero
significa éxito para cualquiera que invoque el proceso, incluido el instalador de
la fase 5 y cualquier tarea programada futura. Sale con **5**.

`[!]` **Enmienda E16 — política de DPI antes de `QApplication`.** Los atributos
de alta resolución y la política de redondeo de escala se fijan **antes** de
construir `QApplication`; después ya no tienen efecto. La fase 5 saca una segunda
ventana a un monitor con otra densidad, así que esta es una decisión de la fase 1
que la fase 5 no puede tomar retroactivamente. Se fija
`QGuiApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)` en la primera
línea de `__main__.py`.

`[!]` **Enmienda E7a — `QApplication` va primero.** El borrador colocaba
`QApplication` implícitamente al final y a la vez enviaba los fallos de migración
y de base corrupta a "diálogo + salida". Un `QMessageBox` sin `QApplication` viva
aborta el proceso: el diálogo de error habría sido, precisamente, un crash sin
mensaje. Se construye `QApplication` en la primera línea y todo lo de abajo puede
usar diálogos.

`[!]` **Enmienda E7b — el arranque NO se registra en `auditoria`.** El borrador
insertaba una fila de auditoría en cada arranque. `auditoria` es el rastro que
alimenta el acta del sorteo, un comprobante que se entrega a la organización;
mezclarlo con ruido de ciclo de vida de la aplicación degrada el registro que más
importa. El arranque (versión de la app, versión de Python, ruta de la base,
versión de esquema) va a `aplicacion.log`, que es donde se busca cuando algo
falla. `auditoria` guarda hechos del negocio: alta de organización, alta de
evento, cambio de estado.

Cada flecha de fallo tiene destino explícito y código de salida distinto. Los
únicos caminos que terminan el proceso lo hacen con diálogo traducido y línea de
log, nunca con un traceback en una consola que en producción no existe.

`[+]` **Instancia única con `QLockFile`** (enmienda E13). Qt ya lo trae y, además
de bloquear, **detecta bloqueos rancios**: guarda el PID y el nombre del equipo, y
`tryLock()` reclama el bloqueo solo si el proceso dueño ya no existe. Ese es el
escenario que de verdad importa aquí: un cierre brusco a las seis de la tarde que
dejaría la aplicación sin arrancar a las siete, el día del evento. Es
multiplataforma, ya está pagado dentro de la dependencia de PySide6, y son cinco
líneas en lugar de veinte con ramas por sistema operativo. Aun así se añade
`--forzar-instancia` como salida de emergencia, documentado en el README, y la
función auxiliar recibe un `forzar: bool` explícito para que las pruebas no tengan
que parchear `sys.argv`.

#### 1.7.2 `ui/ventana_principal.py` — dos niveles de navegación

`[!]` **Enmienda E14 — la cáscara tiene dos niveles, no uno, y el eje es el
evento, no la organización.**

El borrador montaba un `QStackedWidget` plano con tres entradas hermanas y un
selector global de "organización activa" que además retematizaba la aplicación
entera. Las dos cosas están mal, y las fases siguientes lo demuestran:

- La fase 2 pide literalmente "**vista dentro del evento**: botón de generar lote".
- La fase 3 edita `evento.plantilla_json`.
- La fase 4 carga compradores, rondas y premios del evento, y `evento.tema_json`.
- La fase 5 abre dos ventanas contra un evento en curso.

**Todo lo que viene está delimitado por evento.** La organización es derivable
(`evento.organizacion_id`) y no delimita nada. Un modo global de organización no
aporta información que el evento no lleve ya, y en la fase 5 crea dos autoridades
sueltas en la misma sala: "organización activa" (que repinta la interfaz desde un
combo, en cualquier momento) y "evento en curso" (que manda en el sorteo). Nada
las ata. Cambiar de organización a mitad de una ronda, en vivo y con la cámara
encendida, repinta la interfaz del operador.

**Estructura, entonces:**

- **Nivel global:** Eventos (inicio), Organizaciones, Ajustes.
- **Espacio de trabajo del evento:** se entra abriendo un evento desde el inicio.
  Tiene cabecera propia (logo de la organización, nombre del evento, fecha, chip
  de estado, botón "cerrar evento") y su propio riel de secciones. En la fase 1
  ese riel tiene **una** entrada, *Datos del evento*. Las fases 2 a 5 le cuelgan
  *Cartones*, *Plantilla*, *Compradores*, *Rondas* y *Transmisión* sin tocar la
  cáscara.

`Preferencias.organizacion_activa_id` desaparece y en su lugar queda
`ultimo_evento_abierto_id`, que además es exactamente lo que la fase 5 va a
necesitar para la reanudación del §6.3.

El coste hoy es una clase de widget y cerca de una hora. El coste en la fase 3 es
reescribir la ventana principal, el registro de `retraducir()` y el contrato de
carga de datos de todas las vistas.

```
  NIVEL GLOBAL
  ┌───────────────────────────────────────────────────────────┐
  │ BINGO                                           [_][□][X] │
  ├────────────────┬──────────────────────────────────────────┤
  │ ▸ Eventos      │  [buscar…]        [+ Nuevo evento]       │
  │ ▸ Organizaciones  ┌────────────────────────────────────┐  │
  │ ▸ Ajustes      │  │ (logo) Bingo Solidario 2026        │  │
  │                │  │        Fundación X · 12 dic · ▪borrador│
  │                │  └────────────────────────────────────┘  │
  ├────────────────┴──────────────────────────────────────────┤
  │ Sin evento abierto · sin cambios sin guardar              │
  └───────────────────────────────────────────────────────────┘

  ESPACIO DE TRABAJO DEL EVENTO  (al abrir una fila)
  ┌───────────────────────────────────────────────────────────┐
  │ ◀ Eventos │ (logo) Bingo Solidario 2026 · 12 dic ▪borrador │
  │           │ ▔▔▔▔ franja de 4 px en el color de la marca    │
  ├────────────────┬──────────────────────────────────────────┤
  │ ▸ Datos        │                                          │
  │   Cartones   ⏳│         (sección activa)                 │
  │   Plantilla  ⏳│                                          │
  │   Compradores⏳│   ⏳ = "llega en una versión próxima"     │
  │   Rondas     ⏳│                                          │
  ├────────────────┴──────────────────────────────────────────┤
  │ Bingo Solidario 2026 · sin cambios sin guardar            │
  └───────────────────────────────────────────────────────────┘
```

`[!]` **Enmienda E14b — la barra de estado deja de ser telemetría.** El borrador
ponía ahí ruta de la base, versión y esquema: información que no cambia nunca y
que ya vive en Ajustes, ocupando el sitio permanente más visible de la ventana.
Pasa a llevar estado que sí cambia: qué evento está abierto, si hay cambios sin
guardar y (desde la fase 5) cuánto hace del último respaldo, que es justo el aviso
que pide el §11 del documento técnico.

- Registro de vistas para `retraducir()` **a nivel de aplicación, no de ventana**
  (ver enmienda E20 en §1.4.3).

#### 1.7.3 `ui/vistas/vista_organizaciones.py`

`[!]` **Enmienda E17 — rejilla de tarjetas, no lista-detalle.** Una organización
tiene entre cinco y quince filas en toda la vida de la aplicación, y su razón de
ser entera es la identidad visual. Una lista de etiquetas de texto es la forma
equivocada. Se pinta una **rejilla de tarjetas**: logo, nombre, tres muestras de
color, número de eventos. Se reconoce a un cliente por su marca.

- Formulario en un panel lateral o diálogo al crear/editar.
- **Campos obligatorios marcados como tales.** Solo `nombre` lo es. El borrador
  presentaba ocho campos sin distinguir; los tres selectores de color, la
  tipografía y el logo secundario se agrupan en una sección plegable
  *"Identidad visual"* que se puede rellenar después. Una organización con nombre
  y contacto es una organización válida.
- `[!]` **`tipografia` es un combo cerrado**, no texto libre. El §16.3 del
  documento técnico deja las tipografías personalizadas como decisión abierta, con
  implicaciones de licencia y de registro doble (Qt y ReportLab). Un campo de texto
  libre en la fase 1 recolecta basura que la fase 3 tiene que interpretar.
  `[!]` **Enmienda G24 — pero `recursos/` está vacía.** El borrador decía "el combo
  ofrece las fuentes empaquetadas en `recursos/`" y a la vez creaba `recursos/` sin
  contenido y sin ninguna tarea que eligiera, licenciara o empaquetara una fuente:
  el combo habría salido vacío, o sea peor que el campo de texto libre que
  sustituye. Se cierra así: **la fase 1 empaqueta dos familias de licencia abierta**
  en `recursos/fuentes/` (una con serifa y una sin), y el combo ofrece esas dos más
  "(por defecto)". La decisión abierta del §16.3 —permitir que la organización
  cargue su propia fuente— va a `TODOS.md` para la fase 3.
- Selector de color con `QColorDialog` y muestra del color aplicado.
- Carga de logo: `QFileDialog`, `validar_y_normalizar`, vista previa. La copia
  definitiva a `medios/<id>/` la hace el servicio al guardar; antes de eso el
  archivo normalizado vive en un temporal.
  `[!]` Si se copiara a `medios/<id>/` al seleccionar, cancelar el formulario
  dejaría basura y, en un alta, todavía no existe el `id`.

**Cobertura de estados (enmienda E17b — el borrador cubría cuatro de siete):**

| Estado | Qué se ve |
|---|---|
| VACÍO | "Aún no hay organizaciones" con botón de alta. Ya estaba |
| VACÍO TRAS FILTRO | Mensaje distinto: "Ninguna organización coincide con *X*" con botón de limpiar filtro |
| ERROR | **Faltaba.** Franja de error no modal en la cabecera de la vista, con acción de reintentar: base bloqueada, fallo de lectura, disco lleno al copiar el logo |
| GUARDANDO | Botones deshabilitados. Ya estaba |
| ÉXITO | **Faltaba.** Confirmación breve tras guardar. En el alta de la **primera** organización, la confirmación ofrece el paso siguiente: "Crear el primer evento" |
| PARCIAL a | **Faltaba.** El logo se redimensionó por `lado_max`: se avisa ("la imagen se redujo a 1600 px"), no se hace en silencio |
| PARCIAL b | **Faltaba.** `logo_path` apunta a un archivo que no está en disco (respaldo restaurado en otra máquina, caso que el propio §1.4.4 anticipa): se pinta el marcador de "sin logo" con un aviso y la opción de volver a cargarlo |
| VALIDACIÓN | Mensaje junto al campo, foco al campo, sin modal. Ya estaba |
| BORRADO | Confirmación normal, con el nombre de la organización en el texto (G29). El botón ya está deshabilitado cuando hay eventos o patrones, que es cuando hay algo que perder |

- `[+]` Botón "Eliminar" deshabilitado con explicación visible cuando la
  organización tiene eventos o patrones, en vez de habilitarlo y fallar al pulsarlo.
- `[!]` **Enmienda G29 (revisa E17c) — al borrar, `medios/<id>/` se borra, sin
  papelera.** El borrador proponía moverlo a `medios/.eliminados/<id>-<fecha>/`
  más una confirmación escribiendo el nombre de la organización. Se cortan las dos
  cosas: borrar una organización **ya está bloqueado** cuando tiene eventos o
  patrones, es decir, siempre que los datos importen. Lo único que se puede borrar
  es una organización vacía creada por error, y lo único que se pierde es su logo.
  Un nivel de borrado suave más un modal de escribir-el-nombre para ese caso es
  protección contra un escenario en el que no hay nada que perder. Queda una
  confirmación normal, y el borrado de la carpeta va dentro de la misma
  transacción, después del `DELETE`.
- `[!]` **Enmienda E17d — la primera organización creada queda seleccionada.**
  Sin esto, Gabriel crea su primera organización, va a Eventos y se encuentra "no
  hay organización activa, crea una primero". Acababa de crear una. Era el callejón
  sin salida del primer arranque.

#### 1.7.4 `ui/vistas/vista_eventos.py` — inicio de la aplicación

`[!]` **Enmienda E18 — Eventos es la pantalla de inicio y lista TODOS los
eventos**, de todas las organizaciones, con el logo de la organización en cada
fila. El filtrado por organización es un **filtro**, no un modo global (enmienda
E14). Se añade un campo de búsqueda por nombre, organización, estado y año: en
tres años esta lista tiene cientos de filas, y la fase 5 va a añadir búsqueda por
código dentro del evento, así que el patrón se establece aquí.

`[!]` **Enmienda E18b — hacer clic en un evento abre su espacio de trabajo**
(enmienda E14). En las fases 2 a 5 ese clic es *el* gesto principal de la
aplicación. En el borrador no hacía nada: una fila con aspecto de ser pulsable que
no responde no es una carencia, es un error.

En la fase 1 el espacio de trabajo muestra los datos del evento y un marcador
explícito de "Cartones, plantilla y sorteo llegan en versiones próximas". Un
"todavía no" visible es honesto; un clic muerto es un fallo.

**Cobertura de estados (el borrador cubría uno de seis):**

| Estado | Qué se ve |
|---|---|
| VACÍO SIN ORGANIZACIONES | "Primero crea una organización", con el botón que lleva allí |
| VACÍO CON ORGANIZACIONES | **Faltaba, y es el caso común.** "Aún no hay eventos" con botón de alta |
| VACÍO TRAS FILTRO | "Ningún evento coincide", con limpiar filtro |
| ERROR | **Faltaba.** Franja no modal con reintento |
| ÉXITO | **Faltaba.** Confirmación tras guardar |
| PARCIAL | Nombre duplicado dentro de la organización (E4a): aviso **en línea, junto al campo, antes de guardar**, que no bloquea y no reaparece después de guardar |

**Contrato de la fila:** logo de la organización, nombre del evento, nombre de la
organización, fecha, chip de estado. Orden por fecha descendente, los borradores
primero dentro de la misma fecha.
- Formulario: nombre, fecha (`QDateEdit`, se guarda como `YYYY-MM-DD`), hora
  (`QTimeEdit`, opcional, `HH:MM`), lugar, precio de la tabla (`QDoubleSpinBox`
  con dos decimales de cara al usuario, convertido a **centavos enteros** al
  guardar, por la enmienda E4b), estado (solo lectura en esta fase, siempre
  `borrador` al crear).
- Validación: nombre no vacío, precio mayor o igual a 0. El nombre duplicado
  dentro de la organización **avisa pero no bloquea** (enmienda E4a): una
  organización repite el mismo nombre de evento cada año con toda razón.
- `[+]` Muestra el estado del evento como etiqueta con color, porque desde la fase
  4 será la información más consultada de esa lista.

#### 1.7.5 `ui/vistas/vista_ajustes.py`

`[!]` **Enmienda E19 — agrupada en tres bloques**, no diez filas indiferenciadas:

**Preferencias**
- Idioma (combo es/en): guarda la preferencia y dispara la retraducción de toda la
  aplicación sin reiniciar. Confirmación visible de que se guardó.

**Ubicaciones**
- Raíz de datos, base, logs, respaldos, medios, cada una con botón "abrir carpeta".
- `[!]` **Enmienda E19b — el aviso de ubicación de la base vive aquí, y no se
  puede descartar.** El borrador lo mostraba una vez al arrancar con un "no volver
  a mostrar", y la tabla de riesgos califica ese riesgo de **crítico**. Descartado
  una vez en el primer mes, la aplicación no lo vuelve a mencionar nunca, ni
  siquiera en la máquina del evento. El diálogo de arranque es la notificación;
  **Ajustes es el domicilio**: mientras `advertencia_ubicacion_bd()` devuelva algo,
  aquí hay una fila de aviso permanente con un enlace a "por qué esto importa".
  Descartar silencia el diálogo de arranque, nada más.

**Diagnóstico**
- Versión de la aplicación, versión de Python, versión del esquema
  (`schema_version`).
- `[+]` Botón "abrir log de aplicación". Cuando algo falle en un evento real, el
  operador es Gabriel y va a necesitar el archivo en dos clics, no una ruta que
  copiar a mano.
- Estados: error al abrir una carpeta (borrada, sin permisos), ruta que resuelve
  pero no existe, `schema_version` ilegible. Los tres se muestran en la propia
  fila, no en un diálogo.

#### 1.7.7 `[+ E21]` `ui/atajos.py` — teclado y foco

El borrador no contenía un solo atajo, orden de tabulación, botón por defecto ni
comportamiento de Enter y Escape. Para una aplicación cuya restricción definitoria
es "se opera en vivo, frente a cámara, contra reloj", es la omisión más grande
después del tema.

- Un diccionario de módulo con los atajos de la fase, no una clase de registro:
  `Ctrl+1/2/3` navegación global, `Ctrl+N` nuevo, `Ctrl+S` guardar, `Esc`
  cancelar, `Ctrl+L` abrir log.
  `[!]` **Enmienda G30 — se recorta a un diccionario.** El borrador diseñaba un
  registro central de acciones argumentando que "la fase 5 registra `Espacio`
  contra este mismo registro". Eso es generalidad especulativa para una aplicación
  de cuatro superficies. Un diccionario `ATAJOS: dict[str, str]` en un módulo son
  cinco líneas, da el mismo sitio único donde mirar, y la fase 5 lo convierte en lo
  que necesite cuando tenga más de una superficie manejada por teclado.
  Lo concreto se mantiene entero: orden de tabulación, botón por defecto,
  `Esc` con comprobación de cambios sin guardar y anillo de foco visible.
- Cada formulario: orden de tabulación explícito, botón por defecto, `Esc` =
  cancelar con comprobación de cambios sin guardar.
- Anillo de foco con contraste mínimo 3:1 contra las dos superficies contiguas,
  declarado en `tema.py` (enmienda E15).
- Tipografía mínima de 13–14 px y objetivos de pulsación de 32 px: Gabriel lee
  esto mirando de reojo, con la cámara delante.

#### 1.7.8 `[+ E22]` `ui/dialogos.py` — tres canales de error, no uno

El plan construye `ErrorPersistencia`, `ErrorIntegridad`, `ErrorBaseBloqueada` y
`ErrorValidacion`, cada uno con su `clave_i18n`, y el borrador los mandaba todos al
diálogo modal del manejador global. Ese manejador es para lo **inesperado**.
`ErrorBaseBloqueada` es esperado, recuperable y reintentable; presentarlo como un
choque es incorrecto, y en la fase 5 un modal encima de una transmisión en vivo es
un incidente.

| Canal | Cuándo | Forma |
|---|---|---|
| En línea, junto al campo | `ErrorValidacion` | Texto bajo el campo, foco al campo |
| Franja de vista, no modal | `ErrorPersistencia`, `ErrorIntegridad`, `ErrorBaseBloqueada` | Barra en la cabecera de la vista con acción de reintentar |
| Modal | Solo condiciones terminales: migración fallida, base corrupta, sin permisos | Diálogo con detalle copiable y ruta del log |

`[!]` **Enmienda G28 — la bandera `modo_vivo` se corta.** El borrador la añadía
para que la fase 5 suprimiera los modales durante la transmisión. No tiene
consumidor hasta la fase 5 y su semántica correcta depende de una interfaz de
sorteo que todavía no existe: es diseño contra requisitos imaginados. Los tres
canales se quedan, que son lo valioso y lo barato; la supresión de modales en vivo
la define la fase 5, cuando pueda verla.

#### 1.7.6 `ui/tema.py` — dos funciones, dos públicos

`[!]` **Enmienda E15 — la marca de la organización NO pinta la interfaz del
operador.** Ver el desafío al usuario **DU-1** en la puerta final: esta enmienda
contradice una frase explícita del alcance y por lo tanto la decide Gabriel, no
el plan. Lo que sigue es la recomendación y su argumento.

```python
def aplicar_tema_operador(app) -> None        # neutro, fijo, sin argumento de organización
def paleta_organizacion(org) -> PaletaMarca   # validada, devuelta, NO aplicada a la app
```

**El argumento, en cinco puntos:**

1. **El alcance pide un dashboard con marca, no una cabina con marca.** El §4.1
   dice que la organización activa "determina la apariencia de toda la app". Pero
   el §5.2, que es el catálogo real de lo personalizable en el programa, se titula
   *"En el programa (dashboard de sorteo)"* y todos sus elementos son superficie de
   transmisión: logo en la pantalla principal y en la de transmisión, imagen de
   fondo de la escena, composición de bloques. Ninguno describe el cromo
   administrativo de Gabriel.
2. **Un color de marca no es un color semántico.** Si la organización es roja,
   el color de acción primaria y el color de peligro son el mismo rojo. La fase 5
   necesita colores memorizados e inequívocos para PAUSAR, ANULAR y CONFIRMAR
   GANADOR, y el propio plan (§1.7.4) ya quiere chips de color por estado de
   evento. No se puede construir una paleta de estados encima de la paleta que un
   cliente eligió para su papel membretado.
3. **Destruye la memoria muscular del único usuario.** Gabriel corre la misma
   aplicación para la Fundación X (rojo oscuro) y el Club Y (amarillo sobre
   blanco). Mismo botón, otro color, cada evento, contra reloj y frente a cámara.
4. **La paleta por defecto del documento técnico no pasa su propia puerta.**
   Calculado: `#e94560` sobre `#1a1a2e` da **4,46:1** — por debajo del 4,5:1 que
   el borrador se comprometía a exigir. Y blanco sobre `#e94560` da **3,83:1**,
   o sea que un botón primario con etiqueta blanca tampoco pasa AA. Si el defecto
   no pasa, el aviso de contraste va a saltar siempre y se va a ignorar siempre.
5. **Tres colores no generan una interfaz.** `organizacion` guarda
   `color_primario`, `color_secundario` y `color_texto`. Una interfaz Qt necesita
   superficie, superficie elevada, borde, texto primario, texto secundario, texto
   deshabilitado, anillo de foco, hover, pulsado, peligro, aviso, éxito, más
   cuatro chips de estado. Derivar quince fichas de tres hexadecimales arbitrarios
   no sale bien.

**Qué hace cada función:**

- `aplicar_tema_operador(app)` instala **una** paleta neutra oscura fija, pensada
  para sala en penumbra con un segundo monitor brillante y una cámara al lado,
  con fichas semánticas de verdad y reglas explícitas de `:focus`, `:hover`,
  `:pressed`, `:disabled` y `:checked` para cada clase de widget con estilo.
  `[!]` En cuanto una hoja de estilo Qt fija `background-color` en un
  `QPushButton`, Qt deja de dibujar los estados nativos de foco, hover, pulsado y
  deshabilitado salvo que se redeclaren todos. El plan **depende** de que
  "deshabilitado" se vea, en dos sitios distintos ("Eliminar deshabilitado con el
  motivo visible" y "guardando: botones deshabilitados"). Sin las pseudo-clases,
  esos dos estados desaparecen visualmente.
- `paleta_organizacion(org)` **devuelve** una paleta de marca validada
  (`#RRGGBB` o se cae al defecto, con registro) y con el contraste ya calculado.
  Nadie la aplica a la aplicación. La consumen: la vista previa del cartón
  (fase 3), el motor de PDF (fase 3) y `ventana_transmision` (fase 5).
- La marca **sí** aparece en la interfaz del operador, como identidad y no como
  cromo: el logo de la organización y una fila de tres muestras de color en su
  tarjeta, y una franja de 4 px en el color primario en la cabecera del espacio de
  trabajo del evento. Siempre sabes de quién es el evento; los botones nunca
  cambian de color.
- El aviso de contraste se conserva, pero **como dato informativo en la tarjeta de
  la organización**, referido a lo que de verdad importa: legibilidad del
  encabezado del cartón impreso y de la pantalla de transmisión. No es una puerta
  de guardado.

`[!]` **Enmienda E15b — los colores de la organización son una semilla, no la
paleta final.** El `plantilla_json` del §5.1 consume `color_encabezado`,
`color_grilla`, `fondo` y `opacidad_fondo`; el `tema_json` del §7 consume `fondo`,
`acento`, `numero_actual` y `texto`. Ninguno de los dos se deriva de tres
hexadecimales. Se escribe la decisión junto a la política E4e en el `README`:
**las tres columnas de color de `organizacion` son el valor inicial que proponen
los editores por evento de las fases 3 y 5; el valor que manda es el del evento.**

---

### 1.8 `[+ E27]` Contratos de módulo y convenciones

`[!]` **La enmienda más importante de toda la revisión.** El borrador especificaba
con cuidado las **formas** (firmas, capas, la regla del repositorio) y callaba las
**reglas** (quién es dueño de la conexión, quién traduce los errores del driver,
qué verbo se usa, cómo consigue una prueba una base migrada). Las formas se usan
solas; las reglas no escritas cuestan entre cinco y cuarenta minutos cada una en la
fase 2, y cada una produce una decisión que las fases 3 a 5 heredan sea buena o mala.

Peor: hoy esas reglas viven en **este archivo de plan**, que se archiva al etiquetar
`v0.1.0`. A partir de ahí no existen en ningún sitio que el desarrollador — o el
asistente — vaya a leer. **Un convenio que no está en `CLAUDE.md` no existe.**

Por eso la fase 1 entrega también `docs/convenciones-codigo.md`, con sus reglas
reflejadas como viñetas en `CLAUDE.md`. Es una página. Cierra diez hallazgos.

#### 1.8.1 Conexiones e hilos

- **Una conexión por hilo. Nunca se comparte.** `check_same_thread` se queda en
  `True`. Un trabajador llama a `abrir_conexion()` él mismo y la cierra en un
  `finally`.
  `[!]` La fase 1 instala `threading.excepthook` justificándolo en que "las fases 2
  y 3 usan `QThread`", y no dejaba escrita ni una línea sobre cómo un hilo obtiene
  su conexión. Los objetos `sqlite3.Connection` lanzan `ProgrammingError` al usarse
  fuera del hilo que los creó. Es el fallo que costaría media hora de documentación
  de SQLite en la primera hora de la fase 2.
- En WAL conviven **un escritor y N lectores**. Una conexión de interfaz que
  mantenga abierta una transacción de escritura bloquea el `BEGIN IMMEDIATE` de un
  trabajador hasta `busy_timeout` (5 s). Regla: **la interfaz no mantiene nunca una
  transacción abierta entre dos vueltas del bucle de eventos.**
- `abrir_conexion` acepta `":memory:"` y, en ese caso, se salta la comprobación de
  WAL: `journal_mode` no es aplicable a una base en memoria.

#### 1.8.2 Transacciones

- **Los repositorios nunca abren transacciones y nunca hacen commit.** Solo los
  servicios y `__main__` abren `transaccion()`.
- **`transaccion()` no es reentrante.** Anidarla lanza `ErrorPersistencia` con
  mensaje claro, no un `OperationalError` crudo de SQLite.
  `[!]` La fase 5 envuelve en una sola transacción el `INSERT extraccion`, el
  `INSERT ganador`, el `UPDATE ronda` y el volcado del log. Si un repositorio de la
  fase 5 abriera su propia `transaccion()` copiando lo que encontrara al lado, esa
  transacción por bola reventaría en vivo. Una prueba en rojo en la fase 1 cuesta
  infinitamente menos.
- Con `isolation_level=None`, una llamada a repositorio fuera de `transaccion()`
  hace autocommit; dentro, participa. Documentado en el docstring de `conexion.py`.

#### 1.8.3 Tabla de verbos de repositorio

| Verbo | Forma de la firma | Devuelve |
|---|---|---|
| `crear` | `(con, modelo)` | el modelo persistido (E26) |
| `crear_varios` | `(con, list[modelo])` | `int` insertados; usa `executemany` |
| `obtener` | `(con, id)` | `Modelo \| None` — siempre por clave primaria |
| `obtener_por_<campo>` | `(con, valor)` | `Modelo \| None` |
| `listar` / `listar_por_<campo>` | `(con, ..., limite=None, desplazamiento=0)` | `list[Modelo]` |
| `contar` / `contar_por_<campo>` | `(con, ...)` | `int` |
| `existe_<campo>` | `(con, valor, excluir_id=None)` | `bool` |
| `actualizar` / `actualizar_<campo>` | `(con, modelo)` / `(con, id, valor)` | `None` |
| `eliminar` / `eliminar_por_<campo>` | `(con, id)` | `None` |

- Nombres de archivo: `repo_<entidad en singular>`, `servicio_<lo que gestiona, en
  plural>`. Quedan predeclarados para que nadie adivine: `servicio_cartones`,
  `servicio_impresion`, `servicio_compradores`, `servicio_sorteo`,
  `servicio_respaldo`.
- Paginación: siempre `limite` y `desplazamiento`, en ese orden.
- `con` va **siempre primero**, en repositorios y en servicios.
  `[!]` El contrato de la fase 2 escribe `generar_lote(evento_id, cantidad,
  prefijo_codigo)`, sin `con`. Contradice el convenio de la fase 1. Se resuelve
  aquí, de una vez: `generar_lote(con, evento_id, cantidad, prefijo_codigo)`.
- `repo_auditoria.registrar` es la única excepción a la tabla, porque el contrato
  la nombró así. Es una excepción, no un patrón a generalizar.

#### 1.8.4 Mapeo fila → modelo

Cada repositorio termina con dos funciones privadas, y esa es la plantilla que
copian los siete repositorios que faltan (`carton`, `lote`, `comprador`, `patron`,
`ronda`, `extraccion`, `ganador`):

```python
def _desde_fila(fila: sqlite3.Row) -> Organizacion: ...
def _a_parametros(modelo: Organizacion) -> dict[str, object]: ...
```

`[!]` En un flujo con asistente de IA esto es lo de mayor apalancamiento de toda la
revisión: el asistente reproduce el patrón que encuentra en el archivo de al lado.
Escribir bien el primero decide cómo se escriben los siete siguientes.

#### 1.8.5 Quién captura qué

- La vista captura `ErrorValidacion` → mensaje en línea sobre `e.campo`.
- La vista captura `ErrorBingo` → franja no modal o modal según el §1.7.8.
- **La vista no captura nunca `Exception`.** Lo que no sea `ErrorBingo` es un fallo
  de programa y pertenece al manejador global.
- Los repositorios devuelven `None` cuando no encuentran; **los servicios lanzan
  `ErrorNoEncontrado`**. Sin esta regla, cada servicio de las fases 2 a 5 escribe
  `if x is None: raise <algo distinto>`.

#### 1.8.6 `dominio/dinero.py` `[+ E28]`

```python
def a_centavos(valor: Decimal | str) -> int
def formatear(centavos: int, idioma: str) -> str
```

La enmienda E4b (dinero en enteros) es correcta, pero el borrador ponía la
conversión **en la vista** (`QDoubleSpinBox` "convertido a centavos al guardar").
La fase 3 necesita la inversa para la recaudación teórica y la fase 5 para el acta
y el reporte, y cada una redondearía a su manera — en un documento que el propio
alcance describe como comprobante firmado. Dos funciones, un archivo de prueba, y
se cierra la clase entera de error. Queda prohibida la conversión ad hoc.

#### 1.8.7 `ui/tarea.py` `[+ E29]` — trabajador `QThread`

Unas 60 líneas, sin consumidor en la fase 1, escritas y probadas aquí porque las
fases 2, 3 y 5 lo necesitan y si no lo inventan tres veces:

- Subclase de `QThread` que recibe un invocable normal.
- Señales `progreso(int, int)`, `terminado(object)`, `fallado(ErrorBingo)`.
- `cancelar()` cooperativo.
- **Abre y cierra su propia conexión dentro de `run()`** (regla 1.8.1).

Convenio del lado del servicio, indisociable: **los servicios aceptan
`al_progresar: Callable[[int, int], None] | None = None` y
`debe_cancelar: Callable[[], bool] | None = None`, y no importan Qt jamás.**
Sin este convenio, la fase 2 importa `Signal` dentro de `servicio_cartones.py`,
`test_arquitectura.py` se pone en rojo, y el fallo llega **después** de escribir el
código en vez de antes.

#### 1.8.8 `tests/conftest.py` y `tests/factorias.py` `[+ E30]`

`BINGO_HOME` es la mejor decisión del plan y el borrador no especificaba **ni una
sola fixture** para quince archivos de prueba. Cada archivo se habría inventado la
suya, habrían derivado, y la fase 2 habría copiado la primera que abriera.

Primeras dos líneas de `conftest.py`, antes de cualquier otro import:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

`[!]` Tiene que ser antes de que cualquier módulo importe PySide6; ponerlo dentro
de una prueba llega tarde. Y `[tool.pytest.ini_options]` **no tiene** una clave
`env` nativa: eso exigiría el plugin `pytest-env`, que no estaba en las
dependencias. El borrador daba por hecho un mecanismo que no existía, y el fallo se
ve como una ventana parpadeando a mitad de la suite.

Fixtures:

| Fixture | Alcance | Qué hace |
|---|---|---|
| `bingo_home` | **autouse**, función | `monkeypatch` de `BINGO_HOME` a `tmp_path` + `asegurar_estructura()`. Autouse a propósito: hace **estructuralmente imposible** que una prueba escriba en el `%LOCALAPPDATA%` real |
| — | — | `[!]` **Enmienda G16 (crítica): `plantilla_bd` NO depende de `bingo_home`.** El borrador hacía `plantilla_bd` de sesión y `bingo_home` autouse de función (usa `monkeypatch`, que es de función). Una fixture de sesión no puede depender de una de función: pytest lanza `ScopeMismatch` en la recolección. Y si se "arreglaba" al revés, `plantilla_bd` no vería `BINGO_HOME` y migraría dentro del `%LOCALAPPDATA%` real del desarrollador — exactamente lo que `bingo_home` existe para hacer imposible. `plantilla_bd` construye su ruta con `tmp_path_factory`, independiente de `BINGO_HOME`; `con` copia esa plantilla dentro del hogar de la prueba |
| `plantilla_bd` | sesión | Migra **una vez** por sesión sobre una ruta de `tmp_path_factory`, **hace `wal_checkpoint(TRUNCATE)` y cierra**, y guarda el archivo como plantilla |
| `con` | función | Copia la plantilla **ya cerrada y con checkpoint** dentro del hogar de la prueba, abre con `synchronous="OFF"`, cede, y en el desmontaje hace `PRAGMA wal_checkpoint(TRUNCATE)` y **cierra**. `[!]` Copiar `bingo.db` mientras `bingo.db-wal` todavía guarda el esquema confirmado produce una plantilla vacía; por eso el checkpoint va también al **crear** la plantilla, no solo al desmontar |
| `con_memoria` | función | `":memory:"` para lo que no necesita WAL |
| `organizacion_creada`, `evento_creado` | función | Fábricas en `tests/factorias.py`, que cada fase amplía |
| `estado_limpio` | **autouse**, función | Reinicia el idioma cargado de `i18n` y quita los manejadores de log |

Tres razones concretas detrás de estas decisiones:

- **`synchronous="OFF"` en pruebas.** FULL es el defecto correcto en producción
  (E2), pero en pruebas significa un fsync real por commit, sobre un `tmp_path` que
  Windows Defender está escaneando. Las pruebas de bloques de 500 cartones de la
  fase 2 pagarían 20 fsync cada una. Una única prueba comprueba que el **defecto**
  es FULL.
- **Cerrar la conexión en el desmontaje, obligatorio.** Una conexión abierta deja
  `bingo.db-wal` y `-shm` bloqueados y la limpieza de `tmp_path` lanza
  `PermissionError: [WinError 32]`. El plan ya sabía de los archivos laterales de
  WAL (los puso en `.gitignore`) pero no de esta consecuencia.
- **`estado_limpio`.** `i18n` guarda el idioma en un global y `log.py` configura el
  logger raíz. pytest corre en un solo proceso: un `cargar("en")` en la prueba A se
  filtra a la B. Produce el peor modo de fallo que existe, el que pasa en solitario
  y falla en la suite.

`[!]` **Y una regla sin la cual `BINGO_HOME` no funciona:** `raiz_datos()` lee
`os.environ` **en cada llamada**, sin cachear en una constante de módulo. Si se
cachea — que es exactamente lo que se escribe por reflejo en un módulo de
configuración — `monkeypatch.setenv` después del import no hace nada y las pruebas
escriben en el perfil real del desarrollador, en silencio. Se prueba con
`test_rutas.py::test_bingo_home_no_se_cachea`, que cambia la variable dos veces en
el mismo proceso.

#### 1.8.9 Carril rápido de pruebas `[+ E31]`

```
tests/
├── conftest.py          # sin imports de Qt: PySide6 cuesta ~1 s por proceso
├── factorias.py
├── dominio/             # instantáneas: sin Qt, sin base
├── persistencia/        # conexión, migraciones, esquema, repos, errores_sqlite
├── config/              # rutas, preferencias
├── utilidades/          # errores, log, fechas, imágenes
├── arquitectura/        # test_arquitectura.py
└── ui/                  # conftest.py propio con las fixtures de Qt
```

`[!]` **Enmienda G26.** El borrador mandaba tres subcarpetas y luego listaba
veintidós archivos planos, de los cuales nueve (`test_i18n`, `test_imagenes`,
`test_preferencias`, `test_arquitectura`, `test_errores`, `test_arranque`,
`test_rutas`, `test_fechas`, `test_dinero`) no encajaban en ninguna de las tres.
El primero que fuera a escribir `test_rutas.py` habría tenido que adivinar.

`[tool.pytest.ini_options] markers = ["lento: pruebas de volumen"]`.
Bucle interno: `pytest -m "not lento"`. Suite completa al cerrar la fase.
`[!]` El contrato de la fase 2 exige generar **50.000 cartones** para comprobar
colisiones de firma; el de la fase 5, reproducciones completas de partida. Sin
marcadores, `pytest` se convierte en una pausa para el café, y una suite lenta es
una suite que se corre menos.

#### 1.8.10 Base de desarrollo obsoleta tras editar la 001

La política E4e (la 001 es editable hasta el primer evento real) tiene un modo de
fallo silencioso: se edita la 001, y toda base de desarrollo ya existente conserva
`version = 1`, así que el runner no aplica nada y el desarrollador trabaja contra
un esquema viejo persiguiendo errores fantasma.

`[!]` **Enmienda G15 — se corta la guardia de hash (la antigua E32) y se resuelve
con `--reiniciar-datos`.** El borrador traía las dos cosas para el mismo problema.
La guardia de hash necesitaba una columna nueva en `schema_version` que el §1.2.4
nunca llegó a definir (contradicción real: la prueba de E32 no podía pasar), una
rutina de hash, normalización de saltos de línea, un `.gitattributes` para que el
`autocrlf` de git no diera hashes distintos en dos máquinas, una comprobación al
arrancar y una prueba. `--reiniciar-datos` son tres líneas, no toca el esquema y
resuelve lo mismo: borra la base de desarrollo y vuelve a migrar.

La política E4e se traslada de `README.md` a `docs/convenciones-codigo.md` (es una
regla de desarrollo, no de instalación) y se acompaña de la instrucción operativa:
*si editas la 001, corre `python -m bingo --reiniciar-datos`.*

`[+]` Se añade igualmente un **`.gitattributes`** con `*.sql text eol=lf`. No por
el hash, que ya no existe, sino porque el volcado de esquema y cualquier
comparación de archivos `.sql` entre máquinas se rompe con `autocrlf`.

#### 1.8.11 Otros contratos que se fijan aquí

- **`puede_transicionar` se generaliza:**
  `puede_transicionar(transiciones: Mapping[str, set[str]], actual, nuevo) -> bool`,
  con `TRANSICIONES_EVENTO` pasada como argumento. Así la fase 2 solo añade
  `TRANSICIONES_CARTON` y la fase 5 `TRANSICIONES_RONDA`, en vez de renombrar la
  función de la fase 1 y sus pruebas.
- **Dónde vive cada entidad de dominio:** las que tienen comportamiento van en su
  propio módulo, como fija el §2.2 del documento técnico (`dominio/carton.py`,
  `dominio/patron.py`, `dominio/bombo.py`). Las que son solo registro van en
  `dominio/modelos.py` (`Organizacion`, `Evento`, `RegistroAuditoria`).
- **`rutas.dir_logs_evento(evento_id)`** (tres líneas, se mantiene pese a ser
  superficie de la fase 5: evitar reabrir un módulo de cimientos a mitad del
  trabajo de sorteo vale más que las tres líneas), que el §2.3 del documento
  técnico exige
  (`logs/<evento>/`) y el borrador no incluía. Tres líneas, con el mismo criterio de
  id y no nombre que ya se aplicó a `medios/`.
- **`ui/registro_vistas.py`:** una lista de `(clave_i18n, icono, fábrica)` que la
  ventana recorre. La fase 2 añade una tupla en lugar de editar
  `ventana_principal.py`; lo mismo las fases 3, 4 y 5.
- **Cancelación por compensación.** El contrato de la fase 2 pide a la vez "bloques
  de 500 por transacción" y "si se cancela, se revierte el lote completo". Son
  incompatibles: una vez confirmado el bloque 3, ninguna transacción lo revierte.
  La cancelación se hace con un borrado compensatorio (`eliminar_por_lote`), que
  vive en el repositorio; la decisión de llamarlo, en el servicio. Se escribe ahora
  para que la fase 2 no descubra la contradicción a mitad de camino.
- **Punto de entrada probable:** `def principal(argv: list[str] | None = None) -> int`,
  para que `test_arranque.py` lo llame directamente en vez de parchear `sys.argv`,
  y para que el bloqueo de instancia reciba un `forzar: bool` explícito.
- **Docstrings:** todo módulo de `persistencia/`, `servicios/` y `utilidades/`
  abre con un docstring que declara su contrato y sus reglas. Es el domicilio
  natural de las reglas 1.8.1, 1.8.2 y del constructor de E25.
- **`docs/decisiones.md`:** una entrada corta por decisión (E1 a E32), añadida al
  cerrar cada fase. Sin esto, la fase 4 mira `precio_tabla_centavos` y se pregunta
  por qué, y la fase 5 ve `auditoria` vacía al arrancar y lo "arregla".
- `[!]` **Enmienda G31 — `docs/esquema-actual.sql` se difiere.** El borrador
  añadía una prueba de instantánea del esquema. Choca de frente con la política
  E4e: mientras la 001 sea editable (toda la fase 1 y parte de la 4), esa prueba
  falla en **cada edición intencionada**, que es exactamente como una prueba de
  instantánea acaba actualizándose por reflejo sin mirarla. Además duplica
  `test_esquema.py`, que ya comprueba tablas, columnas y restricciones. Se
  introduce el día que la 001 se congela, o sea en el primer evento real. (Nota
  técnica para entonces: `.schema` es un comando del cliente `sqlite3`, no de la
  API; hay que leer `sqlite_master`.)
- **README, bucle de desarrollo:** cómo correr un solo archivo de prueba, cómo
  arrancar contra un `BINGO_HOME` desechable, y **cómo reiniciar la base de
  desarrollo** (`--reiniciar-datos`), que es una operación constante en cuanto la
  fase 2 empiece a generar diez mil cartones de basura.

---

### 1.9 Pruebas y cierre

**Suite obligatoria de la fase.** Todas corren sin abrir ventana, con `BINGO_HOME`
apuntando a `tmp_path` y `QT_QPA_PLATFORM=offscreen` donde haga falta Qt.

| Archivo | Cubre |
|---|---|
| `test_rutas.py` | Estructura creada; `BINGO_HOME` respetado y **releído en cada llamada, sin cachear** (E30); detección de carpeta sincronizada y ruta UNC; `dir_logs_evento` |
| `test_conexion.py` | PRAGMAs efectivos (`foreign_keys`=1, `journal_mode`=wal, `synchronous`=FULL **por defecto**); `transaccion()` hace rollback ante error; `busy_timeout` fijado; el parámetro `synchronous` cambia el valor efectivo; `[+ E27]` `transaccion()` anidada lanza `ErrorPersistencia` y no `OperationalError`; una llamada fuera de transacción hace autocommit; dos conexiones en contienda respetan `busy_timeout`; `":memory:"` se acepta y se salta la comprobación de WAL |
| `test_migraciones.py` | Primera aplicación crea el esquema; segunda no reaplica; numeración con hueco falla; archivo mal nombrado falla; versión futura aborta; `[!]` **atomicidad real (G1)**: un `002_falla.sql` que crea una tabla y luego tiene SQL inválido; se afirma que **ninguna** tabla de la 002 sobrevive y que `schema_version` no ganó fila. Es la prueba que el borrador decía tener y que, con la implementación obvia, no podía pasar |
| `test_esquema.py` | Las 10 tablas de §3.1 existen con sus columnas; FK rechaza huérfanos; CHECK rechaza estados inválidos; los dos UNIQUE de `carton` funcionan |
| `test_repo_organizacion.py` | CRUD; borrado bloqueado con eventos; borrado bloqueado con patrones; `existe_nombre` |
| `test_repo_evento.py` | CRUD; listado por organización; JSON inválido rechazado; precio guardado y leído en centavos sin pérdida |
| `test_estados.py` | `dominio/estados.py`: transiciones válidas aceptadas, inválidas y hacia atrás rechazadas; `servicio_eventos.cambiar_estado` lanza `ErrorTransicionInvalida` |
| `test_repo_auditoria.py` | `registrar` con y sin `evento_id`; lectura ordenada y limitada |
| `test_i18n.py` | Paridad de claves es/en; paridad de marcadores; clave faltante devuelve la marca visible sin excepción; parámetro faltante no rompe |
| `test_preferencias.py` | Ida y vuelta; JSON corrupto da valores por defecto y renombra; escritura atómica |
| `test_fechas.py` | ISO 8601 UTC ida y vuelta; fecha de calendario sin zona |
| `test_imagenes.py` | PNG válido; JPG convertido; archivo corrupto rechazado; sobredimensionado redimensionado; bomba de descompresión rechazada; escritura atómica |
| `test_errores.py` | El manejador global escribe al log; `[!] (G11)` una excepción lanzada desde un **hilo trabajador** solo registra y **no** intenta construir un `QMessageBox`; una excepción dentro de un *slot* invocado por el bucle de eventos pasa por `sys.excepthook`, registra y **termina el proceso** (G12) |
| `test_arquitectura.py` | Importaciones: `dominio/` sin PySide6 ni sqlite3, `ui/` sin sqlite3, `servicios/` sin PySide6; literales de cadena que empiecen por SQL fuera de `persistencia/` (E6); `[+ E27]` ningún módulo fuera de `persistencia/` llama a `.execute(`, `.executemany(` ni `.executescript(` — es la valla de verdad, no una heurística; `[+ E27]` toda `clave_i18n` pasada a un constructor `Error*` existe en `es.json` |
| `test_arranque.py` | `principal(argv)` completo en `tmp_path` limpio, sin ventana, crea todo y sale sin error; el arranque **no** deja fila en `auditoria` (E7b); `--forzar-instancia` funciona |
| `test_errores_sqlite.py` | `[+ E25d]` Los cuatro tipos de restricción (unique, foreign_key, check, not_null) contra el esquema real de la 001, con `restriccion` poblada; `SQLITE_BUSY` da `ErrorBaseBloqueada`; `SQLITE_CORRUPT` da `ErrorBaseCorrupta`; `__cause__` se conserva |
| `test_dinero.py` | `[+ E28]` `a_centavos` sin pérdida en los casos que rompen coma flotante (0.1, 0.29, 19.99); `formatear` en es y en en |
| `test_tarea.py` | `[+ E29]` El trabajador emite progreso, respeta `cancelar()`, propaga `ErrorBingo` por `fallado` y cierra su conexión |
| `test_servicio_organizaciones.py` | `[+ G14]` **El único punto de consistencia entre disco y base de la fase, y el borrador no lo probaba.** Alta completa; commit que falla tras copiar el logo deja cero filas y cero archivos; disco lleno a mitad de `os.replace`; borrado que elimina la carpeta de medios; orden INSERT → copiar → UPDATE → COMMIT (G8) |
| `test_i18n_retraduccion.py` | `[+ G18]` Crear una segunda ventana de nivel superior, destruirla, y volver a disparar el cambio de idioma sin `RuntimeError: Internal C++ object already deleted`. Es la justificación entera de E20 y no tenía prueba |
| `test_concurrencia.py` | `[+ G16]` Una conexión en `BEGIN IMMEDIATE` y otra **leyendo con éxito** (la propiedad de WAL de la que depende §1.8.1); un segundo escritor agota `busy_timeout` y sale como `ErrorBaseBloqueada`; una conexión usada desde otro hilo lanza `ProgrammingError` |
| `test_persistencia_degradada.py` | `[+ G33]` Directorio de datos de solo lectura y disco lleno: `SQLITE_READONLY`, `SQLITE_FULL` e `SQLITE_IOERR` salen como `ErrorPersistencia` traducido y **no** por el manejador global. `[!]` El mapa de `errores_sqlite` del borrador cubría unique/fk/check/not_null/BUSY/CORRUPT y dejaba caer estos tres al manejador global, que mata el proceso, para una condición recuperable y probable en un portátil de evento |
| `test_tema.py` | `[+ E15]` `paleta_organizacion` valida `#RRGGBB` y cae al defecto ante basura; calcula el contraste correctamente contra valores conocidos; `aplicar_tema_operador` no acepta argumento de organización |
| `test_navegacion.py` | `[+ E14]` Abrir un evento entra al espacio de trabajo y `ultimo_evento_abierto_id` queda guardado; cerrar vuelve al inicio; sin organizaciones, Eventos muestra el estado vacío correcto |

**Cierre de fase:**

1. `ruff check .` y `ruff format --check .` limpios.
2. `pytest` verde.
3. Ensayo manual del guion de aceptación (§5).
4. `CHANGELOG.md` actualizado, merge a `main`, `git tag v0.1.0`.

---

## 4. Estructura de archivos resultante

```
Bingo_App/
├── .gitignore
├── CHANGELOG.md
├── CLAUDE.md
├── README.md
├── TODOS.md
├── pyproject.toml
├── src/bingo/
│   ├── __init__.py            # __version__
│   ├── __main__.py            # arranque
│   ├── config/
│   │   ├── ajustes.py         # constantes
│   │   ├── rutas.py           # [+] rutas + guardia de ubicación
│   │   └── preferencias.py    # [+] preferencias.json
│   ├── dominio/
│   │   ├── modelos.py         # dataclasses Organizacion, Evento, RegistroAuditoria
│   │   ├── estados.py         # [+ E5] transiciones, puede_transicionar genérica
│   │   └── dinero.py          # [+ E28] a_centavos / formatear
│   ├── persistencia/
│   │   ├── conexion.py
│   │   ├── errores_sqlite.py  # [+ E25d] único punto de traducción de sqlite3
│   │   ├── migraciones.py
│   │   ├── migraciones/001_inicial.sql
│   │   ├── repo_organizacion.py
│   │   ├── repo_evento.py
│   │   └── repo_auditoria.py
│   ├── servicios/             # [+]
│   │   ├── servicio_organizaciones.py
│   │   └── servicio_eventos.py
│   ├── i18n/
│   │   ├── __init__.py        # t()
│   │   ├── es.json
│   │   └── en.json
│   ├── ui/
│   │   ├── ventana_principal.py   # [E14] nivel global
│   │   ├── espacio_evento.py      # [+ E14] espacio de trabajo del evento
│   │   ├── tema.py                # [E15] aplicar_tema_operador + paleta_organizacion
│   │   ├── atajos.py              # [+ E21] registro de acciones y atajos
│   │   ├── registro_vistas.py     # [+ E27] las fases 2-5 añaden una tupla
│   │   ├── tarea.py               # [+ E29] trabajador QThread reutilizable
│   │   ├── dialogos.py            # [+ E22] tres canales de error
│   │   └── vistas/
│   │       ├── vista_organizaciones.py
│   │       ├── vista_eventos.py       # inicio de la aplicación [E18]
│   │       ├── vista_datos_evento.py  # [+ E14] sección única del espacio en la fase 1
│   │       └── vista_ajustes.py
│   └── utilidades/
│       ├── errores.py
│       ├── log.py
│       ├── fechas.py
│       └── imagenes.py
├── tests/                     # [E30] conftest.py + factorias.py + 3 subcarpetas
│   ├── conftest.py            #  sin imports de Qt
│   ├── factorias.py
│   ├── dominio/               #  instantáneas
│   ├── persistencia/
│   └── ui/conftest.py         #  fixtures de Qt aquí
├── recursos/
└── docs/
    ├── convenciones-codigo.md # [+ E27] los contratos que la fase 2 necesita
    ├── decisiones.md          # [+ E27] una entrada por decisión E1-E32
    ├── esquema-actual.sql     # [+ E27] volcado verificado por prueba
    └── runbook.md             # [+ O2] los seis fallos de arranque (ver §1.9)
```

Carpetas del documento técnico creadas vacías con `.gitkeep` para las fases
siguientes: el resto de `dominio/` (carton, patron, bombo, partida, reglas),
`impresion/`, `ui/widgets/`.

---

## 5. Criterios de aceptación (guion verificable)

Los seis del contrato, convertidos en pasos comprobables:

| # | Criterio del contrato | Cómo se verifica |
|---|---|---|
| 1 | Arranca en equipo limpio y crea su estructura sola | Borrar `%LOCALAPPDATA%\Bingo`, ejecutar `python -m bingo`, confirmar `datos/ logs/ respaldos/ medios/` más `bingo.db` y `preferencias.json` |
| 2 | Crear organización con logo y colores, cerrar, reabrir, sigue ahí | Alta con PNG y tres colores, cerrar, reabrir: la organización y el logo se ven; existe `medios/<id>/logo_principal.png` |
| 3 | Crear evento en borrador asociado | Alta de evento con nombre, fecha, lugar y precio: aparece en la lista con estado `borrador` |
| 4 | Cambiar idioma cambia todos los textos visibles | Ajustes, inglés, recorrer las **cuatro superficies** (Eventos, Organizaciones, Ajustes y el espacio de trabajo de un evento abierto, cabecera incluida) sin reiniciar: ningún texto en español, ninguna marca `⟦clave⟧` |
| 5 | Migraciones se aplican al primer arranque, no al segundo | Log del primer arranque con "migración 001 aplicada"; segundo arranque sin líneas de migración; `schema_version` con una sola fila |
| 6 | `ruff check` pasa sin errores | `ruff check .` sale con código 0 |

`[+]` Añadidos al guion:

| # | Criterio | Cómo se verifica |
|---|---|---|
| 7 | La aplicación no muere en silencio ante un error inesperado | Provocar una excepción en un slot: diálogo legible más línea en `aplicacion.log` |
| 8 | Un archivo de preferencias corrupto no impide arrancar | Escribir basura en `preferencias.json`: arranca en español, con `preferencias.json.corrupto` a un lado |
| 9 | Una imagen corrupta se rechaza con mensaje claro | Cargar un `.png` truncado: mensaje traducido, sin traceback |
| 10 | Segunda instancia bloqueada | Ejecutar `python -m bingo` dos veces: la segunda avisa y sale |
| 11 | La regla del repositorio se sostiene | `pytest tests/test_arquitectura.py` verde |
| 12 | La base en carpeta sincronizada se avisa | Ejecutar con `BINGO_HOME` bajo una ruta que contenga `OneDrive`: aviso al arrancar **y** fila permanente en Ajustes › Ubicaciones (E19b) |
| 13 | Primer arranque sin callejón sin salida | Equipo limpio: crear la primera organización, y desde la confirmación llegar a crear el primer evento sin toparse con "no hay organización activa" (E17d) |
| 14 | Hacer clic en un evento hace algo | Pulsar una fila de evento abre su espacio de trabajo con la cabecera y el marcador de secciones futuras (E18b) |
| 15 | El teclado alcanza para operar | Recorrer las cuatro superficies y completar un alta usando solo el teclado; el foco es visible en todo momento (E21) |
| 16 | Un error recuperable no se presenta como choque | Bloquear la base desde otro proceso y guardar: franja no modal con reintento, no diálogo de error fatal (E22) |

---

## 6. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Apurar los cimientos por llegar al bingo (riesgo declarado en el contrato) | Alta | Alto | Las pruebas de 1.9 son puerta de cierre de fase, no opcionales |
| SQL filtrándose fuera de los repositorios | Media | Alto | `test_arquitectura.py` lo hace fallar |
| `.db` en carpeta sincronizada | Media | Crítico | Guardia de ubicación al arrancar (1.2.2) |
| PySide6 6.11 sobre Python 3.12 | Baja | Medio | Rueda `cp310-abi3`: instala en 3.12 y en 3.14. Esqueleto que camina (§1.0) lo confirma en la primera hora |
| `reportlab` 5.x con API distinta a la 4.x | Media | Medio (fase 3) | Pin `>=4.2,<6` más nota de verificación al abrir la fase 3 |
| Textos escritos directo en el código por prisa | Alta | Medio | `retraducir()` concentra las cadenas en un único método por vista, más revisión al cerrar la fase. `[!]` **Riesgo aceptado, no probado**: la enmienda E6 eliminó la detección de literales visibles por falsos positivos, así que la mitigación es disciplina y no una prueba en rojo |
| El empaquetado no encuentra las migraciones (fase 5) | Media | Alto | `importlib.resources` desde ya (1.2.4) |
| La cáscara de un solo nivel obliga a reescribir la navegación en la fase 2 o 3 | **Alta** | Alto | Enmienda E14: dos niveles desde ya, con el riel de secciones futuras ya marcado |
| La marca del cliente pintando el cromo del operador choca con los colores de estado de la fase 5 | Alta | Alto | Enmienda E15, sujeta al desafío **DU-1** |
| Una hoja de estilo Qt sin pseudo-clases deja invisible el estado "deshabilitado", del que dependen dos funciones del plan | Alta | Medio | Enmienda E15: `:focus`, `:hover`, `:pressed`, `:disabled`, `:checked` declarados por clase |
| El aviso de base en carpeta sincronizada se descarta una vez y no vuelve | Media | **Crítico** | Enmienda E19b: fila permanente en Ajustes |

---

## 7. Queda listo para la fase 2

- Esquema completo en la base, incluidas `lote` y `carton` con sus índices y su
  `UNIQUE (evento_id, firma)`.
- `abrir_conexion` con `transaccion()` reutilizable para la inserción por bloques
  de 500 cartones. `[!]` **Enmienda E24 — se corrige una contradicción del
  borrador**, que aquí prometía un parámetro `modo_sorteo=False` que el §1.2.3
  nunca definió. El contrato real es: el trabajador de la fase 2 **abre su propia
  conexión** con `abrir_conexion(synchronous="NORMAL")`. Y hay una consecuencia
  que nadie había unido: como `synchronous` se fija al abrir, la única forma de
  que la fase 2 use `NORMAL` es en una conexión aparte del trabajador — que es
  justo lo que exige la regla de una conexión por hilo (§1.8.1).
- `ui/tarea.py`, el trabajador `QThread` con progreso y cancelación, ya escrito y
  probado (§1.8.7).
- `tests/conftest.py` con las fábricas de organización y evento, para que las
  pruebas de cartones no empiecen con ocho líneas de preparación (§1.8.8).
- `docs/convenciones-codigo.md`: las reglas que la fase 2 tendría que inventar.
- `repo_evento` con estado validado, listo para pasar el evento a `preparado`.
- `[!]` **Enmienda G21.** El borrador prometía aquí "ventana principal con
  `QStackedWidget` donde colgar la vista de generación", que es la cáscara plana de
  un nivel que la enmienda E14 eliminó. Lo que la fase 2 recibe de verdad es el
  **espacio de trabajo del evento** de dos niveles: se añade la sección *Cartones*
  al riel del evento registrando una tupla en `ui/registro_vistas.py`, sin tocar
  `ventana_principal.py`. Quien lea solo este apartado y no el §1.7.2 construiría
  contra un diseño borrado.
- `t()` y el mecanismo de `retraducir()` para las nuevas vistas.
- `servicios/` con dos servicios que fijan el patrón para `servicio_cartones`.
- `utilidades/errores.py` con la jerarquía donde colgar `ErrorGeneracion`.

---
---

# GSTACK REVIEW REPORT

Generado por `/gstack-autoplan` el 2026-09-04. Modo: **SELECTIVE EXPANSION**
(auto-seleccionado: fase greenfield sobre un contrato ya cerrado — el alcance del
contrato es la línea base y las ampliaciones se ofrecen una a una).
Voces externas: **subagente Claude** en las cuatro fases. **Codex no disponible**
(binario no instalado) — matriz de degradación `[subagent-only]` en todas.

---

# FASE 1 — REVISIÓN CEO (estrategia y alcance)

## 0A. Desafío de premisas

| # | Premisa del contrato / documentos | Veredicto | Acción |
|---|---|---|---|
| P1 | "Punto de partida: nada, repositorio vacío" | **Válida** (verificado: 4 `.md`, sin `.git`, sin código) | — |
| P2 | La fase 1 tiene que existir antes de la 2 | **Válida**. `carton.evento_id` y `lote.evento_id` son NOT NULL: no hay cartón sin evento, ni evento sin organización | — |
| P3 | "Se crea todo el esquema desde ya" aunque rondas y extracciones no se usen hasta la fase 4 y 5 | **Válida pero incompleta**. Congelar hoy `patron`/`ronda` choca con el §16.1 del documento técnico, que deja abierta la modelación de patrones con variantes hasta la fase 4. Y el esquema "completo" del §3.1 no incluye los textos legales que el alcance §4.1 sí exige | Enmiendas **E4c** (columnas que faltan) y **E4e** (política de 001 editable hasta el primer evento real) |
| P4 | El patrón repositorio existe "para migrar a otra base en el futuro sin reescribir la aplicación" | **Falsa como justificación.** Una app local monousuario no va a migrar de SQLite, y si algún día va a la nube (fuera del alcance v1) la frontera del repositorio no la salva: cambian latencia, concurrencia y autorización, o sea la forma de cada llamada | El patrón **se mantiene**, con la razón correcta escrita: hace testeable el dominio sin abrir ventana, que es el principio rector del §2.1. La regla se verifica con `test_arquitectura.py` (enmienda **E6**) |
| P5 | `synchronous=FULL` siempre | **Válida**, y el borrador de este plan la había invertido con una justificación de rendimiento inventada | Enmienda **E2**: FULL por defecto |
| P6 | Los medios van en `medios/<organizacion>/` | **Frágil.** El nombre de la organización lleva acentos, barras y dos puntos, y renombrar deja huérfanos | Enmienda ya en §1.2.1: `medios/<id>/` |
| P7 | Una sola máquina, todo local, respaldo manual | **Válida como decisión de producto** (alcance §8 la asume explícitamente) **pero sin dueño**: ninguna fase del plan general contiene una tarea de recuperación ante equipo muerto | Queda como **desafío al usuario** en la puerta final |
| P8 | Existe un plan de cinco fases, ninguna con fecha ni presupuesto de horas | **Hueco real.** Sin una fecha objetivo del primer evento pagado no hay forma de juzgar si esta fase está sobre-construida | **Desafío al usuario** en la puerta final |

**Es la fase 1 el problema correcto?** Sí, con matices. La fase 1 es
inevitable por dependencia (P2) y su contrato está bien delimitado. Pero es
también el riesgo más barato del proyecto: el código de cimientos es
re-derivable, no hay dinero en juego, y una equivocación aquí cuesta horas. Los
riesgos que terminan el negocio (legalidad de premios en efectivo, políticas de
Facebook/YouTube, aceptación del PDF por la imprenta, comportamiento de OBS con
dos monitores) están todos fuera de esta fase y sin dueño en ninguna otra. Eso no
es motivo para cambiar la fase 1; es motivo para poner esas cuatro cosas en el
calendario en paralelo. Se lleva a la puerta final.

**Qué pasa si no se hace nada?** No hay software, no hay servicio. Hay
alternativas de mercado (llamadores de bingo gratuitos, generadores de cartones
en PDF) que podrían cubrir un primer evento. Lo que ninguna cubre es el paquete
completo en español con la marca de la organización impresa y el acta como
comprobante, que es la propuesta de valor real. Construir está justificado; lo
que no está escrito en ningún documento es **por qué** lo está.

## 0B. Aprovechamiento de código existente y escalera de reutilización

El repositorio está vacío: no hay código propio que reutilizar. La escalera de
reutilización se aplica entonces contra el ecosistema, antes de escribir cada
pieza.

| Sub-problema | Peldaño 1 (existente en el repo) | Peldaño 2 (biblioteca estándar) | Peldaño 3 (plataforma nativa) | Peldaño 4 (dependencia ya instalada) | Decisión |
|---|---|---|---|---|---|
| Migraciones | — | `sqlite3` + `importlib.resources` | — | — | **Propio, ~80 líneas.** `alembic` está atado a SQLAlchemy y aquí no hay ORM por decisión del §1 del documento técnico; `yoyo-migrations` sería una dependencia entera para lo que resuelven ochenta líneas |
| Rutas de datos | — | `os.environ` + `pathlib` | `%LOCALAPPDATA%` | — | **Propio, ~15 líneas.** `platformdirs` es la respuesta estándar y sería defendible; se descarta porque son quince líneas y una dependencia menos que empaquetar en la fase 5 |
| i18n | — | `gettext` | Qt Linguist (`.ts`/`.qm`) | — | **JSON**, como fija el §9 del documento técnico. `gettext` exige `.po`/`.mo` compilados y una cadena de herramientas; Qt Linguist obliga a compilar `.qm` en cada build. Las claves JSON además se referencian igual desde `plantilla_json` y `tema_json` en las fases 3 y 5 |
| Preferencias | — | `json` + `os.replace` | `QSettings` (registro de Windows) | — | **JSON en archivo.** `QSettings` escribe en el registro en Windows, o sea que las preferencias no viajan con el respaldo `.zip` del §11 ni sobreviven a restaurar en otra máquina |
| Instancia única | — | `msvcrt.locking` / `fcntl.flock` | **`QLockFile`** | PySide6 (ya es dependencia) | **Enmienda E13: `QLockFile`.** Ver abajo |
| Validación de imágenes | — | — | — | **Pillow** (ya es dependencia) | Pillow. Peldaño correcto |
| Log | — | `logging.handlers.RotatingFileHandler` | — | — | Biblioteca estándar |
| Hash / firma (fase 2) | — | `hashlib` | — | — | Biblioteca estándar |

`[!]` **Enmienda E13 — instancia única con `QLockFile`, no con `msvcrt`.**
La escalera se detiene en el peldaño 3 y el borrador la saltó hasta el 2. Qt
trae `QLockFile`, que además de bloquear **detecta bloqueos rancios**: guarda el
PID y el nombre del host, y `tryLock()` los reclama solo si el proceso ya no
existe. Es exactamente la defensa contra el escenario que más importa aquí —
un cierre brusco a las seis de la tarde que dejaría la aplicación sin arrancar a
las siete, el día del evento. Es multiplataforma, ya está pagado en la dependencia
de PySide6, y son cinco líneas en vez de veinte con `#ifdef` de sistema operativo.

## 0C. Estado soñado

```
  ESTADO ACTUAL              ESTA FASE                    IDEAL A 12 MESES
  ─────────────              ─────────                    ────────────────
  4 documentos .md      ──▶  App que abre sola en    ──▶  v1.0 instalada, varios
  Sin código                 un equipo limpio             eventos corridos, actas
  Sin repositorio            Esquema completo             entregadas, la organización
  Sin entorno                Organizaciones + eventos     repite y recomienda
                             persistidos                  ───────────────────────
                             i18n es/en operativo         Motor de sorteo probado en
                             Dominio testeable            vivo, PDF aceptado por la
                             sin abrir ventana            imprenta sin retoques,
                                                          respaldo restaurable en
                                                          una segunda máquina
```

**Delta.** Esta fase deja el 100% del andamiaje y el 0% del producto. Es lo
correcto para el contrato de la fase. Lo que no cubre, y el ideal a 12 meses sí
exige, es: un segundo equipo capaz de retomar un evento, un PDF validado por una
imprenta real, y una política de retención de datos de compradores conforme a la
LOPDP. Los tres están fuera de esta fase; los tres van a `TODOS.md` con dueño.

## 0C-bis. Alternativas de implementación

El §2 del plan compara tres **órdenes de construcción** (A vertical, B por capas,
C interfaz primero) y elige B. Esa comparación se mantiene. Lo que faltaba, y se
añade aquí, son las **bifurcaciones de arquitectura** que el borrador resolvió por
silencio:

| Bifurcación | Alternativa considerada | Decisión | Por qué |
|---|---|---|---|
| Medios (logos) | BLOB en la base vs archivos en `medios/<id>/` | **Archivos en disco** | El documento técnico fija `logo_path TEXT` y `medios/<organizacion>/`. Además, `medios/` no guarda solo logos: en la fase 4 entran las imágenes de premios (varias por premio) y en la 5 el fondo de la escena de transmisión, que son megabytes. Meter todo eso en el `.db` infla el archivo que se respalda en caliente y se copia en cada `.zip`. El coste real (consistencia entre disco y base) se paga en **un** sitio con nombre, `servicio_organizaciones`, y el respaldo del §11 ya incluye `medios/`. **Decisión de gusto, cercana** |
| Alcance del archivo `.db` | Una base por evento vs una base global | **Una base global** | El documento técnico fija `datos/bingo.db`. Organizaciones y patrones son transversales a eventos. Una base por evento haría trivial el borrado LOPDP y la entrega a la organización, y se anota en `TODOS.md` como opción para la v2 |
| Sistema de migraciones | Biblioteca vs propio | **Propio** | Ver 0B |
| i18n | `gettext` / Qt Linguist vs JSON | **JSON** | Ver 0B |
| Recarga de idioma | Reiniciar la aplicación vs `retraducir()` en caliente | **`retraducir()`** | Decisión de gusto, se detalla en la puerta final |
| Instancia única | `msvcrt`/`fcntl` vs `QLockFile` | **`QLockFile`** | Enmienda E13 |

**Recomendación:** enfoque B (capas de abajo hacia arriba) **precedido por el
esqueleto que camina de la enmienda E8**. B sin E8 deja todo el riesgo ambiental
para el final; E8 lo mueve a la primera hora por el precio de una hora.

## 0D. Análisis de modo (SELECTIVE EXPANSION)

**Comprobación de complejidad.** El plan crea unos 30 archivos de código y 15 de
prueba. Es más de 8, que es el umbral de olor. Se examina y se acepta: no son 30
archivos de una funcionalidad, son 30 archivos que son *ocho módulos* (rutas,
conexión, migraciones, tres repositorios, i18n, cuatro utilidades) más tres
vistas. Ninguno introduce una abstracción especulativa. La única clase nueva
distinta de una dataclass es `Preferencias`.

**Mínimo que logra el objetivo declarado.** Estrictamente: rutas + conexión +
migraciones + dos repositorios + ventana con dos formularios + i18n. Todo lo
demás del contrato (auditoría, utilidades de error, fechas e imágenes) es del
contrato, no ampliación, y se mantiene.

**Ampliaciones ofrecidas (barrido de expansión).** Se listan con su decisión
tomada bajo los seis principios de `/autoplan`; las que quedaron cerca se llevan a
la puerta final como decisiones de gusto.

| # | Ampliación | Esfuerzo (humano / CC) | Decisión | Principio |
|---|---|---|---|---|
| 1 | Esqueleto que camina antes de las capas (E8) | 1 h / 5 min | **ACEPTADA** | P2 boil lakes: dentro del radio, coste ridículo |
| 2 | `QLockFile` en vez de bloqueo manual (E13) | 15 min / 2 min | **ACEPTADA** | P4 DRY: la plataforma ya lo trae |
| 3 | Dinero en centavos enteros (E4b) | 20 min / 3 min | **ACEPTADA** | P1 completitud: evita números mal en un comprobante |
| 4 | Columnas de texto legal de la organización (E4c) | 20 min / 3 min | **ACEPTADA** | P1 completitud: el alcance ya las exige |
| 5 | `evento.hora` separada de `evento.fecha` (E4d) | 15 min / 2 min | **ACEPTADA** | P1: el §5.1 imprime "fecha y hora" en el cartón |
| 6 | Política "001 editable hasta el primer evento real" (E4e) | 5 min / 1 min | **ACEPTADA** | P6 sesgo a la acción: descongela la fase 4 por una frase |
| 7 | Guardia de ubicación de la base (§1.2.2) | 30 min / 5 min | **ACEPTADA** | P1: el documento lo llama regla crítica |
| 8 | `BINGO_HOME` para pruebas (§1.2.1) | 15 min / 2 min | **ACEPTADA** | Requisito, no ampliación: sin él la suite escribe en datos reales |
| 9 | Comprobación de contraste WCAG en `tema.py` | 45 min / 8 min | **ACEPTADA, degradada a aviso** | P3 pragmático: 15 líneas, no bloquea, y el color de la organización termina impreso |
| 10 | Prueba de arquitectura (E6, ya recortada) | 1 h / 10 min | **ACEPTADA recortada** | P5 explícito: dos comprobaciones fiables, cero heurísticas |
| 11 | `retraducir()` en caliente vs reiniciar | 2 h / 20 min | **ACEPTADA — decisión de gusto** | Ver puerta final |
| 12 | Carga de patrones del sistema | 2 h / 20 min | **DIFERIDA a fase 4** | P2: fuera del radio de esta fase |
| 13 | Logos como BLOB | 2 h / 20 min | **RECHAZADA — decisión de gusto** | Ver puerta final |
| 14 | Una base por evento | 4 h / 40 min | **DIFERIDA a v2** | Fuera del radio; contradice el documento técnico |
| 15 | Spikes de OBS / imprenta / latencia | 2 días / — | **DESAFÍO AL USUARIO** | Fuera del contrato de la fase 1 |
| 16 | Consultas legal y de plataforma | 1 semana / — | **DESAFÍO AL USUARIO** | Fuera del contrato de la fase 1 |

## 0E. Interrogación temporal

```
  HORA 1 (cimientos)      ¿Python 3.12 o 3.14?  → E1: 3.12
                          ¿Layout src/ o plano? → src/, ya fijado por §2.2
                          ¿Se puede abrir una ventana Qt en esta máquina? → E8 lo responde

  HORA 2-3 (núcleo)       ¿schema_version dentro o fuera de 001? → fuera, §1.2.4
                          ¿PRAGMA antes o dentro de la transacción? → antes, §1.2.3
                          ¿Los repositorios devuelven Row o dataclass? → dataclass, §1.3.4
                          ¿Quién valida la máquina de estados? → dominio, E5

  HORA 4-5 (integración)  ¿Cuándo se copia el logo a medios/? → al guardar, §1.7.3
                          ¿Qué pasa si el commit falla tras copiar? → se borra, §1.6
                          ¿QApplication antes o después de las migraciones? → antes, E7a
                          ¿El arranque va a auditoria? → no, a aplicacion.log, E7b

  HORA 6+ (pulido)        ¿Cómo se prueba la UI sin pantalla? → QT_QPA_PLATFORM=offscreen
                          ¿Cómo consigue una prueba una base migrada? → fixture (ver fase DX)
                          ¿Qué se etiqueta como v0.1.0? → tras §1.8 completo
```

Con equipo humano, esas seis horas. Con Claude Code y este plan delante, entre 30
y 60 minutos de reloj: las decisiones son idénticas, la escritura es lo que se
comprime.

## 0F. Confirmación de modo

**SELECTIVE EXPANSION**, con el enfoque B + E8 del 0C-bis. El alcance del
contrato es la línea base intocable; las dieciséis ampliaciones del 0D se
decidieron una a una y las dos que quedaron cerca viajan a la puerta final.

## Sección 1 — Arquitectura

### Grafo de dependencias (después de la fase 1)

```
        ┌──────────────────────────────────────────────┐
        │  ui/  (PySide6)                              │
        │  ventana_principal · vistas/ · tema · dialogos│
        └───────┬──────────────────────────┬───────────┘
                │                          │
                ▼                          ▼
        ┌───────────────┐          ┌────────────────┐
        │  servicios/   │          │  i18n/  t()    │◀── ui, servicios,
        │  organizaciones│         └────────────────┘    utilidades
        │  eventos      │
        └───┬───────┬───┘
            │       │
            ▼       ▼
   ┌──────────────┐ ┌──────────────────────┐
   │  dominio/    │ │  persistencia/       │
   │  modelos     │ │  conexion            │
   │  estados     │ │  migraciones         │
   │  (Python     │ │  repo_organizacion   │
   │   puro)      │ │  repo_evento         │
   └──────────────┘ │  repo_auditoria      │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  config/rutas        │◀── todos
                    │  utilidades/*        │
                    └──────────────────────┘

  Reglas verificadas por test_arquitectura.py:
    dominio/ ──X──▶ PySide6, sqlite3
    ui/      ──X──▶ sqlite3
    SQL solo dentro de persistencia/
```

**Hallazgo A1 (medio) — `dominio/` no depende de `persistencia/`, pero
`persistencia/` sí depende de `dominio/`.** Los repositorios devuelven dataclasses
de `dominio/modelos.py`, así que la flecha apunta hacia arriba. Es correcto y es
lo que hace testeable el dominio, pero conviene dejarlo escrito: `dominio/` no
importa nada del proyecto salvo `utilidades/errores`. *Decisión: documentar la
regla en el encabezado de `dominio/modelos.py`. Auto-decidida (P5).*

**Hallazgo A2 (alto) — `conexion.py` no define quién posee la conexión.** El plan
pasa `con` como primer argumento a todo. Funciona en la fase 1, donde hay una
sola conexión y un solo hilo. En la fase 2 hay un `QThread` generando cartones y
en la fase 5 hay escritura por bola: los objetos `sqlite3.Connection` **no son
seguros entre hilos** por defecto (`check_same_thread=True` los rechaza).
*Decisión: se documenta ahora la regla "una conexión por hilo, creada en el hilo
que la usa" en `conexion.py`, y `abrir_conexion` se deja apto para llamarse
varias veces. No se construye un pool: sería abstracción prematura para un
monousuario. Auto-decidida (P5 explícito sobre inteligente).*

### Flujo de datos — alta de organización con logo (los cuatro caminos)

```
  FELIZ
    formulario ─▶ validar ─▶ normalizar PNG (temporal) ─▶ BEGIN
              ─▶ INSERT organizacion ─▶ id ─▶ copiar a medios/<id>/
              ─▶ UPDATE logo_path ─▶ auditoria ─▶ COMMIT ─▶ refrescar lista

  NULO (sin logo)
    logo_origen = None ─▶ se salta normalización y copia ─▶ logo_path = NULL
    ─▶ la vista pinta el marcador de "sin logo". NO es un error.

  VACÍO (nombre = "" o solo espacios)
    validar ─▶ ErrorValidacion(clave="org.error.nombre_vacio")
    ─▶ mensaje junto al campo, foco al campo, sin diálogo modal, sin BEGIN

  ERROR AGUAS ARRIBA
    a) imagen corrupta   ─▶ ErrorImagen ─▶ mensaje traducido, formulario intacto
    b) fallo de INSERT   ─▶ ROLLBACK ─▶ borrar el PNG ya copiado ─▶ ErrorPersistencia
    c) fallo al copiar   ─▶ ROLLBACK ─▶ ErrorPersistencia("no se pudo escribir en medios")
    d) disco lleno       ─▶ OSError ─▶ envuelto en ErrorPersistencia con la ruta
```

**Hallazgo A3 (alto) — hay una ventana entre el `INSERT` y la copia del archivo.**
El `id` de la organización solo existe después del `INSERT`, y la carpeta destino
lo necesita. Si el proceso muere entre el `INSERT` y el `COMMIT`, la transacción
revierte y no queda fila; pero si muere **después** del `COMMIT` y antes de
terminar de copiar, queda una fila con `logo_path` apuntando a un archivo que no
existe. *Decisión: el orden es INSERT → copiar → UPDATE logo_path → COMMIT, todo
dentro de la misma transacción, y la vista tolera `logo_path` inexistente pintando
el marcador de "sin logo" con un aviso en el log. Dos defensas, no una.
Auto-decidida (P1 completitud).*

### Máquina de estados — `evento.estado`

```
                    ┌──────────────┐
      crear ──────▶ │  borrador    │
                    └──────┬───────┘
                           │ preparar (fase 4: hay cartones y rondas)
                           ▼
                    ┌──────────────┐
                    │  preparado   │
                    └──────┬───────┘
                           │ iniciar (fase 5)
                           ▼
                    ┌──────────────┐
                    │  en_curso    │
                    └──────┬───────┘
                           │ finalizar
                           ▼
                    ┌──────────────┐
                    │  finalizado  │  (terminal)
                    └──────────────┘

  Transiciones imposibles y qué las impide:
    finalizado ─▶ borrador     dominio/estados.py + servicio_eventos (E5)
    borrador   ─▶ en_curso     idem (no se salta 'preparado')
    cualquiera ─▶ 'borado'     CHECK en la columna (E4 mantiene los CHECK)
```

En la fase 1 solo se usa la creación en `borrador`. La tabla completa se escribe
igual, porque escribir tres filas más de una tabla de transiciones cuesta nada y
la fase 4 la va a necesitar entera.

### Acoplamiento, escalado, puntos únicos de fallo

- **Acoplamiento nuevo:** `ui/` queda acoplada a `servicios/` y a `i18n/`, no a
  `persistencia/`. Es el acoplamiento que se quería.
- **Qué se rompe primero con 10x carga:** nada en esta fase. Con 100 organizaciones
  y 1.000 eventos, `listar()` sin paginar devuelve 1.000 filas y la vista las pinta
  todas. *Hallazgo A4 (bajo): `repo_evento.listar_por_organizacion` sin límite.
  Decisión: se deja sin paginar en la fase 1 — un operador no tiene mil eventos —
  pero la firma acepta `limite`/`desplazamiento` desde ya para que la fase 2, que
  sí lista cartones por miles, no tenga que cambiar el estilo del módulo.
  Auto-decidida (P1).*
- **Punto único de fallo:** el archivo `bingo.db`. Mitigado parcialmente por la
  guardia de ubicación (§1.2.2) y por WAL. **No mitigado:** la máquina. Va a
  `TODOS.md`.
- **Postura de reversión:** no hay despliegue. Revertir es `git revert` y borrar
  `%LOCALAPPDATA%\Bingo`. Con la política E4e (001 editable hasta el primer evento
  real), revertir un cambio de esquema en esta fase es borrar el `.db` de
  desarrollo. Coste: segundos.

## Sección 2 — Mapa de errores y rescates

```
  MÉTODO / CAMINO                     | QUÉ PUEDE FALLAR                      | CLASE DE EXCEPCIÓN
  ------------------------------------|---------------------------------------|--------------------------
  rutas.asegurar_estructura           | Sin permisos de escritura             | PermissionError
                                      | Disco lleno                           | OSError(ENOSPC)
  conexion.abrir_conexion             | Archivo .db corrupto                  | sqlite3.DatabaseError
                                      | .db bloqueado por otro proceso        | sqlite3.OperationalError
                                      | foreign_keys no quedó en 1            | (comprobación propia)
  migraciones.aplicar_migraciones     | SQL inválido en el archivo            | sqlite3.OperationalError
                                      | Hueco o duplicado en la numeración    | ErrorMigracion
                                      | Archivo mal nombrado                  | ErrorMigracion
                                      | Versión de base mayor que la app      | ErrorMigracion
  repo_*.crear / actualizar           | FK inexistente                        | sqlite3.IntegrityError
                                      | UNIQUE violado                        | sqlite3.IntegrityError
                                      | CHECK violado                         | sqlite3.IntegrityError
  repo_evento.actualizar_plantilla    | JSON inválido                         | json.JSONDecodeError
  servicio_eventos.cambiar_estado     | Transición no permitida               | ErrorTransicionInvalida
  servicio_organizaciones.crear       | Commit falla tras copiar el logo      | ErrorPersistencia
  i18n.cargar                         | JSON del idioma corrupto              | json.JSONDecodeError
  i18n.t                              | Clave inexistente                     | (ninguna: devuelve marca)
                                      | Parámetro faltante en el formato      | (ninguna: devuelve plantilla)
  preferencias.cargar                 | JSON corrupto / ilegible              | json.JSONDecodeError, OSError
  imagenes.validar_y_normalizar       | Archivo inexistente                   | FileNotFoundError
                                      | Formato no soportado                  | PIL.UnidentifiedImageError
                                      | Archivo truncado o corrupto           | OSError (desde verify())
                                      | Bomba de descompresión                | Image.DecompressionBombError
                                      | Mayor de 20 MB                        | ErrorImagen
  tema.aplicar_tema                   | Color almacenado no es #RRGGBB        | (ninguna: cae al defecto)
```

```
  CLASE DE EXCEPCIÓN            | RESCATADA | ACCIÓN DE RESCATE                      | QUÉ VE EL USUARIO
  ------------------------------|-----------|----------------------------------------|---------------------------------
  PermissionError (rutas)       | Sí        | Envolver en ErrorConfiguracion, salir 2| Diálogo: "no se pudo crear la
                                |           |                                        |  carpeta de datos" + ruta
  OSError ENOSPC                | Sí        | ErrorPersistencia con la ruta          | Diálogo con espacio requerido
  sqlite3.DatabaseError         | Sí        | ErrorPersistencia, salir 3             | Diálogo: base ilegible + ruta del
                                |           |                                        |  respaldo más reciente
  sqlite3.OperationalError      | Sí        | busy_timeout reintenta 5 s; luego      | Diálogo: "la base está en uso"
   (locked)                     |           |  ErrorBaseBloqueada                    |
  ErrorMigracion                | Sí        | ROLLBACK, log con número y archivo,    | Diálogo con el número de
                                |           |  salir 4                               |  migración que falló
  sqlite3.IntegrityError        | Sí        | Traducida a ErrorIntegridad **en el    | Mensaje junto al campo:
                                |           |  repositorio**, distinguiendo FK /     |  "ya existe", "no se puede
                                |           |  UNIQUE / CHECK por el texto de sqlite | borrar: tiene N eventos"
  json.JSONDecodeError (idioma) | Sí        | Cae al español, log de advertencia     | Nada; la app sigue en español
  json.JSONDecodeError (prefs)  | Sí        | Valores por defecto + renombrar a      | Nada visible; aviso en el log
                                |           |  .corrupto                             |
  json.JSONDecodeError (plant.) | Sí        | ErrorValidacion antes de escribir      | "la plantilla no es válida"
  ErrorTransicionInvalida       | Sí        | El servicio la lanza, la vista la pinta| "no se puede pasar de X a Y"
  FileNotFoundError (imagen)    | Sí        | ErrorImagen                            | "el archivo ya no existe"
  UnidentifiedImageError        | Sí        | ErrorImagen                            | "formato de imagen no soportado"
  OSError desde verify()        | Sí        | ErrorImagen                            | "la imagen está dañada"
  DecompressionBombError        | Sí        | ErrorImagen                            | "la imagen es demasiado grande"
  Cualquier otra no prevista    | Sí        | Manejador global: log completo +       | Diálogo legible + botón copiar
                                |           |  diálogo, NO se traga                  |  detalle + ruta del log
```

**Hallazgo E1 (alto) — dónde se traduce `sqlite3.IntegrityError`.** El borrador no
lo decía. Si se traduce en el servicio, el servicio tiene que conocer los nombres
de las restricciones, o sea el esquema, o sea SQL filtrado. *Decisión: se traduce
**dentro del repositorio**, que es el único módulo que ya conoce el esquema, y
sale como `ErrorIntegridad` con `clave_i18n` distinta según sea FK, UNIQUE o
CHECK. Ningún `sqlite3.*` cruza la frontera de `persistencia/`. Auto-decidida (P5).
Añade una línea a `test_repo_organizacion.py`: borrar con eventos levanta
`ErrorIntegridad`, no `sqlite3.IntegrityError`.*

**Hallazgo E2 (medio) — el manejador global es lo único que puede usar
`except Exception`.** Y debe. En todo lo demás, capturar `Exception` es un olor.
*Decisión: se escribe la regla en `utilidades/errores.py` y se acepta la única
excepción en `instalar_manejador_global`. Auto-decidida.*

**Sin huecos abiertos.** Cada clase de excepción de la tabla tiene rescate, acción
y texto para el usuario. Ninguna se traga en silencio.

## Sección 3 — Seguridad y modelo de amenazas

Aplicación local, monousuario, sin red, sin autenticación. La superficie es
pequeña pero no es cero.

| # | Amenaza | Probabilidad | Impacto | ¿Mitigada? |
|---|---|---|---|---|
| S1 | Inyección SQL vía nombre de organización o de evento | Baja | Alto | **Sí.** Todo con parámetros `?`; ninguna consulta se construye por concatenación. Se añade a `test_arquitectura.py`: ningún literal SQL contiene `%` ni `.format(` ni f-string en `persistencia/` |
| S2 | Recorrido de rutas al copiar el logo | Baja | Medio | **Sí.** El destino se construye desde `dir_medios_organizacion(id)` con nombre fijo (`logo_principal.png`), nunca desde el nombre del archivo origen |
| S3 | Bomba de descompresión en un logo | Baja | Medio | **Sí.** `Image.MAX_IMAGE_PIXELS` elevado a error (§1.5.4) |
| S4 | Datos personales de compradores (LOPDP) | Alta (fase 4) | Alto | **No en esta fase.** La tabla `comprador` se crea en 001 y guarda nombre, teléfono, cédula y correo. El alcance §9 deja la política de retención pendiente. *Hallazgo S4: la fase 1 fija la forma de los datos que hará fácil o difícil el borrado. Decisión: se añade a `TODOS.md` con prioridad P1 y se anota en el `README` que `comprador` cae bajo LOPDP. Auto-decidida (P1)* |
| S5 | El `.db` se copia a un pendrive con datos de compradores | Media | Alto | **Parcial.** La guardia de ubicación avisa de nube/red, no de pendrive. Va a `TODOS.md` para la fase 5, junto con el cifrado opcional del respaldo |
| S6 | Secretos | — | — | **N/A.** No hay credenciales en la fase 1. La clave HMAC del QR aparece en la fase 3; se anota para que nazca en `%LOCALAPPDATA%` y no en el repositorio |
| S7 | Riesgo de dependencias | Baja | Medio | PySide6, Pillow, reportlab y openpyxl son proyectos maduros con historial de seguridad público. Pillow es el de mayor superficie (analizadores de imagen) y es justo el que recibe entrada de archivo del usuario: por eso `verify()` y el tope de píxeles |
| S8 | Rastro de auditoría | — | — | **Sí**, `auditoria` cubre alta de organización, alta de evento y cambio de estado. La enmienda E7b la deja limpia de ruido de arranque |

## Sección 4 — Flujo de datos y casos borde de interacción

```
  ENTRADA ──▶ VALIDACIÓN ──▶ TRANSFORMA ──▶ PERSISTE ──▶ SALIDA
     │             │             │             │            │
     ▼             ▼             ▼             ▼            ▼
  [None?]     [vacío?]      [excepción?]  [FK rota?]   [obsoleto?]
  [muy largo?][hex mal?]    [OOM imagen?] [UNIQUE?]    [parcial?]
  [tipo mal?] [precio<0?]   [disco?]      [bloqueada?] [codificación?]
```

| Interacción | Caso borde | ¿Cubierto? | Cómo |
|---|---|---|---|
| Guardar organización | Doble clic en Guardar | **Sí** | El botón se deshabilita al entrar en el guardado y se rehabilita en el `finally` |
| | Nombre de 500 caracteres | **Sí** | Tope de 200 en el campo + validación; la base no tiene tope, el formulario sí |
| | Nombre solo con espacios | **Sí** | `strip()` y rechazo |
| | Color pegado como `rojo` | **Sí** | Validación `#RRGGBB`; `QColorDialog` no lo permite, pegar sí |
| | Cerrar la ventana a mitad de guardar | **Sí** | La transacción es síncrona y corta; al volver, o está o no está |
| Cargar logo | Archivo borrado entre elegir y guardar | **Sí** | `FileNotFoundError` → `ErrorImagen` |
| | Archivo de 300 MB | **Sí** | Tope de 20 MB antes de abrir con Pillow |
| | Archivo en un pendrive que se saca | **Sí** | `OSError` → `ErrorPersistencia` |
| Borrar organización | Tiene 3 eventos | **Sí** | Botón deshabilitado con el motivo visible + `ErrorIntegridad` como segunda defensa |
| | Tiene patrones propios | **Sí** | Enmienda §1.3.1: se comprueban las dos FK |
| | Confirmar y que otro proceso la haya borrado | **Sí** | `ErrorIntegridad`/0 filas afectadas → mensaje "ya no existe" + refrescar |
| Lista de eventos | Cero resultados | **Sí** | Estado vacío con llamada a la acción |
| | Sin ninguna organización creada | **Sí** | Estado vacío que lleva a crear una organización primero (E18) |
| | Con organizaciones pero sin eventos | **Sí** | Estado vacío distinto, que es el caso común (E18) |
| | 10.000 resultados | **Parcial** | Hallazgo A4: no pagina en la fase 1, la firma lo admite |
| Cambio de idioma | Con un formulario a medio llenar | **Hueco → cubierto** | *Hallazgo D1 (medio): `retraducir()` reasigna etiquetas, no valores. Decisión: `retraducir()` toca solo textos estáticos (etiquetas, botones, encabezados, marcadores de posición); jamás el contenido de un campo. Se escribe como regla del protocolo en §1.4.3. Auto-decidida (P5)* |
| Arranque | `%LOCALAPPDATA%` no existe | **Sí** | Se crea |
| | Base de una versión futura | **Sí** | Guardia de versión futura |
| | Segunda instancia | **Sí** | `QLockFile` (E13) con detección de bloqueo rancio |

## Sección 5 — Calidad de código

- **Organización y módulos:** siguen el §2.2 del documento técnico al pie. Las
  únicas carpetas nuevas son `utilidades/` y `dominio/estados.py`; ambas se
  justifican arriba.
- **DRY:** la única repetición real que se detecta en el plan es la construcción de
  rutas. Está resuelta por diseño: `config/rutas.py` es el único que las arma, y
  ningún otro módulo llama a `os.environ` ni concatena. *Segunda repetición
  potencial: el patrón "abrir transacción, escribir, auditar" aparece en los dos
  servicios. Con dos usos no se abstrae — sería abstracción prematura. Se revisa
  al tercer uso, en la fase 2. Auto-decidida (P5, evitar abstracción prematura).*
- **Nombres:** en español y por lo que hacen (`aplicar_migraciones`,
  `validar_y_normalizar`, `advertencia_ubicacion_bd`). Consistentes.
- **Sub-ingeniería:** ninguna encontrada tras las enmiendas E2, E5, E7 y E13.
- **Sobre-ingeniería:** se recortaron tres piezas (detección de literales
  visibles E6, `GetDriveTypeW` E3, bloqueo manual de instancia E13).
- **Complejidad ciclomática:** el único candidato a ramificar más de cinco veces es
  `imagenes.validar_y_normalizar` (existe, formato, corrupto, tamaño, píxeles,
  redimensionar, convertir). *Decisión: se parte en `es_imagen_valida` (las
  comprobaciones, que ya está en el plan) y `normalizar` (las transformaciones).
  Auto-decidida (P5).*

## Sección 6 — Revisión de pruebas

```
  NUEVOS FLUJOS DE INTERFAZ
    alta/edición/borrado de organización · alta/edición de evento
    abrir y cerrar el espacio de trabajo de un evento (E14)
    cambio de idioma · filtrado de eventos · abrir carpeta / log

  NUEVOS FLUJOS DE DATOS
    formulario ─▶ servicio ─▶ repositorio ─▶ SQLite
    archivo de imagen ─▶ Pillow ─▶ medios/<id>/
    preferencias.json ─▶ memoria ─▶ preferencias.json
    archivos .sql ─▶ runner ─▶ esquema + schema_version

  NUEVOS CAMINOS DE CÓDIGO
    12 funciones de rutas · 3 de conexión · 3 de migraciones
    7 de repo_organizacion · 7 de repo_evento · 2 de repo_auditoria
    4 de i18n · 2 de preferencias · 4 de fechas · 2 de imágenes
    2 de dominio/estados · 5 de servicios

  TRABAJO ASÍNCRONO / EN SEGUNDO PLANO
    ninguno en la fase 1  ← se anota: el primer QThread llega en la fase 2

  INTEGRACIONES EXTERNAS
    ninguna. Sin red. Solo sistema de archivos y SQLite.

  CAMINOS DE ERROR / RESCATE
    los 16 de la sección 2
```

Cobertura planificada por tipo: **unitarias** para dominio, utilidades, i18n,
fechas, imágenes, estados; **de integración** para repositorios y migraciones
(contra una base SQLite real en `tmp_path`, que es rápida y no necesita dobles);
**de sistema** una sola, `test_arranque.py`, sin ventana.

**La prueba que da confianza para etiquetar a las 2 de la madrugada:**
`test_arranque.py` sobre un `BINGO_HOME` recién creado, que verifica estructura de
carpetas, migración aplicada una sola vez, alta de organización con logo, alta de
evento, y **segundo arranque** que encuentra todo donde quedó. Es el guion de
aceptación del contrato, automatizado.

**La prueba que escribiría un QA hostil:** dejar la base con `schema_version` en
99 y ver si la aplicación arranca igual. Cubierta por la guardia de versión futura.
Segunda: cortar el archivo `001_inicial.sql` a la mitad y comprobar que la
transacción revierte entera y `schema_version` queda vacía. *Hallazgo T1 (alto):
esa segunda no estaba en la tabla de pruebas. Decisión: se añade a
`test_migraciones.py` como "fallo a mitad hace rollback completo". Auto-decidida
(P1). Ya reflejada en la tabla de §1.8.*

**Prueba de caos:** matar el proceso durante `servicio_organizaciones.crear` y
comprobar que no queda ni fila huérfana ni PNG huérfano. Difícil de automatizar de
forma fiable; se deja como comprobación manual del guion de cierre, anotada.

**Riesgo de fragilidad:** `test_arranque.py` depende de Qt con
`QT_QPA_PLATFORM=offscreen` y del reloj (marcas ISO). Se mitiga: sin comparar
marcas de tiempo exactas, solo formato. Ninguna prueba depende de red, orden de
ejecución ni aleatoriedad.

**Pirámide:** ~13 archivos unitarios/integración contra 1 de sistema. Correcta,
no invertida.

## Sección 7 — Rendimiento

Fase sin carga. Aun así:

- **N+1:** el único candidato es pintar la lista de organizaciones con su conteo de
  eventos. *Hallazgo P1 (medio): `contar_eventos` por fila es N+1. Decisión:
  `listar()` devuelve el conteo en la misma consulta con un `LEFT JOIN` y un
  `GROUP BY`. Una consulta, no N+1. Auto-decidida (P1).*
- **Memoria:** la estructura más grande de la fase es una imagen de hasta 20 MB en
  el momento de normalizarla. Se libera con `with Image.open(...)`.
- **Índices:** `evento(organizacion_id)` y `auditoria(evento_id, momento)` añadidos
  en la 001. Las consultas de la fase 1 son todas por clave primaria o por esos
  dos índices.
- **Caché:** el diccionario de idioma se carga una vez por cambio de idioma, no por
  llamada a `t()`. Explícito en §1.4.1.
- **Camino más lento de la fase:** normalizar una imagen grande, del orden de
  cientos de milisegundos. En el hilo de la interfaz. Aceptable para una acción de
  formulario; se anota que en la fase 4, con galerías de premios, esto se va a un
  hilo.

## Sección 8 — Observabilidad

- **Log:** `aplicacion.log` con rotación. Se registran: arranque con versiones y
  rutas, migraciones aplicadas, errores rescatados con contexto completo, clave
  i18n faltante, preferencias corruptas, imagen rechazada, color inválido.
- **Auditoría:** hechos de negocio, limpia de ruido (E7b).
- **Métrica de que funciona:** la aplicación arranca y `schema_version` tiene una
  fila. No hay panel; no hay servidor.
- **Depurar un fallo reportado a tres semanas:** posible si el log conserva
  versión, ruta y traza completa. *Hallazgo O1 (medio): con rotación de 5 MB × 3,
  un evento ruidoso puede tragarse el log del incidente. Decisión: rotación diaria
  además de por tamaño, conservando 14 días. `TimedRotatingFileHandler` con
  `backupCount=14`. Coste: una línea. Auto-decidida (P1).*
- **Herramientas de operación:** el botón "abrir log" y los botones "abrir carpeta"
  de Ajustes son, literalmente, la consola de administración de esta aplicación. Es
  la decisión correcta para un operador único.
- **Runbook:** se escribe en `docs/runbook.md` una página con los cuatro fallos de
  arranque (permisos, base corrupta, migración fallida, instancia duplicada), su
  código de salida y qué hacer. *Hallazgo O2 (medio): no estaba en el plan.
  Decisión: se añade. La va a leer Gabriel, de noche, con el evento empezando.
  Auto-decidida (P1).*

## Sección 9 — Despliegue y salida a producción

No hay despliegue en la fase 1: no hay instalador hasta la fase 5. Lo que sí hay:

- **Seguridad de la migración:** la 001 crea tablas desde cero. Sin bloqueos, sin
  compatibilidad hacia atrás que romper. La política E4e la deja editable hasta el
  primer evento real.
- **Reversión:** `git revert` + borrar `%LOCALAPPDATA%\Bingo`. Segundos.
- **Verificación posterior:** el guion de aceptación de §5 del plan, once puntos.
- **Paridad de entornos:** *Hallazgo Dp1 (medio): se desarrolla y se prueba en la
  misma máquina, que ya tiene Python. El criterio de aceptación número 1 dice
  "arranca en un equipo limpio", y eso no se puede verificar de verdad hasta la
  fase 5, que trae el instalador. Decisión: en la fase 1 se verifica el sustituto
  honesto — entorno virtual nuevo, `BINGO_HOME` nuevo, `pip install -e .` desde
  cero — y se anota que la verificación real es de la fase 5. No se finge que está
  cubierto. Auto-decidida (P6 sesgo a la acción, con la limitación declarada).*
- **Banderas de funcionalidad:** ninguna. No aplica a una aplicación local sin
  usuarios simultáneos.

## Sección 10 — Trayectoria a largo plazo

- **Deuda introducida:** (a) `evento.listar_por_organizacion` sin paginar
  (hallazgo A4, firma preparada); (b) sin política de retención LOPDP (S4, en
  `TODOS.md`); (c) sin plan de segunda máquina (P7, en `TODOS.md`);
  (d) la 001 editable es deuda deliberada con fecha de caducidad explícita (E4e).
- **Dependencia de camino:** la decisión más difícil de deshacer es el esquema de
  la 001, y por eso se le pusieron las cuatro enmiendas E4. La segunda es el
  patrón repositorio: deshacerlo sería reescribir toda la capa de datos. Se
  mantiene porque el §2.1 lo hace principio rector y `test_arquitectura.py` lo
  sostiene.
- **Reversibilidad: 4/5.** Casi todo es reversible borrando el `.db` de
  desarrollo. Lo único que no: el esquema una vez que haya datos reales.
- **Concentración de conocimiento:** un solo desarrollador. Mitigado por
  `CLAUDE.md`, `README.md`, `docs/runbook.md` y el propio plan, que juntos son la
  documentación de arranque.
- **La pregunta del año:** un desarrollador nuevo leyendo esto en 12 meses
  entiende la estructura por `CLAUDE.md` y el §2.2, y entiende **por qué** por las
  enmiendas E1–E13, que dejan escrito no solo qué se decidió sino qué se descartó y
  con qué argumento. Eso es más de lo que tiene la mayoría de los proyectos.
- **Qué viene después:** la fase 2 cuelga de `servicios/`, `persistencia/` y del
  `QStackedWidget`. La arquitectura la soporta sin tocar nada de la fase 1, salvo
  añadir una entrada a la barra lateral y un `repo_carton.py`.

## Sección 11 — Diseño y experiencia de usuario

Se ejecuta en profundidad en la **Fase 2 (revisión de diseño)** más abajo, que es
donde vive el análisis completo de las siete dimensiones. Aquí solo el veredicto
del CEO: el plan tiene tres vistas descritas con estados vacíos, de error y de
guardado explícitos, lo cual ya es más intencionalidad de la que suele tener una
fase de cimientos. La duda estratégica que se pasa a la fase 2 es si aplicar la
marca de la organización a **toda** la interfaz del operador es acierto o error.

---

# FASE 2 — REVISIÓN DE DISEÑO

Alcance de interfaz detectado en la fase 0: **sí** (ventana principal, tres
vistas, formularios, diálogos, sistema de tema). Voces: **subagente Claude**;
Codex no disponible.

## Flujo de usuario — primer arranque en equipo limpio

```
  arranque                    ┌──────────────────────────────┐
     │                        │  ¿hay organizaciones?        │
     ▼                        └───────┬──────────────┬───────┘
  ventana                          NO │              │ SÍ
  principal ───────────────────────────┘              │
     │                                                ▼
     ▼                                   ┌─────────────────────────┐
  ORGANIZACIONES (vacío)                 │ EVENTOS (inicio)        │
  "Aún no hay organizaciones"            │ o el último evento      │
  [+ Crear organización]                 │ abierto (E23)           │
     │                                   └────────┬────────────────┘
     ▼                                            │ clic en una fila
  formulario: nombre* + contacto                  ▼
  ▸ Identidad visual (plegado, opcional)  ┌──────────────────────────┐
     │                                    │ ESPACIO DEL EVENTO       │
     ▼                                    │ cabecera: logo · nombre  │
  guardar ─▶ ÉXITO                        │  fecha · chip de estado  │
     │      "Crear el primer evento" ─────▶ riel: Datos             │
     │                                    │   Cartones     ⏳        │
     ▼                                    │   Plantilla    ⏳        │
  queda seleccionada (E17d)               │   Compradores  ⏳        │
                                          │   Rondas       ⏳        │
                                          └──────────────────────────┘
                                                   │ ◀ Eventos
                                                   ▼  vuelve al inicio

  Callejones sin salida eliminados:
    ✗ "no hay organización activa" justo después de crear una  → E17d
    ✗ fila de evento que no responde al clic                   → E18b
    ✗ ocho campos sin distinguir cuál es obligatorio            → E17
```

## Evaluación por dimensión

| # | Dimensión | Antes | Después de las enmiendas | Qué la movió |
|---|---|---|---|---|
| 1 | Arquitectura de información | 4/10 | **8/10** | E14: dos niveles, eje evento, riel de secciones futuras marcado |
| 2 | Cobertura de estados | 4/10 | **8/10** | E17b, E18, E19: cargando, vacío, vacío-tras-filtro, error, éxito y parcial nombrados vista por vista |
| 3 | Coherencia del recorrido | 5/10 | **8/10** | E17d, E18b, campos obligatorios marcados, siguiente paso ofrecido tras el primer alta |
| 4 | Modelo de "activo" | 3/10 | **8/10** | E14: "evento abierto" sustituye a "organización activa" |
| 5 | Riesgo de interfaz genérica | 4/10 | **7/10** | E17 rejilla de tarjetas, E14b barra de estado con estado real, E19 Ajustes agrupado, tipografía en combo cerrado. **No sube más porque la vista previa del cartón se difiere a la fase 3** (ver decisión de gusto DG-3) |
| 6 | Accesibilidad y ergonomía de operador | 3/10 | **8/10** | E21 atajos, foco y objetivos de pulsación; E15 pseudo-clases y paleta neutra; E16 política de DPI |
| 7 | Deuda de diseño | 3/10 | **8/10** | Los cuatro elementos estructurales (nivel de navegación, eje de alcance, marca en el cromo, ámbito de `retraducir`) resueltos ahora, que es cuando son baratos |

**Media: 3,7/10 → 7,9/10.**

## Hallazgos y decisiones

| # | Hallazgo | Gravedad | Decisión | Principio |
|---|---|---|---|---|
| D1 | Cáscara plana contra fases todas delimitadas por evento | Crítica | **Aceptada** → E14 | P1 completitud |
| D2 | "Organización activa" es el eje equivocado y no tiene relato en la fase 5 | Crítica | **Aceptada** → E14 | P1 |
| D3 | La marca del cliente pinta el cromo del operador | Crítica | **Aceptada como recomendación** → E15, elevada a **desafío al usuario DU-1** | Contradice el §4.1 del alcance: la decide Gabriel |
| D4 | Ninguna vista tiene estado de ERROR pese a existir una jerarquía de errores | Alta | **Aceptada** → E22, tres canales | P1 |
| D5 | Estados faltantes vista por vista (Ajustes: cero de cinco) | Alta | **Aceptada** → E17b, E18, E19 | P1 |
| D6 | El aviso de base en carpeta sincronizada, descartable para siempre | Alta | **Aceptada** → E19b | P1 |
| D7 | Callejones sin salida en el primer arranque | Alta | **Aceptada** → E17d, E18b | P1 |
| D8 | Cero teclado, foco, DPI y pseudo-clases de Qt | Alta | **Aceptada** → E21, E15, E16 | P1 |
| D9 | Medios huérfanos al borrar una organización | Media | **Aceptada** → E17c, mover a `.eliminados/` | P1 |
| D10 | Lista-detalle genérica para una entidad cuya razón de ser es visual | Media-alta | **Aceptada** → E17, rejilla de tarjetas | P5 |
| D11 | Vista previa del cartón junto al formulario de organización | Media-alta | **Diferida a la fase 3** → decisión de gusto **DG-3** | P2: fuera del radio de la fase |
| D12 | Barra de estado con telemetría en lugar de estado | Media | **Aceptada** → E14b | P5 |
| D13 | `tipografia` como texto libre, con el §16.3 abierto | Media | **Aceptada** → combo cerrado + `TODOS.md` | P4 DRY / P5 |
| D14 | Tres colores no siembran ni `plantilla_json` ni `tema_json` | Media | **Aceptada** → E15b, semilla y no paleta final, escrito en el README | P1 |
| D15 | Sin búsqueda ni filtro en ninguna lista | Media | **Aceptada** → filtro en Eventos (E18); en Organizaciones se difiere: son quince filas | P3 pragmático |
| D16 | `retraducir()` no alcanza la segunda ventana de la fase 5 | Media | **Aceptada** → E20, señal de aplicación | P1 |
| D17 | Sin geometría de ventana en preferencias | Baja-media | **Aceptada** → E23 | P2, coste nulo |
| D18 | Textos de la organización monolingües en un producto bilingüe | Baja | **Aceptada la decisión, no el cambio**: una columna por texto; el idioma del **cartón** es propiedad del evento; se revisa en la fase 3. Escrito en el README | P6 sesgo a la acción |

## Estados de interacción — mapa consolidado

| Vista | CARGANDO (G27) | VACÍO | VACÍO-FILTRO | ERROR | ÉXITO | PARCIAL |
|---|---|---|---|---|---|---|
| Organizaciones | n/a | ✔ con acción | ✔ limpiar filtro | Franja + reintento | ✔ y ofrece el paso siguiente | Logo redimensionado · logo ausente en disco |
| Eventos (inicio) | n/a | ✔ dos variantes | ✔ limpiar filtro | Franja + reintento | ✔ | Aviso de nombre duplicado, no bloquea |
| Espacio del evento | n/a | — | — | Franja + reintento | ✔ | Secciones futuras marcadas ⏳ |
| Ajustes | — | — | — | Por fila | ✔ al cambiar idioma | Ruta que resuelve pero no existe |

## Riesgo de interfaz genérica — dónde quedaba y qué se hizo

- **Lista-detalle de administrador** para organizaciones → rejilla de tarjetas con
  logo y muestras de color (E17). Se reconoce a un cliente por su marca, no por una
  fila de texto.
- **Barra de estado como telemetría de desarrollo** → estado real que cambia
  (E14b).
- **Ajustes como diez filas planas** → tres grupos con propósito (E19).
- **Lo que sigue genérico y se acepta:** el formulario de organización no tiene
  vista previa de cartón. Es la carencia más real que queda, y la decisión es
  diferirla a la fase 3, donde nace el motor de render de verdad. Ver **DG-3**.

## Veredictos de la fase de diseño

| Pregunta | Antes | Después |
|---|---|---|
| ¿Arquitectura de información sólida? | NO | **SÍ** (E14) |
| ¿Cobertura de estados completa? | NO | **SÍ** (E17b, E18, E19, E22) |
| ¿Recorrido coherente? | PARCIAL | **SÍ** (E17d, E18b) |
| ¿Deuda de diseño controlada? | NO | **SÍ**, con una excepción declarada: DU-1 sigue abierta y es del usuario |

**Fase 2 completa.** Codex: no disponible. Subagente Claude: 15 hallazgos
(3 críticos, 5 altos, 6 medios, 1 bajo). Consenso: `[subagent-only]` — 14 de 15
aceptados, 1 diferido (D11), 1 elevado a desafío al usuario (D3).

---

# FASE 2.5 — REVISIÓN DE EXPERIENCIA DE DESARROLLO (DX)

Alcance de desarrollador detectado en la fase 0: **sí**. El producto entero de la
fase 1 es una superficie de API interna que consumen las fases 2 a 5, escritas por
la misma persona con un asistente de IA. El riesgo declarado en el contrato de la
fase es literalmente un riesgo de DX: *"si los repositorios quedan mal hechos o el
SQL se riega por la aplicación, lo pagas en la fase 5 con intereses."*
Voces: **subagente Claude**; Codex no disponible.

## El diagnóstico en una frase

El plan especificaba con cuidado las **formas** y callaba las **reglas**. Las
firmas, las capas y la regla del repositorio estaban escritas y se habrían usado
bien desde el primer minuto. La propiedad de la conexión, la propiedad de la
transacción, la traducción de errores del driver, la tabla de verbos, la política
de hilos y las fixtures de prueba no estaban, y cada una cuesta entre cinco y
cuarenta minutos en la fase 2 — más una decisión que las fases 3 a 5 heredan sea
buena o mala.

Comprobación de la ausencia, por búsqueda en el borrador: `conftest` = 0
apariciones, `fixture` = 0, `check_same_thread` = 0, `executemany` = 0,
`QThread` = 1 (una mención de pasada).

## Recorrido del desarrollador — primera hora de la fase 2 (con el borrador)

```
  0:00  git checkout -b feature/fase-2-cartones            ✔ fluido
  0:05  dominio/carton.py                                  ✔ fluido
        └─ el algoritmo está literal en el documento técnico
        └─ FRICCIÓN 1: ¿Carton en modelos.py o en carton.py? dos convenios, ninguna regla
  0:15  repo_carton.py — mapeo fila→modelo copiado a mano
        └─ FRICCIÓN 2: crear() no escala a 10.000; ¿crear_varios? ¿insertar_lote?
  0:25  └─ FRICCIÓN 3: lote necesita repo, nadie lo nombró → se cuela en repo_carton
  0:30  test_repo_carton.py: no hay conftest
        └─ FRICCIÓN 4: cuarta copia divergente de la misma preparación de seis líneas
  0:40  └─ FRICCIÓN 5: PermissionError [WinError 32] en el desmontaje (WAL sin cerrar)
  0:50  servicio_cartones.generar_lote(evento_id, ...) — sin `con`
        └─ FRICCIÓN 6: el contrato de la fase 2 contradice el convenio de la fase 1
  1:00  hace falta el QThread. grep en el repo: cero.
        └─ FRICCIÓN 7: hay un manejador de excepciones de hilo y ningún hilo
  1:10  sqlite3.ProgrammingError: created in a thread can only be used in that thread
        └─ FRICCIÓN 8 ── 35 min en la documentación de SQLite. La más cara, y la que
           la fase 1 estaba en mejor posición de evitar
  1:45  └─ FRICCIÓN 9: §7 prometía modo_sorteo=False. No existe.
  1:50  importa Signal en servicio_cartones → test_arquitectura en rojo
        └─ FRICCIÓN 10: la prueba hace su trabajo, pero avisa DESPUÉS de escribir
  2:00  └─ FRICCIÓN 11: cancelar no puede revertir bloques ya confirmados

  Fin de la "primera hora", que son dos: dominio hecho (la parte sin dependencias
  de la fase 1), repositorio a medias con un nombre dudoso y una segunda tabla
  colada dentro, el servicio bloqueado en hilos, y un fallo latente de Windows.
```

**El patrón: todas las carencias eran reglas, no formas.** Por eso la enmienda
E27 (§1.8 del plan) es la de mayor valor de toda la revisión.

## Evaluación por dimensión

| # | Dimensión | Antes | Después | Qué la movió |
|---|---|---|---|---|
| 1 | Ergonomía de la API | 6/10 | **9/10** | E24 (contradicción resuelta), §1.8.1 hilos, §1.8.2 transacciones, §1.8.3 tabla de verbos, E26 `crear` devuelve el modelo |
| 2 | Contrato de errores | 5/10 | **9/10** | E25: constructor fijado, `campo` en validación, `ErrorDominio`, `ErrorBaseCorrupta`, y un único punto de traducción de `sqlite3` que **conserva qué restricción falló** |
| 3 | Nombres y consistencia | 6/10 | **9/10** | Tabla de verbos, regla singular/plural, `puede_transicionar` generalizada, nombres de servicio predeclarados para las fases 3-5 |
| 4 | Tiempo hasta el primer cambio productivo | 4/10 | **8/10** | Las once fricciones del recorrido, atacadas una a una; `docs/convenciones-codigo.md` como domicilio |
| 5 | Testabilidad | 5/10 | **9/10** | E30: `conftest.py`, `factorias.py`, `synchronous="OFF"`, cierre obligatorio, `estado_limpio`, y la regla de que `raiz_datos()` no cachea |
| 6 | Documentación | 4/10 | **9/10** | `convenciones-codigo.md`, `decisiones.md`, `esquema-actual.sql`, `runbook.md`, política de docstrings, bucle de desarrollo en el README |
| 7 | Puntos de extensión | 7/10 | **9/10** | `registro_vistas.py`, `dir_logs_evento`, cancelación por compensación, y E32 que cierra el modo de fallo silencioso de la política E4e |
| 8 | Bucles de realimentación | 5/10 | **8/10** | E31: carriles rápido y lento, subcarpetas, sin Qt en el conftest raíz, `offscreen` fijado donde de verdad funciona |

**Media: 5,3/10 → 8,8/10.**

## Hallazgos y decisiones (45 hallazgos del subagente)

Aceptados e incorporados: **41**. Diferidos: **3**. Rechazados: **1**.

| Grupo | Hallazgos | Decisión | Dónde quedó |
|---|---|---|---|
| Forma de la API `con`-primero | 1 | **Confirmada, no cambia.** El subagente comparó las cuatro alternativas (funciones con `con`, clase repositorio, conexión ambiental de módulo, unidad de trabajo) y `con`-primero gana para un caso con hilos: el trabajador pasa la suya sin fontanería, y las pruebas pasan una temporal sin dobles. La unidad de trabajo sería la única mejora real, y se puede envolver encima más adelante sin tocar el cuerpo de un solo repositorio | — |
| Conexión por hilo | 2 | **Aceptada (crítica)** | §1.8.1 |
| Contradicción `modo_sorteo` | 3 | **Aceptada** | E24 |
| Propiedad y reentrancia de transacciones | 4, 5 | **Aceptadas (crítica)** | §1.8.2 |
| Inserción masiva y cancelación por compensación | 6 | **Aceptada** | §1.8.3, §1.8.11 |
| `crear` devuelve el modelo | 7 | **Aceptada** | E26 |
| Convenio `_desde_fila` / `_a_parametros` | 8 | **Aceptada** | §1.8.4 |
| Constructor de `ErrorBingo` | 9 | **Aceptada (crítica)** | E25 |
| Traducción de `sqlite3` con `restriccion` estructurada | 10, 11 | **Aceptadas (crítica)** | E25d |
| Quién captura qué, `campo` en validación | 12 | **Aceptada** | E25b, §1.8.5 |
| `ErrorNoEncontrado` | 13 | **Aceptada** | E25, §1.8.5 |
| Prueba de que toda `clave_i18n` existe | 14 | **Aceptada** | `test_arquitectura.py` |
| `ErrorTransicionInvalida` fuera de validación | 15 | **Aceptada** | E25c |
| Tabla de verbos | 16 | **Aceptada** | §1.8.3 |
| `puede_transicionar` genérica | 17 | **Aceptada** | §1.8.11 |
| `dominio/dinero.py` | 18 | **Aceptada** | E28 |
| Singular/plural y nombres predeclarados | 19, 20 | **Aceptadas** | §1.8.3 |
| `dir_logs_evento` | 21 | **Aceptada** | §1.8.11 |
| Catorce huecos de la fase 2 | 22 | **Aceptados** | §1.8 completa |
| `ui/tarea.py` + callbacks de progreso | 23 | **Aceptada** | E29 |
| `conftest.py` y fábricas | 24, 26, 28, 29, 43 | **Aceptadas** | E30 |
| `raiz_datos()` no cachea | 25 | **Aceptada (alta)** | E30 |
| `":memory:"` y la aserción de WAL | 27 | **Aceptada** | §1.8.1 |
| Pruebas del contrato de transacción | 30 | **Aceptada** | `test_conexion.py` |
| `principal(argv)` y `forzar` explícito | 31 | **Aceptada** | §1.8.11 |
| `.execute(` fuera de `persistencia/` | 32 | **Aceptada** | `test_arquitectura.py` |
| `convenciones-codigo.md` + `CLAUDE.md` | 33 | **Aceptada (crítica)** | E27 |
| Guardia de hash de migración | 34 | **Aceptada** | E32 |
| `decisiones.md` | 35 | **Aceptada** | §1.8.11 |
| Bucle de desarrollo en el README | 36 | **Aceptada** | §1.8.11 |
| Política de docstrings | 37 | **Aceptada** | §1.8.11 |
| `esquema-actual.sql` | 38 | **Aceptada** | §1.8.11 |
| `registro_vistas.py` | 39 | **Aceptada** | §1.8.11 |
| `QT_QPA_PLATFORM` fijado de verdad | 40 | **Aceptada (alta)** | E30 |
| Marcadores y carriles de prueba | 41, 42 | **Aceptadas** | E31 |
| `ruff` en el guardado / pre-commit | 44 | **Aceptada a medias**: línea en el README emparejando `ruff check --fix .` con `ruff format .`. `.pre-commit-config.yaml` se difiere: es una dependencia más para empaquetar y hay una sola persona | README |
| Integración continua | 45 | **Diferida a `TODOS.md`.** No hay repositorio remoto todavía; un workflow de GitHub Actions no tiene dónde correr. Se anota para cuando se cree el remoto, con `ruff` + `pytest -m "not lento"` | `TODOS.md` |

## Veredictos de la fase DX

| Pregunta | Antes | Después |
|---|---|---|
| ¿Superficie de API bien formada? | PARCIAL | **SÍ** — la forma ya era correcta; ahora las reglas están escritas |
| ¿Contrato de errores claro? | NO | **SÍ** — constructor fijado, un único traductor, `restriccion` conservada para la fase 2 |
| ¿Testabilidad suficiente? | NO | **SÍ** — `conftest` autouse, plantilla de sesión, cierre obligatorio, sin caché en `raiz_datos()` |
| ¿Traspaso a la fase 2 limpio? | PARCIAL | **SÍ** — las once fricciones del recorrido tienen dueño; queda la de menor coste (dónde vive cada entidad), resuelta por regla en §1.8.11 |

**Fase 2.5 completa.** Codex: no disponible. Subagente Claude: 45 hallazgos
(4 críticos, 11 altos, 21 medios, 9 bajos). Consenso: `[subagent-only]` — 41
aceptados, 3 diferidos, 1 confirmado sin cambio.

---

# Comprobación empírica de las afirmaciones técnicas del plan

Cuatro afirmaciones del plan sobre SQLite se verificaron ejecutándolas en esta
máquina, con el mismo `sqlite3` de Python 3.14 que se va a usar. No se aceptaron
por memoria ni por analogía.

| Afirmación del plan | Sección | Resultado |
|---|---|---|
| `PRAGMA foreign_keys` dentro de una transacción abierta es un no-op **silencioso** | §1.2.3 | **Confirmada.** Tras `BEGIN IMMEDIATE` + `PRAGMA foreign_keys=ON`, la relectura devuelve `0`. Fuera de transacción devuelve `1`. Sin excepción, sin aviso |
| `PRAGMA journal_mode` falla dentro de una transacción | §1.2.3 | **Confirmada.** `sqlite3.OperationalError: cannot change out of wal mode from within a transaction` |
| El DDL de SQLite es transaccional, así que una migración a medias revierte entera | §1.2.4 | **Confirmada.** `CREATE TABLE` seguido de `ROLLBACK` no deja rastro en `sqlite_master` |
| `transaccion()` anidada revienta y hay que envolverla | §1.8.2 | **Confirmada.** `sqlite3.OperationalError: cannot start a transaction within a transaction`. Es exactamente el error crudo que la enmienda E27 obliga a traducir a `ErrorPersistencia` con mensaje claro |

Y dos del entorno, verificadas en la fase 0:

| Afirmación | Resultado |
|---|---|
| PySide6 instala sobre el Python de esta máquina | **Confirmada.** 6.11.2, rueda `cp310-abi3-win_amd64`, sin compilación |
| La paleta por defecto del documento técnico pasa WCAG AA | **Refutada.** `#e94560` sobre `#1a1a2e` = **4,46:1** y blanco sobre `#e94560` = **3,83:1**; el umbral AA es 4,5:1. Es la base fáctica de la enmienda E15 y del desafío DU-1 |

---

# Registro de decisiones automáticas

| # | Fase | Decisión | Clase | Principio | Razón | Descartado |
|---|---|---|---|---|---|---|
| 1 | 0 | Modo SELECTIVE EXPANSION | Mecánica | — | Fase greenfield sobre un contrato ya cerrado: el contrato es la línea base y las ampliaciones se ofrecen una a una | EXPANSION (el contrato ya está cerrado), REDUCTION (nada sobra) |
| 2 | 0 | Enfoque B (capas de abajo hacia arriba) + esqueleto que camina | Mecánica | P1 | El riesgo declarado de la fase es que los cimientos queden mal; B es el único orden que prueba cada capa sin abrir ventana | A (vertical), C (interfaz primero) |
| 3 | CEO | E1: desarrollar sobre Python 3.12, no 3.14 | **Gusto** | P3 | 3.12 es el piso que se promete y la versión con más kilometraje en PyInstaller e Inno Setup | Desarrollar en 3.14, que es lo instalado |
| 4 | CEO | E2: `synchronous=FULL` por defecto | Mecánica | P1 | El contrato lo manda; la justificación de rendimiento del borrador era falsa y sin medir | `NORMAL` por defecto |
| 5 | CEO | E3: quitar `GetDriveTypeW`, dejar comparación de cadenas y ruta UNC | Mecánica | P3, P5 | Código Win32 sin prueba posible para cubrir lo que ya cubre la comprobación de UNC | Mantener la llamada Win32 |
| 6 | CEO | E4a: retirar `UNIQUE (organizacion_id, nombre)` en `evento` | Mecánica | P5 | Una organización repite nombre de evento cada año (el argumento técnico del borrador era falso, ver G5) | Mantener el UNIQUE |
| 7 | CEO | E4b: dinero en centavos enteros | Mecánica | P1 | Alimenta un comprobante firmado; coma flotante da números mal al sumar mil cartones | `REAL`, como dice el §3.1 |
| 8 | CEO | E4c: añadir columnas de texto legal a `organizacion` | Mecánica | P1 | El alcance §4.1 las exige y el §3.1 no las tiene: si la tesis es "esquema completo", que lo sea | Dejarlas para la fase 3 |
| 9 | CEO | E4d: `evento.hora` separada de `evento.fecha` | Mecánica | P1 | El §5.1 imprime "fecha y hora" en el cartón | Solo fecha |
| 10 | CEO | E4e: la 001 es editable hasta el primer evento real | Mecánica | P6 | Descongela la fase 4, cuyo modelado de patrones el §16 deja abierto | Congelar la 001 desde ya |
| 11 | CEO | Mantener los `CHECK` de `ronda` | Mecánica | P1 | Sus valores están cerrados (§6.1 y §4.5); lo abierto en §16 afecta a `patron`, no a esas columnas | Quitarlos, como sugería la voz externa |
| 12 | CEO | E5: la máquina de estados va al dominio, no al repositorio | Mecánica | P5 | Lógica de negocio dentro de la capa de SQL es la erosión que vuelve decorativa la regla del repositorio | Dejarla en `repo_evento` |
| 13 | CEO | E6: recortar `test_arquitectura.py` a dos comprobaciones fiables | Mecánica | P3, P5 | La detección de "literales visibles" es una máquina de falsos positivos que acaba desactivando también las comprobaciones buenas | Mantener las tres |
| 14 | CEO | E7a: `QApplication` en la primera línea | Mecánica | P1 | Un `QMessageBox` sin `QApplication` aborta: el diálogo de error habría sido un choque sin mensaje | Dejarlo al final |
| 15 | CEO | E7b: el arranque no va a `auditoria` | Mecánica | P5 | `auditoria` alimenta el acta que se entrega a la organización; el ruido de ciclo de vida la degrada | Registrar cada arranque |
| 16 | CEO | E8: esqueleto que camina en la primera hora | Mecánica | P2 | Mueve todo el riesgo ambiental de la última hora a la primera, por el precio de una hora | Dejar la prueba de humo al final |
| 17 | CEO | E13: instancia única con `QLockFile` | Mecánica | P4 | Peldaño 3 de la escalera de reutilización: la plataforma ya lo trae y además detecta bloqueos rancios | `msvcrt.locking` a mano |
| 18 | CEO | Logos en disco, no como BLOB | **Gusto** | P3 | `medios/` también guardará imágenes de premios y fondos de escena; meterlos en el `.db` infla lo que se respalda en caliente | BLOB en la base |
| 19 | Diseño | E14: dos niveles de navegación, eje evento | Mecánica | P1 | Las fases 2 a 5 están todas delimitadas por evento; la organización no delimita nada | Cáscara plana de tres vistas |
| 20 | Diseño | E15: la marca no pinta el cromo del operador | **DESAFÍO AL USUARIO (DU-1)** | — | Contradice una frase explícita del §4.1 del alcance: la decide Gabriel | — |
| 21 | Diseño | E17: rejilla de tarjetas para organizaciones | Mecánica | P5 | Quince filas cuya razón de ser es la identidad visual; una lista de texto es la forma equivocada | Lista-detalle |
| 22 | Diseño | Vista previa del cartón en el formulario | **Gusto (DG-3)** | P2 | Duplica el motor de render de la fase 3 | Hacerla ya con Qt |
| 23 | Diseño | E19b: el aviso de ubicación vive en Ajustes y no se descarta | Mecánica | P1 | Riesgo calificado de crítico que el borrador dejaba silenciable para siempre | Solo diálogo descartable |
| 24 | Diseño | E21, E22: atajos, foco y tres canales de error | Mecánica | P1 | La aplicación se opera en vivo; un modal encima de una transmisión es un incidente | Un solo canal modal |
| 25 | Diseño | E20: la retraducción es de aplicación, no de ventana | Mecánica | P1 | La fase 5 abre una segunda ventana de nivel superior a la que un registro de la ventana principal no llega | Registro en `ventana_principal` |
| 26 | DX | Confirmar `con`-primero frente a clase, ambiente y unidad de trabajo | Mecánica | P5 | El trabajador de la fase 2 pasa su propia conexión sin fontanería; las pruebas pasan una temporal sin dobles | Clase repositorio, conexión ambiental (peligrosa con hilos), unidad de trabajo (más maquinaria de la necesaria hoy) |
| 27 | DX | E27: `docs/convenciones-codigo.md` + reglas en `CLAUDE.md` | Mecánica | P1 | Un convenio que no está en `CLAUDE.md` no existe: el plan se archiva al etiquetar v0.1.0 | Dejar las reglas en el plan |
| 28 | DX | §1.8.1: una conexión por hilo, `check_same_thread=True` | Mecánica | P1 | Es el fallo de 35 minutos que la fase 1 estaba en mejor posición de evitar | No decir nada |
| 29 | DX | §1.8.2: los repositorios no abren transacciones; `transaccion()` no es reentrante | Mecánica | P1 | La transacción por bola de la fase 5 reventaría si un repositorio abriera la suya | No decir nada |
| 30 | DX | E25d: un único traductor de `sqlite3` que conserva `restriccion` | Mecánica | P1 | La fase 2 necesita distinguir `UNIQUE(evento_id, firma)` de las demás para su bucle de reintento | Envolver a ciegas |
| 31 | DX | E28: `dominio/dinero.py` | Mecánica | P4 | La conversión estaba en la vista y se habría reimplementado tres veces, sobre un comprobante | Convertir en cada vista |
| 32 | DX | E29: `ui/tarea.py` sin consumidor en la fase 1 | Mecánica | P2 | Las fases 2, 3 y 5 lo necesitan; si no está, lo inventan tres veces | Que lo escriba la fase 2 |
| 33 | DX | E30: `conftest.py` con `bingo_home` autouse | Mecánica | P1 | Hace estructuralmente imposible que una prueba escriba en el `%LOCALAPPDATA%` real | Que cada archivo se lo monte |
| 34 | DX | E32: hash del contenido de la migración en `schema_version` | Mecánica | P1 | Cierra el modo de fallo silencioso de la política E4e | Confiar en el número de versión |
| 35 | DX | Integración continua diferida | Mecánica | P3 | No hay repositorio remoto donde correr un workflow | Escribirlo ya |
| 36 | DX | `.pre-commit-config.yaml` diferido, línea en el README en su lugar | Mecánica | P3 | Una dependencia más que empaquetar, para una sola persona | Instalarlo |

---

# Salidas obligatorias de la revisión

## "NO está en el alcance de la fase 1"

Trabajo considerado y explícitamente diferido, con su razón en una línea.

| Diferido | Razón | Va a |
|---|---|---|
| Carga de los patrones del sistema en la tabla `patron` | El catálogo y el editor son de la fase 4; la tabla existe pero cargarla ahora es adivinar el modelado que el §16.1 deja abierto | `TODOS.md` |
| Vista previa del cartón junto al formulario de organización | Duplicaría el motor de render que nace en la fase 3 | `TODOS.md` (DG-3) |
| Una base de datos por evento | Contradice el `datos/bingo.db` único del documento técnico; organizaciones y patrones son transversales | `TODOS.md` (v2) |
| Logos como BLOB en la base | `medios/` guardará también imágenes de premios y fondos de escena, que son megabytes | Rechazado, con argumento en 0C-bis |
| Cifrado del respaldo | El `.zip` con datos de compradores es de la fase 5 | `TODOS.md` |
| Integración continua | No hay repositorio remoto donde correr un workflow | `TODOS.md` |
| `.pre-commit-config.yaml` | Una dependencia más que empaquetar para una sola persona; basta la línea del README | `TODOS.md` |
| Filtro en la vista de organizaciones | Quince filas en toda la vida de la aplicación | `TODOS.md` |
| Textos de organización por idioma | Hoy una columna por texto; se revisa en la fase 3, con el editor de plantilla delante | `TODOS.md` |
| Paginación real de eventos | Un operador no tiene mil eventos; la **firma** admite `limite`/`desplazamiento` desde ya para no cambiar el estilo del módulo en la fase 2 | Firma preparada |
| Plan de segunda máquina | El respaldo restaurable es de la fase 5 | `TODOS.md` (P2) |
| Consulta legal, políticas de plataforma, spikes de OBS, imprenta y latencia | Fuera del contrato de la fase 1, pero **sin dueño en ninguna fase** y con capacidad de invalidar el proyecto entero | `TODOS.md` (P1) + desafío **DU-2** |

## "Qué ya existe"

| Sub-problema | Qué existe | ¿Se reutiliza? |
|---|---|---|
| Código propio del proyecto | **Nada.** Repositorio vacío: cuatro `.md` y ningún `.git` | N/A |
| Esquema de base de datos | El §3.1 del documento técnico lo trae escrito y completo | **Sí**, se copia con cinco enmiendas justificadas (E4a-E4e) |
| Algoritmo de generación de cartones | El §4.2 del documento técnico lo trae en Python | Sí, pero es de la fase 2 |
| Estructura de carpetas | El §2.2 del documento técnico | **Sí**, al pie de la letra |
| Convenciones de código | El §14 del documento técnico | **Sí**, y se amplían en `CLAUDE.md` y `docs/convenciones-codigo.md` |
| Migraciones | `alembic` (atado a SQLAlchemy, y aquí no hay ORM), `yoyo-migrations` | **No**, propio en ~80 líneas |
| Rutas de datos por plataforma | `platformdirs` | **No**, quince líneas y una dependencia menos que empaquetar |
| i18n | `gettext` (biblioteca estándar), Qt Linguist | **No**, JSON como fija el §9; las mismas claves se referencian desde `plantilla_json` y `tema_json` |
| Preferencias | `QSettings` | **No**, escribe en el registro de Windows y no viaja con el respaldo |
| Instancia única | `QLockFile` de Qt | **Sí** (E13), y sustituye al `msvcrt` a mano del borrador |
| Validación de imágenes | Pillow | **Sí**, ya es dependencia |
| Log con rotación | `logging.handlers` | **Sí**, biblioteca estándar |

## Delta respecto al estado soñado

Esta fase deja el **100% del andamiaje y el 0% del producto**, que es exactamente
lo que pide el contrato. Respecto al ideal a doce meses (v1.0 instalada, varios
eventos corridos, actas entregadas, la organización repite), lo que queda fuera y
sigue sin dueño en ninguna fase es:

1. Un segundo equipo capaz de retomar un evento. El alcance §8 acepta el equipo
   único como punto de fallo y ninguna fase lo mitiga.
2. Un PDF validado por una imprenta real.
3. Una política de retención de datos de compradores conforme a la LOPDP.
4. Las dos preguntas existenciales: legalidad de premios en efectivo en Ecuador y
   políticas de Facebook y YouTube.

Los cuatro están en `TODOS.md`. Los cuatro se pueden empezar hoy, en paralelo con
la fase 1, sin tocar una línea de código.

## Registro de modos de fallo

| Camino | Modo de fallo | ¿Rescatado? | ¿Probado? | ¿Qué ve el usuario? | ¿Registrado? |
|---|---|---|---|---|---|
| `asegurar_estructura` | Sin permisos / disco lleno | Sí | Sí | Diálogo con la ruta | Sí |
| `abrir_conexion` | Base corrupta | Sí (`ErrorBaseCorrupta`) | Sí | Diálogo + ruta del último respaldo | Sí |
| `abrir_conexion` | Base bloqueada | Sí (`busy_timeout` y luego `ErrorBaseBloqueada`) | Sí | Franja no modal con reintento | Sí |
| `abrir_conexion` | `foreign_keys` no quedó en 1 | Sí (comprobación propia) | Sí | Diálogo | Sí |
| `aplicar_migraciones` | SQL inválido / hueco / duplicado / versión futura | Sí | Sí | Diálogo con el número de migración | Sí |
| `aplicar_migraciones` | **Migración ya aplicada editada** (política E4e) | Sí (guardia de hash, E32) | Sí | Aviso: "base de desarrollo obsoleta, bórrala" | Sí |
| Repositorios | FK / UNIQUE / CHECK / NOT NULL | Sí (`ErrorIntegridad` con `tipo` y `restriccion`) | Sí | Mensaje junto al campo | Sí |
| `servicio_organizaciones.crear` | Commit falla tras copiar el logo | Sí (rollback + borrar el PNG) | Manual (prueba de caos) | Franja no modal | Sí |
| `servicio_organizaciones.eliminar` | Medios huérfanos | Sí (mover a `.eliminados/`, E17c) | Sí | — | Sí |
| `servicio_eventos.cambiar_estado` | Transición imposible | Sí (`ErrorTransicionInvalida`) | Sí | Franja no modal | Sí |
| `i18n.t` | Clave inexistente | Sí (devuelve la clave marcada) | Sí | Texto entre marcas visibles | Sí |
| `i18n.t` | Parámetro faltante en el formato | Sí (devuelve la plantilla) | Sí | Plantilla cruda, sin choque | Sí |
| `preferencias.cargar` | JSON corrupto | Sí (defectos + renombrar) | Sí | Nada; arranca en español | Sí |
| `imagenes.validar_y_normalizar` | Corrupta / formato / tamaño / bomba | Sí (`ErrorImagen`) | Sí | Mensaje traducido | Sí |
| `tema` | Color almacenado inválido | Sí (cae al defecto) | Sí | Color por defecto | Sí |
| Arranque | Segunda instancia | Sí (`QLockFile`) | Sí | Aviso y salida | Sí |
| Arranque | Bloqueo rancio tras cierre brusco | Sí (`QLockFile` detecta el PID muerto) | Sí | Arranca normalmente | Sí |
| Cualquiera | Excepción no prevista | Sí (manejador global, único `except Exception` permitido) | Sí | Diálogo legible + copiar detalle + ruta del log | Sí |

**Cero filas con RESCATADO=No.** Cero filas con "el usuario no ve nada" donde
debería ver algo. La única fila que no está cubierta por prueba automatizada es la
de caos (matar el proceso a mitad de `servicio_organizaciones.crear`), que queda
como comprobación manual del guion de cierre y así está declarado, no fingido.

---

# FASE 3 — REVISIÓN DE INGENIERÍA (corre la última, sobre el plan ya enmendado)

Voces: **subagente Claude**; Codex no disponible (`[subagent-only]`).
52 hallazgos: 4 críticos, 14 altos, 25 medios, 9 bajos.
**Aceptados: 46. Cortes de alcance aplicados: 6. Diferido: 1 (decisión de gusto).**

Esta fase corre la última a propósito: es la puerta de embarque, y tiene que
revisar el plan **con las enmiendas de las tres fases anteriores ya dentro**. Y
valió la pena: encontró un defecto crítico que ninguna de las otras vio, y revirtió
una decisión que yo había tomado mal.

## Lo que se verificó ejecutándolo, no razonándolo

| Afirmación | Resultado |
|---|---|
| `executescript()` emite un `COMMIT` implícito y destruye el `BEGIN` abierto | **Confirmada.** `in_transaction` pasa de `True` a `False`; el `COMMIT` posterior lanza `cannot commit - no transaction is active`. Con un `.sql` que falla a mitad, **el esquema a medias sobrevive** al `ROLLBACK`. Ver G1 |
| Meter `BEGIN`/`COMMIT` dentro del script arregla la atomicidad | **Confirmada.** Con el `BEGIN` dentro, un fallo a mitad revierte entero |
| `verify()` de Pillow no rechaza datos de imagen truncados | **Confirmada para JPEG** (pasa las tres truncaciones probadas; `load()` las rechaza todas). **Refutada para PNG truncado por la cola**, que sí caza `verify()` por los CRC de chunk. La enmienda G13 recoge el matiz, no la versión gruesa |
| `sqlite3` con `isolation_level=None` y `BEGIN IMMEDIATE` se comporta como describe el plan | **Confirmada** (ya verificado en la fase CEO) |

## Los cuatro críticos

| # | Hallazgo | Enmienda |
|---|---|---|
| 1 | **La migración no era atómica.** El mecanismo obvio (`BEGIN` + `executescript`) descarta la transacción en silencio y deja esquema a medias sin fila en `schema_version`. Y `test_migraciones.py` afirmaba cubrir exactamente ese caso | **G1** |
| 2 | **`crear()` tenía tres contratos distintos** en el mismo documento: `-> Organizacion` en §1.3.1 con un párrafo explicando por qué `-> int` está mal, `-> int` en §1.3.2, `-> int` en §1.6. Y §1.8.4 dice que el primer repositorio es la plantilla que copian los otros siete | **G7** |
| 3 | **Las fixtures no podían arrancar.** `plantilla_bd` de sesión dependiendo de `bingo_home` autouse de función: `ScopeMismatch` en la recolección. Y si se "arreglaba" al revés, migraba dentro del `%LOCALAPPDATA%` real — justo lo que `bingo_home` existe para impedir | **G16** |
| 4 | **`ronda.estado` congelado tras un `CHECK`.** Ver abajo: es una reversión de una decisión mía | **G4** |

## Una decisión revertida

En las secciones 1 y 2 de esta misma revisión descarté el consejo de la voz CEO de
quitar el `CHECK` de `ronda.estado`, con el argumento de que sus valores estaban
cerrados en el §6.1 del documento técnico. **El argumento era falso**, y la prueba
estaba en el mismo documento que cité: la decisión pendiente número 2 del §16 dice
que qué hacer si nadie reclama el premio *"impacta la máquina de estados de la
sección 6.1"*. Declaré cerrada una máquina de estados que el documento declara
abierta, y la iba a congelar detrás de la única restricción que SQLite no puede
alterar sin reconstruir la tabla. Corregido en **G4**.

## Contradicciones internas encontradas

| Contradicción | Enmienda |
|---|---|
| §1.1 creaba el entorno con Python 3.14.2 mientras E1 lo prohibía tres páginas antes | G6 |
| §7 prometía a la fase 2 el `QStackedWidget` plano que E14 había eliminado | G21 |
| La tabla de riesgos mitigaba con la prueba de literales que E6 había borrado | G22 |
| La guardia de hash (E32) necesitaba una columna que §1.2.4 nunca definió | G15 (se corta) |
| `puede_transicionar` publicada con dos firmas | G25 |
| §1.8.1 hablaba de "saltarse la comprobación de WAL" que no existía en ningún sitio | G3b |
| El combo de tipografías ofrecía fuentes de una carpeta `recursos/` vacía | G24 |
| El orden de copiar el logo era imposible en el alta: la carpeta usa un `id` que no existe hasta el `INSERT` | G8 |
| Los criterios de aceptación decían "las tres vistas" tras E14/E18 haber creado cuatro superficies | G23 |

## Errores fácticos sobre la tecnología

| Afirmación del borrador | Realidad | Enmienda |
|---|---|---|
| "Este orden de PRAGMA no es cosmético" | Entre `journal_mode`, `foreign_keys` y `synchronous` **sí** lo es. La única restricción real es `busy_timeout` **antes** de `journal_mode=WAL`, y el borrador lo ponía después | G2 |
| `threading.excepthook` cubre `QThread` | **No.** Solo cubre `threading.Thread`. Un `QThread` va a `sys.excepthook` **en el hilo trabajador**, y el manejador habría intentado construir un `QMessageBox` fuera del hilo de la interfaz | G11 |
| `verify()` basta para rechazar una imagen dañada | No para JPEG (medido) | G13 |
| Pillow "solo emite un aviso" ante una bomba de descompresión | Lanza `DecompressionBombError` por encima del doble del límite | G13b |
| `importlib.resources` mitiga el riesgo de empaquetado | Ni una cosa ni la otra: en `onedir` `__file__` funciona, y `importlib.resources` no encuentra lo que nunca se empaquetó. Lo que falta de verdad es `package-data` | G14 |
| "En SQLite no se puede quitar un UNIQUE sin reconstruir la tabla" | Solo si es una restricción de tabla; como `CREATE UNIQUE INDEX` es un `DROP INDEX` | G5 |

## Cortes de alcance aplicados

El plan había crecido del contrato de seis tareas a unos 30 archivos de código.
Se cortan seis cosas, ninguna de ellas del contrato:

| Cortado | Por qué |
|---|---|
| Guardia de hash de migración (E32) | Duplicaba `--reiniciar-datos`, que son tres líneas y no toca el esquema. **G15** |
| Prueba de instantánea del esquema | Choca con E4e: falla en cada edición intencionada de la 001 durante toda la fase. **G31** |
| Estados CARGANDO | Esqueletos de carga para listas de 5 a 15 filas de un SQLite local. **G27** |
| Bandera `modo_vivo` | Sin consumidor hasta la fase 5, y su semántica depende de una interfaz que no existe. **G28** |
| `medios/.eliminados/` y confirmación escribiendo el nombre | Borrar ya está bloqueado siempre que haya algo que perder. **G29** |
| Registro central de atajos | Cinco líneas de diccionario hacen lo mismo para cuatro superficies. **G30** |

**No cortado, y marcado como decisión de gusto:** `ui/tarea.py`. La voz DX pedía
escribirlo ahora (evita tres reinvenciones y es lo que el asistente copia); la voz
de ingeniería pedía cortarlo (diseño contra requisitos imaginados, sin consumidor
en la fase). Las dos tienen razón. Ver **DG-1** en la puerta.

## Lo que faltaba probar

El diagnóstico más incómodo: había 22 archivos de prueba, y las seis cosas con más
probabilidad de romperse no tenían ninguno. Añadidos:

- `test_servicio_organizaciones.py` — el único punto de consistencia disco/base de
  la fase, señalado por su nombre en el §1.6 y sin una sola prueba.
- Atomicidad real de migración con un `002_falla.sql` (G1).
- El camino real de `sys.excepthook` en un *slot* y su variante en hilo (G11, G12).
- `test_i18n_retraduccion.py` con una segunda ventana destruida (G18) — la
  justificación entera de E20, sin prueba.
- `test_concurrencia.py`: lector no bloqueado bajo WAL, escritor agotando
  `busy_timeout`, conexión usada desde otro hilo (G16).
- `test_persistencia_degradada.py`: solo lectura y disco lleno (G33).

## Veredictos

| Pregunta | Antes de esta fase | Después |
|---|---|---|
| ¿Técnicamente correcto? | NO | **SÍ** — los seis errores fácticos corregidos, cuatro de ellos verificados ejecutándolos |
| ¿Internamente consistente? | NO | **SÍ** — nueve contradicciones cerradas |
| ¿Implementable sin ambigüedad? | NO | **SÍ** — marca i18n, política de `format_map`, vida del registro de retraducción, conjunto de `synchronous` y constructor de `ErrorIntegridad`, todos fijados |
| ¿Orden de construcción sólido? | PARCIAL | **SÍ** — G20 escribe el orden real, que no es el de los números |
| ¿Modos de fallo cubiertos? | PARCIAL | **SÍ** — migración parcial, solo lectura, disco lleno y el orden del alta, cerrados |
| ¿Plan de pruebas del tamaño correcto? | NO | **SÍ** — seis pruebas nuevas donde estaba el riesgo, dos quitadas donde no |

**Fase 3 completa.** Con esto se cierra la tubería: CEO → Diseño → DX → Ingeniería.
