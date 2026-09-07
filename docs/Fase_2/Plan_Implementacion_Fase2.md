<!-- /autoplan restore point: C:\Users\Gabo\.gstack\projects\Bingo_App\main-autoplan-restore-20260904-231614.md -->

# Plan de implementación — FASE 2: Generación de cartones

**Generado por:** `/autoplan` (gstack) — modo SELECTIVE EXPANSION, sin implementar código.
**Fecha:** 2026-09-04 · **Rama:** `main` · **Commit base:** `7896482`
**Fuente de alcance:** `docs/Fase_2/Contrato_Fase2.md`, `docs/Plan_Fases_Bingo.md` (§FASE 2),
`docs/Documento_Tecnico.md` (§3.1, §4.1-4.3), `docs/convenciones-codigo.md`.
**No implementar nada a partir de este documento sin pasar por el gate final** (última
sección). Este archivo es el *plan*, no el código.

---

## 0. Auditoría previa del sistema (pre-review system audit)

- **`git log --oneline -30`**: rama `main` al día con `dev`; Fase 1 cerrada y etiquetable
  en `v0.1.0` (commits `5ab193d`, `2be51c9`, `6804bb7`, `3927ea3`, `7896482`). Sin trabajo a
  medias (`git stash list` vacío).
- **`git diff main --stat`**: N/A — esta sesión no ha tocado código, solo lee.
- **TODO/FIXME/HACK**: no hay grep global de esos marcadores en `src/`; el proyecto usa
  `docs/decisiones.md` y comentarios de enmienda (`E4a`, `E14`, `E27`...) como historial de
  decisiones, no marcadores en código.
- **CLAUDE.md**: leído — confirma convenciones de repositorio, idioma, `t()`, línea de 100,
  y que `docs/convenciones-codigo.md` es la fuente de verdad de implementación.
- **Documento de diseño (`/office-hours`)**: no existe (`~/.gstack/projects/Bingo_App/*-design-*.md`
  ausente, sin `DESIGN.md` ni `docs/designs/`). Se ofrecería `/office-hours` en modo
  interactivo; en `/autoplan` se procede sin él y se nota como límite del análisis: no hay
  documento de exploración de alternativas previo a este plan, más allá del contrato de fase
  ya escrito por el propio autor del proyecto.
- **Nota de handoff de CEO**: no existe.
- **Ámbito UI**: SÍ detectado (vista dentro del evento, botón, barra de progreso, listado
  paginado, visor con cuadrícula, panel de resumen → Fase 2 de `/autoplan` corre).
- **Ámbito DX (developer-facing)**: NO detectado (no hay API, CLI, SDK ni integración para
  terceros desarrolladores; el "cliente" es un operador de bingo, no un programador) → Fase
  2.5 (DX review) se omite.

### Qué ya existe (leverage map — se detalla también en la sección CEO §0B)

| Sub-problema de la Fase 2 | Código ya existente que lo resuelve parcial o totalmente |
|---|---|
| Ejecutar trabajo largo sin congelar la UI | `ui/tarea.py::Tarea` (`QThread` con `progreso`, `terminado`, `fallado`, `cancelar()` cooperativo) — escrito en la Fase 1 explícitamente para este consumidor, sin usar todavía |
| Colgar una sección nueva en el espacio del evento | `ui/registro_vistas.py::SECCIONES_ESPACIO_EVENTO` ya tiene la entrada `"espacio_evento.seccion.cartones"` con `fabrica=None` — placeholder esperando esta fase |
| Esquema de `lote` y `carton` | Ya migrado en `001_inicial.sql` con los `CHECK` de estado y los índices `idx_carton_evento_estado`, `idx_carton_codigo` — no hace falta migración 002 |
| Máquina de estados genérica | `dominio/estados.py::puede_transicionar()` — Fase 2 solo añade `TRANSICIONES_CARTON`, no toca la función |
| Traducción de errores SQLite / unicidad | `persistencia/errores_sqlite.py::traducir_errores_sqlite()` ya distingue `tipo="unique"` y `restriccion` — la colisión de firma la señaliza sin código nuevo |
| Transacciones por bloque | `persistencia/conexion.py::transaccion()` ya soporta abrir/cerrar transacciones sucesivas; no es reentrante (falla claro si se anida) |
| Auditoría | `repo_auditoria.registrar(con, evento_id, accion, detalle)` ya genérico, reutilizable para "lote generado" |
| Dinero | No aplica en esta fase (Fase 2 no toca precios) |
| Patrón repositorio / verbos | Tabla de verbos en `docs/convenciones-codigo.md` ya fija nombres; `repo_evento.py` es la plantilla a seguir para `repo_carton.py` y `repo_lote.py` |

**Conclusión de leverage:** la Fase 1 dejó literalmente enganchado el punto de entrada
(`SECCIONES_ESPACIO_EVENTO`) y el trabajador de hilo (`Tarea`) para esta fase exacta. No hay
nada que reconstruir; todo el trabajo de la Fase 2 es *añadir*, no *refactorizar*.

---

## 1. Alcance (verbatim del contrato, para trazabilidad)

Generar lotes de cartones de 75 bolas, únicos, con código correlativo, consultables en
pantalla. Dominio puro, probable sin abrir ventana. Ver `docs/Fase_2/Contrato_Fase2.md`
para el texto de referencia completo (tareas 2.1-2.6, criterios de aceptación, riesgos).

---

## 2. Plan de implementación (task breakdown)

### 2.1 `dominio/carton.py` (nuevo)

Python puro. No importa PySide6 ni sqlite3 (verificado por `test_arquitectura.py`, que ya
corre sobre toda `dominio/` sin cambios).

```python
"""Generación y representación del cartón de 75 bolas. Dominio puro: ver
docs/convenciones-codigo.md. Cuadrícula 5x5, columnas B-I-N-G-O, None = libre.
"""
RANGOS: dict[int, tuple[int, int]] = {0: (1, 15), 1: (16, 30), 2: (31, 45),
                                       3: (46, 60), 4: (61, 75)}
BIT_LIBRE = 12

def indice_bit(fila: int, columna: int) -> int: ...          # fila*5 + columna
def generar_carton(rng: Random) -> list[list[int | None]]: ...  # §4.2 doc técnico
def orden_canonico(carton: list[list[int | None]]) -> str: ...  # "3,7,12,..." (24 núms)
def firma(carton: list[list[int | None]]) -> str: ...           # sha256(orden_canonico)
def numeros_por_bit(carton: list[list[int | None]]) -> dict[int, int]: ...
def carton_desde_orden_canonico(cadena: str) -> list[list[int | None]]: ...  # inverso
```

`carton_desde_orden_canonico` **no está en el contrato original** pero es imprescindible:
el repositorio solo persiste la cadena `numeros` (24 números), y el visor (2.5) necesita
reconstruir la matriz 5x5 para dibujar un cartón cargado desde la base. Sin esta función no
hay forma de pintar un cartón que no acaba de generarse en memoria. Se añade aquí como parte
del propio dominio del cartón, no como código de UI (P5: hueco obvio, arreglo de una función,
no una decisión de arquitectura — se resuelve sin preguntar, ver Decisión Audit Trail #3).

`generar_carton` recibe `rng` inyectado (nunca lo instancia): producción usa
`secrets.SystemRandom()`, pruebas usan `random.Random(semilla)` — regla ya fijada por el
contrato y coherente con `Bombo` de la Fase 5 (mismo patrón, no se reinventa).

### 2.2 `dominio/estados.py` (editar — añadir, no tocar lo existente)

```python
TRANSICIONES_CARTON: Mapping[str, set[str]] = {
    "generado":  {"impreso", "anulado"},
    "impreso":   {"entregado", "anulado"},
    "entregado": {"vendido", "anulado"},
    "vendido":   {"anulado"},
    "anulado":   set(),
}
```

Reutiliza `puede_transicionar()` tal cual — cero líneas nuevas en esa función. Rechazo de
transición inválida ya tiene canal: `ErrorTransicionInvalida` (franja no modal, ya
existente, ya traducida en `es.json`/`en.json`: `error.transicion_invalida`). **No hace
falta ninguna clave i18n nueva para esto.**

### 2.3 `dominio/modelos.py` (editar — añadir dos dataclasses de registro)

```python
@dataclass(slots=True)
class Lote:
    evento_id: int
    cantidad: int
    semilla: str
    prefijo_codigo: str
    id: int | None = None
    generado_en: str = ""
    completado_en: str | None = None   # NULL = huérfano/en curso; ver E2 revisado en Eng §1

@dataclass(slots=True)
class Carton:
    evento_id: int
    lote_id: int
    codigo: str
    numeros: str          # 24 números, orden canónico, coma-separado
    firma: str
    id: int | None = None
    estado: str = "generado"
```

Van en `modelos.py` (registro puro, sin comportamiento) y no en `carton.py`, siguiendo la
regla explícita de `docs/convenciones-codigo.md`: "Entidades con comportamiento propio en su
propio módulo... las que son solo registro en `dominio/modelos.py`". `carton.py` opera sobre
`list[list[int | None]]`, nunca sobre este dataclase — son dos representaciones distintas a
propósito (una es lo que genera el algoritmo, la otra es la fila persistida).

### 2.4 `persistencia/repo_lote.py` (nuevo — no listado explícitamente en el contrato,
añadido porque `carton.lote_id` es `NOT NULL REFERENCES lote(id)`: sin este repo no hay
forma de insertar un cartón. Ver Decisión Audit Trail #1.)

Verbos según la tabla de `docs/convenciones-codigo.md`:

```python
def crear(con, lote: Lote) -> Lote: ...                 # INSERT, devuelve con id
def obtener(con, lote_id: int) -> Lote | None: ...
def listar_por_evento(con, evento_id: int) -> list[Lote]: ...
def eliminar(con, lote_id: int) -> None: ...             # usado en rollback de cancelación
def existe_prefijo(con, evento_id: int, prefijo_codigo: str) -> bool: ...  # ver hallazgo Eng #4
def marcar_completado(con, lote_id: int) -> None: ...    # completado_en = ahora_iso()
def listar_huerfanos(con) -> list[Lote]: ...              # completado_en IS NULL, ver Eng §1
```

`completado_en` es una columna nueva en `lote` (editable en `001_inicial.sql`: la política de
`docs/convenciones-codigo.md` permite editar la migración inicial mientras no haya un evento
con datos reales, y este proyecto todavía no tiene ninguno). Se fija en la **misma
transacción** que cierra el lote con éxito o lo cancela — nunca se infiere del log de
auditoría (ver por qué en Eng §1, hallazgo crítico #5 revisado). Tras editar la migración,
corre `python -m bingo --reiniciar-datos` (regla ya fijada en CLAUDE.md para este caso
exacto).

### 2.5 `persistencia/repo_carton.py` (nuevo)

```python
def crear_varios(con, cartones: list[Carton]) -> int: ...       # executemany, devuelve N
def obtener(con, carton_id: int) -> Carton | None: ...
def obtener_por_codigo(con, evento_id: int, codigo: str) -> Carton | None: ...
def listar_por_evento(con, evento_id, *, estado=None, texto_busqueda=None,
                       limite=None, desplazamiento=0) -> list[Carton]: ...
def contar_por_estado(con, evento_id: int) -> dict[str, int]: ...
def listar_firmas_por_evento(con, evento_id: int) -> set[str]: ...  # ver §2.6, unicidad
def actualizar_estado(con, carton_id: int, estado: str) -> None: ...       # ya validado
def actualizar_estado_por_lote(con, lote_id: int, estado: str) -> int: ...  # bulk, devuelve N
def eliminar_por_lote(con, lote_id: int) -> int: ...             # rollback de cancelación
```

`listar_firmas_por_evento` no está en el contrato tal cual, pero es la pieza que hace
posible la unicidad sin N consultas (ver §2.6). `obtener_por_codigo` alimenta el buscador de
2.5 y el buscador por código de la Fase 5 (mismo repo, no se reescribe).

**Verificación de índice** (criterio de aceptación del contrato: "verificar con `EXPLAIN
QUERY PLAN` que la búsqueda por código los usa"): tarea de prueba, no de código productivo —
se cubre en `tests/persistencia/test_repo_carton.py` con
`con.execute("EXPLAIN QUERY PLAN SELECT ...")` y una aserción de que el plan menciona
`idx_carton_codigo` o el índice implícito del `UNIQUE(evento_id, codigo)`.

### 2.6 `servicios/servicio_cartones.py` (nuevo)

```python
def generar_lote(
    con: sqlite3.Connection,
    evento_id: int,
    cantidad: int,
    prefijo_codigo: str,
    *,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
    rng: Random | None = None,          # inyectable para pruebas; default secrets.SystemRandom()
) -> Lote: ...

def limpiar_lotes_huerfanos(con: sqlite3.Connection) -> int: ...  # devuelve N lotes limpiados
```

**`regenerar_lote` queda FUERA del alcance de esta fase (resolución del gate, decisión D1):**
misma función que `generar_lote` con el `rng` inyectado desde `lote.semilla` en vez de
`secrets.SystemRandom()`, pero sin ningún llamador real hasta que la Fase 3 pierda un PDF y
necesite reproducir un lote exacto — se implementa ahí, no aquí. Ver `TODOS.md`.

**Algoritmo de `generar_lote` (el corazón de la fase, detallado porque el contrato deja
ambigüedades reales — resueltas aquí, ver Decisión Audit Trail):**

1. Validar (todas `ErrorValidacion`, cada una con su propio `campo`):
   - `cantidad > 0` **y `cantidad <= LIMITE_CARTONES_POR_LOTE`** (constante en
     `config/ajustes.py`, valor por defecto 50.000 — hallazgo Eng #2: sin tope, un valor como
     10.000.000 es "válido" por la sola regla `>0` y el `set` de firmas en memoria crecería sin
     límite operable; 50.000 cubre con margen el "miles de cartones" real de un bingo de una
     organización, documentado en `docs/Proyecto_Alcance.md`).
   - `prefijo_codigo` no vacío, longitud máxima 12 y solo `[A-Za-z0-9-]` (hallazgo Eng #6: el
     prefijo termina impreso en el cartón físico en la Fase 3 — validarlo ahora evita que un
     carácter raro llegue al PDF dos fases después).
   - **`not repo_lote.existe_prefijo(con, evento_id, prefijo_codigo)`** (hallazgo Eng #4:
     sin esto, dos lotes del mismo evento con el mismo prefijo generan secuencias que
     reinician en 1 y chocan en `UNIQUE(evento_id, codigo)` a mitad de bloque — un error real,
     no un caso de borde teórico. Rechazo explícito y temprano en vez de dejar que la
     violación de integridad lo descubra a mitad de la inserción).
2. `con transaccion(con):` crear la fila `lote` (semilla generada con `secrets.token_hex(16)`
   si no se inyecta `rng` de prueba; si se inyecta un `Random(semilla)` de prueba, la semilla
   registrada es esa; `completado_en=None`). Registrar auditoría `"lote.creado"`.
3. **Precargar unicidad una sola vez:** `firmas_existentes = repo_carton.listar_firmas_por_evento(con, evento_id)`
   (una consulta, no N). Se mantiene un `set` en memoria que empieza como copia de esa
   consulta y crece con cada cartón nuevo generado en este lote — así nunca hay que volver a
   la base para comprobar unicidad durante la generación.
4. Ancho de secuencia = `len(str(cantidad))` (contrato: "secuencia rellenada con ceros según
   la cantidad del lote"). Año del código = año de `ahora_iso()` en el momento de generar el
   lote (no la fecha del evento — el código identifica cuándo se imprimió el lote, no cuándo
   es el evento; se documenta como asunción explícita, Decisión de Gusto **D2**, ver gate
   final).
5. Bucle de generación en bloques de 500:
   - Por cada cartón: generar con `dominio.carton.generar_carton(rng)`, calcular firma; si la
     firma ya está en el set en memoria, descartar y reintentar, con un **tope de 1.000
     colisiones consecutivas** (hallazgo Eng #3 — sin tope, una semilla mal configurada o
     reutilizada produce un bucle infinito real, no hipotético: congela la aplicación en un
     evento en vivo o cuelga la suite de pruebas en CI). Al superar el tope, lanzar
     `ErrorDominio("cartones.error.generacion_bloqueada")` — nunca debería dispararse con
     `secrets.SystemRandom()` dado el espacio de combinaciones, pero es la diferencia entre un
     error con nombre y un proceso colgado sin explicación.
   - Construir el código correlativo `f"{prefijo}-{anio}-{secuencia:0{ancho}d}"`.
   - Acumular hasta 500 objetos `Carton` (estado `"generado"`).
   - Comprobar `debe_cancelar()` **entre cartones**, no solo entre bloques — con 10.000
     cartones y bloques de 500, cancelar solo entre bloques deja hasta 500 cartones de
     retraso perceptible; comprobar cada ~50 cartones generados mantiene la cancelación
     responsiva sin pagar el costo de comprobar en cada iteración.
   - Al completar 500 (o al llegar al final): `con transaccion(con): repo_carton.crear_varios(con, bloque)`;
     emitir `al_progresar(generados_hasta_ahora, cantidad)` (incluye timestamp para que la UI
     derive "cartones/seg", E4 — el servicio no calcula la velocidad, solo expone los datos
     crudos; el cálculo de tasa es responsabilidad de la vista, no del dominio de servicio).
   - **Si `debe_cancelar()` es verdadero:** cortar el bucle, y en una transacción final
     `repo_carton.eliminar_por_lote(con, lote.id)` + `repo_lote.eliminar(con, lote.id)` +
     `repo_auditoria.registrar(con, evento_id, "lote.cancelado", ...)` — se elimina la fila de
     `lote` directamente (no se marca `completado_en`) porque un lote cancelado no debe
     quedar listado en absoluto, ni siquiera como fila fantasma.
   - **Si `repo_carton.crear_varios` lanza `ErrorIntegridad`** en cualquier bloque (violación
     real de `UNIQUE`, no la colisión de firma ya filtrada en memoria — p. ej. un bug futuro):
     no hay reintento silencioso; se relanza tal cual hacia `Tarea`, que la traduce a
     `fallado`. El lote queda con `completado_en=None` — lo recoge el barrido de huérfanos
     (Eng §1) en el siguiente arranque, sin necesitar lógica de limpieza especial aquí.
6. **Al terminar con éxito (todo el bucle completado sin cancelar ni fallar):** en la
   transacción del último bloque, o en una transacción final si el último bloque ya cerró,
   `repo_lote.marcar_completado(con, lote.id)` — pone `completado_en = ahora_iso()`. Esta es
   la corrección del hallazgo crítico de Eng (revisado abajo, Eng §1): el barrido de
   huérfanos ya no interpreta el log de auditoría, lee directamente esta columna.
7. Devolver el `Lote` persistido (con `completado_en` fijado).

`regenerar_lote` reconstruye un lote ya perdido (PDF extraviado, contrato §2.2 "registro del
lote con su semilla, para poder reproducirlo") usando `random.Random(lote.semilla)` en vez de
`secrets.SystemRandom()` — misma función `generar_lote` internamente, con el generador
inyectado. No tiene gancho de UI en esta fase (nadie lo llama todavía: la Fase 3 lo necesita
si se pierde un PDF). Se implementa ahora porque es la misma función con un parámetro
distinto — bloque de radio pequeño, cero costo adicional real (P2: boil lakes, dentro del
radio de impacto).

### 2.7 `ui/widgets/cuadricula_carton.py` (nuevo — primer archivo de `ui/widgets/`)

```python
class CuadriculaCarton(QWidget):
    def __init__(self, carton: list[list[int | None]] | None = None, *,
                 marcados: set[int] | None = None,        # bits marcados (Fase 5)
                 patron_resaltado: int | None = None,      # máscara a resaltar (Fase 5)
                 parent: QWidget | None = None): ...
    def actualizar(self, carton, *, marcados=None, patron_resaltado=None) -> None: ...
    def limpiar(self) -> None: ...   # carton=None: dibuja el placeholder "sin selección"
```

El contrato pide explícitamente diseñar esta API pensando en la Fase 5 ("recibe un cartón y
opcionalmente un conjunto de números marcados y un patrón a resaltar"). En la Fase 2 solo se
usa sin `marcados` ni `patron_resaltado` (dibuja la cuadrícula simple con el centro libre).
`ui/widgets/` no existe todavía como carpeta — la crea esta fase, tal como anticipa la
estructura de `docs/Documento_Tecnico.md` §2.2.

**Tratamiento del centro libre (hallazgo de diseño, resuelto):** la celda del espacio libre
(`None`) se dibuja con el mismo borde que las demás celdas, sin número, y el texto
`t("carton.libre")` centrado en tamaño reducido — nunca una celda en blanco indistinguible ni
un icono (el tema es neutro y fijo, decisión DU-1: no hay color de marca disponible por
defecto para diferenciarla de otra forma). Se añade la clave `carton.libre` (`"LIBRE"` /
`"FREE"`) al bloque de i18n de §2.9.

**Estado "sin selección" (hallazgo de diseño, resuelto):** `limpiar()` dibuja un marco vacío
con el texto `t("cartones.visor.sin_seleccion")` centrado, en vez de un widget en blanco o
`None` sin manejar. Es el estado por defecto al abrir la vista, tras generar un lote nuevo
(antes de que el operador seleccione una fila), y tras un filtro que deja la selección
anterior fuera del resultado.

### 2.8 `ui/vistas/vista_cartones.py` (nuevo) + registro

```python
def _vista_cartones(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_cartones import VistaCartones
    return VistaCartones(con, evento)
```

Editar `ui/registro_vistas.py`: cambiar
`EntradaSeccionEvento("espacio_evento.seccion.cartones", None)` a
`EntradaSeccionEvento("espacio_evento.seccion.cartones", _vista_cartones)` — **una línea**,
sin tocar `espacio_evento.py` (confirma la promesa de la Fase 1: "sin tocar este archivo").

**Layout (fijado aquí, no dejado al implementador — hallazgo de diseño):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Panel de resumen: Total N · Generado n1 · Impreso n2 · ...  [chips] │
│ [Generar lote]                                        [Cancelar]*   │
├───────────────────────────────┬───────────────────────────────────┤
│ Filtro estado ▾   Buscar código │                                   │
│ ┌───────────────────────────┐ │                                   │
│ │ QTableView paginado        │ │        CuadriculaCarton          │
│ │ código | estado | ...      │ │   (visor del cartón seleccionado, │
│ │ ...                         │ │    o placeholder "sin selección")│
│ └───────────────────────────┘ │                                   │
└───────────────────────────────┴───────────────────────────────────┘
* "Cancelar" y la barra de progreso solo aparecen mientras una Tarea corre.
```

Panel de resumen **siempre visible arriba** (da contexto de estado antes de tocar nada).
Maestro-detalle horizontal: listado a la izquierda, visor a la derecha — no una lista de
viñetas suelta como en el borrador original de este plan.

- **Widget del listado: `QTableView` con modelo `QAbstractTableModel` propio, paginado**
  (decisión fijada aquí — no "`QTableView` o `QListWidget`" dejado al implementador). Con
  filtro de estado + búsqueda por código + hasta miles de filas, hace falta orden por columna
  (código, estado) y escala mejor que una lista; `QListWidget` no da ninguna de las dos.
- **Estado vacío (evento recién creado, cero cartones — el primer contacto real, no un caso
  raro):** en vez del `QTableView` vacío, un panel centrado con
  `t("cartones.vacio.titulo")` ("Aún no hay cartones generados") + botón grande
  `t("cartones.generar_lote")` como única llamada a la acción visible. El panel de resumen
  arriba muestra "Total 0".
- **Botón "Generar lote"** (en la cabecera de la vista, no dentro de la lista) → diálogo con
  cantidad + prefijo → lanza `Tarea(servicio_cartones.generar_lote, con_nueva, evento.id, cantidad, prefijo)`
  — **la conexión SQLite de este hilo se abre dentro de la función de servicio, no se reutiliza
  la de la UI** (regla de una conexión por hilo, `docs/convenciones-codigo.md`), conectada a
  `progreso` (barra + contador "N/total — ~X cartones/seg", E4 incorporado aquí, no solo en
  el registro de decisiones), `terminado` (refrescar listado + panel de resumen),
  `fallado` (franja de error). El botón se deshabilita al lanzar la tarea y se reactiva en
  `terminado`/`fallado` — cierra el caso borde de doble clic detectado en la Sección 4 del CEO.
- **Botón "Cancelar"**, visible solo mientras la tarea corre, junto a la barra de progreso →
  `tarea.cancelar()`.
- **Confirmación de éxito:** franja no modal (mismo canal que `ErrorPersistencia` en
  `ui/dialogos.py`, pero en tono de éxito) con `t("cartones.exito.lote_generado")` — no un
  diálogo modal ni un toast nuevo; reutiliza el componente de franja ya existente en el
  proyecto en vez de introducir un cuarto canal de feedback.
- Listado paginado con filtro de estado (combo) y campo de búsqueda por código
  (`repo_carton.obtener_por_codigo` o `listar_por_evento(..., texto_busqueda=...)`).
- Al seleccionar una fila: `CuadriculaCarton.actualizar(...)` con la matriz reconstruida vía
  `carton_desde_orden_canonico`. Al perder la selección (filtro, tras generar) → `limpiar()`.
- Panel de resumen: `repo_carton.contar_por_estado(con, evento.id)` renderizado como chips
  (mismo patrón visual que `_OBJETO_CHIP` de `espacio_evento.py`, reutilizado por analogía).

### 2.9 i18n — claves nuevas (namespace `cartones.*`, añadir a `es.json` y `en.json`)

```
cartones.titulo, cartones.generar_lote, cartones.campo.cantidad,
cartones.campo.prefijo, cartones.accion.cancelar, cartones.progreso,
cartones.progreso.velocidad, cartones.buscar_codigo, cartones.filtro.estado,
cartones.resumen.total, cartones.vacio.titulo, cartones.visor.sin_seleccion,
cartones.error.cantidad_invalida, cartones.error.cantidad_excede_maximo,
cartones.error.prefijo_vacio, cartones.error.prefijo_invalido,
cartones.error.prefijo_repetido, cartones.error.generacion_bloqueada,
cartones.vacio.filtro, cartones.exito.lote_generado, cartones.aviso.cancelado, carton.libre,
estado_carton.generado, estado_carton.impreso, estado_carton.entregado,
estado_carton.vendido, estado_carton.anulado
```

`error.transicion_invalida` y `error.no_encontrado` **ya existen** — no se listan de nuevo.
`test_claves_i18n_de_errores_existen_en_es_json` (ya en el repo) falla sola si se olvida
alguna clave de un `Error*` nuevo — es la red de seguridad, no hace falta duplicarla aquí.

### 2.10 Pruebas (mapeadas 1:1 al criterio de aceptación del contrato)

```
tests/dominio/test_carton.py
  - columnas sin repetidos, rangos correctos, N tiene 4 + libre en centro
  - orden_canonico / firma deterministas con semilla fija
  - carton_desde_orden_canonico(orden_canonico(c)) == c  (round-trip)
  - generar 50.000 cartones (random.Random, semilla fija) → cero firmas repetidas
    (marcado @pytest.mark.lento)
  - reproducibilidad: misma semilla → mismo lote de N cartones, en orden

tests/dominio/test_estados.py (editar, añadir casos)
  - TRANSICIONES_CARTON: cada transición válida pasa, cada inválida falla
  - anulado no transiciona a nada

tests/persistencia/test_repo_lote.py, test_repo_carton.py (nuevos)
  - crear_varios inserta N filas en un solo executemany
  - UNIQUE(evento_id, firma) y UNIQUE(evento_id, codigo) lanzan ErrorIntegridad tipo="unique"
  - listar_por_evento con filtro de estado y paginación
  - EXPLAIN QUERY PLAN confirma uso de índice en obtener_por_codigo
  - eliminar_por_lote no dispara FK violation contra comprador/ganador (no existen todavía)

tests/servicios/test_servicio_cartones.py (nuevo)
  - generar_lote con Random(semilla) → N cartones, sin colisiones, códigos correlativos
    correctos (ancho de ceros según cantidad)
  - cancelación a mitad (debe_cancelar devuelve True tras el bloque 2 de 500) → cero
    cartones y cero fila de lote sobreviven (consulta directa a la tabla tras la llamada)
  - al_progresar se llama con (generados, total) creciente y monótono
  - cantidad > LIMITE_CARTONES_POR_LOTE (50.000) → ErrorValidacion; cantidad == límite exacto
    pasa (hallazgo Eng #2)
  - segundo lote del mismo evento con el mismo prefijo → ErrorValidacion antes de tocar la
    base; con prefijo distinto sí funciona (hallazgo Eng #4)
  - prefijo con carácter fuera de [A-Za-z0-9-] o más de 12 caracteres → ErrorValidacion;
    12 caracteres exactos pasa (hallazgo Eng #6)
  - rng fabricado que siempre repite la misma firma → ErrorDominio tras 1.000 intentos
    consecutivos, sin bucle infinito (hallazgo Eng #3)
  - limpiar_lotes_huerfanos: un lote con completado_en IS NULL y cartones asociados se
    elimina por completo; si hay dos huérfanos y uno falla, el otro se limpia igual
    (transacción por lote, no una sola para todos — hallazgo Eng #5)

tests/test_arranque.py (editar — el barrido de huérfanos corre en __main__ antes de mostrar
  la ventana; se añade un caso que simula un lote con completado_en=NULL preexistente en la
  base y confirma que desaparece tras `principal()`)

tests/ui/test_vista_cartones.py (nuevo, offscreen)
  - abrir la vista sin cartones muestra el estado vacío con el CTA "Generar el primer lote"
  - generar un lote pequeño (mock de Tarea o cantidad=5 sin hilo real en prueba) actualiza
    listado y panel de resumen
  - filtrar por un estado sin resultados muestra "Ningún cartón coincide" (hallazgo de
    diseño, Pase 2)
  - doble clic en "Generar lote" mientras la tarea corre no lanza una segunda Tarea; el botón
    se reactiva tanto en terminado como en fallado (hallazgo CEO Sección 4)
  - seleccionar una fila dibuja el cartón; perder la selección tras un filtro vuelve al
    placeholder "sin selección" (hallazgo de diseño, Pase 1)
  - retraducir() cambia los textos estáticos sin tocar el campo de búsqueda con texto tecleado
```

---

## FASE 1 DE /autoplan — Revisión CEO (modo SELECTIVE EXPANSION)

### 0A. Desafío de premisas

1. **¿Es el problema correcto?** Sí. Sin cartones únicos y persistidos no hay nada que
   imprimir (Fase 3), vender (Fase 4) ni jugar (Fase 5). Es la dependencia real que el propio
   `docs/Plan_Fases_Bingo.md` documenta ("no se puede probar el sorteo sin cartones"). No hay
   reencuadre que la evite.
2. **¿El resultado real es el de negocio?** Sí: "generar N cartones únicos, consultables" es
   directamente el entregable `v0.2.0`, no un proxy de otra cosa.
3. **¿Qué pasa si no se hace nada?** La aplicación se queda en gestión de eventos vacíos — no
   hay bingo posible. Dolor real, no hipotético; es la siguiente fase obligatoria del propio
   plan del autor.

Premisas evaluadas como razonables y aceptadas (P6). No hay premisa "claramente equivocada"
que amerite un User Challenge en el gate final.

### 0B. Aprovechamiento de código existente

Ver la tabla de la sección 0 arriba (auditoría previa) — no se repite aquí. Punto clave: la
Fase 1 dejó `Tarea` y el placeholder de `SECCIONES_ESPACIO_EVENTO` construidos *a propósito*
para este consumidor exacto. Cero reconstrucción; el 100% del trabajo es aditivo.

### 0C. Mapa de estado ideal (12 meses)

```
ESTADO ACTUAL                    ESTE PLAN                         IDEAL A 12 MESES
Eventos en borrador,     --->    Cartones únicos generados,  --->  Bingo completo en vivo:
sin nada de bingo.               persistidos, consultables         cartones, impresión,
Cero cartones.                   con visor reutilizable.           compradores, sorteo,
                                  Motor de sorteo (Fase 5)          actas y respaldos.
                                  ya tiene su widget listo.         (v1.0.0)
```

Este plan mueve directamente hacia el estado ideal: no hay trabajo desechable, el widget de
cuadrícula construido aquí es el mismo que usará la Fase 5 sin reescritura.

### 0C-bis. Alternativas de implementación

```
ENFOQUE A: Mínimo viable — solo dominio + repos, sin UI de generación
  Resumen: generar_carton/orden_canonico/firma + repo_carton, probado por pytest,
           sin botón ni visor; se generarían lotes desde una consola de depuración.
  Esfuerzo: S   Riesgo: Bajo
  Pros: entrega la parte "dominio puro" del contrato en un día; cero riesgo de UI
  Contras: no cumple el criterio de aceptación "se puede buscar un cartón por su código y
           verlo dibujado en pantalla" — incompleto respecto al contrato firmado
  Reutiliza: nada de UI (no hace falta)

ENFOQUE B (recomendado): Dominio + repos + servicio + UI completa (lo descrito en la
  sección 2 de este plan)
  Resumen: todo lo que pide el contrato: generación en hilo, listado paginado, visor,
           panel de resumen.
  Esfuerzo: M   Riesgo: Bajo (todo el andamiaje de hilos y navegación ya existe)
  Pros: cumple los 5 criterios de aceptación del contrato tal cual están escritos;
        usa exactamente el gancho que la Fase 1 dejó preparado, sin trabajo de más
  Contras: más superficie a revisar en una sola fase que el Enfoque A
  Reutiliza: Tarea, SECCIONES_ESPACIO_EVENTO, patrón de repo_evento.py, i18n existente

ENFOQUE C: B + reescritura del algoritmo de generación con NumPy para paralelizar
  Resumen: usar arrays de NumPy y generación vectorizada para lotes de 100k+.
  Esfuerzo: L   Riesgo: Medio (nueva dependencia, el proyecto no usa NumPy en ningún
           lado; el documento técnico no lo lista en el stack)
  Pros: generación más rápida a escalas que el proyecto no requiere (bingos de una
        organización rondan cientos a pocos miles de cartones, no cientos de miles)
  Contras: dependencia nueva sin justificación de negocio; el contrato ya dice que
           "10.000 cartones en segundos" es la meta, y el algoritmo puro de Python ya
           la cumple de sobra (extracción sin reemplazo sobre listas de ≤15 elementos)
  Reutiliza: nada nuevo — sustituye código que ya funcionaría

**RECOMENDACIÓN:** Enfoque B. Es el único que satisface los criterios de aceptación del
contrato tal como el propio autor los redactó, y reutiliza al 100% el andamiaje que la Fase 1
dejó preparado. El Enfoque C resuelve un problema de escala que no existe en el alcance
documentado (`docs/Proyecto_Alcance.md` describe eventos de una organización, no una
plataforma masiva).

*(Auto-decidido: en `/autoplan` la selección de alternativa resuelve al Enfoque B por
completitud (P1) — es la única que cumple el contrato completo. No es una decisión de gusto:
el Enfoque A incumple criterios de aceptación firmados, y el C añade una dependencia sin
problema real que resolver.)*

### 0D. Análisis específico del modo (SELECTIVE EXPANSION)

**Chequeo de complejidad:** el plan toca 9 archivos nuevos + 2 ediciones de una línea
(`registro_vistas.py`, `estados.py`) + 2 ediciones de dataclasses (`modelos.py`). No cruza el
umbral de "más de 8 archivos o más de 2 clases/servicios nuevos" de forma alarmante — es
exactamente lo que el contrato pide, ni más ni menos.

**Mínimo conjunto de cambios:** el Enfoque A (arriba) sería el mínimo técnico, pero incumple
el contrato firmado por el propio autor del proyecto — no se recorta scope por debajo de lo
que el contrato de fase exige sin que el usuario lo pida explícitamente.

**Candidatos de expansión (cherry-pick, postura neutral, el usuario decide en el gate):**

| # | Candidato | Archivos | Esfuerzo | Encaja en el radio de impacto |
|---|---|---|---|---|
| E1 | `regenerar_lote` ahora (sin consumidor hasta Fase 3) | 1 (mismo `servicio_cartones.py`) | S | Sí, pero sin caller real — código no verificado end-to-end hasta que algo lo llame |
| E2 | Barrido de "lote huérfano" al iniciar la app (mitiga la ventana de fallo del rollback por cancelación, hallazgo #2 del subagente) | 1 (`servicios/servicio_cartones.py` + gancho en `__main__.py`) | S | Sí — cierra un hueco real de la Fase 2 misma |
| E3 | Prueba de tiempo acotado para "10.000 cartones en segundos" (hallazgo #3 del subagente) | 1 (`tests/servicios/test_servicio_cartones.py`) | S | Sí — el propio criterio de aceptación lo exige y hoy no está probado |
| E4 | Contador en vivo "cartones/seg" en la barra de progreso | 1 (`vista_cartones.py`) | S | Sí, cosmético, bajo riesgo |
| E5 | Exportar el listado de cartones a Excel/PDF antes de tiempo (esto es trabajo de Fase 3/4) | 3+ (nuevo módulo de exportación) | M | No — fuera del radio de esta fase, es la Fase 3 |

Decisiones (P2: dentro del radio + <1 día → aprobar; fuera → diferir a TODOS.md; P4: no
duplica nada existente en ninguno de los casos):

- **E2 y E3 se aprueban y se incorporan al plan** (auto-decidido, P1 completitud: ambos
  cierran huecos que el propio contrato de esta fase ya exige — no son expansión de alcance,
  son completar lo que "cartones únicos, sin huérfanos" y "10.000 en segundos" ya prometen).
  Ver §2.6 actualizado abajo.
- **E4 se aprueba** (auto-decidido, P3 pragmático: una línea de UI, sin riesgo).
- **E5 se difiere a TODOS.md** (auto-decidido, P2: fuera de radio, pertenece a la Fase 3).
- **E1 queda como DECISIÓN DE GUSTO para el gate final** — ni completamente dentro ni fuera
  del radio: es la misma función que ya se escribe, pero el subagente CEO tiene razón en que
  "cero llamadores" significa cero verificación real. Recomendación: diferir a Fase 3 (cuando
  la impresión pierde un PDF y necesita regenerar). Ver Decisión de Gusto D1 en el gate.

### Actualización de §2.6 (E2 + E3 aceptados)

**E2 — barrido de lote huérfano (mitigación del hallazgo crítico #2), versión final tras
la corrección de Eng §1 (la primera versión de este párrafo, basada en inferir el estado
desde el texto de `auditoria`, era autocontradictoria — ver el hallazgo #5 de la revisión de
Eng más abajo; se sustituye por completo, no se repara en el sitio):** al arrancar la
aplicación (`__main__.py`, después de aplicar migraciones, antes de mostrar la ventana),
`servicio_cartones.limpiar_lotes_huerfanos(con)` llama a `repo_lote.listar_huerfanos(con)`
(`WHERE completado_en IS NULL`) y, **para cada lote huérfano, en su propia `transaccion(con)`
independiente** (nunca todos en una sola transacción — una fila corrupta no debe bloquear la
limpieza del resto): `repo_carton.eliminar_por_lote(con, lote.id)` +
`repo_lote.eliminar(con, lote.id)` + `repo_auditoria.registrar(con, evento_id,
"lote.huerfano_limpiado", detalle=f"lote {lote.id}, {n} cartones")`. `completado_en` es una
columna directa en `lote` (no un evento de auditoría a interpretar), fijada dentro de la
misma transacción que cierra el lote — sin ambigüedad de parseo, sin condición
imposible-por-construcción.

**E3 — prueba de rendimiento acotada:** `tests/servicios/test_servicio_cartones.py` añade
`test_generar_10000_cartones_toma_menos_de_10_segundos` marcada `@pytest.mark.lento`, corre
con `time.perf_counter()` y un margen generoso (10s en vez del "segundos" narrado, para
tolerar hardware de CI lento sin volverse flaky).

### 0E. Interrogación temporal

- **Hora 1:** `dominio/carton.py` + sus pruebas, sin ninguna dependencia de la base de datos.
  Verificable con `pytest tests/dominio/test_carton.py` de forma aislada.
- **Hora 2-3:** `repo_lote.py`, `repo_carton.py`, `dominio/estados.py` (edición), y sus
  pruebas contra `:memory:`. El `EXPLAIN QUERY PLAN` se verifica aquí.
- **Hora 4-5:** `servicios/servicio_cartones.py` con el algoritmo completo (unicidad
  precargada, bloques de 500, cancelación con rollback, barrido de huérfanos). Es el tramo de
  mayor riesgo real del plan — concentra toda la lógica de transacciones.
- **Hora 6+:** `ui/widgets/cuadricula_carton.py`, `ui/vistas/vista_cartones.py`, cambio de una
  línea en `registro_vistas.py`, claves i18n, pruebas de UI offscreen. Bajo riesgo porque el
  patrón de vista-dentro-del-evento ya existe (`vista_datos_evento.py` como plantilla).

### 0F. Confirmación de modo

**SELECTIVE EXPANSION** confirmado (impuesto por `/autoplan`, no hay razón para desviarse: el
contrato de fase ya fija un alcance detallado y completo — se sostiene ese alcance como base
y se ofrecen expansiones puntuales, que es exactamente lo que ocurrió en 0D).

### 0.5 Voces duales — CEO

**Codex:** no disponible en esta máquina (`codex: command not found`) → degradado, sin
fallback doble (autoplan ya corre con Claude subagent como voz por defecto). Tag:
`[subagent-only]`.

**CLAUDE SUBAGENT (CEO — independencia estratégica):**

> 1. Problema correcto pero alcance "acolchado" más allá de lo validado (Medio) — el widget
>    `CuadriculaCarton` fija una API pensada para la Fase 5 antes de tiempo.
> 2. Premisa no declarada: "borrado compensatorio = rollback" (Alto) — la cancelación no es
>    atómica de verdad; una caída de proceso entre el commit de un bloque y la limpieza deja
>    huérfanos exactamente como el criterio de aceptación promete que no pasará.
> 3. Afirmación de rendimiento sin prueba (Medio) — "10.000 en segundos" no tenía ninguna
>    aserción de tiempo en el plan original.
> 4. Supuesto enterrado que resurge como queja del operador (Medio) — el año en el código
>    correlativo usa la fecha de generación, no la del evento; decisión no confirmada por
>    nadie fuera de este documento.
> 5. Scope creep disfrazado de "gratis" (Bajo/Medio) — `regenerar_lote` sin ningún llamador
>    real en esta fase.
> 6. Riesgo competitivo: no aplica — herramienta de un solo operador, no hay carrera de mercado.

**Resolución de cada hallazgo:** #1 se mantiene (el propio contrato del autor pide
explícitamente esa reutilización — no es invención de este plan; se anota como riesgo a
vigilar en la Sección 5 de abajo). #2 se resuelve con E2 (barrido de huérfanos, ya
incorporado arriba). #3 se resuelve con E3 (ya incorporado). #4 se marca como Decisión de
Gusto D2 en el gate final — es un juicio de negocio, no técnico, y el subagente tiene razón en
que nadie fuera de este documento lo decidió. #5 se marca como Decisión de Gusto D1 en el
gate final (diferir `regenerar_lote` a Fase 3, recomendado).

```
CEO DUAL VOICES — TABLA DE CONSENSO:
═══════════════════════════════════════════════════════════════
  Dimensión                             Claude   Codex   Consenso
  ──────────────────────────────────── ─────── ─────── ─────────
  1. ¿Premisas válidas?                  Sí      N/A     N/A (voz única)
  2. ¿Problema correcto?                 Sí      N/A     N/A (voz única)
  3. ¿Alcance bien calibrado?             Con matices N/A  N/A (voz única)
  4. ¿Alternativas suficientemente exploradas? Sí N/A     N/A (voz única)
  5. ¿Riesgos competitivos cubiertos?     N/A (no aplica) N/A  N/A
  6. ¿Trayectoria a 6 meses sólida?       Con 1 hallazgo crítico (rollback) N/A N/A
═══════════════════════════════════════════════════════════════
Codex no disponible en esta máquina — todas las filas quedan N/A por falta de segunda
voz, no por desacuerdo. El hallazgo #2 (rollback no atómico) se trata como crítico
independientemente de la falta de segunda voz — un solo hallazgo crítico de una voz
disponible se marca igual (regla de degradación de /autoplan).
```

### Secciones 1-10 (+ 11 condicional) de la revisión de 11 secciones

**Sección 1 (Arquitectura):** El diagrama de dependencias ya existe en el documento técnico
(§2.1) y este plan no lo altera: Presentación → Servicios → {Dominio, Persistencia}. Nuevo
acoplamiento: `vista_cartones.py` → `servicio_cartones` → `repo_carton`/`repo_lote` →
`dominio/carton.py`, `dominio/estados.py`. Ningún componente nuevo se salta una capa (no hay
SQL en `servicios/` ni PySide6 en `dominio/`, verificable con `test_arquitectura.py` sin
tocarlo). Punto único de fallo: la conexión SQLite del hilo de `Tarea` — si `abrir_conexion()`
falla dentro del hilo, `Tarea.run()` ya captura `ErrorBingo`/`Exception` y emite `fallado`
(mecanismo ya existente, cero código nuevo necesario). Reversibilidad de rollback: **Ver
hallazgo crítico #2 arriba — resuelto con E2.** Sin hallazgos adicionales.

**Sección 2 (Errores y rescate):** tabla completa en "Registro de Errores y Rescate"
(salida obligatoria, más abajo).

**Sección 3 (Seguridad):** superficie de ataque nueva: ninguna que cruce un límite de
confianza (aplicación de escritorio monousuario, sin red, sin autenticación de por medio). El
único input "hostil" plausible es el campo de búsqueda por código (`texto_busqueda`) — ya se
parametriza con `?` en SQL (patrón de todo el repo existente, `repo_carton.py` seguirá el
mismo). Sin hallazgos.

**Sección 4 (Flujo de datos y casos borde de interacción):** ver el diagrama de flujo de
datos abajo (salida obligatoria). Casos de interacción cubiertos en las pruebas de §2.10:
doble clic en "Generar lote" mientras la tarea corre → el botón debe deshabilitarse al
lanzar la `Tarea` y rehabilitarse en `terminado`/`fallado` (hallazgo nuevo, menor — se añade
a la tabla de Eng, Sección 5 de Code Quality, como comprobación explícita de la vista).
Cancelar y cerrar la vista antes de que termine el hilo: `Tarea` sigue viva en segundo plano
hasta `run()` retornar — la vista debe desconectar sus slots pero NO forzar la destrucción
del hilo (sería `QThread` inseguro); se documenta como nota de implementación en Eng.

**Sección 5 (Calidad de código):** el plan sigue el patrón exacto de `repo_evento.py` /
`servicio_eventos.py` para los repos y servicios nuevos — cero desviación de convención.
Riesgo anotado por el subagente (#1, API de `CuadriculaCarton` con parámetros de Fase 5): se
mantiene per contrato explícito, pero se limita el alcance real de esta fase a **guardar** los
parámetros y pintarlos si vienen, sin construir ninguna lógica de "qué se considera marcado"
todavía — eso es 100% trabajo de la Fase 5, cero líneas de más aquí.

**Sección 6 (Pruebas):** diagrama de pruebas completo en la salida obligatoria de Eng
(Sección 3, más abajo — evita duplicar el mismo diagrama dos veces).

**Sección 7 (Rendimiento):** cubierto por E3 (prueba de tiempo acotado) y por el propio
diseño de precarga de firmas en memoria (evita N consultas). Sin hallazgos adicionales aquí;
detalle de N+1 en la Sección 4 de Eng (Performance).

**Sección 8 (Observabilidad):** `repo_auditoria.registrar` ya cubre "lote.creado",
"lote.completado" (nuevo, de E2) y "lote.cancelado". El log de aplicación
(`utilidades/log.py`, ya existente en Fase 1) captura las colisiones de firma esperadas
(contrato: "registrar en el log cuántas colisiones hubo"). No hay métricas ni tableros
nuevos que añadir — es una app de escritorio monousuario, no un servicio con panel de
operación; el log de auditoría + el log de aplicación son la observabilidad completa que
este contexto necesita.

**Sección 9 (Despliegue):** no aplica una migración nueva (el esquema de `lote`/`carton` ya
existe desde la Fase 1). Sin bandera de features (aplicación de escritorio de un único
operador, sin despliegue gradual). Riesgo de "versión vieja corriendo a la vez que la nueva":
no aplica (no hay servidor).

**Sección 10 (Trayectoria a largo plazo):** reversibilidad 5/5 — cualquier repo/servicio
nuevo se puede editar libremente hasta que haya datos reales (regla ya escrita en
`convenciones-codigo.md` para la migración 001). Deuda técnica introducida: ninguna nueva;
`regenerar_lote` sin llamador es la única pieza que podría envejecer mal si Fase 3 cambia de
enfoque — de ahí que se difiera (Decisión de Gusto D1).

**Sección 11 (Diseño — ámbito UI detectado, se ejecuta):** ver la Fase 2 completa de
`/autoplan` más abajo (revisión de diseño dedicada) — aquí solo la mirada de alto nivel del
CEO: jerarquía de información correcta (evento → sección "Cartones" → generar/consultar);
sin estados de carga/vacío/error documentados todavía en el plan de UI — **hallazgo, resuelto
en la Fase de Diseño de abajo**, no se duplica aquí.

---

### "Fuera de alcance" (NOT in scope)

- Exportar cartones a Excel/PDF (E5) — pertenece a la Fase 3 (impresión) y a la Fase 4
  (conciliación). Diferido a `TODOS.md`.
- Reescritura del algoritmo con NumPy (Enfoque C) — sin problema de escala real que resolver
  en el alcance documentado.
- Cualquier UI de venta o registro de comprador — Fase 4.
- Marcado de números / evaluación de patrón sobre `CuadriculaCarton` — Fase 5; esta fase solo
  construye la superficie visual, no la lógica de juego.

### "Qué ya existe"

Ver tabla completa en la sección 0 (auditoría previa) al inicio del documento.

### Delta de estado ideal

Al cerrar esta fase, el sistema queda a mitad de camino exacto hacia el estado ideal a 12
meses: tiene cartones reales y un widget de visualización reutilizable, que es precisamente
lo que la Fase 3 (impresión) y la Fase 5 (sorteo) necesitan como insumo. No hay retroceso ni
desvío del camino.

### Registro de Errores y Rescate (Sección 2)

```
CODEPATH                              | QUÉ PUEDE FALLAR              | CLASE DE EXCEPCIÓN
---------------------------------------|-------------------------------|---------------------
servicio_cartones.generar_lote         | cantidad <= 0                 | ErrorValidacion
                                        | prefijo_codigo vacío          | ErrorValidacion
                                        | evento_id inexistente         | ErrorNoEncontrado
                                        | colisión de firma (rarísimo)  | (interno, reintento — no escapa)
                                        | UNIQUE violada en insert real | ErrorIntegridad (tipo="unique")
                                        | conexión bloqueada (SQLITE_BUSY)| ErrorBaseBloqueada
                                        | cancelación a mitad de bloque | (controlado, no es excepción)
repo_carton.crear_varios               | FK lote_id inexistente        | ErrorIntegridad (tipo="foreign_key")
Tarea.run() (ya existente)             | cualquier excepción no ErrorBingo | ErrorBingo("error.desconocido")
vista_cartones (botón generar)         | doble clic mientras corre     | (UI: deshabilitar botón, no hay excepción)
---------------------------------------|-------------------------------|---------------------

CLASE DE EXCEPCIÓN            | ¿RESCATADA? | ACCIÓN DE RESCATE                  | QUÉ VE EL USUARIO
-------------------------------|-----------|--------------------------------------|-------------------
ErrorValidacion                | Sí        | mensaje en línea junto al campo     | "Cantidad inválida" / "Prefijo vacío"
ErrorNoEncontrado               | Sí        | franja no modal                     | "Evento no encontrado"
ErrorIntegridad (unique)        | Sí        | reintento interno del cartón (no llega a la vista) | nada (transparente)
ErrorIntegridad (foreign_key)   | Sí        | franja no modal, con detalle al log | "No se pudo guardar el lote"
ErrorBaseBloqueada              | Sí        | franja no modal con acción "Reintentar" | "Base de datos ocupada, reintentar"
Cancelación a mitad de bloque   | Sí        | rollback E2 + barrido de huérfanos al reabrir | "Generación cancelada"
```

Ninguna fila queda con RESCATADA=No / PRUEBA=No / USUARIO VE=Silencioso → sin GAP crítico
tras incorporar E2.

### Registro de Modos de Fallo

```
CODEPATH                    | MODO DE FALLO                  | RESCATADO | PROBADO | USUARIO VE | REGISTRADO
-----------------------------|--------------------------------|-----------|---------|------------|------------
generar_lote                | proceso muere a mitad de bloque | Sí (E2, al reabrir) | Sí (E2 test) | Ve el lote reaparecer limpio la próxima vez | Sí (auditoría)
generar_lote                | cancelación normal (usuario)    | Sí        | Sí      | "Generación cancelada" | Sí
crear_varios (batch insert)  | violación UNIQUE por bug futuro | Sí (rollback de bloque vía transaccion()) | Sí | franja de error | Sí
vista_cartones               | doble clic en "Generar"         | Sí (deshabilitar botón) | Sí (test UI) | botón inactivo, sin doble tarea | N/A
```

Sin filas CRÍTICAS tras las decisiones tomadas arriba.

### Resumen de finalización — Fase 1 (CEO)

```
+====================================================================+
|            MEGA PLAN REVIEW — RESUMEN DE FINALIZACIÓN (CEO)        |
+====================================================================+
| Modo seleccionado     | SELECTIVE EXPANSION                          |
| Auditoría de sistema  | Fase 1 cerrada; Tarea y placeholder listos  |
| Paso 0                | Premisas aceptadas; Enfoque B recomendado    |
| Sección 1  (Arq)      | 1 hallazgo (rollback no atómico) — resuelto E2|
| Sección 2  (Errores)  | 10 codepaths mapeados, 0 GAPS tras E2       |
| Sección 3  (Seguridad)| 0 hallazgos (sin superficie de red)          |
| Sección 4  (Datos/UX) | 2 casos borde de interacción, ambos resueltos|
| Sección 5  (Calidad)  | 1 riesgo anotado (API de Fase 5), mitigado   |
| Sección 6  (Pruebas)  | diagrama en Eng §3, 0 gaps tras E3           |
| Sección 7  (Rendim.)  | 0 hallazgos nuevos (E3 cubre la aserción)    |
| Sección 8  (Observ.)  | 0 gaps (auditoría + log ya suficientes)      |
| Sección 9  (Despliegue)| no aplica (sin migración, sin servidor)      |
| Sección 10 (Futuro)   | reversibilidad 5/5, 1 ítem diferido (D1)     |
| Sección 11 (Diseño)   | ver Fase 2 de /autoplan (Design Review)      |
+--------------------------------------------------------------------+
| Fuera de alcance       | escrito (4 ítems)                            |
| Qué ya existe          | escrito                                      |
| Delta de estado ideal  | escrito                                      |
| Registro errores/rescate| 10 codepaths, 0 GAPS críticos               |
| Modos de fallo         | 4 total, 0 CRÍTICOS                          |
| TODOS.md               | 1 ítem propuesto (E5)                        |
| Propuestas de alcance  | 5 propuestas, 3 aceptadas (E2,E3,E4), 1 diferida (E5), 1 en gate (E1) |
| Voz externa            | Claude subagent (Codex no disponible) — [subagent-only] |
| Diagramas producidos   | 2 (dependencias, flujo de datos)             |
| Decisiones sin resolver| 2 (D1: regenerar_lote ahora/después: D2: año del código) |
+====================================================================+
```

---

## FASE 2 DE /autoplan — Revisión de Diseño (ámbito UI detectado)

### Paso 0 — Alcance de diseño

**0A. Calificación inicial:** el borrador de §2.7/§2.8 (antes de las correcciones de esta
fase) calificaba **4/10** en completitud de diseño — describía qué hace el backend
(generar, listar, buscar) pero dejaba layout, estados vacío/sin-selección, y la elección de
widget de lista sin decidir. Un 10/10 para este plan específico especifica: layout exacto,
los cinco estados de interacción por función, el canal de cada tipo de feedback, y el
tratamiento visual del espacio libre — sin dejar ninguna decisión de UI "a discreción del
implementador". Tras las correcciones ya aplicadas a §2.7/§2.8 (arriba), la calificación sube
a **8/10** — quedan pendientes el detalle de accesibilidad y una decisión de gusto sobre el
diálogo de "Generar lote" (ver Pase 7).

**0B. Estado de DESIGN.md:** no existe `DESIGN.md` ni `docs/designs/` en el repositorio. El
proyecto usa en su lugar `docs/decisiones.md` (decisión DU-1: tema neutro fijo, colores de
marca solo en identidad — logo, franja, tarjeta — nunca repintan la interfaz del operador).
Se calibra contra esa decisión explícita en vez de un sistema de diseño formal.

**0C. Aprovechamiento de patrones existentes:** `_OBJETO_CHIP` y el patrón de chip de estado
de `espacio_evento.py` se reutilizan tal cual para el panel de resumen. `vista_datos_evento.py`
es la plantilla de layout de una vista dentro del espacio del evento, aunque esta vista
necesita maestro-detalle (dos paneles) donde `vista_datos_evento` es de una sola columna —
no hay un patrón maestro-detalle existente en el proyecto que copiar; esta fase lo introduce
por primera vez (anotado, no es un defecto: alguien tiene que ser el primero).

**0D. Áreas de foco:** las 7 dimensiones se ejecutan completas (autoplan no recorta).

### 0.5 Voces duales — Diseño

**Codex:** no disponible → `[subagent-only]`.

**CLAUDE SUBAGENT (diseño — revisión independiente), resumido (texto completo arriba, ya
incorporado a §2.7/§2.8):**

> 0. CRÍTICO — el plan se remitía a una sección de diseño que todavía no existía en el
>    momento de la revisión (autorreferencia rota). **Resuelto:** esta sección es esa
>    referencia, ahora completa.
> 1. ALTA — jerarquía de información ausente (layout no dibujado). **Resuelto** con el
>    diagrama ASCII de §2.8.
> 2. CRÍTICA — estado vacío mencionado solo en una prueba, nunca diseñado (es el primer
>    contacto real de cada operador). **Resuelto** con el bloque "Estado vacío" de §2.8.
> 3. ALTA — elección de widget de lista sin decidir ("QTableView o QListWidget").
>    **Resuelto**, fijado a `QTableView` con modelo paginado.
> 4. MEDIA — estado por defecto del visor sin selección, indefinido. **Resuelto** con
>    `CuadriculaCarton.limpiar()` y el texto de placeholder.
> 5. MEDIA — tratamiento visual del espacio libre no especificado, y sin color de marca
>    disponible por el tema neutro fijo (DU-1). **Resuelto** con el texto `carton.libre`.
> 6. MEDIA — el contador "cartones/seg" (E4) aprobado en CEO pero huérfano, no incorporado
>    a la especificación de la vista. **Resuelto**, movido a la línea de progreso en §2.8.
> 7. BAJA/MEDIA — canal de confirmación de éxito sin fijar. **Resuelto**, franja no modal
>    en tono de éxito, mismo componente que los errores.

```
DESIGN LITMUS SCORECARD — TABLA DE CONSENSO:
═══════════════════════════════════════════════════════════════
  Dimensión                              Claude   Codex   Consenso
  ──────────────────────────────────── ─────── ─────── ─────────
  1. Jerarquía de información            4→8/10  N/A     N/A (voz única)
  2. Cobertura de estados                3→8/10  N/A     N/A (voz única)
  3. Coherencia del recorrido            7/10    N/A     N/A (voz única)
  4. Riesgo de "AI slop" (genérico)      Bajo tras fijar layout N/A N/A
  5. Alineación con sistema de diseño    Cumple DU-1 (tema neutro) N/A N/A
  6. Responsivo / accesibilidad          Sin evaluar aún (Pase 6) N/A N/A
═══════════════════════════════════════════════════════════════
Todas las filas N/A por falta de segunda voz (Codex no instalado), no por desacuerdo.
Los 8 hallazgos de la voz disponible ya se incorporaron al plan (ver arriba) — cero
hallazgos pendientes de esta ronda.
```

### Pase 1: Arquitectura de información

Orden de lectura confirmado: panel de resumen (contexto de estado del evento en cartones) →
acción principal ("Generar lote", único CTA cuando está vacío) → una vez hay cartones,
listado + visor en paralelo (maestro-detalle). Coincide con "hierarchy as service": el
operador primero entiende dónde está parado (resumen), luego actúa o consulta. Sin
hallazgos adicionales tras las correcciones de §2.8.

### Pase 2: Cobertura de estados de interacción

```
FUNCIÓN                  | CARGA              | VACÍO             | ERROR              | ÉXITO                | PARCIAL
--------------------------|--------------------|-------------------|--------------------|-----------------------|------------------
Generar lote              | barra + contador   | N/A               | franja de error    | franja de éxito       | cancelación → vuelve a vacío o al conteo previo
Listado de cartones       | N/A (síncrono, repo)| panel + CTA grande| franja no modal    | filas visibles         | filtro sin resultados → "ningún cartón coincide" (nueva, ver abajo)
Visor de cartón           | N/A (instantáneo)  | placeholder "sin selección" | N/A (no falla)| dibuja el cartón       | N/A
Búsqueda por código       | N/A                | mismo vacío del listado | N/A            | resalta/filtra fila    | código no encontrado → mensaje inline bajo el campo
```

**Hallazgo nuevo (menor, auto-decidido con P1 completitud):** "filtro sin resultados" (estado
parcial del listado) no tenía texto asignado — se añade `cartones.vacio.filtro` ("Ningún
cartón coincide con el filtro"), siguiendo exactamente el patrón ya usado en
`eventos.vacio.filtro` (`es.json`, visto en la auditoría de código) — mismo formato con
marcador `{texto}`, cero invención de un patrón nuevo.

### Pase 3: Recorrido del usuario y arco emocional

Storyboard: evento recién creado → pestaña "Cartones" vacía con una sola acción clara → clic
en "Generar lote" → diálogo simple (cantidad, prefijo) → progreso con cifra creciente y
cancelable → franja de éxito + listado poblado instantáneamente → explorar/buscar/verificar
visualmente un cartón. El arco no tiene quiebres tras las correcciones: el punto de mayor
riesgo emocional (la espera de varios segundos en un lote grande) ahora tiene contador visible
y opción de cancelar, en vez de una barra muda.

### Pase 4: Riesgo de "AI slop" (patrones genéricos)

El diseño evita genericidad: el maestro-detalle, los chips de estado y la franja no modal son
todos patrones que **ya existen en este proyecto concreto**, no importados de un vocabulario
de diseño ajeno. No hay tarjetas con sombra, gradientes ni iconografía decorativa sin función
— coherente con el tema neutro fijo (DU-1). Sin hallazgos.

### Pase 5: Alineación con el sistema de diseño

DU-1 (tema neutro fijo, colores de marca solo en identidad) se respeta: la cuadrícula del
cartón, los chips de estado y la franja de feedback no toman color de la organización activa
— siguen la paleta neutra de la aplicación del operador. El diagrama de plantilla de
impresión (Fase 3, `evento.plantilla_json`) es donde sí aparece la marca de la organización;
esta vista nunca es esa superficie. Sin hallazgos.

### Pase 6: Responsivo y accesibilidad

- **Responsivo:** la ventana de escritorio no tiene breakpoints móviles (Windows 10/11,
  plataforma fija) — el layout maestro-detalle debe usar un `QSplitter` (no proporciones
  fijas en píxeles) para que el usuario pueda redimensionar panel de lista vs. visor según su
  monitor; se añade esta nota a §2.8 como requisito, no como sugerencia.
- **Accesibilidad:** navegación por teclado — `QTableView` da foco y flechas de navegación
  por defecto (Qt), sin trabajo adicional; el diálogo de "Generar lote" debe tener foco
  inicial en el campo "cantidad" y `Tab` en orden lógico cantidad→prefijo→Generar→Cancelar
  (siguiendo `ui/atajos.py`, ya existente en Fase 1, sin necesidad de un mecanismo nuevo).
  Contraste: heredado del tema neutro global de la aplicación (fuera del alcance de esta
  fase decidir contraste de tema, ya resuelto en Fase 1 con `ui/tema.py`).

**Hallazgo (menor):** el plan no mencionaba `QSplitter` explícitamente. **Auto-decidido**
(P5 explícito): se añade como requisito de §2.8 arriba en el diagrama de layout ("┬"
representa el splitter, no una división fija).

### Pase 7: Decisiones de diseño sin resolver

Una sola queda abierta, y es de gusto, no de completitud — pasa al gate final:

- **D3 (nueva, de diseño):** el diálogo de "Generar lote" — ¿modal bloqueante (`QDialog.exec()`)
  o un panel inline dentro de la propia vista (como el editor de organización en
  `vista_organizaciones.py`, si sigue ese patrón)? Ambos son razonables; no hay ganador claro
  por completitud (ambos cubren los mismos campos). Se marca como Decisión de Gusto D3 en el
  gate final. Recomendación por defecto: modal simple (`QDialog`), coherente con que es una
  acción puntual de un paso, no un formulario extenso como el de organización.

### "Fuera de alcance" (diseño)

- Mockups visuales pixel-perfect — este plan fija estructura y estados, no compone visuales;
  no hay herramienta de mockup de gstack disponible/solicitada en este flujo de `/autoplan`.
- Animación de la barra de progreso más allá de lo estándar de Qt — sin valor añadido
  detectado para una barra de progreso de generación en lote.

### "Qué ya existe" (diseño)

`_OBJETO_CHIP`, la franja de error de `ui/dialogos.py`, el patrón de vista-dentro-del-evento
de `vista_datos_evento.py`, y `ui/atajos.py` para el orden de tabulación — los cuatro se
reutilizan sin modificación.

### TODOS.md (diseño)

Ninguno propuesto — todos los hallazgos de esta fase se resolvieron dentro del propio plan
(no hay expansión de alcance real, solo especificación completa de lo ya planeado).

### Resumen de finalización — Fase 2 (Diseño)

```
+====================================================================+
|            DESIGNER'S EYE PLAN REVIEW — RESUMEN                    |
+====================================================================+
| Calificación inicial   | 4/10                                       |
| Calificación final     | 8/10                                       |
| DESIGN.md               | no existe — calibrado contra DU-1          |
| Pase 1 (Info arch)      | 0 hallazgos tras corrección de layout      |
| Pase 2 (Estados)        | 1 hallazgo (filtro sin resultados) — resuelto |
| Pase 3 (Recorrido)      | 0 quiebres tras corrección                 |
| Pase 4 (AI slop)        | 0 hallazgos                                |
| Pase 5 (Sistema diseño) | 0 hallazgos, cumple DU-1                   |
| Pase 6 (Responsivo/A11y)| 1 hallazgo (QSplitter) — resuelto            |
| Pase 7 (Sin resolver)   | 1 decisión de gusto (D3) → gate final        |
| Voz externa             | Claude subagent (Codex no disponible)        |
| Decisiones sin resolver | 1 (D3)                                       |
+====================================================================+
```

---

## FASE 2.5 DE /autoplan — Revisión DX

**Omitida.** No se detectó ámbito de cara a desarrolladores en el Paso 0: la Fase 2 no
expone API, CLI, SDK, webhook ni ninguna integración para terceros programadores — el
"cliente" es un operador de bingo usando una aplicación de escritorio, no un desarrollador
integrando con este sistema.

---

## FASE 3 DE /autoplan — Revisión de Ingeniería (Eng, siempre última — revisa el plan ya
enmendado por CEO y Diseño)

### Paso 0 — Desafío de alcance

El plan toca 9 archivos nuevos y 3 ediciones de una línea o pocas líneas
(`registro_vistas.py`, `estados.py`, `modelos.py`) más una edición de `001_inicial.sql` (para
`completado_en`) y de `__main__.py` (gancho del barrido de huérfanos). Ninguna reducción de
alcance se justifica: cada pieza traza a un criterio de aceptación del contrato de fase o a un
hallazgo de esta misma revisión. Mapa de sub-problema → código ya existente: ver la tabla de
la sección 0 al inicio del documento (auditoría previa) — no se repite aquí.

### 0.5 Voces duales — Eng

**Codex:** no disponible → `[subagent-only]`.

**CLAUDE SUBAGENT (eng — revisión independiente), hallazgos y su resolución:**

> 1. Arquitectura sana, sin violación de capas; acoplamiento real: `generar_lote` corre 1 +
>    N/500 + posiblemente 1 transacciones **separadas**, no una operación atómica — un
>    fallo entre dos de ellas es un resultado válido a diseñar, no un caso de borde.
>    **Resuelto:** exactamente ese es el trabajo del barrido de huérfanos (E2, corregido) —
>    se documenta explícitamente como el modelo de consistencia (ver diagrama de
>    arquitectura abajo, nota sobre atomicidad).
> 2. A 10x (100.000 cartones): sin tope superior en `cantidad`, y el `set` de firmas en
>    memoria crecería sin límite operable. **Resuelto:** `LIMITE_CARTONES_POR_LOTE = 50.000`
>    en `config/ajustes.py`, validado con `ErrorValidacion` (ya incorporado a §2.6).
> 3. Bucle de reintento de colisión de firma sin tope — bucle infinito real con una semilla
>    mal configurada. **Resuelto:** tope de 1.000 colisiones consecutivas → `ErrorDominio`
>    (ya incorporado a §2.6).
> 4. Prefijo repetido entre dos lotes del mismo evento no está prevenido — la secuencia
>    reinicia en 1 por lote y choca en `UNIQUE(evento_id, codigo)` a mitad de bloque.
>    **Resuelto:** `repo_lote.existe_prefijo` valida antes de generar (ya incorporado a
>    §2.4 y §2.6).
> 5. **CRÍTICO — E2 (barrido de huérfanos) tal como se escribió en la revisión CEO era
>    autocontradictorio:** su condición (a) ("último evento de auditoría es
>    `lote.cancelado` sin limpieza completada") es lógicamente imposible — si esa fila de
>    auditoría existe, es porque la transacción que también borra el lote ya comprometió, así
>    que no queda nada que limpiar; si no comprometió, no existe la fila de auditoría, que es
>    la condición (b), no la (a). Un hallazgo de "resuelto" que en realidad nunca puede
>    dispararse. **Resuelto de raíz, no parcheado en el sitio:** columna `completado_en` en
>    `lote`, fijada dentro de la misma transacción de cierre o cancelación; el barrido pasa a
>    ser `WHERE completado_en IS NULL`, sin interpretar texto de auditoría (ya reescrito por
>    completo en la sección CEO de este documento y en §2.4/§2.6 arriba). Además: el barrido
>    procesa **un lote huérfano por `transaccion()`**, nunca todos en una — una fila corrupta
>    no debe bloquear la limpieza del resto (ya incorporado).
> 6. Seguridad: sin longitud/charset validado en `prefijo_codigo`, que termina impreso en un
>    cartón físico en la Fase 3. **Resuelto:** máximo 12 caracteres, charset `[A-Za-z0-9-]`
>    (ya incorporado a §2.6).

```
ENG DUAL VOICES — TABLA DE CONSENSO:
═══════════════════════════════════════════════════════════════
  Dimensión                              Claude   Codex   Consenso
  ──────────────────────────────────── ─────── ─────── ─────────
  1. ¿Arquitectura sólida?               Sí, con nota de atomicidad N/A N/A (voz única)
  2. ¿Cobertura de pruebas suficiente?   No (hasta incorporar 6 casos) → ahora sí N/A N/A
  3. ¿Riesgos de rendimiento cubiertos?  No (sin tope) → ahora sí         N/A N/A
  4. ¿Amenazas de seguridad cubiertas?   No (prefijo sin validar) → ahora sí N/A N/A
  5. ¿Rutas de error manejadas?          1 crítico (E2 roto) → corregido de raíz N/A N/A
  6. ¿Riesgo de despliegue manejable?    N/A (sin despliegue en esta fase) N/A N/A
═══════════════════════════════════════════════════════════════
Todas las filas N/A por falta de segunda voz. El hallazgo #5 se trata como CRÍTICO pese a
venir de una sola voz — regla de degradación de /autoplan: un hallazgo crítico de la voz
disponible no se descarta por falta de consenso.
```

### Sección 1: Arquitectura

```
                         ┌────────────────────────────┐
                         │   VistaCartones (nueva)     │
                         │   ui/vistas/vista_cartones  │
                         └───────────┬────────────────┘
                                     │ lanza / conecta señales
                         ┌───────────▼────────────────┐
                         │   Tarea (Fase 1, sin cambios)│
                         │   QThread: progreso/terminado│
                         │   /fallado, cancelar()       │
                         └───────────┬────────────────┘
                                     │ ejecuta en su propio hilo
                         ┌───────────▼────────────────┐
                         │ servicio_cartones (nuevo)    │
                         │ generar_lote / regenerar_lote │
                         │ limpiar_lotes_huerfanos       │
                         └──┬──────────────┬───────────┘
                            │              │
                 ┌──────────▼───┐   ┌──────▼──────────┐
                 │ repo_lote     │   │ repo_carton      │
                 │ (nuevo)       │   │ (nuevo)          │
                 └──────────┬───┘   └──────┬───────────┘
                            │              │
                            └──────┬───────┘
                                   │ opera sobre
                         ┌─────────▼──────────┐
                         │ dominio/carton.py    │   dominio/estados.py (editado:
                         │ (nuevo, Python puro) │   + TRANSICIONES_CARTON)
                         └──────────────────────┘   dominio/modelos.py (editado:
                                                       + Lote, Carton)

Nota de atomicidad (hallazgo Eng #1): generar_lote NO es una única transacción — es 1
(crear lote) + N/500 (bloques) + a lo sumo 1 (cierre/cancelación), cada una `transaccion()`
independiente por diseño (evita una transacción de minutos abierta). El modelo de
consistencia real no es "todo o nada en una operación" sino "todo commit parcial se resuelve
solo, sin intervención humana, en el siguiente arranque" — vía completado_en +
limpiar_lotes_huerfanos. Esto se documenta explícitamente aquí para que nadie en Fase 3/4/5
asuma erróneamente que generar_lote es atómico de punta a punta.
```

Acoplamiento nuevo: `VistaCartones` → `servicio_cartones` → `{repo_lote, repo_carton}` →
`{dominio/carton.py, dominio/estados.py}`. Ningún componente existente cambia su forma
pública (excepto la línea de registro en `registro_vistas.py` y la adición de dataclasses en
`modelos.py`, ambas no disruptivas). Puntos únicos de fallo: la conexión SQLite del hilo de
`Tarea` (ya gestionada por el manejador global de excepciones de la Fase 1, sin código nuevo).
Postura de rollback: ver nota de atomicidad arriba — no hay "revertir el despliegue" porque no
hay despliegue; el equivalente es simplemente no lanzar el nuevo `EntradaSeccionEvento` (una
línea en `registro_vistas.py`) si algo saliera mal en producción, lo cual es trivialmente
reversible con un `git revert`.

### Sección 2: Calidad de código

Sigue el patrón exacto de `repo_evento.py`/`servicio_eventos.py` — mismo orden de parámetros
(`con` primero), mismos verbos de la tabla de convenciones, mismo patrón `_desde_fila`/
`_a_parametros` en los repos nuevos. Sin violaciones DRY detectadas: no hay lógica de
paginación, transacción ni traducción de errores reimplementada — todo reutiliza los módulos
transversales ya existentes. Complejidad ciclomática: `generar_lote` es la función más
compleja del plan (validaciones + bucle con dos rupturas posibles: cancelación y tope de
colisiones + cierre). Se mantiene en una sola función porque cada rama está descrita en la
propia especificación de negocio del contrato — dividirla en sub-funciones privadas
(`_generar_bloque`, `_validar_parametros`) es una decisión de implementación razonable pero no
se prescribe aquí como obligatoria (es "explícito", no "clever", cualquiera de las dos formas
cumple P5).

### Sección 3: Revisión de pruebas

Diagrama completo y tabla de cobertura por ítem (21 casos, 6 añadidos por esta revisión) ya
escritos como **artefacto en disco**:
`C:\Users\Gabo\.gstack\projects\Bingo_App\gabriel-main-test-plan-20260904-231614.md` — no se
duplica aquí; ver ese archivo para el diagrama de flujos de datos, la pirámide de pruebas, el
riesgo de inestabilidad y los requisitos de carga. §2.10 de este plan (arriba) ya incorpora
los 6 casos nuevos identificados en esa revisión.

### Sección 4: Rendimiento

- **N+1:** no aplica — no hay traversal de asociaciones tipo ORM; las únicas consultas son
  `listar_firmas_por_evento` (una vez por lote, no por cartón) y los `executemany` por bloque.
- **Memoria:** el `set` de firmas en memoria es el único estructura que crece con el tamaño
  del lote — con el tope de 50.000 (hallazgo #2), el máximo son 50.000 cadenas hexadecimales
  de 64 caracteres (~3-4 MB), trivial para cualquier equipo objetivo.
- **Índices:** ya existen (`idx_carton_evento_estado`, `idx_carton_codigo`,
  `UNIQUE(evento_id, firma)`, `UNIQUE(evento_id, codigo)`) — la nueva columna
  `lote.completado_en` se consulta con `WHERE completado_en IS NULL`, sin índice dedicado
  (la tabla `lote` es de bajo volumen — un lote por generación, no por cartón — un `scan`
  completo es instantáneo incluso con miles de lotes históricos).
- **Caché:** no aplica (sin cómputo repetido costoso fuera de la propia generación).
- **Dimensionado de trabajo en segundo plano:** peor caso 50.000 cartones ≈ 100 bloques de
  500 — con `synchronous=FULL` (el valor por defecto real de `abrir_conexion`, no `NORMAL`
  como se asumía implícitamente antes de esta revisión) el costo de 100 `fsync` por lote es el
  límite de rendimiento real, no la generación en memoria. **Se documenta explícitamente
  como riesgo de hardware, no se prescribe bajar `synchronous`** — bajarlo comprometería la
  garantía de durabilidad que el resto de la aplicación (sorteo en vivo, Fase 5) necesita
  sobre la misma conexión de patrón; la prueba E3 usa un margen de 10s precisamente para
  absorber esta variable sin ser inestable en hardware lento.
- **Presión de conexiones:** una conexión nueva por invocación de `Tarea` (regla de una
  conexión por hilo), cerrada en su `finally` — sin acumulación.

### "Fuera de alcance" (Eng)

- Dividir `generar_lote` en sub-funciones privadas — mejora de legibilidad opcional, no
  bloqueante, decisión de implementación.
- Bajar `synchronous` para acelerar la escritura por bloques — compromete durabilidad que
  otras fases (5, sorteo en vivo) necesitan sobre el mismo patrón de conexión; fuera de
  alcance de esta fase decidirlo unilateralmente.
- Índice dedicado sobre `lote.completado_en` — volumen de filas demasiado bajo para
  justificarlo.

### "Qué ya existe" (Eng)

`Tarea`, `transaccion()`, `traducir_errores_sqlite()`, `puede_transicionar()`,
`repo_auditoria.registrar`, el patrón `_desde_fila`/`_a_parametros` de `repo_evento.py` — los
seis se reutilizan sin ninguna modificación de su forma pública.

### Registro de Modos de Fallo (Eng, ampliado sobre el de CEO)

```
CODEPATH                         | MODO DE FALLO                         | RESCATADO | PROBADO | USUARIO VE                    | REGISTRADO
-----------------------------------|----------------------------------------|-----------|---------|-------------------------------|------------
generar_lote                      | cantidad > 50.000                     | Sí        | Sí (#9) | mensaje en línea, campo cantidad | N/A (rechazado antes de escribir)
generar_lote                      | prefijo repetido en el evento          | Sí        | Sí (#10)| mensaje en línea, campo prefijo  | N/A
generar_lote                      | prefijo con carácter inválido/largo    | Sí        | Sí (#11)| mensaje en línea, campo prefijo  | N/A
generar_lote                      | 1.000 colisiones de firma consecutivas | Sí        | Sí (#12)| franja de error                  | Sí (auditoría + log app)
generar_lote                      | proceso muere a mitad de bloque        | Sí (barrido, próximo arranque) | Sí (#14) | ve el lote desaparecer limpio | Sí
limpiar_lotes_huerfanos           | un huérfano corrupto entre varios      | Sí (transacción por lote) | Sí (#14) | los demás se limpian igual   | Sí
```

Sin filas CRÍTICAS — el único CRÍTICO real de todo el plan (E2 autocontradictorio) se corrigió
de raíz, no se dejó como gap documentado.

### Resumen de finalización — Fase 3 (Eng)

```
+====================================================================+
|            ENG PLAN REVIEW — RESUMEN DE FINALIZACIÓN                |
+====================================================================+
| Sección 1  (Arq)       | 1 nota de atomicidad documentada, 0 gaps    |
| Sección 2  (Calidad)   | 0 violaciones DRY, complejidad justificada  |
| Sección 3  (Pruebas)   | diagrama + artefacto en disco, 6 casos añadidos |
| Sección 4  (Rendim.)   | 1 riesgo de hardware documentado (fsync), sin acción prescrita |
| Fuera de alcance        | escrito (3 ítems)                            |
| Qué ya existe           | escrito (6 piezas reutilizadas sin cambio)   |
| Modos de fallo          | 6 total, 0 CRÍTICOS (1 corregido de raíz)    |
| Artefacto de pruebas    | gabriel-main-test-plan-20260904-231614.md    |
| Voz externa             | Claude subagent (Codex no disponible)        |
| Decisiones sin resolver | 0 nuevas en Eng (D1-D3 ya en el gate)         |
+====================================================================+
```

---

## Registro de Decisiones Autónomas (Decision Audit Trail)

| # | Fase | Decisión | Clasificación | Principio | Justificación | Rechazado |
|---|---|---|---|---|---|---|
| 1 | CEO | Enfoque B (dominio+repos+servicio+UI completa) sobre A (mínimo) y C (NumPy) | Mecánica | P1 completitud | Único enfoque que cumple los 5 criterios de aceptación del contrato firmado | A (incompleto), C (dependencia sin problema real) |
| 2 | CEO | `repo_lote.py` añadido pese a no estar listado explícitamente en el contrato | Mecánica | P1 completitud | `carton.lote_id` es `NOT NULL REFERENCES lote(id)` — sin este repo no hay forma de insertar un cartón | — |
| 3 | CEO | E2 (barrido de huérfanos) y E3 (prueba de tiempo acotado) incorporados al alcance | Mecánica | P1 completitud | Ambos cierran huecos que el propio contrato de esta fase ya promete ("sin huérfanos", "10.000 en segundos") | — |
| 4 | CEO | E4 (contador cartones/seg) incorporado | Mecánica | P3 pragmático | Una línea de UI, sin riesgo, mejora la percepción de progreso en esperas largas | — |
| 5 | CEO | E5 (exportar a Excel/PDF ahora) diferido a TODOS.md | Mecánica | P2 boil lakes | Fuera del radio de impacto de esta fase — es trabajo de la Fase 3/4 | Incluir ahora |
| 6 | CEO | `carton_desde_orden_canonico` añadida al dominio, no listada en el contrato original | Mecánica | P5 explícito | El visor no puede reconstruir la matriz 5x5 desde la cadena persistida sin ella — hueco obvio, no una decisión de arquitectura | — |
| 7 | Diseño | Layout maestro-detalle fijado explícitamente (antes: lista de viñetas sin dibujar) | Mecánica | P5 explícito, P1 completitud | Un implementador no debe inventar el reparto de espacio entre lista y visor | — |
| 8 | Diseño | `QTableView` con modelo paginado, sobre `QListWidget` | Mecánica | P5 explícito | Orden por columna + escalado a miles de filas; el "o" del borrador era una decisión de arquitectura de UI disfrazada de detalle | QListWidget |
| 9 | Diseño | Estado vacío y estado "sin selección" diseñados con texto y CTA específicos | Mecánica | P1 completitud | Primer contacto real de cada operador con la vista — no es un caso raro que se pueda dejar sin especificar | — |
| 10 | Diseño | `QSplitter` para el layout responsivo en vez de proporciones fijas | Mecánica | P5 explícito | Ventana de escritorio redimensionable; proporciones fijas en píxeles se rompen en monitores distintos | — |
| 11 | Diseño | Confirmación de éxito por franja no modal, reutilizando el canal de error existente | Mecánica | P4 DRY | Evita introducir un cuarto canal de feedback (modal, franja, toast, y ahora otro) | Toast nuevo |
| 12 | Eng | Límite de 50.000 cartones por lote (`LIMITE_CARTONES_POR_LOTE`) | Mecánica | P1 completitud | Sin tope, `cantidad` arbitrariamente grande no está cubierto por ningún criterio de aceptación ni prueba | Sin límite |
| 13 | Eng | Tope de 1.000 colisiones de firma consecutivas → `ErrorDominio` | Mecánica | P1 completitud | Bucle infinito real con una semilla mal configurada; error con nombre es mejor que un proceso colgado | Reintento sin límite |
| 14 | Eng | Validar `(evento_id, prefijo_codigo)` único antes de generar | Mecánica | P5 explícito | Sin esto, dos lotes con el mismo prefijo chocan a mitad de bloque con un error de integridad genérico y difícil de diagnosticar | Continuar secuencia desde el máximo existente (más código, mismo resultado) |
| 15 | Eng | Validación de charset/longitud de `prefijo_codigo` (máx. 12, `[A-Za-z0-9-]`) | Mecánica | P1 completitud | El prefijo termina impreso en el cartón físico en la Fase 3 — validarlo dos fases antes evita un defecto de impresión | — |
| 16 | Eng | **E2 rediseñado de raíz:** columna `lote.completado_en` en vez de inferir el estado del texto de auditoría | Mecánica (corrección de un error lógico, no una preferencia) | P5 explícito | La condición (a) de la primera versión de E2 era imposible por construcción — no es una decisión de gusto entre dos opciones válidas, es arreglar un hallazgo roto | Parchear la lógica de auditoría en el sitio |
| 17 | Eng | Barrido de huérfanos procesa un lote por `transaccion()`, nunca todos en una | Mecánica | P1 completitud | Una fila corrupta no debe bloquear la limpieza del resto | Una sola transacción para todo el barrido |
| D1 | CEO | `regenerar_lote` implementado ahora sin llamador real en esta fase | **Decisión de gusto** | — | Misma función, distinto parámetro, pero sin verificación end-to-end hasta que algo la use | — (pendiente de confirmación del usuario en el gate) |
| D2 | CEO | Año del código correlativo = año de generación, no año del evento | **Decisión de gusto** | — | Juicio de negocio (qué significa el año en el código), no técnico — nadie fuera de este documento lo confirmó | — (pendiente) |
| D3 | Diseño | Diálogo de "Generar lote": modal (`QDialog`) vs panel inline en la vista | **Decisión de gusto** | — | Ambos cubren los mismos campos con completitud equivalente — es una preferencia de interacción, no una brecha | — (pendiente) |

---

## Tareas de implementación (agregadas de las 3 fases de revisión)

Sintetizadas de los hallazgos de arriba. Ejecutables con Claude Code o a mano; marcar al
completar. Ninguna requiere una decisión de gusto pendiente para empezar (D1-D3 solo afectan
alcance/detalle menor, no bloquean el resto).

- [ ] **T1 (P1, humano: ~4h / CC: ~20min) — dominio** — Crear `dominio/carton.py` con
  `generar_carton`, `orden_canonico`, `firma`, `numeros_por_bit`, `indice_bit`,
  `carton_desde_orden_canonico` y sus pruebas (`tests/dominio/test_carton.py`)
  - Surgido de: Contrato §2.1 + hallazgo CEO #6 (función de deserialización añadida)
  - Archivos: `src/bingo/dominio/carton.py`, `tests/dominio/test_carton.py`
  - Verificar: `pytest tests/dominio/test_carton.py -m "not lento"`

- [ ] **T2 (P1, humano: ~1h / CC: ~10min) — dominio** — Añadir `TRANSICIONES_CARTON` a
  `dominio/estados.py` y sus dataclasses `Lote`/`Carton` a `dominio/modelos.py`
  - Surgido de: Contrato §2.3 + Eng (columna `completado_en`)
  - Archivos: `src/bingo/dominio/estados.py`, `src/bingo/dominio/modelos.py`
  - Verificar: `pytest tests/dominio/test_estados.py`

- [ ] **T3 (P1, humano: ~2h / CC: ~15min) — persistencia** — Editar `001_inicial.sql`
  (añadir `lote.completado_en TEXT`); correr `python -m bingo --reiniciar-datos`
  - Surgido de: Eng, hallazgo #5 (E2 rediseñado)
  - Archivos: `src/bingo/persistencia/migraciones/001_inicial.sql`
  - Verificar: `pytest tests/persistencia/test_esquema.py tests/persistencia/test_migraciones.py`

- [ ] **T4 (P1, humano: ~4h / CC: ~25min) — persistencia** — Crear `repo_lote.py` y
  `repo_carton.py` con los verbos de §2.4/§2.5 y sus pruebas, incluyendo el `EXPLAIN QUERY
  PLAN` sobre `obtener_por_codigo`
  - Surgido de: Contrato §2.4 + hallazgo CEO #2 (`repo_lote.py` no listado explícitamente)
  - Archivos: `src/bingo/persistencia/repo_lote.py`, `src/bingo/persistencia/repo_carton.py`,
    `tests/persistencia/test_repo_lote.py`, `tests/persistencia/test_repo_carton.py`
  - Verificar: `pytest tests/persistencia/test_repo_lote.py tests/persistencia/test_repo_carton.py`

- [ ] **T5 (P1, humano: ~5h / CC: ~35min) — servicios** — Crear `servicio_cartones.py` con
  `generar_lote` y `limpiar_lotes_huerfanos`, incluyendo las 4 validaciones nuevas de Eng
  (tope de cantidad, prefijo repetido, charset de prefijo, tope de colisiones).
  `regenerar_lote` queda fuera de esta tarea (D1, diferido a Fase 3 — ver `TODOS.md`)
  - Surgido de: Contrato §2.2 + hallazgos Eng #2, #3, #4, #5, #6
  - Archivos: `src/bingo/servicios/servicio_cartones.py`,
    `tests/servicios/test_servicio_cartones.py`
  - Verificar: `pytest tests/servicios/test_servicio_cartones.py`

- [ ] **T6 (P1, humano: ~1h / CC: ~5min) — arranque** — Enganchar
  `limpiar_lotes_huerfanos` en `__main__.py` tras aplicar migraciones, antes de mostrar la
  ventana
  - Surgido de: Eng, hallazgo #5 (E2 rediseñado)
  - Archivos: `src/bingo/__main__.py`, `tests/test_arranque.py`
  - Verificar: `pytest tests/test_arranque.py`

- [ ] **T7 (P2, humano: ~6h / CC: ~35min) — UI** — Crear
  `ui/widgets/cuadricula_carton.py` (con estado "sin selección" y tratamiento del espacio
  libre) y `ui/vistas/vista_cartones.py` (layout maestro-detalle con `QSplitter`, estado
  vacío, `QTableView` paginado, franja de éxito)
  - Surgido de: Contrato §2.5 + hallazgos de diseño (Pases 1, 2, 6)
  - Archivos: `src/bingo/ui/widgets/cuadricula_carton.py`,
    `src/bingo/ui/vistas/vista_cartones.py`, `tests/ui/test_vista_cartones.py`
  - Verificar: `pytest tests/ui/test_vista_cartones.py`

- [ ] **T8 (P2, humano: ~15min / CC: ~5min) — registro** — Cambiar
  `EntradaSeccionEvento("espacio_evento.seccion.cartones", None)` a apuntar a
  `_vista_cartones` en `ui/registro_vistas.py`
  - Surgido de: Contrato §2.5, gancho ya preparado en Fase 1
  - Archivos: `src/bingo/ui/registro_vistas.py`
  - Verificar: `pytest tests/ui/test_navegacion.py`

- [ ] **T9 (P2, humano: ~1h / CC: ~10min) — i18n** — Añadir las claves de §2.9 a `es.json` y
  `en.json`
  - Surgido de: Contrato + hallazgos de diseño (estados vacío/filtro/libre)
  - Archivos: `src/bingo/i18n/es.json`, `src/bingo/i18n/en.json`
  - Verificar: `pytest tests/test_i18n.py tests/arquitectura/test_arquitectura.py`

- [ ] **T10 (P3, humano: ~2h / CC: ~15min) — pruebas de volumen** — Prueba de 50.000
  firmas sin repetición y prueba de rendimiento de 10.000 cartones < 10s, ambas `lento`
  - Surgido de: Contrato §2.6 + hallazgo CEO #3 (E3)
  - Archivos: `tests/dominio/test_carton.py`, `tests/servicios/test_servicio_cartones.py`
  - Verificar: `pytest -m lento`

### Artefacto JSONL

No se generó `tasks-*.jsonl` vía los scripts de `~/.claude/skills/gstack/bin/` en esta
sesión — el aparato de telemetría de gstack (`gstack-review-log`, `gstack-decision-log`,
`gstack-learnings-log`) es infraestructura de sesión-a-sesión de gstack, no parte del
entregable que pediste ("crea el plan, no implementes"); se documenta aquí en su lugar la
tabla de tareas de arriba, en markdown, dentro del propio plan versionado en el repositorio
— más útil para este proyecto que un JSONL en `~/.gstack/` que nadie más en el repo puede leer.

---

## GATE FINAL DE APROBACIÓN

**No se ha escrito ni modificado ningún archivo de código fuente.** Esta sesión solo escribió:
`docs/Fase_2/Plan_Implementacion_Fase2.md` (este archivo), una entrada nueva en `TODOS.md`, y
el artefacto de plan de pruebas en `~/.gstack/projects/Bingo_App/`.

### Resumen del plan

Plan de implementación completo para la Fase 2 (generación de cartones), derivado de
`docs/Fase_2/Contrato_Fase2.md`, revisado en 3 fases (CEO, Diseño, Ingeniería) con voz
independiente de Claude en cada una (Codex no disponible en esta máquina). Un hallazgo crítico
real (el diseño original del barrido de "lote huérfano" era lógicamente autocontradictorio)
se detectó y se corrigió de raíz durante la propia revisión, antes de llegar a este gate.

### Decisiones: 17 totales (14 mecánicas, 3 de gusto)

### Decisiones de gusto (tu turno de decidir)

**D1 — ¿Implementar `regenerar_lote` ya en esta fase, o diferirlo a la Fase 3?**
Recomiendo diferirlo — es la misma función con un parámetro distinto, así que no cuesta nada
técnicamente escribirla más tarde, pero sin ningún llamador real en esta fase queda sin
verificación end-to-end hasta que la Fase 3 (donde sí hay un caso de uso: PDF perdido) la
necesite de verdad.
  Si eliges implementarla ahora: queda como código correcto pero no ejercitado por ningún
  flujo real durante toda la Fase 2 y 3 hasta que llegue su consumidor.

**D2 — ¿El año del código correlativo (`PREFIJO-AÑO-SECUENCIA`) es el año en que se genera
el lote, o el año del evento?**
Recomiendo año de generación (siempre disponible, incluso si el evento no tiene fecha
fijada todavía). El riesgo: un operador que imprime en diciembre para un evento de enero verá
cartones con el año "equivocado" desde la perspectiva de quien los recibe en la mano.

**D3 — ¿El diálogo de "Generar lote" es modal (`QDialog.exec()`) o un panel inline dentro de
la propia vista?**
Recomiendo modal — es una acción puntual de un paso (dos campos), no un formulario extenso
como el de organización; un modal comunica "esto es una acción, no una sección permanente
de la pantalla".

### Puntuaciones de revisión

- CEO: 0 hallazgos sin resolver tras E2/E3/E4 incorporados; 1 hallazgo crítico (rollback no
  atómico) resuelto con el barrido de huérfanos
- CEO Voces: Codex no disponible, Claude subagent 6 hallazgos (2 ya resueltos por diseño
  explícito del contrato, 2 incorporados al plan, 2 marcados como decisión de gusto)
- Diseño: 4/10 → 8/10 en completitud; 8 hallazgos, todos resueltos dentro del propio plan
- Diseño Voces: Codex no disponible, Claude subagent 8 hallazgos, 0 pendientes
- Eng: 1 hallazgo CRÍTICO (E2 autocontradictorio) corregido de raíz; 5 hallazgos adicionales
  incorporados (tope de cantidad, tope de colisiones, prefijo repetido, charset de prefijo,
  nota de atomicidad)
- Eng Voces: Codex no disponible, Claude subagent 6 hallazgos, 0 pendientes
- DX: omitida (sin ámbito de cara a desarrolladores)

### Temas transversales entre fases

**Tema: "el plan original subestimaba los estados de fallo intermedios"** — apareció en CEO
(rollback no atómico), Diseño (estados vacío/sin-selección no diseñados) y Eng (E2
autocontradictorio, sin tope de reintentos) de forma independiente. Señal de alta confianza:
la primera versión de este plan trataba "generar un lote" como una operación que solo tiene
éxito o cancelación, y las tres revisiones, cada una desde su ángulo, encontraron que los
estados intermedios (a mitad de generación, sin selección, huérfano tras un crash) eran los
que realmente faltaban especificar.

### Diferido a TODOS.md

- E5 — Exportar cartones a Excel/PDF ahora (pertenece a Fase 3/4). Ver `TODOS.md`, sección
  "Añadidos por `/gstack-autoplan` sobre `docs/Fase_2/Contrato_Fase2.md`".

### Tareas de implementación

Ver la tabla de 10 tareas (T1-T10) más arriba.

### Resolución del gate (Gabriel, 2026-09-04)

**APROBADO TAL CUAL** — las 3 recomendaciones por defecto quedan confirmadas:

- **D1 → diferido a Fase 3.** `regenerar_lote` NO se implementa en el alcance de esta fase;
  se anota en `TODOS.md` junto a E5, con dependencia "Fase 3 (cuando un PDF perdido necesite
  regenerar un lote exacto)". §2.6 de este plan se marca como referencia de diseño para ese
  momento, no como tarea de la Fase 2 (T5 arriba se ajusta: `generar_lote` y
  `limpiar_lotes_huerfanos` sí se implementan; `regenerar_lote` se retira de T5 y pasa a
  TODOS.md).
- **D2 → año de generación** (no el del evento), tal como estaba redactado en §2.6.
  Confirmado como decisión de negocio, no solo técnica.
- **D3 → diálogo modal** (`QDialog`) para "Generar lote", tal como estaba redactado en §2.8.

Plan **CERRADO Y APROBADO**. No se ha escrito ni modificado ningún archivo de código fuente en
esta sesión — el siguiente paso, cuando el usuario decida empezar a programar, es T1 en la
tabla de tareas de arriba.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via /autoplan) | Scope & strategy | 1 | CLEAR | 6 findings (Claude subagent), 4 incorporated, 2 resolved at gate (D1, D2) |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | N/A | Codex CLI not installed on this machine |
| Eng Review | `/plan-eng-review` (via /autoplan) | Architecture & tests (required) | 1 | CLEAR | 6 findings (Claude subagent), 1 critical (orphan-sweep logic) fixed at the root, 5 incorporated |
| Design Review | `/plan-design-review` (via /autoplan) | UI/UX gaps | 1 | CLEAR | 8 findings (Claude subagent), 4/10 → 8/10, 7 incorporated, 1 resolved at gate (D3) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | SKIPPED | No developer-facing scope detected (desktop app for a bingo operator, not a dev tool) |

- **CROSS-MODEL:** N/A — Codex unavailable this run; all findings are single-voice (Claude subagent), tagged `[subagent-only]` throughout.
- **VERDICT:** CEO + DESIGN + ENG CLEARED via /autoplan — plan approved by the user at the Final Approval Gate (2026-09-04) with all 3 default recommendations (D1, D2, D3) accepted. Ready to implement (T1-T10 in the aggregated task list above); no code has been written yet by design (`/autoplan` invoked in plan-only mode per the user's explicit request).

NO UNRESOLVED DECISIONS

