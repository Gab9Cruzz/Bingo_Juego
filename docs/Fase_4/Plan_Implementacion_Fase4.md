<!-- /autoplan restore point: ~/.gstack/projects/Bingo_App/feature-fase-2-cartones-autoplan-restore-20260909-145853.md -->

# Plan de implementación — FASE 4: Compradores, rondas y premios

**Generado por:** Claude Code (`/gstack-autoplan`), sobre `docs/Fase_4/Contrato_Fase4.md`.
**Fecha:** 2026-09-09 · **Rama:** `feature/fase-2-cartones` · **Commit base:** `3461b9b`
**Fuente de alcance:** `docs/Fase_4/Contrato_Fase4.md`, `docs/Plan_Fases_Bingo.md` (§FASE 4),
`docs/Documento_Tecnico.md` (§3.1, §4.4, §7, §8, §16.1), `docs/convenciones-codigo.md`, `TODOS.md`.
**No implementar nada a partir de este documento sin que Gabriel lo revise.** Este archivo es el
*plan*, no el código.

---

## 0. Contexto verificado (leído en el código, no asumido)

Todo lo de esta sección se comprobó abriendo los archivos en el commit `3461b9b` más el árbol de
trabajo de la fase 3.

- **`openpyxl>=3.1,<4` y `pillow>=10.4,<12` ya están en `pyproject.toml`.** La fase 4 no añade
  ninguna dependencia de producción: el Excel y la normalización de imágenes de premio corren con
  lo que ya se instala. (`pypdf` sigue siendo solo de desarrollo.)
- **`TRANSICIONES_CARTON` no permite `impreso → vendido`.** La tabla real
  (`dominio/estados.py`) es `impreso → {entregado, anulado}` y `entregado → {vendido, anulado}`.
  El contrato §4.2 dice "los cartones con comprador pasan a estado `vendido`" y el propio punto de
  partida dice que los cartones están "en estado `impreso` o `entregado`". **Tal como está, la
  importación fallaría en el caso más común.** Ver decisión D2.
- **`ronda.premio_valor` es `REAL`** en `001_inicial.sql`, mientras que `evento.precio_tabla_centavos`
  es `INTEGER` por la enmienda E4b y `docs/convenciones-codigo.md` prohíbe la conversión ad hoc de
  dinero fuera de `dominio/dinero.py`. La fase 4 es el primer consumidor real de `premio_valor`.
  Ver decisión D3.
- **`patron.mascara` es un solo `INTEGER`.** El contrato §4.5 pide patrones con variantes y el
  documento técnico §16.1 asigna esa decisión explícitamente a esta fase ("se decide al empezar la
  fase 4"). Ver decisión D1.
- **`ronda` tiene `UNIQUE (evento_id, orden)`.** Reordenar por arrastre choca con esa restricción a
  mitad del intercambio: SQLite comprueba `UNIQUE` por sentencia, no al final de la transacción.
  Ver decisión D5.
- **`ronda.estado` no tiene `CHECK` a propósito** (comentario en `001_inicial.sql`: su máquina de
  estados sigue abierta, doc técnico §16.2). La fase 4 crea rondas en `pendiente` y **no** define
  `TRANSICIONES_RONDA` — eso es fase 5.
- **`comprador.carton_id` es `NOT NULL UNIQUE`**: un cartón tiene como mucho un comprador. La
  reimportación del contrato §4.2 ("un segundo archivo con más ventas no debe romper lo ya cargado")
  se apoya en esa restricción, no la contradice.
- **`SECCIONES_ESPACIO_EVENTO` ya tiene los dos puntos de entrada con `fabrica=None`**:
  `"espacio_evento.seccion.compradores"` y `"espacio_evento.seccion.rondas"`
  (`ui/registro_vistas.py:77-78`). La fase 4 los rellena; no toca `ventana_principal.py` ni
  `espacio_evento.py`. **No existe** entrada para el editor de tema del dashboard (§4.8): hay que
  añadirla.
- **`repo_carton.actualizar_estado_por_lote(con, lote_id, estado_actual, estado_nuevo)`** ya filtra
  por estado actual (corregido en fase 3). El patrón "cambiar estado solo desde el estado esperado"
  ya está establecido y se reutiliza en la importación.
- **`utilidades/imagenes.validar_y_normalizar(origen, destino, lado_max=1600)`** ya existe y produce
  PNG saneado con escritura atómica. La imagen de premio (§4.7) la reutiliza tal cual.
- **`ui/tarea.py::Tarea`** (señales `progreso/terminado/fallado`, `cancelar()` cooperativo, conexión
  propia) ya sirve a dos llamadores (`generar_lote`, `generar_pdf_lote`). La importación de Excel
  es el tercero, sin tocar la clase.
- **`repo_auditoria.registrar(con, evento_id, accion, detalle)`** existe y es el canal de la
  anulación del contrato §4.3.
- **No existen** `repo_comprador.py`, `repo_patron.py`, `repo_ronda.py`, `dominio/patron.py`,
  ni ningún servicio de compradores/patrones/rondas. Todo el trabajo de la fase 4 es *añadir*.
- **`tests/arquitectura/test_arquitectura.py` es una valla real**: `.execute(` fuera de
  `persistencia/` falla la prueba, y toda `clave_i18n` pasada a un `Error*` debe existir en
  `es.json`. Cualquier módulo nuevo nace bajo esas reglas.

---

## 1. Alcance (del contrato, para trazabilidad)

Cerrar la brecha entre el cartón impreso y la partida: registrar compradores desde el Excel de la
organización (exportar plantilla, importar con validación en seco, gestión manual), conciliar,
y dejar el evento configurado con patrones, rondas, premios y tema del dashboard. Ver
`docs/Fase_4/Contrato_Fase4.md` para el texto completo (tareas 4.1-4.9, criterios de aceptación).

---

## 2. Qué ya existe (leverage map)

| Sub-problema de la Fase 4 | Código ya existente que lo resuelve parcial o totalmente |
|---|---|
| Importar sin congelar la UI, con progreso y cancelación | `ui/tarea.py::Tarea` — tercer llamador, sin tocar la clase |
| Escritura atómica de la importación | `persistencia/conexion.py::transaccion()` — no reentrante, ya probada |
| Normalizar la imagen del premio | `utilidades/imagenes.py::validar_y_normalizar()` — mismo camino que el logo |
| Dónde guardar la imagen del premio | `config/rutas.py::dir_medios_evento(evento_id)` — ya existe (fase 3) |
| Dinero del premio | `dominio/dinero.py::a_centavos/formatear` — punto único, ya probado |
| Registro de la anulación | `persistencia/repo_auditoria.py::registrar()` |
| Puntos de entrada de UI | `ui/registro_vistas.py` — `compradores` y `rondas` con `fabrica=None` esperando |
| Contadores de conciliación | `repo_carton.contar_por_estado(con, evento_id)` — ya devuelve `{estado: n}` |
| Grilla 5x5 para el editor de patrones | `ui/widgets/cuadricula_carton.py` — dibuja una cara de cartón; el editor necesita una variante clicable (ver §4.6) |
| Motor de PDF para el reporte de conciliación | `impresion/render_pdf.py` usa ReportLab; el reporte es un `Canvas` nuevo, no el motor de cartón |
| Cambio de estado en bloque con guarda | `repo_carton.actualizar_estado_por_lote(..., estado_actual, ...)` |
| Máquina de estados genérica | `dominio/estados.py::puede_transicionar(tabla, actual, nuevo)` |

**Conclusión de leverage:** igual que en las fases 2 y 3, los puntos de entrada y el modelo de datos
ya están enganchados. El trabajo es añadir tres repositorios, tres servicios, un módulo de dominio y
tres vistas — más **una migración correctiva** que es lo único que toca esquema ya escrito.

---

## 3. Decisiones de diseño

**D1 — Patrones con variantes: una columna `mascaras` TEXT con lista JSON, no filas relacionadas.**
Resuelve la decisión pendiente del documento técnico §16.1. Un patrón guarda `mascaras` como
`"[1082401, 34636833]"` (lista JSON de enteros). Gana quien complete **cualquiera** de ellas.
Razones: (a) la evaluación en vivo de la fase 5 es `any(marcado & m == m for m in mascaras)` sobre
una lista de 1 a 5 enteros ya cargada en memoria — con filas relacionadas habría un JOIN o una
segunda consulta por ronda, sin ganancia; (b) un patrón es inmutable en la práctica una vez
asignado a una ronda, así que la normalización no compra integridad; (c) `evento.plantilla_json` y
`evento.tema_json` ya establecen el precedente de JSON en TEXT en este esquema. Se conserva la
columna `mascara` existente por compatibilidad y se rellena con la **primera** máscara de la lista,
para que cualquier lectura vieja siga funcionando. *Alternativa descartada:* tabla
`patron_mascara(patron_id, mascara)` — más correcta en teoría relacional, cero beneficio operativo
aquí, y obliga a un repositorio más.

**D2 — `TRANSICIONES_CARTON` gana `impreso → vendido`; `entregado` queda como estado opcional.**
El hallazgo de §0 es un bloqueo real del criterio de aceptación "importar un Excel de 1.000
compradores... la escritura es atómica". La tabla nueva:
```
"generado":  {"impreso", "anulado"},
"impreso":   {"entregado", "vendido", "anulado"},
"entregado": {"vendido", "anulado"},
"vendido":   {"entregado", "anulado"},
"anulado":   set(),
```
`impreso → vendido` porque la organización vende cartones que nunca se marcaron "entregados" (el
paso `entregado` es un control de inventario opcional: "le di 200 talonarios a Juan para que los
venda"). `vendido → entregado` es el retorno de la anulación de venta (D4). `anulado` sigue siendo
terminal.

**D3 — `premio_valor_centavos INTEGER`, migración correctiva.**
`premio_valor REAL` contradice la enmienda E4b y `docs/convenciones-codigo.md` ("Prohibida la
conversión ad hoc: alimenta un comprobante que se entrega a la organización"). El premio en efectivo
va literalmente en el acta de la fase 5. Se corrige ahora, que es cuando el campo estrena
consumidor y aún **no hay ninguna fila `ronda` en ninguna base**. Migración `003_fase4.sql`:
columna nueva `premio_valor_centavos INTEGER`, la vieja `premio_valor` se deja muerta (SQLite no
permite `DROP COLUMN` sin reconstruir la tabla, y no vale reconstruirla por una columna sin datos)
con un comentario que lo diga. `dominio/modelos.py::Ronda` expone solo `premio_valor_centavos`.

**D4 — "Anular una venta" borra el comprador y devuelve el cartón a `entregado`; no lo pone en
`anulado`.** El contrato §4.3 dice "anulación de una venta con registro en auditoría" y §4.4 pide
conciliar "vendidos y anulados" por separado. Son dos cosas distintas y conviene no confundirlas:
- **Anular la venta** (§4.3): el comprador se equivocó, se arrepintió, o el dato estaba mal. Se
  borra la fila `comprador`, el cartón vuelve a `entregado` (queda disponible para revender) y se
  registra en auditoría con los datos del comprador borrado en el `detalle`. Un cartón físico
  perfectamente válido no debe morir porque alguien tecleó mal.
- **Anular el cartón** (estado `anulado`, terminal): el cartón físico se dañó, se perdió o se
  imprimió mal. Ya existía en la máquina de estados desde la fase 2 y **no es alcance nuevo de la
  fase 4** más allá de contarlo en la conciliación.

**D5 — Reordenar rondas: dos pasadas dentro de una transacción, con desplazamiento negativo.**
`UNIQUE (evento_id, orden)` se comprueba por sentencia. `servicio_rondas.reordenar(con, evento_id,
ids_en_orden)` hace, dentro de una sola `transaccion()`: (1) `UPDATE ronda SET orden = -(orden+1)
WHERE evento_id = ?` para sacar todas las filas del rango positivo sin colisionar; (2) un `UPDATE`
por fila con su orden final 1..N. Dos sentencias en bloque, no N intercambios. *Alternativa
descartada:* `PRAGMA defer_foreign_keys` no aplica a `UNIQUE`, y hacer la restricción `DEFERRABLE`
obliga a reconstruir la tabla.

**D6 — La importación lee el Excel con `openpyxl` en modo `read_only`, y la validación en seco corre
sobre el archivo entero antes de abrir ninguna transacción.** `load_workbook(ruta, read_only=True,
data_only=True)` es lo que evita que un `.xlsx` de 10.000 filas se cargue entero como objetos de
celda. El informe (`InformeImportacion`, dataclass de dominio) se construye completo en memoria —
son a lo sumo 50.000 filas de texto corto, cabe— y solo después, con confirmación explícita del
operador, se escribe en **una** `transaccion()`. Esto es lo que cumple literalmente "un archivo con
errores no deja la base a medio llenar".

**D7 — Las columnas del Excel se localizan por encabezado normalizado, no por posición.**
El riesgo que el propio contrato subraya ("columnas renombradas, columnas movidas de lugar"). Se
lee la primera fila, se normaliza cada encabezado (minúsculas, sin acentos, sin espacios) y se
mapea contra un diccionario de alias por campo (`{"codigo", "code", "cartón", "carton", ...}`). Si
falta la columna de código o la de nombre, el informe falla entero con un mensaje que dice qué
columna falta — no se adivina por posición. Las columnas extra que la organización haya añadido se
ignoran en silencio.

**D8 — El reporte de conciliación se genera con ReportLab (PDF) y openpyxl (Excel) en un módulo
nuevo `impresion/reporte.py`, no dentro de `render_pdf.py`.** `render_pdf.py` es el motor del
cartón (`MotorRenderCarton`, con su caché de imágenes y su disposición por hoja); un reporte
tabular no comparte nada con él salvo la librería. Mismo paquete `impresion/` (ya cubierto por
`test_impresion_no_importa_pyside6_ni_sqlite3`), archivo distinto.

**D9 — El editor de tema del dashboard (§4.8) produce y valida el `tema_json`, con vista previa
estática por composición de bloques, no un simulador del dashboard.**
La fase 5 construye la ventana de transmisión real. Duplicar aquí su layout produciría dos
renderizadores que divergen — exactamente el problema que la fase 3 evitó con `QPdfDocument`.
La vista previa de esta fase es un `QGraphicsScene` a escala sobre un lienzo 1920x1080 que dibuja
**rectángulos etiquetados** en la posición y escala de cada bloque, con los colores del tema
aplicados. Muestra fielmente *dónde* va cada cosa y de qué color, sin fingir el contenido en vivo
(bombo animado, tablero de 75, número actual). Cuando la fase 5 tenga los widgets reales, puede
sustituir los rectángulos por los widgets sin cambiar el modelo ni el editor.

**D10 — `dominio/patron.py` incluye `es_ganador` y `faltan`, no solo `mascara`.**
El contrato §4.5 solo pide `mascara(celdas)` y las constantes, pero el documento técnico §4.6 define
`es_ganador(marcado, patron)` y `faltan(marcado, patron)` en dos líneas cada una, y §4.9 del
contrato pide probar "que un patrón con variantes se cumpla con cualquiera de sus máscaras" — que
*es* la prueba de `es_ganador` sobre una lista de máscaras. Escribir la función que la prueba ya
exige, en la fase que escribe el módulo, cuesta cero y evita que la fase 5 tenga que volver a abrir
`dominio/patron.py` para añadir dos líneas. **No** entra nada más del motor de sorteo: ni `Bombo`,
ni `CartonEnJuego`, ni `partida.py`, ni `reglas.py`.

**D11 — Fuera de esta fase (quedan en `TODOS.md`):**
- *Política de retención LOPDP* (P1 de `TODOS.md`): esta fase es la que **crea** los datos
  personales de compradores. Se implementa el borrado por evento (`servicio_compradores.eliminar_
  todos_del_evento`) porque el criterio operativo lo va a necesitar, pero la *política* (cuántos
  días, quién la ejecuta) sigue siendo una decisión de Gabriel, no de este plan.
- *Exportar el listado de cartones a Excel/PDF desde la vista de la Fase 2* (`TODOS.md`, diferido a
  "fase 3 y fase 4"): la conciliación (§4.4) cubre el reporte agregado. El listado cartón-por-cartón
  con su comprador **sí** entra, como hoja del Excel de conciliación.
- *`TRANSICIONES_RONDA`* y la máquina de estados de la ronda: fase 5 (doc técnico §16.2, la decisión
  de "qué pasa si nadie reclama el premio" sigue abierta).
- *Bandera `modo_vivo`* y *registro central de atajos*: `TODOS.md` los ata a la fase 5.

---

## 4. Plan de implementación (task breakdown)

### 4.1 Migración `003_fase4.sql` y modelos

```sql
-- Fase 4. Tres correcciones y una extensión sobre el esquema de la 001:
--  * patron.mascaras: lista JSON de máscaras (decisión D1, doc técnico §16.1)
--  * patron.descripcion: el editor (§4.6) necesita distinguir "Línea horizontal
--    (cualquiera)" de "Línea horizontal superior" más allá del nombre.
--  * ronda.premio_valor_centavos: dinero en entero (decisión D3, enmienda E4b).
--    ronda.premio_valor (REAL) queda muerta: SQLite no permite DROP COLUMN sin
--    reconstruir la tabla y no hay ninguna fila que migrar.
--  * ronda.premio_descripcion: lo pide el contrato §4.7, no está en la 001.

ALTER TABLE patron ADD COLUMN mascaras     TEXT;
ALTER TABLE patron ADD COLUMN descripcion  TEXT;
ALTER TABLE ronda  ADD COLUMN premio_valor_centavos  INTEGER;
ALTER TABLE ronda  ADD COLUMN premio_descripcion     TEXT;

CREATE INDEX idx_patron_organizacion ON patron(organizacion_id);
CREATE INDEX idx_ronda_evento        ON ronda(evento_id, orden);
CREATE INDEX idx_comprador_carton    ON comprador(carton_id);
```

`dominio/modelos.py`: dataclasses nuevas `Comprador`, `Patron`, `Ronda` siguiendo el estilo ya
establecido (`slots=True`, `id: int | None = None`, campos obligatorios primero).

`dominio/estados.py`: `TRANSICIONES_CARTON` según D2.

### 4.2 `dominio/patron.py` (contrato §4.5, decisión D10)

Python puro, sin PySide6 ni sqlite3.

```python
def mascara(celdas: Iterable[tuple[int, int]]) -> int: ...
def celdas_desde_mascara(m: int) -> list[tuple[int, int]]: ...   # inverso, lo usa el editor
def es_ganador(marcado: int, mascaras: Sequence[int]) -> bool: ...  # any(marcado & m == m)
def faltan(marcado: int, mascaras: Sequence[int]) -> int: ...       # mínimo sobre las variantes
```

`PATRONES_SISTEMA`: tupla de `PatronSistema(clave_i18n, mascaras, usa_libre)` con los 15+ patrones
que el contrato enumera: líneas horizontales (una constante con 5 máscaras), verticales (5),
diagonales (2), cuatro esquinas, X, cruz, marco, diamante, postage stamp, letras T/L/H/E, escalera,
cartón lleno. **El nombre visible no vive aquí**: `dominio/` no importa i18n; se guarda la
`clave_i18n` y la vista la traduce con `t()`.

El espacio libre (bit 12) participa según `usa_libre`: un patrón con `usa_libre=False` que incluya
el bit 12 en su máscara exigiría que salga un número en el centro, lo cual es imposible. La
validación del editor (§4.6) rechaza esa combinación.

### 4.3 Persistencia: `repo_comprador.py`, `repo_patron.py`, `repo_ronda.py`

Verbos de `docs/convenciones-codigo.md`, `con` primero, `_desde_fila`/`_a_parametros`, sin
transacciones propias, `traducir_errores_sqlite()` en la frontera de cada escritura.

- `repo_comprador`: `crear`, `crear_varios` (`executemany`, la importación), `obtener_por_carton`,
  `listar_por_evento(con, evento_id, *, texto_busqueda=None, limite, desplazamiento)` (JOIN con
  `carton` para poder buscar por código o por nombre), `contar_por_evento`, `actualizar`,
  `eliminar`, `eliminar_por_evento`.
- `repo_patron`: `crear`, `obtener`, `listar(con, *, organizacion_id=None, incluir_sistema=True)`,
  `existe_nombre`, `actualizar`, `eliminar` (el servicio impide borrar `es_sistema=1`),
  `contar_sistema` (para la precarga idempotente).
- `repo_ronda`: `crear`, `obtener`, `listar_por_evento`, `siguiente_orden`, `actualizar`,
  `actualizar_orden`, `eliminar`. `listar_por_evento` devuelve `ORDER BY orden`.

### 4.4 `servicios/servicio_compradores.py` (contrato §4.1, §4.2, §4.3)

```python
def exportar_plantilla(con, evento_id, ruta_destino: Path, idioma: str) -> Path: ...
def validar_importacion(con, evento_id, ruta_origen: Path, *, al_progresar=None,
                        debe_cancelar=None) -> InformeImportacion: ...
def aplicar_importacion(con, evento_id, informe: InformeImportacion) -> int: ...
def registrar_manual(con, evento_id, codigo: str, comprador: Comprador) -> Comprador: ...
def actualizar_comprador(con, comprador: Comprador) -> None: ...
def anular_venta(con, comprador_id: int, motivo: str) -> None: ...
```

**Exportación (§4.1).** `openpyxl` con `Workbook(write_only=False)`. Dos hojas:
`Compradores` (una fila por cartón del evento: código + 4 columnas vacías) e `Instrucciones`
(texto traducido con `t()`, escrito por la **vista**, no por el servicio — o el servicio recibe los
textos ya traducidos como parámetro, para no importar i18n desde `servicios/`). Detalles que
importan y son fáciles de olvidar:
- La columna de código va con `cell.protection = Protection(locked=True)` y
  `hoja.protection.sheet = True`. Sin lo segundo, `locked` no hace nada: Excel solo respeta el
  bloqueo de celda si la hoja está protegida.
- Teléfono y cédula: `cell.number_format = "@"` (texto) en toda la columna, que es lo que evita que
  Excel se coma el cero inicial de `0987654321`. Esto hay que fijarlo en las celdas vacías de las
  N filas, no solo en el encabezado.
- Ancho de columna razonable y fila de encabezado congelada (`hoja.freeze_panes = "A2"`).

**Validación en seco (§4.2, decisión D6/D7).** Devuelve:
```python
@dataclass(slots=True)
class FilaImportacion:
    numero_fila: int
    codigo: str
    nombre: str
    telefono: str | None
    cedula: str | None
    correo: str | None

@dataclass(slots=True)
class InformeImportacion:
    correctas: list[FilaImportacion]
    codigo_inexistente: list[FilaImportacion]
    duplicado_en_archivo: list[FilaImportacion]
    ya_asignado: list[FilaImportacion]        # con comprador distinto
    sin_nombre: list[FilaImportacion]
    ya_registrado_igual: list[FilaImportacion]  # reimportación: mismo comprador, sin cambio
    columnas_faltantes: list[str]
```
La categoría `ya_registrado_igual` es lo que hace que reimportar sea seguro y no ruidoso: un
segundo archivo que repite las 800 ventas del primero más 200 nuevas debe reportar 200 correctas y
800 "sin cambios", no 800 errores. Comparación por `(nombre, telefono, cedula, correo)` normalizados
(trim, colapso de espacios internos, comparación de nombre sin distinguir mayúsculas).

**Escritura (§4.2).** `aplicar_importacion` abre **una** `transaccion()` y dentro:
`repo_comprador.crear_varios(...)`, luego `repo_carton.actualizar_estado` por cartón desde su estado
real (`impreso` o `entregado`, validado con `puede_transicionar`), y `repo_auditoria.registrar`.
Cualquier `ErrorBingo` aborta la transacción entera: la base queda como estaba.

**Anulación (§4.3, decisión D4).** Dentro de `transaccion()`: leer el comprador, borrarlo, devolver
el cartón a `entregado`, y `repo_auditoria.registrar(con, evento_id, "venta.anulada", detalle=...)`
con nombre y código en el detalle — el detalle es lo único que queda del comprador borrado, y es
justamente lo que hace falta si hay que reconstruir qué pasó.

### 4.5 `servicios/servicio_patrones.py` (contrato §4.5, §4.6)

```python
def asegurar_patrones_sistema(con) -> int: ...   # idempotente, primera ejecución
def crear_patron(con, patron: Patron) -> Patron: ...
def duplicar_patron(con, patron_id: int, nombre_nuevo: str) -> Patron: ...
def eliminar_patron(con, patron_id: int) -> None: ...   # lanza si es_sistema
def validar_patron(patron: Patron) -> None: ...
```

`asegurar_patrones_sistema` resuelve el `TODOS.md` P2 ("carga de los patrones del sistema... se
difiere a la fase 4"). Idempotente por `(nombre, es_sistema=1, organizacion_id IS NULL)`: si ya
están, no reinserta. Se llama desde `__main__.py` justo después de las migraciones, dentro de su
propia `transaccion()`.

Validación: al menos una máscara, cada máscara en `[1, 2**25-1]`, no la máscara vacía, `usa_libre`
coherente con el bit 12 (§4.2), nombre no vacío y único dentro de la organización.

### 4.6 `servicios/servicio_rondas.py` (contrato §4.7)

```python
def crear_ronda(con, ronda: Ronda) -> Ronda: ...
def actualizar_ronda(con, ronda: Ronda) -> None: ...
def eliminar_ronda(con, ronda_id: int) -> None: ...
def reordenar(con, evento_id: int, ids_en_orden: list[int]) -> None: ...   # decisión D5
def guardar_imagen_premio(con, evento_id: int, origen: Path) -> str: ...
def validar_evento_listo(con, evento_id: int) -> list[str]: ...
```

`validar_evento_listo` es el criterio de aceptación "un evento con rondas incompletas no deja
iniciar el sorteo, **y dice exactamente qué falta**". Devuelve una lista de claves i18n con
parámetros — no un `bool`, no un texto ya formateado (que sería una cadena visible fuera de `t()`).
Comprueba: al menos una ronda; toda ronda tiene `patron_id` válido; toda ronda tiene
`premio_nombre`; toda ronda de tipo `efectivo` tiene `premio_valor_centavos > 0`; al menos un cartón
en estado `vendido`. La fase 5 la llama antes de permitir `preparado → en_curso`; esta fase la
muestra en la vista de rondas como una lista de pendientes.

`guardar_imagen_premio` reutiliza `validar_y_normalizar` contra `dir_medios_evento(evento_id)`,
con nombre de archivo por `ronda_id` para no acumular huérfanos.

### 4.7 `servicios/servicio_conciliacion.py` + `impresion/reporte.py` (contrato §4.4, decisión D8)

```python
@dataclass(slots=True)
class Conciliacion:
    generados: int; impresos: int; entregados: int; vendidos: int; anulados: int
    total_cartones: int
    precio_tabla_centavos: int
    recaudacion_teorica_centavos: int   # vendidos * precio_tabla_centavos
    compradores_registrados: int
```
`calcular(con, evento_id) -> Conciliacion` se apoya en `repo_carton.contar_por_estado` (ya existe) y
`repo_comprador.contar_por_evento`. `recaudacion_teorica_centavos` es multiplicación de enteros:
cero coma flotante en el camino del comprobante.

`impresion/reporte.py`: `reporte_conciliacion_pdf(conciliacion, evento, organizacion, ruta, textos)`
y `reporte_conciliacion_excel(conciliacion, filas_detalle, ruta, textos)`. El Excel lleva dos hojas:
`Resumen` (los contadores y la recaudación) y `Detalle` (cartón, estado, comprador, teléfono) —
esto último es lo que cierra el ítem diferido de `TODOS.md` sobre exportar el listado.
`textos` es un diccionario ya traducido que pasa la vista: `impresion/` no importa i18n, igual que
no importa Qt.

**Discrepancia que el reporte debe hacer visible, no esconder:** si
`compradores_registrados != vendidos`, algo está mal (un cartón `vendido` sin fila `comprador`, o
al revés). El reporte lo muestra como una línea de advertencia, no lo normaliza en silencio. Eso es
lo que significa "el reporte de conciliación cuadra con lo que hay en base de datos".

### 4.8 Vistas

> **Esta sección quedó corta y la revisión de diseño la sustituye.** Lo que sigue es la
> estructura; los estados de interacción, la jerarquía, el teclado y las decisiones concretas de
> widget están en el **ANEXO B §B.3 (DS1-DS21)**, que manda sobre este texto donde difieran.
> En particular: la fase 4 **sí toca `ui/espacio_evento.py`** (chip de "listo para jugar", DS1),
> contra lo que afirmaba §0.

Tres vistas nuevas, más una entrada de sección nueva en `ui/registro_vistas.py`.

**`ui/vistas/vista_compradores.py`** (rellena `"espacio_evento.seccion.compradores"`).
Maestro-detalle como `VistaCartones`: tabla de compradores con búsqueda por código o nombre,
formulario de alta/edición manual a la derecha. Barra de acciones: *Exportar plantilla*,
*Importar Excel*, *Anular venta*.
El flujo de importación es un modal de dos pasos que hace literal el contrato: elegir archivo →
`Tarea(validar_importacion)` con progreso y cancelación → **pantalla de informe** con un contador
por categoría y una tabla de las filas problemáticas → botón *Confirmar e importar* (deshabilitado
si no hay ninguna fila correcta) → `Tarea(aplicar_importacion)`. El informe se puede exportar a
`.xlsx` desde esa misma pantalla (contrato §4.2).

**`ui/vistas/vista_rondas.py`** (rellena `"espacio_evento.seccion.rondas"`).
Lista de rondas ordenada con botones *Subir*/*Bajar* **y** arrastre
(`QAbstractItemView.InternalMove`), ambos llamando a `servicio_rondas.reordenar`. Formulario de
ronda a la derecha: nombre, selector de patrón (con vista previa de la grilla 5x5 del patrón
elegido, reutilizando el widget del editor en modo solo lectura), premio (nombre, descripción,
tipo, valor con `dominio/dinero`, imagen). Panel inferior fijo con el resultado de
`validar_evento_listo`: la lista de lo que falta, en verde cuando está vacía.
El editor de patrones (§4.6) es un modal lanzado desde el selector de patrón — *Nuevo* / *Duplicar*
/ *Editar* (deshabilitado en patrones del sistema, que solo se duplican).

**`ui/widgets/rejilla_patron.py`** (nuevo). Grilla 5x5 clicable que enciende/apaga celdas y expone
`mascara() -> int` / `establecer_mascara(int)`. Se usa en el editor (clicable) y en la vista de
rondas (solo lectura). **No** se modifica `ui/widgets/cuadricula_carton.py`: dibuja una cara de
cartón con números, que es otra cosa — comparten la geometría 5x5 y nada más. Duplicar 40 líneas de
layout es más barato que un widget con dos modos que se estorban.

**`ui/vistas/vista_tema.py`** (contrato §4.8, decisión D9). Entrada **nueva** en
`SECCIONES_ESPACIO_EVENTO`: `EntradaSeccionEvento("espacio_evento.seccion.tema", _vista_tema)`,
después de `rondas`. Formulario en `QScrollArea` (colores, imagen de fondo, un grupo por bloque con
visible/posición/escala, y los ajustes de juego), con la vista previa `QGraphicsScene` de D9 a la
derecha. Mismo patrón de guardado que `vista_plantilla.py`: `QTimer` de un solo disparo con
`RETARDO_VISTA_PREVIA_MS` y `repo_evento.actualizar_tema(con, evento_id, tema_json)`
(**verbo nuevo**, gemelo del `actualizar_plantilla` que ya existe).

**`dominio/tema.py`** (nuevo, gemelo de `impresion/plantilla.py`): dataclasses `ConfigColores`,
`ConfigBloque`, `ConfigJuego`, `TemaDashboard` con `por_defecto()`, `desde_json()`, `a_json()` y
`validar()`. Vive en `dominio/` y no en `impresion/` porque no tiene nada que ver con ReportLab y
la fase 5 lo consume desde `ui/tema.py`. Claves ausentes caen al valor por defecto del campo, igual
que `PlantillaCarton` — es lo que permite que la fase 5 añada campos sin migrar los `tema_json` ya
guardados.

### 4.9 i18n

Todas las cadenas nuevas a `es.json` y `en.json`: nombres de los ~15 patrones del sistema, las 6
categorías del informe de importación, los mensajes de `validar_evento_listo`, las etiquetas de las
tres vistas, y los errores nuevos. Recordatorio de la valla: toda `clave_i18n` de un `Error*` debe
existir en `es.json` o `test_arquitectura.py` falla.

### 4.10 Pruebas (contrato §4.9)

- `tests/dominio/test_patron.py`: **bit por bit** de cada patrón del sistema (el contrato lo pide
  explícitamente) — para cada uno, el conjunto de `(fila, columna)` esperado contra
  `celdas_desde_mascara`. `es_ganador` con variantes: un cartón que completa la línea horizontal 3
  gana el patrón "cualquier línea horizontal" y no gana "línea horizontal superior". `faltan` con
  variantes devuelve el mínimo. Casos borde: patrón con el bit libre y sin él, máscara vacía
  rechazada, `CARTON_LLENO == 2**25 - 1`.
- `tests/dominio/test_tema.py`: roundtrip `a_json`/`desde_json`, defaults por campo ausente,
  validación de cada campo fuera de rango.
- `tests/servicios/test_servicio_compradores.py`: **el corazón de la fase.** Archivos
  deliberadamente sucios, construidos con `openpyxl` en la propia prueba (no ficheros binarios en
  el repositorio): códigos inventados, filas totalmente vacías en medio, código duplicado dentro
  del archivo, cartón ya asignado a otro comprador, fila sin nombre, columnas reordenadas, columnas
  renombradas con alias, encabezado con acentos y mayúsculas, teléfono con cero inicial (que debe
  sobrevivir el viaje), y una columna extra desconocida. Más: reimportación (800 repetidas + 200
  nuevas → 200 correctas, 800 `ya_registrado_igual`), atomicidad (forzar un fallo a mitad de
  `aplicar_importacion` con `monkeypatch` y comprobar que **no queda ninguna fila** `comprador` ni
  ningún cartón en `vendido`), y el marcado `lento` con 1.000 filas del criterio de aceptación.
- `tests/servicios/test_servicio_rondas.py`: `reordenar` con permutación completa (invertir el
  orden de 5 rondas de una vez, que es lo que mata la implementación ingenua), `validar_evento_listo`
  devolviendo exactamente qué falta en cada caso, imagen de premio normalizada.
- `tests/servicios/test_servicio_patrones.py`: `asegurar_patrones_sistema` es idempotente
  (llamarla dos veces deja el mismo número de filas), no se puede borrar un patrón del sistema,
  duplicar produce uno editable de la organización.
- `tests/servicios/test_servicio_conciliacion.py`: los contadores cuadran con la base contra un
  evento con cartones en los cinco estados; recaudación teórica en enteros; la advertencia de
  discrepancia aparece cuando `vendidos != compradores`.
- `tests/persistencia/`: un `test_repo_*.py` por repositorio nuevo, más `test_migraciones.py`
  actualizado para la 003.
- `tests/ui/`: `test_vista_compradores.py` (el modal de dos pasos no escribe nada hasta confirmar),
  `test_vista_rondas.py` (subir/bajar llama a `reordenar` con la lista correcta),
  `test_vista_tema.py` (guardar llama a `actualizar_tema`), `test_navegacion.py` actualizado por la
  sección nueva.

---

## 5. Riesgos y notas

- **La migración 003 es correctiva sobre columnas que ya existen** (`premio_valor` muerta). Es la
  primera vez que el proyecto deja una columna muerta; el comentario en el `.sql` es obligatorio o
  dentro de seis meses nadie sabrá por qué hay dos columnas de valor de premio.
- **`D2` cambia una máquina de estados que la fase 5 va a consumir.** Añadir `impreso → vendido` y
  `vendido → entregado` amplía el grafo; conviene que la fase 5 lo lea antes de escribir
  `TRANSICIONES_RONDA` por analogía.
- **El Excel de 1.000 filas es el criterio de aceptación, no el techo.** El contrato dice 1.000;
  `LIMITE_CARTONES_POR_LOTE` es 50.000. Vale medir la validación en seco con 10.000 filas antes de
  cerrar la fase — es la ruta que corre en `Tarea` y la que se cuelga si alguien la escribió con
  una consulta por fila.
- **Riesgo de N+1 en la validación en seco:** la implementación ingenua consulta
  `repo_carton.obtener_por_codigo` una vez por fila del Excel. Con 10.000 filas son 10.000
  consultas. Se precarga `{codigo: (carton_id, estado)}` del evento entero en un diccionario, igual
  que `listar_firmas_por_evento` hace en la fase 2. **Escribirlo así desde el principio**, no
  optimizarlo después.
- **Datos personales.** Esta fase crea la primera tabla con nombre, teléfono, cédula y correo de
  personas reales. El `.zip` de respaldo de la fase 5 los va a llevar dentro
  (`TODOS.md` P3, "cifrado del respaldo"), y el `detalle` de auditoría de la anulación también.
  Decidir la política de retención (P1 de `TODOS.md`) deja de ser teórico a partir de aquí.
- **La vista previa del tema no es el dashboard.** Riesgo aceptado de D9: el operador ve
  rectángulos, no el bombo. Si en la fase 5 resulta que la posición "se ve bien en rectángulos y
  mal en vivo", el editor sigue sirviendo y se afina ahí — pero conviene decirlo ahora y no
  venderlo como WYSIWYG.

---

## 6. Mapeo a criterios de aceptación del contrato

| Criterio | Cubierto por |
|---|---|
| Excel de 1.000 compradores: informe correcto antes de escribir, escritura atómica | `validar_importacion` / `aplicar_importacion` (4.4, D6) + prueba `lento` (4.10) |
| Un archivo con errores no deja la base a medio llenar | Una sola `transaccion()` en `aplicar_importacion` + prueba de atomicidad con fallo forzado (4.10) |
| Crear un patrón propio desde la grilla y asignarlo a una ronda | `rejilla_patron.py` + `servicio_patrones.crear_patron` + selector de `vista_rondas` (4.8) |
| Evento con rondas incompletas no deja iniciar, y dice qué falta | `servicio_rondas.validar_evento_listo` → lista de claves i18n, panel fijo en `vista_rondas` (4.6, 4.8) |
| El reporte de conciliación cuadra con la base | `servicio_conciliacion.calcular` sobre `contar_por_estado` + línea de advertencia de discrepancia (4.7) |

---

## 7. Entregable

Etiqueta `v0.4.0` (contrato). Al cerrar: compradores cargados desde Excel con informe previo,
conciliación exportable, catálogo de patrones con editor, rondas con premio, y `tema_json` definido.

---

# ANEXO A — Revisión CEO (`/gstack-autoplan` Fase 1)

Voces: Claude subagente (independiente, contexto fresco). **Codex no disponible** (binario no
instalado) → `[subagent-only]` en las cuatro fases. Consenso 0/6 CONFIRMED por ausencia de la
segunda voz; los 6 ejes quedan marcados por hallazgo crítico de voz única.

## A.1 Premisas evaluadas

| # | Premisa | Veredicto |
|---|---|---|
| P1 | La organización devuelve un `.xlsx` con los compradores | Razonable; el contrato ya la duda y pide alta manual |
| P2 | Registrar compradores es requisito para jugar | **Parcialmente falsa** → User Challenge UC-1 |
| P3 | Hace falta un editor de patrones | Aceptada |
| P4 | El editor de tema pertenece a la fase 4 | **Cuestionable** → User Challenge UC-2 |
| P5 | Excel es el formato de intercambio | Aceptada (`openpyxl` ya instalado) |

## A.2 Dream state delta

```
  ESTADO ACTUAL                  ESTE PLAN                    IDEAL A 12 MESES
  Cartones generados e     -->   Compradores cargados y  -->  El operador abre la app la
  impresos con PDF.              conciliados. Rondas con      mañana del evento, importa
  Nadie sabe quién compró        patrón y premio. Evento      la hoja, ve UN panel que dice
  qué. Sin forma de              jugable.                     qué falta, y pulsa Iniciar.
  configurar la partida.                                      La conciliación es un PDF
                                                              para el tesorero.
```

**Delta:** el plan llega casi entero. Falta del ideal: (a) el "qué falta" vive en un panel del
espacio del evento, no dentro de la vista de rondas; (b) la conciliación compara contra dinero
real recibido, no solo contra el teórico.

## A.3 Registro de errores y rescate (Sección 2)

| Codepath | Qué puede salir mal | Clase de excepción | ¿Rescatada? | Acción | Ve el usuario |
|---|---|---|---|---|---|
| `validar_importacion` | Archivo `.xls` legado | `openpyxl` `InvalidFileException` | **GAP** → rescatar | Detectar extensión antes de abrir | "Guarda el archivo como .xlsx y vuelve a intentar" |
| `validar_importacion` | `.xlsx` con contraseña | `InvalidFileException` | **GAP** → rescatar | `ErrorValidacion` | "El archivo está protegido con contraseña" |
| `validar_importacion` | Falta columna código o nombre | `ErrorValidacion` | Sí | Informe con `columnas_faltantes` | Nombre exacto de la columna que falta |
| `validar_importacion` | Celda con fórmula sin cachear → `None` | — (silencioso) | **GAP** → detectar | Contar `None` en columna nombre; si >30% avisar | "Parece exportado de Google Sheets: ábrelo y guárdalo en Excel" |
| `validar_importacion` | Archivo de 200.000 filas | `MemoryError` | **GAP** → acotar | `LIMITE_FILAS_IMPORTACION` | "El archivo excede N filas" |
| `aplicar_importacion` | Cartón cambió de estado entre validar y aplicar | `ErrorTransicionInvalida` | Sí | Revalidar **dentro** de la transacción, `ROLLBACK` | "Los datos cambiaron; vuelve a validar" |
| `aplicar_importacion` | Doble clic en Confirmar | `ErrorIntegridad` (unique) | **GAP** → prevenir | Deshabilitar el botón al primer clic | Nada (no ocurre) |
| `exportar_plantilla` | Destino abierto en Excel | `PermissionError` | **GAP** → rescatar | `ErrorValidacion` | "Cierra el archivo en Excel y reintenta" |
| `guardar_imagen_premio` | Imagen corrupta / bomba | `ErrorImagen` | Sí (ya existe) | En línea junto al campo | Mensaje de `utilidades/imagenes` |
| `reordenar` | Lista con id ajeno al evento | `ErrorValidacion` | Sí | `ROLLBACK` | "Ronda no pertenece a este evento" |
| `asegurar_patrones_sistema` | Falla al arrancar | `ErrorPersistencia` | Sí | Franja no modal, la app abre igual | "Catálogo de patrones no disponible" |
| `eliminar_patron` | Patrón del sistema | `ErrorDominio` | Sí | Botón deshabilitado + guarda en servicio | "Los patrones del sistema no se borran, se duplican" |
| `eliminar_patron` | Patrón referenciado por una ronda | `ErrorIntegridad` (FK) | **GAP** → comprobar antes | Contar rondas que lo usan | "Lo usan N rondas" |

## A.4 Registro de modos de fallo

| Codepath | Modo de fallo | ¿Rescatado? | ¿Prueba? | ¿Ve el usuario? | ¿Log? |
|---|---|---|---|---|---|
| Importación | Transacción a medias | Sí (`transaccion()` hace `ROLLBACK`) | Sí (fallo forzado) | Sí | Sí |
| Importación | Fórmulas → nombres vacíos | **NO — CRÍTICO** | No | **Silencioso** (se ven como `sin_nombre`) | No |
| Importación | Código con formato distinto | **NO — CRÍTICO** | No | Falso "código inexistente" | No |
| Importación | Filas de continuación (1 comprador, N cartones) | **NO — CRÍTICO** | No | Falso `sin_nombre` | No |
| Evaluación de patrón | Se lee `mascara` en vez de `mascaras` | **NO — CRÍTICO** | No | **Silencioso**: el ganador no se detecta | No |
| Conciliación | Nombre con `=` → fórmula al abrir | **NO — CRÍTICO** | No | Ejecución en la máquina del tesorero | No |
| Anulación | Datos personales quedan en `auditoria.detalle` | **NO** | No | Silencioso | (es el log) |
| Reordenado | Colisión de `UNIQUE(evento_id, orden)` | Sí (D5, dos pasadas) | Sí (permutación completa) | Sí | Sí |

**6 CRITICAL GAPS.** Todos se cierran con los ajustes de A.5.

## A.5 Decisiones de la revisión (auto-decididas)

| # | Origen | Decisión | Principio |
|---|---|---|---|
| R1 | F8 | `mascaras` es la **única** fuente. `mascara` se documenta muerta + prueba de arquitectura que falle si aparece en un `SELECT` fuera de la migración | P5 explícito |
| R2 | F9 | `patron.clave_i18n` y `patron.version_semilla` a la 003. Idempotencia por `clave_i18n`; `asegurar_patrones_sistema` **actualiza** máscaras cuando sube la versión | P1 completitud |
| R3 | F5 | `dominio/codigo.py::normalizar(codigo, prefijo, ancho)`: trim, colapso, mayúsculas, y reconstrucción si el valor es puramente numérico. Seis casos probados | P1 |
| R4 | F4 | Categoría `continuacion_de_fila_anterior` + acción "aplicar el comprador anterior a estas N filas" | P1 |
| R5 | F3 | Aceptar `.csv`; detectar `.xls` con mensaje accionable; avisar si >30% de nombres vienen vacíos (síntoma de fórmulas sin cachear) | P1 |
| R6 | F6 | Plantilla de dos hojas: `Ventas` **vacía** con validación de datos, y `Codigos` protegida como origen de la lista | P1 |
| R7 | Riesgo op. 2 | `servicio_compradores.marcar_vendidos_por_rango(desde, hasta)` — así se venden los talonarios físicos | P1 |
| R8 | F2 | `evento.recaudado_real_centavos` y la diferencia teórico − real en el reporte | P1 |
| R9 | F10 | `servicio_eventos.marcar_preparado()` llama a `validar_evento_listo` y falla con la lista de pendientes | P1 |
| R10 | F11 | Editar `docs/Fase_5/Contrato_Fase5.md §5.2` en el mismo commit: reutiliza `dominio/patron.py` | P4 DRY |
| R11 | F14 | En `auditoria.detalle` va código + `comprador.id`, nunca nombre ni teléfono. `eliminar_por_evento` barre también la auditoría | P1 |
| R12 | F12 | Anular devuelve el cartón a **su estado anterior** (registrado en la auditoría); si se desconoce, a `impreso` | P5 |
| R13 | §3 propia | Antifórmula al escribir `.xlsx`: prefijo `'` en valores que empiecen por `= + - @`. Helper compartido por exportación y conciliación | P4 DRY |
| R14 | §2 | Rescatar `PermissionError`, `.xls`, `.xlsx` protegido, y acotar filas con `LIMITE_FILAS_IMPORTACION` | P1 |
| R15 | §4 | Revalidar **dentro** de la transacción; deshabilitar Confirmar al primer clic; la escritura **no es cancelable** (solo la validación lo es) | P1 |
| R16 | §8 | Panel de solo lectura de auditoría del evento (`repo_auditoria.listar_por_evento` ya existe). La importación registra **una** fila resumen | P2 |
| R17 | F-cut | **Rechazada** la propuesta del subagente de recortar `PATRONES_SISTEMA` a 8: el contrato §4.5 los enumera y son constantes, no código | P1 |

## A.6 NO está en el alcance (diferido a `TODOS.md`)

- **Cifrado del `.zip` de respaldo** — fase 5 (`TODOS.md` P3), pero esta fase es la que crea el dato que lo hace urgente.
- **Base de datos por evento** — `TODOS.md` P3.
- **`TRANSICIONES_RONDA`** — fase 5 (doc técnico §16.2 sigue abierto).
- **Historial de conciliación entre eventos** — fuera del contrato.
- **Detección de comprador duplicado por teléfono** — ruidoso, sin valor claro.
- **Textos de organización por idioma** — sigue diferido, ningún criterio de esta fase lo pide.

## A.7 Tareas de implementación (Fase CEO)

- [ ] **T1 (P1, humano ~3h / CC ~20min)** — persistencia — Una sola fuente de máscaras
  - Surgido por: §A.5 R1 (F8) — dos columnas para el dato que decide quién cobra
  - Archivos: `003_fase4.sql`, `repo_patron.py`, `tests/arquitectura/test_arquitectura.py`
  - Verificar: `pytest tests/arquitectura -k mascara`
- [ ] **T2 (P1, humano ~2h / CC ~15min)** — persistencia — `clave_i18n` + `version_semilla` en `patron`
  - Surgido por: §A.5 R2 (F9) — contradicción interna del plan
  - Archivos: `003_fase4.sql`, `servicio_patrones.py`, `dominio/patron.py`
  - Verificar: `pytest tests/servicios/test_servicio_patrones.py`
- [ ] **T3 (P1, humano ~3h / CC ~20min)** — dominio — Normalización de códigos
  - Surgido por: §A.5 R3 (F5) — "980 códigos inexistentes" sobre un archivo correcto
  - Archivos: `dominio/codigo.py` (nuevo), `servicio_compradores.py`
  - Verificar: `pytest tests/dominio/test_codigo.py`
- [ ] **T4 (P1, humano ~4h / CC ~25min)** — servicios — Robustez real del Excel
  - Surgido por: §A.5 R4-R6, R14 (F3, F4, F6) — el archivo que llega de verdad
  - Archivos: `servicio_compradores.py`, `config/ajustes.py`
  - Verificar: `pytest tests/servicios/test_servicio_compradores.py`
- [ ] **T5 (P1, humano ~1h / CC ~10min)** — impresion — Antifórmula al escribir `.xlsx`
  - Surgido por: §3 Seguridad — el reporte al tesorero es vector de ejecución
  - Archivos: `impresion/reporte.py`, `servicio_compradores.py`
  - Verificar: prueba que un nombre `=1+1` sale como texto literal
- [ ] **T6 (P1, humano ~2h / CC ~15min)** — servicios — Venta por rango y `marcar_preparado`
  - Surgido por: §A.5 R7, R9 — 200 ventas de puerta; nadie mueve el evento a `preparado`
  - Archivos: `servicio_compradores.py`, `servicio_eventos.py`
  - Verificar: `pytest tests/servicios -k "rango or preparado"`
- [ ] **T7 (P2, humano ~2h / CC ~15min)** — privacidad — Auditoría sin datos personales
  - Surgido por: §A.5 R11 (F14) — el mecanismo de borrado conserva el dato
  - Archivos: `servicio_compradores.py`, `repo_comprador.py`
  - Verificar: prueba que `auditoria.detalle` no contiene el nombre tras anular
- [ ] **T8 (P2, humano ~2h / CC ~15min)** — conciliación — Recaudado real vs teórico
  - Surgido por: §A.5 R8 (F2) — el criterio de aceptación era una tautología
  - Archivos: `003_fase4.sql`, `servicio_conciliacion.py`, `impresion/reporte.py`
  - Verificar: `pytest tests/servicios/test_servicio_conciliacion.py`
- [ ] **T9 (P2, humano ~1h / CC ~10min)** — ui — Panel de auditoría del evento
  - Surgido por: §A.5 R16 — la fase 4 es la primera que escribe auditoría legible
  - Archivos: `ui/vistas/vista_auditoria.py`, `ui/registro_vistas.py`
  - Verificar: `pytest tests/ui/test_navegacion.py`
- [ ] **T10 (P2, humano ~30min / CC ~5min)** — docs — Alinear el contrato de la fase 5
  - Surgido por: §A.5 R10 (F11) — `es_ganador` en dos sitios
  - Archivos: `docs/Fase_5/Contrato_Fase5.md`
  - Verificar: lectura

---

# ANEXO B — Revisión de diseño (`/gstack-autoplan` Fase 2)

Voz: subagente Claude independiente (sin contexto de la Fase 1). Codex no disponible.
**Puntuación global del plan: 4/10** → objetivo tras correcciones: 8/10.
27 hallazgos (5 críticos, 12 altos, 10 medios). 25 auto-corregidos, 2 a decisión de gusto.

## B.1 Diagnóstico

§4.8 dedicaba 34 líneas a tres vistas y dos modales, mientras §4.10 dedicaba 30 solo a nombrar
casos de prueba. El backend estaba diseñado; la interfaz estaba *referenciada*. "Maestro-detalle
como `VistaCartones`" y "panel inferior fijo" no resuelven ninguna decisión: la delegan al
implementador a la una de la mañana.

## B.2 Hallazgos verificados contra el código

| # | Hallazgo | Verificación |
|---|---|---|
| H6 | **No existe canal visual de éxito.** `QFrame#franjaError` (`tema.py:163`) se pinta con borde `_PELIGRO`. Los éxitos de las fases 2 y 3 **ya** salen sobre fondo rojo (`vista_cartones.py:540,573`). La fase 4 lo multiplicaría por seis | Confirmado en código |
| H22 | **El plan no menciona el teclado ni una vez.** `atajos.py` dice en su docstring "se opera en vivo, frente a cámara, contra reloj: el teclado tiene que alcanzar para todo" y `ATAJOS` no tiene ni un atajo de sección | Confirmado |
| H26 | `TIPOGRAFIA_MINIMA_PX = 13` y `OBJETIVO_PULSACION_MINIMO_PX = 32` (`atajos.py:24-25`) no los importa **ningún** módulo | Confirmado |
| H1 | `validar_evento_listo` enterrado en la vista de rondas. `espacio_evento.py` ya tiene `_chip_estado` donde colgarlo | Confirmado |

## B.3 Decisiones de diseño (auto-corregidas)

| # | Hallazgo | Corrección |
|---|---|---|
| DS1 | H1 | Chip "Faltan N cosas para iniciar" / "Listo para jugar" en la cabecera de `espacio_evento.py`, clicable, desplegando `validar_evento_listo`. **Consecuencia: la fase 4 sí toca `espacio_evento.py`**, contra lo que decía §0 |
| DS2 | H3 | La fila de resumen de `vista_compradores` **es** la conciliación ("820 de 1.000 vendidos · 180 sin comprador · $4.100 teóricos"), con los botones de exportar PDF/Excel en su barra. La advertencia de discrepancia se ve ahí, no solo dentro del PDF |
| DS3 | H4 | Pantalla de informe especificada: veredicto en una frase y tipografía grande arriba; botón primario *Confirmar e importar* visible sin scroll; **una sola** tabla con columna "Problema" filtrada por chips; solo se renderizan las categorías con n > 0; `correctas == 0` → estado vacío propio **sin** botón Confirmar (ausente, no deshabilitado); cero errores → un mensaje y el botón, sin chips |
| DS4 | H5 | Estados vacíos definidos uno por uno: Compradores tiene **tres** (sin cartones → CTA "Genera cartones primero", nunca "Importar"; con cartones sin compradores → CTA doble de DS5; sin resultados por filtro). Rondas: vacío + el intermedio "hay rondas, ninguna con patrón". Editor de patrones: máscara 0 es inicial **e** inválido, Guardar deshabilitado hasta ≥1 celda, contador siempre visible. Tema: arranca en `TemaDashboard.por_defecto()` sembrado de la organización |
| DS5 | H9 | Vacío de Compradores con dos CTA de peso similar: *Importar el archivo que ya tengo* (primario) y *Exportar plantilla en blanco* (secundario), y bajo el primario la línea que baja la tensión: "Reconocemos columnas con otros nombres y en otro orden" |
| DS6 | H6 | `FranjaError` pasa a tres niveles (`info` / `exito` / `error`) con `QFrame#franjaExito` y `#franjaInfo` en `tema.py`, usando `_EXITO` y `_AVISO`, que ya existen sin usar. **Corrige de paso las fases 2 y 3** |
| DS7 | H7, H8 | Barra indeterminada (`setRange(0,0)`) mientras se abre el archivo, determinada al conocer el conteo. La escritura no es cancelable (R15) → el botón Cancelar **se oculta**, no se deshabilita. Cancelar la validación descarta el informe y vuelve al paso 1 con aviso: un informe parcial parece completo y es peligroso |
| DS8 | H10 | Tras confirmar, la pantalla **no se cierra**: "812 importadas · 188 pendientes" con *Exportar las 188 a Excel* y *Corregirlas a mano ahora*, que cierra el modal dejando la vista filtrada por cartones sin comprador |
| DS9 | H11 | `marcar_vendidos_por_rango` (R7) gana puerta de entrada: botón en la barra de Compradores, modal desde/hasta con previsualización del conteo antes de aplicar ("Se marcarán 201 cartones como vendidos") |
| DS10 | H12 | Modo ráfaga en el alta manual: foco en el campo de código al abrir, Tab/Enter avanza, `Ctrl+Enter` guarda y limpia devolviendo el foco al código, y una línea de confirmación de la última alta. 30 ventas de puerta dejan de ser 30 viajes al ratón |
| DS11 | H14 | *Valor* visible solo con tipo = efectivo. Widget: `QLineEdit` con validación + `dominio/dinero.a_centavos`, **nunca** `QDoubleSpinBox` — reintroduciría el flotante que D3 acaba de quitar de la base |
| DS12 | H15 | Vista previa del tema: **solo lectura + spinboxes**, sin arrastre sobre el lienzo. Coherente con D9, que ya renuncia al WYSIWYG. Sin escribirlo, el implementador elige arrastrar y pierde dos días en un editor que la fase 5 reemplaza |
| DS13 | H16 | La rejilla del editor de patrones se pinta con los colores del `tema_json` del evento: cumple literalmente el contrato §4.6 ("vista previa de cómo se verá en la pantalla de transmisión") y conecta las dos superficies nuevas |
| DS14 | H17 | **Regla nueva para `docs/convenciones-codigo.md`:** autoguardado con retardo solo en editores de configuración visual de un registro único (plantilla, tema); Guardar/Cancelar explícito en toda entidad de una colección (comprador, ronda, patrón). Corolario: cambiar de fila con cambios sin guardar pide confirmación de descarte |
| DS15 | H18 | Reordenar en memoria; escribir con retardo (`RETARDO_VISTA_PREVIA_MS`, ya existe); no recargar la lista tras escribir salvo error; **mantener seleccionada y enfocada la ronda movida** para que Subir-Subir-Subir funcione a repetición |
| DS16 | H19 | Dos grupos con encabezado (Sistema / De la organización) e icono de candado. **Restricción sobre R2:** `asegurar_patrones_sistema` **no** actualiza máscaras de un patrón referenciado por una ronda de un evento que no esté en `borrador` — si no, cambia en silencio la definición de quién gana |
| DS17 | H20 | El selector de patrón **no es un `QComboBox`**: un patrón se reconoce por su forma, no por su nombre. Selector visual de miniaturas 5x5 con nombre debajo, agrupadas, con *Nuevo*/*Duplicar*/*Editar* dentro del propio selector (así el catálogo se gestiona sin tener que estar creando una ronda) |
| DS18 | H21 | Claves i18n distintas: "Quitar comprador del cartón" vs "Anular cartón". El diálogo de confirmación dice a qué estado vuelve el cartón (R12) |
| DS19 | H22, H23, H24 | Teclado: ampliar `ATAJOS` con `importar` (Ctrl+I), `buscar` (Ctrl+F), `nueva_ronda`, `subir`/`bajar` (Ctrl+Shift+Arriba/Abajo); secciones del evento con Alt+1..7 en `espacio_evento.py`; las tres vistas conectan `nuevo`/`guardar`/`cancelar`. Modal: botón por defecto por paso, Esc en el informe pide confirmación si ya hay filas validadas, foco inicial en Confirmar. Rejilla 5x5: `StrongFocus`, flechas, Espacio, Inicio/Fin, contorno con `_ANILLO_FOCO`. Más arrastrar y soltar el `.xlsx` sobre la vista (~15 líneas) |
| DS20 | H25, H26, H27 | `addRow("&Nombre", campo)` con buddy y `setTabOrder` en los formularios nuevos; celdas de la rejilla ≥ `OBJETIVO_PULSACION_MINIMO_PX`, contadores del informe ≥ 18 px; señal por **icono + texto**, con el color acompañando y no informando (coherente con DU-1, que trata el color como identidad, no como semántica) |
| DS21 | nota | D9 gana una línea: los colores del editor de tema pintan la **pantalla de transmisión**, nunca el `QSS` de la app del operador (DU-1) |

## B.4 Decisiones de gusto (van al gate)

- **TD-1 (H2):** orden del riel de secciones. Actual: Datos, Cartones, Plantilla, Compradores,
  Rondas. Propuesto por urgencia operativa: Datos, Cartones, **Compradores**, Rondas, Plantilla,
  Tema, Auditoría — Plantilla no se toca nunca más una vez impresos los cartones, y Compradores
  es la sección de la noche del evento.
- **TD-2 (H10b):** editar el código **dentro** de la tabla del informe y revalidar esa fila.
  R3 (normalización) tapa ~80% de los códigos mal transcritos; esto cubriría el 20% restante sin
  salir a Excel. Coste: edición en línea sobre la tabla del informe.

## B.5 Tareas de implementación (Fase Diseño)

- [ ] **T11 (P1, humano ~2h / CC ~15min)** — ui — Canal de éxito de tres niveles
  - Surgido por: B.2 H6 — los éxitos de las fases 2 y 3 ya salen sobre fondo rojo
  - Archivos: `ui/dialogos.py`, `ui/tema.py`, `ui/vistas/vista_cartones.py`
  - Verificar: `pytest tests/ui/test_tema.py`
- [ ] **T12 (P1, humano ~3h / CC ~20min)** — ui — Chip de "listo para jugar" en el espacio del evento
  - Surgido por: B.3 DS1 (H1) — nada responde "¿qué falta para poder jugar?"
  - Archivos: `ui/espacio_evento.py`, `servicios/servicio_rondas.py`
  - Verificar: `pytest tests/ui/test_navegacion.py`
- [ ] **T13 (P1, humano ~5h / CC ~30min)** — ui — Pantalla de informe de importación
  - Surgido por: B.3 DS3, DS7, DS8 (H4, H7, H8, H10) — el corazón de la fase estaba en una frase
  - Archivos: `ui/vistas/vista_compradores.py`
  - Verificar: `pytest tests/ui/test_vista_compradores.py`
- [ ] **T14 (P1, humano ~4h / CC ~25min)** — ui — Selector visual de patrones + rejilla accesible
  - Surgido por: B.3 DS17, DS13, DS19 (H20, H16, H24) — un patrón se reconoce por su forma
  - Archivos: `ui/widgets/rejilla_patron.py`, `ui/widgets/selector_patron.py`
  - Verificar: `pytest tests/ui/test_rejilla_patron.py`
- [ ] **T15 (P1, humano ~3h / CC ~20min)** — ui — Teclado en las superficies nuevas
  - Surgido por: B.3 DS19, DS20 (H22-H26) — `atajos.py` dice que el teclado tiene que alcanzar
  - Archivos: `ui/atajos.py`, `ui/espacio_evento.py`, las tres vistas nuevas
  - Verificar: `pytest tests/ui/ -k teclado`
- [ ] **T16 (P2, humano ~2h / CC ~15min)** — ui — Modo ráfaga y venta por rango
  - Surgido por: B.3 DS9, DS10 (H11, H12) — el flujo real de la noche del evento
  - Archivos: `ui/vistas/vista_compradores.py`
  - Verificar: `pytest tests/ui/test_vista_compradores.py -k rafaga`
- [ ] **T17 (P2, humano ~1h / CC ~10min)** — docs — Regla de guardado explícito vs implícito
  - Surgido por: B.3 DS14 (H17) — el proyecto tiene hoy dos patrones incompatibles
  - Archivos: `docs/convenciones-codigo.md`
  - Verificar: lectura

---

# ANEXO C — Revisión de ingeniería (`/gstack-autoplan` Fase 3)

Voz: subagente Claude independiente, con lectura del código real. Codex no disponible.
**5 CRÍTICOS, 11 ALTOS, 10 MEDIOS, 9 huecos de prueba.** Esta revisión corre la última, sobre el
plan ya enmendado por las fases 1 y 2.

**Dos errores de hecho en §0 de este plan, verificados:**
- `repo_evento.actualizar_tema` **ya existe** (`repo_evento.py:153`), con la misma validación de
  JSON que `actualizar_plantilla`. §4.8 lo llamaba "verbo nuevo".
- `Tarea.run()` (`tarea.py:50-56`) inyecta siempre `al_progresar=`/`debe_cancelar=` y nunca pasa
  conexión. Ver C5.

## C.1 Críticos

| # | Hallazgo | Corrección |
|---|---|---|
| **C1** | D5 pone `UPDATE ronda SET orden = -(orden+1)` **dentro de `servicio_rondas`**: rompe `test_arquitectura.py:77` (literal SQL fuera de `persistencia/`) y `:88` (`.execute` fuera de `persistencia/`), y viola `CLAUDE.md`. El algoritmo además falla si quedan órdenes negativas de un fallo previo (`-(-2+1) = 1` vuelve al rango positivo) y deja rondas en negativo si `ids_en_orden` no las trae todas | `repo_ronda.desplazar_ordenes_a_negativo(con, evento_id) -> int` + `repo_ronda.actualizar_orden(con, ronda_id, orden)`. El servicio solo orquesta dentro de `transaccion()`. Validar que `ids_en_orden` es el conjunto **completo** del evento antes de la primera pasada |
| **C2** | R12 exige `vendido → impreso`; la tabla D2 no lo permite. El camino más común (`impreso → vendido → impreso`) lanza `ErrorTransicionInvalida` | `"vendido": {"impreso", "entregado", "anulado"}`. Y "su estado anterior" no se parsea de `auditoria.detalle`: columna nueva `comprador.estado_carton_previo` en la 003 |
| **C3** | `patron.mascara` es `NOT NULL` (`001_inicial.sql:91`) y SQLite no puede quitar un `NOT NULL` con `ALTER TABLE`. R1 y D1 se contradicen | **Reconstruir `patron` en la 003** (`CREATE TABLE patron_nuevo` → `INSERT ... SELECT` → `DROP` → `RENAME`). Cero filas en cualquier base: este es el momento exacto y no vuelve. La prueba de arquitectura vigila `SELECT` **e** `INSERT` |
| **C4** | §4.1 omite `clave_i18n`, `version_semilla` y `recaudado_real_centavos`, que los anexos dan por decididas. Y `ALTER TABLE ADD COLUMN` **no admite `UNIQUE`** en SQLite | §4.1 se reescribe como única fuente de verdad de la 003. La unicidad de `clave_i18n` va como índice parcial: `CREATE UNIQUE INDEX idx_patron_clave_sistema ON patron(clave_i18n) WHERE clave_i18n IS NOT NULL`. Sin él, dos arranques solapados duplican el catálogo en silencio |
| **C5** | `Tarea(aplicar_importacion)` contra `aplicar_importacion(con, evento_id, informe)` → `TypeError` presentado como `error.desconocido` **después** de lanzar el hilo | Envoltorios de módulo `_validar_importacion_en_hilo` / `_aplicar_importacion_en_hilo`, con `abrir_conexion()`/`cerrar_conexion()` en `try/finally`, calcados de `_generar_lote_en_hilo` (`vista_cartones.py:54`). Los servicios aceptan ambos kwargs aunque `aplicar_importacion` ignore `debe_cancelar` (R15) |

## C.2 Altos

| # | Hallazgo | Corrección |
|---|---|---|
| **A1** | **Riesgo real de `ErrorBaseBloqueada`.** ~20.000 sentencias sosteniendo el lock de escritor; `BUSY_TIMEOUT_MS = 5000`; `test_concurrencia.py:32` ya demuestra el fallo. Escritores que esta fase añade: autoguardado de `vista_tema`, escritura diferida del reordenado (DS15) | **→ Decisión de Gabriel (TD-3).** Mínimo obligatorio: inhibir toda acción de escritura del espacio del evento y parar los `QTimer` de autoguardado mientras corre la Tarea de escritura; y **medir** 10.000 filas con `synchronous=FULL` en disco lento antes de cerrar la fase |
| **A2** | R15 aborta las 999 filas buenas porque una cambió. A las once de la noche eso es inaceptable | Clasificar la discrepancia: mismo comprador → se salta (idempotente); `anulado` o de otro → se salta y se reporta en la pantalla post-escritura de DS8; solo aborta el fallo de integridad real. `FilaImportacion` lleva `carton_id` y `estado_esperado` ya resueltos → `UPDATE ... WHERE id=? AND estado=?` con `rowcount` como detector de carrera (patrón ya establecido en `repo_carton.py:150`) |
| **A3** | R11 deja la auditoría apuntando a una fila borrada (peor que no auditar), y "barrer la auditoría del evento" borraría `lote.creado`, `carton.cambio_estado`… sobre los que T9 construye su panel | **Borrado lógico** (`comprador.anulado_en`), que gana en trazabilidad **y** en minimización — resuelve también TD-4. El barrido LOPDP es selectivo (`accion LIKE 'venta.%'`) |
| **A4** | `exportar_plantilla(..., idioma)` mete i18n en `servicios/` y deja el helper antifórmula de R13 sin casa | `impresion/reporte.py` es el **único** que escribe `.xlsx`. Firma: `exportar_plantilla(con, evento_id, ruta_destino, textos: Mapping[str, str])` |
| **A5** | R13 está mal especificado: en `openpyxl` el `'` se guarda como parte del texto (el quote-prefix real es un atributo de estilo), y `+`/`-`/`@` no los evalúa Excel al abrir un `.xlsx` — eso es inyección de CSV. El vector real es `Cell.value` con `=`, que se guarda como `data_type='f'` | `celda.set_explicit_value(valor, data_type="s")` para toda cadena que empiece por `=`. **La aserción de T5 estaba mal**: debe afirmar `celda.data_type == "s"` **y** `celda.value == "=1+1"` — con el prefijo `'` habría pasado siendo incorrecta |
| **A6** | `LIMITE_FILAS_IMPORTACION` no acota la memoria: `ws.max_row` sale del propio archivo (lo controla quien lo manda) y `sharedStrings.xml` se carga **entera antes** de iterar. Un `.xlsx` de 200 KB puede descomprimir a 2 GB | Tope de tamaño en disco + tope de tamaño **descomprimido** sumando `ZipFile.infolist()[].file_size` antes de `load_workbook` (mismo espíritu que `LIMITE_PIXELES_IMAGEN`); contar filas con `iter_rows`, nunca confiar en `max_row` |
| **A7** | Ni D7 ni R6 dicen **de qué hoja** se lee, y el plan se contradice a sí mismo: §4.4 la llama `Compradores`, R6 la llama `Ventas` | Buscar la primera hoja con fila de encabezado reconocible; si hay varias candidatas, el operador elige en el paso 1. Nombre único: **`Ventas`** |
| **A8** | `validar_evento_listo -> list[str]` no admite parámetros, pero el texto pide "faltan 3 rondas sin premio" y DS1 necesita el contador. Y exigir "al menos un cartón vendido" **impide jugar** un evento que se vende entero en la puerta | `list[PendienteEvento]` (dataclass con `clave_i18n` y `parametros`). La comprobación de cartón vendido es **aviso, no bloqueo** |
| **A9** | `ronda.patron_id` es `NOT NULL` (`001_inicial.sql:102`): la comprobación "toda ronda tiene patrón" está muerta y el estado vacío intermedio de DS4 **no puede existir** | Se mantiene `NOT NULL`: el formulario de ronda exige patrón antes de guardar. Se caen la comprobación muerta y ese estado vacío de DS4 |
| **A10** | N+1 escondido: `ya_asignado` y `ya_registrado_igual` necesitan el comprador actual de cada cartón → 10.000 `SELECT` en la ruta que corre dentro de `Tarea`. Y `al_progresar` por fila son 10.000 señales cruzando hilos | Precargar `dict[carton_id, Comprador]` con una llamada a `listar_por_evento`. Progreso **por bloque**, como `generar_lote` (`servicio_cartones.py:167`) |
| **A11** | Alcance: 3 repos, 5 servicios, 4 vistas, 2 widgets, 2 módulos de dominio, migración correctiva, ~100 claves i18n, más 17 tareas de los anexos — una de las cuales modifica `vista_cartones.py` de la fase 2 | **→ Decisión de Gabriel (UC-4).** Propuesta: `v0.4.0` = compradores + conciliación; `v0.5.0` = patrones + rondas + tema |

## C.3 Medios (auto-corregidos)

- **M1** `repo_evento.actualizar_tema` ya existe (`repo_evento.py:153`) — corregir §4.8 y §0.
- **M2** Verbos fuera de la tabla de convenciones: `contar_sistema` → `contar_por_es_sistema`;
  `siguiente_orden` no es verbo (usar `contar_por_evento` y sumar 1 en el servicio);
  `listar_por_evento` sin defaults (`limite=None, desplazamiento=0`); `existe_nombre` necesita
  `organizacion_id`; `actualizar_comprador` → `actualizar`; `guardar_imagen_premio` no recibe el
  `ronda_id` con el que dice nombrar el archivo; `validar_patron` sin `con` no puede comprobar
  unicidad (esa comprobación sube a `crear_patron`).
- **M3** `idx_ronda_evento` duplica el índice de `UNIQUE(evento_id, orden)` e
  `idx_comprador_carton` duplica el de `carton_id UNIQUE`. Dejar solo `idx_patron_organizacion`.
- **M4** `mascaras` se valida en el repositorio antes de escribir (precedente:
  `repo_evento.actualizar_plantilla`). `_desde_fila` con `mascaras IS NULL` lanza
  `ErrorIntegridad`: devolver `[]` significa "nadie gana nunca" en `any(...)`, que es exactamente
  el modo de fallo crítico y silencioso.
- **M5** `openpyxl` en `read_only=True` deja el `.xlsx` bloqueado en Windows hasta `wb.close()`:
  `try/finally` obligatorio.
- **M6** Celdas combinadas: en `read_only=True` openpyxl no expone `merged_cells`. Decidir por
  escrito si se abre sin `read_only` (y entonces el tope de filas es obligatorio de verdad) o si
  la heurística de R4 es la única defensa. **Decisión: heurística de R4 + prueba explícita.**
- **M7** `normalizar(codigo, prefijo, ancho)` es ambiguo con varios lotes (`1` casa con
  `A-2026-000001` y `B-2026-000001`). Normalizar contra el diccionario del evento; si casa con
  más de un prefijo, clasificar la fila como **ambigua**, no elegir.
- **M8** `eliminar_ronda` no borra la imagen del premio: anotarlo como
  `limpiar_lotes_huerfanos` (`servicio_cartones.py:232`).
- **M9** `patron.nombre` es `NOT NULL` y R2 añade `clave_i18n`: los patrones del sistema tendrían
  dos nombres. **Decisión:** `nombre` guarda el español como respaldo; la vista pinta
  `t(clave_i18n)` y cae a `nombre` solo si la clave falta.
- **M10** `version_semilla` **por fila** de `patron`, no marca global (DS16 deja media base en v1 y
  media en v2). El arranque registra en auditoría los patrones que no pudo actualizar.

## C.4 Diagrama de arquitectura (Fase 4 sobre lo existente)

```
        ui/espacio_evento.py  [MODIFICADO: chip "listo para jugar", DS1]
                 |
   +-------------+--------------+--------------+---------------+
   |             |              |              |               |
 vista_        vista_        vista_         vista_          vista_
 compradores   rondas        tema*          auditoria       cartones
   |             |              |              |            [MODIF: T11]
   |  _*_en_hilo |              |              |
   |  (Tarea)    |              |              |
   v             v              v              v
 servicio_    servicio_     (repo_evento.   repo_auditoria
 compradores  rondas         actualizar_      [YA EXISTE]
   |          servicio_      tema YA EXISTE)
   |          patrones
   |             |
   +------+------+------+---------------+
          |             |               |
     repo_comprador  repo_ronda    repo_patron        <- NUEVOS
          |             |               |
          +-------------+---------------+
                        |
              persistencia/conexion.py  [transaccion(), BEGIN IMMEDIATE]
                        |
                    bingo.db (WAL)

  servicio_conciliacion --> impresion/reporte.py   <- ÚNICO escritor de .xlsx (A4)
                                    ^
                                    +-- exportar_plantilla (movido desde servicios/, A4)

  dominio/  patron.py  codigo.py  tema.py*  estados.py[MODIF: C2]  <- Python puro
  (*) tema.py y vista_tema.py salen si se acepta UC-2
```

## C.5 Diagrama de pruebas y huecos

| Elemento nuevo | Tipo | ¿Existe en el plan? | Hueco |
|---|---|---|---|
| Migración 003 sobre base 002 **poblada** | Integración | **NO** | `conftest.py:48` migra desde cero una vez por sesión; la ruta de actualización real no la ejercita nadie |
| `Tarea` + firmas nuevas (composición) | Integración | **NO** | `test_tarea.py` prueba la clase, no el acoplamiento — es donde revienta C5 |
| Concurrencia con la forma de la fase 4 | Integración | **NO** | Molde en `test_concurrencia.py:32` |
| Paridad `es.json` / `en.json` | Arquitectura | **NO** | `test_arquitectura.py:123` solo compara claves de `Error*` contra `es.json`. Con `MARCA_FALTANTE`, una clave olvidada en inglés sale como `⟦clave⟧` en producción. Esta fase añade ~100 |
| `.xlsx` patológicos | Unidad | Parcial | Faltan: cero filas; solo encabezado; hoja buena en tercera posición; celdas combinadas; `sharedStrings` desproporcionado; extensión `.xlsx` que no es zip; `PermissionError` al exportar |
| `reordenar` con entrada mala | Unidad | Parcial | Faltan: `ids_en_orden` incompleto y con id repetido |
| `anular_venta` desde ambos orígenes | Unidad | **NO** | Donde revienta C2 |
| Rollback de `aplicar_importacion` | Integración | Parcial | Añadir `con.in_transaction is False` y que el envoltorio cerró la conexión en su `finally` |
| `es_ganador` con `mascaras` vacía | Unidad | **NO** | Hoy `any([])` es `False` en silencio |

## C.6 Seguridad y datos personales

El dato personal acaba en **cinco copias sin cifrar** en el disco del operador, y el plan no las
enumeraba: `bingo.db`, `bingo.db-wal`, el `.xlsx` de conciliación (que se manda por WhatsApp), el
`.xlsx` del informe de errores (DS8) y el `.xlsx` de plantilla que devuelve la organización.
Sin cifrado (`TODOS.md` P3) y sin política de retención (P1, diferida por tercera fase consecutiva).
El `.xlsx` de entrada es **entrada no confiable**: no se abre con `keep_vba`, y la ruta de destino
de exportación se valida. Comprobar que el `restriccion` que `ErrorIntegridad` conserva
(`comprador.carton_id UNIQUE`) no acaba enseñando datos personales en la franja de la vista.

## C.7 Tareas de implementación (Fase Eng)

- [ ] **T18 (P1, humano ~2h / CC ~15min)** — persistencia — Reordenado sin SQL en el servicio
  - Surgido por: C.1 C1 — rompe `test_arquitectura.py:77` y `:88`
  - Archivos: `repo_ronda.py`, `servicio_rondas.py`
  - Verificar: `pytest tests/arquitectura tests/servicios/test_servicio_rondas.py`
- [ ] **T19 (P1, humano ~1h / CC ~10min)** — dominio — `vendido → impreso` y estado previo
  - Surgido por: C.1 C2 — fallo garantizado en el camino más común de anulación
  - Archivos: `dominio/estados.py`, `003_fase4.sql`
  - Verificar: `pytest tests/dominio/test_estados.py tests/servicios -k anular`
- [ ] **T20 (P1, humano ~4h / CC ~25min)** — persistencia — Reescribir la 003 (reconstruir `patron`)
  - Surgido por: C.1 C3, C4 — `NOT NULL` no se quita con `ALTER`; `UNIQUE` no se añade con `ALTER`
  - Archivos: `003_fase4.sql`, `tests/persistencia/test_migraciones.py`
  - Verificar: `pytest tests/persistencia/test_migraciones.py -k "003 or poblada"`
- [ ] **T21 (P1, humano ~2h / CC ~15min)** — ui — Envoltorios de hilo para la importación
  - Surgido por: C.1 C5 — `TypeError` presentado como `error.desconocido`
  - Archivos: `ui/vistas/vista_compradores.py`, `servicios/servicio_compradores.py`
  - Verificar: `pytest tests/ui/test_vista_compradores.py -k hilo`
- [ ] **T22 (P1, humano ~3h / CC ~20min)** — servicios — Discrepancia no destructiva + sin N+1
  - Surgido por: C.2 A2, A10 — una fila cambiada no puede tirar las otras 999
  - Archivos: `servicio_compradores.py`
  - Verificar: `pytest tests/servicios/test_servicio_compradores.py -k discrepancia`
- [ ] **T23 (P1, humano ~2h / CC ~15min)** — servicios — Defensa real del `.xlsx` (zip, hoja, cierre)
  - Surgido por: C.2 A6, A7; C.3 M5 — el vector es `sharedStrings`, no el número de filas
  - Archivos: `impresion/reporte.py`, `servicio_compradores.py`, `config/ajustes.py`
  - Verificar: `pytest tests/servicios/test_servicio_compradores.py -k "zip or hoja"`
- [ ] **T24 (P1, humano ~1h / CC ~10min)** — impresion — Antifórmula correcto y su prueba
  - Surgido por: C.2 A5 — la aserción de T5 habría pasado siendo incorrecta
  - Archivos: `impresion/reporte.py`, `tests/impresion/test_reporte.py`
  - Verificar: prueba que afirma `data_type == "s"` **y** `value == "=1+1"`
- [ ] **T25 (P1, humano ~2h / CC ~15min)** — privacidad — Borrado lógico del comprador
  - Surgido por: C.2 A3 — R11 dejaba la auditoría apuntando a una fila borrada
  - Archivos: `003_fase4.sql`, `repo_comprador.py`, `servicio_compradores.py`
  - Verificar: `pytest tests/servicios -k "anular or lopdp"`
- [ ] **T26 (P2, humano ~1h / CC ~10min)** — tests — Paridad `es.json` / `en.json`
  - Surgido por: C.5 — una clave olvidada sale como `⟦clave⟧` en producción, en silencio
  - Archivos: `tests/arquitectura/test_arquitectura.py`
  - Verificar: `pytest tests/arquitectura -k paridad`
- [ ] **T27 (P2, humano ~2h / CC ~15min)** — servicios — `PendienteEvento` y verbos de convención
  - Surgido por: C.2 A8, A9; C.3 M2 — tipo incoherente y 7 firmas fuera de la tabla
  - Archivos: `servicio_rondas.py`, `repo_patron.py`, `repo_ronda.py`, `repo_comprador.py`
  - Verificar: `pytest tests/servicios`

---

# ANEXO D — Decisiones de Gabriel (cerradas el 2026-09-09)

Estas no se auto-decidieron: cada una revertía algo escrito por Gabriel, o pedía una decisión
que no le corresponde al implementador. **Resueltas en el gate final.**

## D.0 Resoluciones

| # | Desafío | Resolución | Efecto en el plan |
|---|---|---|---|
| **UC-1** | Elegibilidad permisiva | **RECHAZADO — se mantiene la regla estricta** | `Proyecto_Alcance.md:190` y `Fase_5/Contrato_Fase5.md:101` se quedan como están. Un cartón solo juega si está `vendido` **y** tiene fila `comprador`. Consecuencia: ver D.1 |
| **UC-2** | Mover §4.8 a la fase 5 | **RECHAZADO — el editor de tema se queda** | `dominio/tema.py` y `ui/vistas/vista_tema.py` siguen en alcance. Mitigación en D.2 |
| **UC-3** | Quitar la cédula | **PARCIAL — columna opcional, no exportada por defecto** | Ver D.3 |
| **UC-4** | Partir en dos entregas | **RECHAZADO — una sola fase** | Las 27 tareas van juntas, etiqueta `v0.4.0`. La numeración de las cinco fases no cambia |
| **D4** | Qué crea la venta por rango | **ACEPTADO — crea comprador provisional** | Ver D.1 |

## D.1 Consecuencia de UC-1 + D4: el comprador provisional

Con la regla estricta, `marcar_vendidos_por_rango` (T6) tenía que crear la fila `comprador` o los
cartones de venta de puerta quedaban vendidos **y sin poder ganar** — el mismo escenario que la
regla estricta pretendía evitar, con la agravante de dar falsa seguridad.

**Enmienda al esquema (003):**
```sql
ALTER TABLE comprador ADD COLUMN provisional INTEGER NOT NULL DEFAULT 0;
```

- `marcar_vendidos_por_rango(con, evento_id, desde, hasta)` crea, dentro de la misma
  `transaccion()`, una fila `comprador` por cartón con `provisional = 1` y `nombre` puesto al
  texto ya traducido que le pasa la vista (`"Venta en puerta"` / `"Door sale"`) — el servicio no
  importa i18n, mismo convenio que A4.
- **Sin datos personales:** teléfono, cédula y correo quedan `NULL`. Estas filas no añaden
  exposición LOPDP; son el mínimo que la regla estricta exige para que el cartón participe.
- **Interacción nueva con la importación** (no existía antes de esta decisión): si el Excel trae
  después el comprador real de un cartón que ya tiene fila provisional, la importación **no**
  puede clasificarlo como `ya_asignado`. Categoría nueva del informe:
  `completa_provisional` — se muestra aparte y al aplicar hace `UPDATE` sobre la fila existente
  poniendo `provisional = 0`. Sin esto, cada venta de puerta que luego aparezca en el Excel se
  reporta como conflicto.
- **Conciliación:** `Conciliacion` gana `compradores_provisionales: int`. La advertencia de
  discrepancia (§4.7) compara contra los **no** provisionales; el reporte muestra las dos cifras
  por separado, porque "820 vendidos, 200 de ellos sin datos de contacto" es exactamente lo que
  la organización necesita saber antes del sorteo.
- **`validar_evento_listo`:** el aviso de "al menos un cartón vendido" (C.2 A8) lo satisface
  también una venta por rango, que es lo correcto.

## D.2 Consecuencia de UC-2: el editor de tema se queda

Se mantiene el alcance, con dos mitigaciones que el propio análisis de UC-2 dejó sobre la mesa:

- **`dominio/tema.py` incluye desde ahora los bloques que `Fase_5/Contrato_Fase5.md:43` ya pide**
  y que el documento técnico §7 no tiene: `contador_bolas`, `reloj` y `banner_texto`. Escribirlos
  ahora cuesta tres entradas más en una dataclass; descubrirlos en la fase 5 cuesta migrar los
  `tema_json` ya guardados. Los defaults por campo ausente (§4.8) ya permiten que la fase 5 añada
  más sin migrar.
- **D9 gana la línea de DS21:** los colores del editor pintan la pantalla de transmisión, nunca el
  `QSS` de la app del operador (DU-1). Sin esa línea, alguien que lea "editor de colores" a las
  dos de la mañana intentará aplicarlos al tema del operador.
- Se acepta explícitamente el riesgo: la vista previa son rectángulos etiquetados, no WYSIWYG
  (D9), y la fase 5 puede sustituirlos por los widgets reales sin tocar el modelo ni el editor.

## D.3 Consecuencia de UC-3: la cédula como columna opcional

- La columna **sigue** en la plantilla de exportación, con encabezado marcado como opcional en la
  hoja `Instrucciones`.
- **El reporte de conciliación no la exporta.** La hoja `Detalle` sale con código, estado y
  nombre; teléfono, cédula y correo solo con una casilla explícita *"incluir datos de contacto"*,
  **desmarcada por defecto**. Esto corta la fuga más grave: el `.xlsx` que viaja por WhatsApp deja
  de llevar cédulas por defecto.
- La hoja `Instrucciones` lleva el aviso de finalidad, plazo de conservación y responsable. Es el
  único punto del sistema donde el titular del dato puede ser informado, y es gratis.
- **Sigue pendiente y sube a P1 en `TODOS.md`:** la política de retención. Es la tercera fase
  consecutiva que la difiere y la primera que crea el dato.

## D.4 Decisiones de gusto pendientes

`TD-3` (atomicidad contra `busy_timeout`) sigue **sin decidir** y es la de más peso: la escritura
de 10.000 filas en una sola transacción puede superar los 5 s de `BUSY_TIMEOUT_MS`. Mínimo
obligatorio mientras no se decida: inhibir toda otra escritura del espacio del evento y parar los
`QTimer` de autoguardado durante la Tarea, y **medir** antes de cerrar la fase.

Sin decidir tampoco: `TD-1` (orden del riel), `TD-2` (editar el código dentro del informe),
`TD-5` (fixtures `.xlsx` reales), `TD-6` (modo escáner QR), `TD-7` (pegar desde el portapapeles).

---

## D.5 Texto original de los desafíos (para trazabilidad)

## User Challenges (dos o más voces independientes piden cambiar tu dirección)

**UC-1 — Compuerta de elegibilidad.**
Tú escribiste: `Proyecto_Alcance.md:190` — *"solo participan cartones en estado vendido **con
comprador registrado**"*, reforzado en `Fase_5/Contrato_Fase5.md:101`.
Ambas voces recomiendan: modo de elegibilidad configurable por evento — (a) estricto, el actual;
(b) permisivo, participa todo cartón `impreso|entregado|vendido` no `anulado`.
Por qué: la organización vende 1.000 y devuelve 780. Las otras 220 tienen cartón físico legítimo
con QR firmado por ti. A las 21:30 una de ellas canta bingo y el sistema la rechaza **en cámara**.
Qué podríamos estar sin ver: quizá la regla estricta es un requisito que la organización te
impuso, o una defensa antifraude que conoces y nosotros no.
Si nos equivocamos, el coste es: un cartón que nunca se vendió podría cobrar un premio.

**UC-2 — El editor de tema del dashboard (§4.8).**
Tú escribiste: `Contrato_Fase4.md §4.8` lo pone en esta fase.
Tres voces independientes recomiendan moverlo a la fase 5.
Por qué: ninguno de los cinco criterios de aceptación de la fase 4 lo menciona; la pantalla que
consume el `tema_json` se construye en la fase 5; `Fase_5/Contrato_Fase5.md:43` ya lista bloques
(contador de bolas, reloj, banner) que **no existen** en el `tema_json` del documento técnico §7.
En la fase 5 la vista previa es gratis: la ventana de transmisión real *es* la vista previa.
Qué podríamos estar sin ver: quizá quieres enseñarle el diseño a la organización antes del evento.
Si nos equivocamos, el coste es: la fase 5 llega con una cosa más que hacer.

**UC-3 — La cédula en el flujo masivo.**
Tú escribiste: `Contrato_Fase4.md §4.1` — columnas de nombre, teléfono, **cédula** y correo.
Recomendación: quitarla de la plantilla y del alta por defecto; pedirla solo al confirmar un
ganador de premio en efectivo (3-8 personas, no 1.000).
Por qué: recorre el sistema entero y no la usa nada — no valida al ganador (lo hace el código del
cartón), no se imprime, no va al acta. Bajo la LOPDP es recolección sin finalidad, y tú eres el
encargado del tratamiento sin contrato que lo diga (`TODOS.md` P1, tres fases sin moverse, con un
evento real agendado).
Qué podríamos estar sin ver: quizá la organización la exige para su propia contabilidad.
Si nos equivocamos, el coste es: pedirla después a los ganadores, que son pocos.

**UC-4 — Partir la fase en dos.**
Recomendación de la revisión de ingeniería: `v0.4.0` = compradores + conciliación;
`v0.5.0` = patrones + rondas + tema.
Por qué: 3 repositorios, 5 servicios, 4 vistas, 2 widgets, 2 módulos de dominio, una migración
correctiva, ~100 claves i18n y 27 tareas — una de las cuales modifica `vista_cartones.py` de la
fase 2. La numeración de fases se desplazaría.
Si nos equivocamos, el coste es: renumerar cinco documentos por una fase que sí cabía entera.

## Decisiones de gusto

- **TD-1** — Orden del riel de secciones (`Compradores` tercera en vez de cuarta).
- **TD-2** — Editar el código **dentro** de la tabla del informe y revalidar esa fila.
- **TD-3** — **Atomicidad contra `busy_timeout`** (C.2 A1). La escritura de 10.000 filas en una
  sola transacción puede superar los 5 s de `BUSY_TIMEOUT_MS` y hacer que otro escritor salga con
  `ErrorBaseBloqueada`. Trocear lo evita, pero rompe la atomicidad, **que es el criterio de
  aceptación**. Opciones: (a) una sola transacción + inhibir todo otro escritor mientras corre;
  (b) subir `busy_timeout` solo durante la importación; (c) trocear y aceptar escritura parcial.
- **TD-5** — Tres `.xlsx` reales de ~20 KB en el repositorio como fixtures.
- **TD-6** — Modo escáner de QR (lector USB de $20; 200 ventas de puerta pasan de 40 min a 5).
- **TD-7** — Pegar desde el portapapeles un bloque tabulado, como tercera vía de entrada.

---

# ANEXO E — Re-revisión de ingeniería sobre las enmiendas del gate

Las enmiendas del ANEXO D tocan esquema y clasificación de la importación, así que Ingeniería
volvió a correr sobre ellas (regla del gate: la revisión de ingeniería siempre revisa el plan
final). **3 críticos, 4 altos, 6 medios.** Dos son contradicciones internas del propio ANEXO D.

**Un error de hecho en D.2, verificado:** `banner_texto` **sí existe** en el documento técnico §7
(línea 526), y con forma **distinta** a los demás bloques — `{"visible": false, "texto": ""}`, sin
`pos` ni `escala`. D.2 afirmaba que los tres bloques faltaban; uno estaba, y el que estaba no es
homogéneo con `ConfigBloque`.

## E.1 Críticos

| # | Hallazgo | Corrección |
|---|---|---|
| **E-C1** | **La advertencia de discrepancia se vuelve falsa alarma permanente.** §4.7 la define como "un cartón `vendido` sin fila `comprador`", pero D.1 ordenaba comparar contra los **no** provisionales. Todo evento con venta de puerta la dispararía, y DS2 la pinta en la vista toda la noche | La comprobación de integridad compara `vendidos` contra `provisionales + no_provisionales` (excluyendo `anulado_en`). `compradores_provisionales` se muestra como cifra informativa aparte — "200 sin datos de contacto" — nunca como discrepancia |
| **E-C2** | **Un cartón ya vendido tira el rango entero.** `carton_id NOT NULL UNIQUE` + una sola `transaccion()`: si algún cartón del rango ya tiene comprador (importación previa, rango solapado, doble clic), el `INSERT` lanza `ErrorIntegridad` y el `ROLLBACK` tira los otros 200. Es el modo de fallo que C.2 A2 prohíbe, reintroducido por la puerta de atrás | `marcar_vendidos_por_rango` **filtra antes de insertar** (cartones del rango sin comprador vivo y en estado que admita `→ vendido`) y devuelve desglose: `marcados`, `ya_vendidos`, `omitidos_anulados`, `omitidos_sin_imprimir`. La previsualización de DS9 muestra las cuatro cifras, no solo "Se marcarán 201" |
| **E-C3** | **El borrado lógico (T25) choca con `UNIQUE(carton_id)`.** Una venta anulada **deja la fila** ocupando el hueco único: revender ese cartón falla con `unique`, y la importación posterior encuentra una fila provisional anulada sin categoría que la acoja | Índice único parcial `CREATE UNIQUE INDEX idx_comprador_carton_vivo ON comprador(carton_id) WHERE anulado_en IS NULL`. **`ALTER` no puede quitar el `UNIQUE` de columna de la 001: hay que reconstruir la tabla `comprador`**, igual que T20 ya hace con `patron`. Esto agranda T25 y D.1 — decidido así por completitud: sin ello, anular una venta inutiliza el cartón para siempre |

## E.2 Altos

| # | Hallazgo | Corrección |
|---|---|---|
| **E-A4** | `completa_provisional` intentaría `vendido → vendido`, que `puede_transicionar` rechaza | Ese camino hace **solo** `UPDATE comprador`, sin tocar el estado del cartón. Escrito explícito, o el implementador lo mete en el bucle común |
| **E-A5** | La regla estricta se sostiene en que **todos** los caminos a `vendido` creen fila. `vista_cartones.py` (fase 2) ya cambia estados a mano | Bloquear `→ vendido` desde ese camino o redirigirlo al servicio de compradores. **Prueba de invariante:** ningún cartón `vendido` sin fila `comprador` viva |
| **E-A6** | Si la fila entrante trae el nombre genérico (que ahora sale en el `Detalle`, D.3), la comparación normalizada la mete en `ya_registrado_igual` y `provisional` se queda en 1 para siempre | Orden de clasificación explícito: **si la fila existente tiene `provisional = 1`, la categoría es `completa_provisional` antes que cualquier otra**, salvo que la entrante sea también el texto genérico |
| **E-A12** | `banner_texto` ya existe en §7 con forma distinta (sin `pos`/`escala`), y `reloj` querrá `formato`. Modelarlos como dataclass uniforme obliga a migrar `tema_json` — el coste exacto que D.2 decía evitar | Fijar **ahora** los nombres de campo de los tres bloques contra `Documento_Tecnico.md §7` y `Fase_5/Contrato_Fase5.md:43`, en el mismo commit. `ConfigBloque` no es homogéneo: `banner_texto` es su propio tipo |

## E.3 Medios

- **E-M7** El nombre genérico se guarda ya traducido y queda congelado: un evento operado en
  español y reportado en inglés saca "Venta en puerta" en la hoja inglesa. **La fuente de verdad
  es la bandera `provisional`, nunca el texto de `comprador.nombre`** — el reporte pinta la
  etiqueta desde la bandera.
- **E-M8** `ADD COLUMN` **sí** admite `CHECK` en SQLite, y después ya no se puede añadir sin
  reconstruir: `provisional INTEGER NOT NULL DEFAULT 0 CHECK (provisional IN (0,1))`.
- **E-M9** La 003 tiene ya cuatro dueños (T20 reconstruye `patron`, T25 añade `anulado_en`, D.1
  añade `provisional`, E-C3 reconstruye `comprador`) y ningún texto consolidado. **Consolidar el
  archivo completo en un solo bloque del plan antes de escribir código**, o se pierde uno.
- **E-M10** `registrado_en` es `NOT NULL`: una sola marca de tiempo para todo el rango, no `now()`
  por fila. `contar_por_evento(con, evento_id, *, provisional=None)` — precedente:
  `repo_carton.listar_por_evento(estado=...)`.
- **E-M11** El filtro de D.3 está en el sitio equivocado: `filas_detalle` lo construye el
  servicio, así que **la casilla decide qué se consulta, no qué se escribe**. Si `impresion/`
  recibe siempre las seis columnas, un futuro llamador se salta la casilla. Además: la casilla
  **no se recuerda entre aperturas** (un `QSettings` la dejaría marcada y anularía la decisión),
  y el PDF **nunca** lleva datos de contacto.
- **E-M13** `Documento_Tecnico.md §7` línea 535 dice que *"el aplicador de tema (`ui/tema.py`)
  traduce este JSON a hojas de estilo de Qt"* — que es justo lo que DS21 prohíbe, y deja dos
  módulos llamados `tema.py` con propósitos opuestos. **Corregir §7 en el mismo commit** y nombrar
  al consumidor de la fase 5 `ui/transmision/tema_transmision.py`.

## E.4 Pruebas que exigen estas enmiendas

1. 003 sobre base **poblada** con filas `comprador` previas → todas con `provisional = 0`;
   `PRAGMA table_info(comprador)` con `notnull=1, dflt_value='0'`.
2. Rango que solapa cartones ya vendidos → no lanza, marca solo los libres, devuelve el desglose.
3. Rango que incluye `anulado` y `generado` → los omite; ninguno queda `vendido` sin comprador.
4. Rango aplicado dos veces (doble clic) → idempotente, el segundo pase marca 0.
5. **Invariante global tras cada servicio de escritura:** cartones `vendido` sin `comprador` vivo == 0.
6. Importación sobre cartón provisional → `completa_provisional`, `UPDATE` con `provisional = 0`,
   **estado del cartón intacto** y sin llamada a `actualizar_estado`.
7. Importación que repite el nombre genérico sobre una fila provisional → no cae en
   `ya_registrado_igual` dejando la bandera en 1.
8. Anular una venta provisional y revenderla por rango → no `unique` (E-C3).
9. Conciliación: 820 vendidos con 200 provisionales → `compradores_provisionales == 200` y **sin**
   advertencia; borrar a mano una fila `comprador` → advertencia sí.
10. `Detalle` con casilla desmarcada → exactamente 3 columnas, ni una cédula; marcada → 6.
    La casilla vuelve desmarcada al reabrir.
11. `dominio/tema.py`: roundtrip con `contador_bolas`/`reloj`/`banner_texto` ausentes → defaults;
    `banner_texto` con `texto` conserva el texto.

## E.5 Tareas añadidas

- [ ] **T28 (P1, humano ~3h / CC ~20min)** — persistencia — Reconstruir `comprador` en la 003
  - Surgido por: E-C3 — anular una venta inutiliza el cartón para siempre
  - Archivos: `003_fase4.sql`, `repo_comprador.py`, `tests/persistencia/test_migraciones.py`
  - Verificar: `pytest tests/persistencia -k "comprador or 003"`
- [ ] **T29 (P1, humano ~2h / CC ~15min)** — servicios — Venta por rango con filtro y desglose
  - Surgido por: E-C2, E-C1 — un cartón ya vendido tiraba el rango entero
  - Archivos: `servicio_compradores.py`, `servicio_conciliacion.py`
  - Verificar: `pytest tests/servicios -k rango`
- [ ] **T30 (P1, humano ~2h / CC ~15min)** — servicios — Categoría `completa_provisional`
  - Surgido por: E-A4, E-A6 — `vendido → vendido` reventaría, y la bandera se quedaba en 1
  - Archivos: `servicio_compradores.py`
  - Verificar: `pytest tests/servicios -k provisional`
- [ ] **T31 (P2, humano ~1h / CC ~10min)** — docs — Corregir §7 y renombrar el consumidor de fase 5
  - Surgido por: E-M13 — §7 dice lo que DS21 prohíbe; dos módulos llamados `tema.py`
  - Archivos: `docs/Documento_Tecnico.md`, `docs/Fase_5/Contrato_Fase5.md`
  - Verificar: lectura
- [ ] **T32 (P1, humano ~1h / CC ~10min)** — persistencia — Consolidar la 003 en un solo texto
  - Surgido por: E-M9 — cuatro dueños de la misma migración y ningún texto consolidado
  - Archivos: `docs/Fase_4/Plan_Implementacion_Fase4.md` §4.1
  - Verificar: revisión antes de escribir código

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | issues_open | 21 propuestas, 12 aceptadas, 5 diferidas; 6 critical gaps |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | binario no instalado |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | issues_open | 26 issues + 13 en la re-revisión del gate; 8 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | issues_open | score 4/10 → 8/10, 21 decisiones |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | skipped | sin alcance orientado a desarrolladores |

- **CROSS-MODEL:** no aplica. Codex no está instalado; las cuatro voces son subagentes Claude de
  contexto fresco — misma familia de modelo, no lectura externa. Su acuerdo pesa menos que un
  consenso entre modelos distintos. Para tener voz externa real: `npm install -g @openai/codex`.
- **DECISIONES DEL GATE (2026-09-09):** UC-1 rechazado (elegibilidad estricta se mantiene),
  UC-2 rechazado (el editor de tema se queda en la fase 4), UC-3 parcial (cédula como columna
  opcional, no exportada por defecto), UC-4 rechazado (una sola fase), D4 aceptado (la venta por
  rango crea comprador provisional). Detalle y consecuencias en el ANEXO D.
- **VERDICT:** CEO + DESIGN + ENG (x2) ejecutadas, User Challenges resueltos.
  **NO CLEARED para implementar todavía**: quedan 32 tareas por aplicar al código, de las cuales
  T20/T28/T32 (la migración 003) son bloqueantes — el archivo tiene cuatro dueños y ningún texto
  consolidado (E-M9). Y `TD-3` sigue sin decidir.

**UNRESOLVED DECISIONS:**
- TD-3 — Atomicidad contra `busy_timeout` (C.2 A1): (a) una transacción + inhibir todo otro
  escritor, (b) subir el timeout solo durante la importación, (c) trocear y aceptar escritura
  parcial. Es la única decisión con consecuencia en el criterio de aceptación de la fase.
- TD-1 — Orden del riel de secciones.
- TD-2 — Editar el código dentro de la tabla del informe y revalidar esa fila.
- TD-5 — Tres `.xlsx` reales de ~20 KB en el repositorio como fixtures.
- TD-6 — Modo escáner de QR para las ventas de puerta.
- TD-7 — Pegar desde el portapapeles como tercera vía de entrada.
