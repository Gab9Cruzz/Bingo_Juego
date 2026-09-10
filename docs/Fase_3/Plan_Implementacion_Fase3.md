# Plan de implementación — FASE 3: Plantilla e impresión

**Generado por:** Claude Code, sobre `docs/Fase_3/Contrato_Fase3.md`. Sesión iniciada con
`/gstack-autoplan`, cortada a petición del usuario antes de la interrogación y las revisiones
automáticas — este documento es lectura de código + contrato, no un dictamen CEO/Eng/Design.
**Fecha:** 2026-09-07 · **Rama:** `feature/fase-2-cartones` · **Commit base:** `3461b9b`
**Fuente de alcance:** `docs/Fase_3/Contrato_Fase3.md`, `docs/Plan_Fases_Bingo.md` (§FASE 3),
`docs/Documento_Tecnico.md` (§5), `docs/convenciones-codigo.md`, `TODOS.md`.
**No implementar nada a partir de este documento sin que Gabriel lo revise.** Este archivo es
el *plan*, no el código.

---

## 0. Contexto verificado (no asumido)

- `reportlab` instalado en `.venv`: **5.0.1** (el TODO "verificar la API de reportlab 5.x" queda
  parcialmente resuelto: la versión pineada por `pyproject.toml` [`>=4.2,<6`] sí instala 5.x;
  falta todavía el posicionamiento fino con una impresión real — ver §5 Riesgos).
- `reportlab.graphics.barcode.qr` importa y funciona sin dependencia adicional: el QR del §3.3
  del contrato **no necesita el paquete `qrcode`**.
- `PySide6.QtPdf.QPdfDocument` importa sin error en este entorno — es la pieza que resuelve el
  requisito "misma motor para PDF y vista previa" sin añadir una dependencia nueva (detalle en
  tarea 3.4).
- `recursos/fuentes/{Merriweather,OpenSans}` son **fuentes variables** (un solo `.ttf` con ejes
  de peso). `pdfmetrics.registerFont(TTFont(...))` las registra sin lanzar excepción, pero eso
  **no** confirma que ReportLab dibuje el peso Bold correctamente — un `TTFont` de ReportLab
  asume una fuente estática; con una variable font probablemente solo accede a la instancia por
  defecto (Regular). Sigue sin verificar visualmente — tarea explícita en 3.2.
- `evento.plantilla_json` y `repo_evento.actualizar_plantilla(con, evento_id, plantilla_json)`
  **ya existen**, escritos en la fase 1 sin consumidor hasta ahora (igual que
  `SECCIONES_ESPACIO_EVENTO["espacio_evento.seccion.plantilla"]`, con `fabrica=None` como
  placeholder). El editor de plantilla (tarea 3.4) no necesita repositorio nuevo para guardar.
- `TRANSICIONES_CARTON` ya incluye `generado → impreso` (fase 2, sin consumidor). No hace falta
  tocar `dominio/estados.py`.
- `repo_carton.actualizar_estado_por_lote(con, lote_id, estado)` ya existe, pero escribe
  `UPDATE carton SET estado = ? WHERE lote_id = ?` **sin filtrar por el estado actual**. Hasta
  ahora no importaba (nadie cambiaba el estado de un cartón todavía). Fase 3 es su primer
  llamador real ("al terminar, ofrecer marcar el lote como `impreso`") — usarla tal cual
  reescribiría a `impreso` un cartón que ya esté `vendido` o `anulado`. Hace falta un ajuste
  (ver tarea 3.5).

---

## 1. Alcance (verbatim del contrato, para trazabilidad)

Convertir cartones `generado` en un PDF listo para imprenta, personalizado con la marca de la
organización, en formatos de 1/2/4/6 cartones por hoja, con QR firmado, vista previa fiel al
PDF final, y generación por lotes en `QThread` sin agotar memoria. Ver
`docs/Fase_3/Contrato_Fase3.md` para el texto completo (tareas 3.1-3.6, criterios de
aceptación, riesgos).

---

## 2. Qué ya existe (leverage map)

| Sub-problema de la Fase 3 | Código ya existente que lo resuelve parcial o totalmente |
|---|---|
| Ejecutar el render de PDF sin congelar la UI | `ui/tarea.py::Tarea` — mismo convenio que fase 2, sin tocar la clase |
| Guardar el JSON de plantilla | `persistencia/repo_evento.py::actualizar_plantilla()` — ya valida el JSON y ya existe |
| Punto de entrada de la sección "Plantilla" | `ui/registro_vistas.py::SECCIONES_ESPACIO_EVENTO["espacio_evento.seccion.plantilla"]`, `fabrica=None` esperando esta fase |
| Marcar cartones como impresos | `estados.TRANSICIONES_CARTON["generado"] = {"impreso", "anulado"}` ya declarado; `repo_carton.actualizar_estado_por_lote` ya escribe en bloque (necesita el ajuste de §0) |
| Validación/normalización de logos | `utilidades/imagenes.py::validar_y_normalizar()` — el logo de organización ya llega como PNG saneado, se reutiliza tal cual en el render |
| Ubicación de archivos generados | `config/rutas.py` ya tiene el patrón (`dir_logs_evento`, `dir_medios_organizacion`); solo falta `dir_impresos_evento` |
| Canales de error / franja / modal | `ui/dialogos.py` sin cambios |
| Reproducir un lote perdido | `servicio_cartones.generar_lote(..., rng=Random(lote.semilla))` ya es reproducible; falta el envoltorio de conveniencia `regenerar_lote` que TODOS.md diferá explícitamente "hasta que la fase 3 tenga ese caso de uso real" — **ya lo tiene** (ver tarea 3.5) |
| QR | `reportlab.graphics.barcode.qr` (verificado §0) — cero dependencias nuevas |
| Reutilización de fuentes empaquetadas | `recursos/fuentes/` (decisión G24) — combo cerrado ya resuelto en fase 1, fase 3 solo las registra en ReportLab además de Qt |

**Conclusión de leverage:** como en la fase 2, el punto de entrada y el modelo de datos ya
están enganchados (`plantilla_json`, `actualizar_plantilla`, el placeholder de sección, los
estados de cartón). Todo el trabajo de la fase 3 es *añadir* un paquete nuevo (`impresion/`) y
una vista nueva, no reconstruir nada existente.

---

## 3. Decisiones de diseño tomadas en este plan

No hay gate de aprobación por decisión (el usuario pidió saltar `/autoplan`); quedan resueltas
aquí con su razón, para que Gabriel las revierta puntualmente si no está de acuerdo.

**D1 — Migración nueva (`002_fase3.sql`), no editar `001_inicial.sql`.**
La política de `docs/convenciones-codigo.md` dice que 001 es editable "hasta el primer evento
con datos reales". La fase 2 la editó porque todavía no había ningún evento real en juego. La
fase 3 es la que produce el primer PDF para una organización con evento ya agendado — es la
frontera natural para dejar de tocar 001. Costo de seguir la regla estricta: cero (una
migración más). Costo de saltarla: si el evento real ya corrió sobre un esquema con 001
editada una vez de más, "editable hasta el primer evento real" se vuelve ambiguo hacia atrás.

**D2 — `impresion/` es un paquete nuevo de nivel superior, tal como lo nombra el contrato.**
`impresion/plantilla.py` es Python puro (sin PySide6 ni sqlite3) pero no vive en `dominio/`:
el contrato lo coloca explícitamente fuera, como un paquete propio junto a `dominio/`,
`persistencia/`, `servicios/`, `ui/`, `utilidades/`. Se respeta la ruta que el propio autor del
proyecto escribió en el contrato.

**D3 — `dominio/firma.py` (no `impresion/`) para el HMAC del QR.**
El contrato no fija archivo para 3.3. `generar_clave_evento`, `firmar_codigo`, `verificar_qr`
son funciones puras (`hmac`, `hashlib`, `secrets` de la librería estándar) sin nada de
render — encajan en la regla de `dominio/` ("entidades con comportamiento propio van en su
propio módulo") y evitan que `impresion/` (que sí importa ReportLab) sea el único lugar de una
lógica que la fase 5 también necesitará para verificar QRs en vivo, sin arrastrar ReportLab a
esa fase.

**D4 — La vista previa reutiliza el `Canvas` real vía `PySide6.QtPdf`, no un renderer aparte.**
El contrato exige explícitamente "el mismo motor que produce el PDF... no una aproximación
dibujada con Qt". La única forma de cumplir eso literalmente sin añadir una dependencia nueva:
1. `MotorRenderCarton.dibujar_carton(canvas, ...)` (tarea 3.2) dibuja sobre un
   `reportlab.pdfgen.canvas.Canvas` real — el mismo objeto que usa el PDF de producción.
2. Para la vista previa, se genera un PDF de una sola página en memoria (`io.BytesIO`) con ese
   mismo motor.
3. Se carga con `PySide6.QtPdf.QPdfDocument` (confirmado disponible en §0, parte de
   `PySide6>=6.7` ya pineado — ninguna dependencia nueva) y se renderiza la página 0 a
   `QImage` → `QPixmap` para pintarla en un `QLabel`.
Alternativa descartada: dibujar con `reportlab.graphics.shapes.Drawing` + `renderPM.drawToPIL`
(sí rasteriza sin depender de Qt), pero exige una API de dibujo distinta a `Canvas`
(`Drawing.add(...)` en vez de `canvas.drawString(...)`), lo que de nuevo produciría dos rutas
de dibujo que pueden divergir — exactamente lo que el contrato prohíbe.

**D5 — `marca.*` de la plantilla se siembra desde `Organizacion` al crear/restablecer, no se
lee en vivo de la organización en cada render.**
El criterio de aceptación "cambiar el logo o los colores de la organización se refleja en el
siguiente PDF sin tocar código" se cumple con un botón "Restablecer desde organización" en el
editor (tarea 3.4) que vuelve a copiar `logo_path`, `logo_secundario`, `color_primario`,
`color_secundario`, `contacto`, `pie_pagina` de `Organizacion` a los campos correspondientes de
`plantilla_json`, en vez de que `render_pdf.py` resuelva esos campos en vivo desde la
organización en cada PDF. Razón: si un evento ya tiene lotes vendidos y la organización cambia
de logo para un evento *distinto*, un acoplamiento en vivo cambiaría silenciosamente el PDF de
reimpresión del primer evento. `titulo`/`subtitulo` **nunca** se siembran de la organización
(son del evento: "Bingo Solidario 2026" no es un dato de `Organizacion`).

**D6 — `servicio_cartones.regenerar_lote(con, lote_id)` entra en esta fase**, tal como
`TODOS.md` lo dejó escrito ("se implementa cuando la fase 3 tenga ese caso de uso real que la
ejercite de punta a punta"): el caso de uso real es "se perdió/corrompió el PDF de impresión,
hay que reproducir el lote exacto sin vender cartones distintos otra vez", y ese caso solo
existe a partir de esta fase. Implementación: `generar_lote` inyectando
`Random(lote.semilla)` en vez de `secrets.token_hex`; sin cambios a `generar_lote` en sí.

**D7 — Fuera de esta fase (quedan en `TODOS.md`, no bloquean los criterios de aceptación):**
- *Tipografía propia cargada por la organización* (decisión abierta de
  `Plan_Fases_Bingo.md`): esta fase resuelve el **combo cerrado** (Merriweather/Open Sans ya
  empaquetadas, registradas también en ReportLab) — cargar una fuente arbitraria subida por la
  organización sigue diferido, no lo pide ningún criterio de aceptación de la fase 3.
- *Textos de organización por idioma* (bilingüe): se revisa, no se implementa. La fase 3 no
  tiene un criterio de aceptación bilingüe.
- *Spike de latencia de transmisión real* (fase 5): el texto de "el ganador es el que canta el
  sistema, hay entre 7 y 30 segundos de retraso" (alcance §6.1, regla de negocio #1) va como
  **valor por defecto sugerido** en `textos.inferior` de la plantilla, editable — la *medición*
  en vivo de ese retraso sigue siendo un spike de la fase 5.

---

## 4. Plan de implementación (task breakdown)

### 4.1 Migración `002_fase3.sql`

```sql
-- Añade la clave HMAC del evento (§3.3 del contrato de la fase 3) y la fecha
-- en la que se marcó impreso un lote, para el resumen de la vista.
-- Política de edición: 001 deja de editarse a partir de aquí (decisión D1,
-- Plan_Implementacion_Fase3.md §3) — evento real agendado.

ALTER TABLE evento ADD COLUMN clave_evento TEXT;
```

`repo_evento.py`:
- Añadir `clave_evento` a `_COLUMNAS`, `_desde_fila`, `_a_parametros` (ya se actualiza sola vía
  `actualizar()` existente).
- Nuevo verbo `actualizar_clave(con, evento_id, clave_evento)` (mismo patrón que
  `actualizar_estado`).

`dominio/modelos.py::Evento`: añadir `clave_evento: str | None = None`.

### 4.2 `dominio/firma.py` (nuevo, decisión D3)

```python
"""Firma HMAC del código de cartón para el QR (contrato de la fase 3, §3.3).
Python puro: sin PySide6 ni sqlite3 (test_arquitectura.py lo cubre por vivir
en dominio/). Compartido con la fase 5 (verificación en vivo del reclamo).
"""
import hashlib, hmac, secrets

LONGITUD_HMAC = 8  # caracteres hex, 32 bits — suficiente para "no fabricable a
                    # mano", no para resistir criptoanálisis dedicado

def generar_clave_evento() -> str:
    return secrets.token_hex(32)  # 256 bits, guardada en evento.clave_evento

def firmar_codigo(clave_evento: str, codigo: str) -> str:
    firma = hmac.new(clave_evento.encode(), codigo.encode(), hashlib.sha256).hexdigest()
    return firma[:LONGITUD_HMAC]

def contenido_qr(clave_evento: str, codigo: str) -> str:
    return f"{codigo}|{firmar_codigo(clave_evento, codigo)}"

def verificar_qr(clave_evento: str, texto_qr: str) -> str | None:
    """Devuelve el código si la firma es válida, None si está alterado o mal formado."""
    if "|" not in texto_qr:
        return None
    codigo, firma = texto_qr.rsplit("|", 1)
    esperada = firmar_codigo(clave_evento, codigo)
    return codigo if hmac.compare_digest(firma, esperada) else None
```

`hmac.compare_digest` es obligatorio aquí (no `==`): comparación en tiempo constante, aunque el
riesgo de timing attack es bajo en este contexto, es la forma correcta de comparar HMACs y
cuesta lo mismo escribirla bien.

`servicios/servicio_eventos.py`: nueva función `asegurar_clave_evento(con, evento_id) -> str`
— si `evento.clave_evento` es `None`, genera y persiste una dentro de `transaccion()`; si ya
existe, la devuelve tal cual. La llama `servicio_impresion` antes de renderizar el primer PDF de
un evento (idempotente, sin caso especial para "ya existe").

### 4.3 `impresion/plantilla.py` (contrato §3.1, decisión D2)

Dataclasses `slots=True` reflejando el JSON de `Documento_Tecnico.md` §5.1:
`ConfigHoja`, `ConfigMarca`, `ConfigEncabezado`, `ConfigLibre`, `ConfigNumeros`,
`ConfigIdentificacion`, `ConfigTextos`, agregadas en `PlantillaCarton`.

- `PlantillaCarton.por_defecto(organizacion: Organizacion) -> PlantillaCarton`: valores
  sensatos del contrato (A4, vertical, 4 por hoja, márgenes 10mm, letras B-I-N-G-O, libre con
  texto "LIBRE", `Helvetica-Bold` 22pt para números — evita depender de las fuentes variables
  para el elemento más denso del cartón) con `marca.*` sembrado desde `organizacion` (D5).
- `PlantillaCarton.desde_json(texto: str) -> PlantillaCarton` / `.a_json() -> str`: usa
  `dataclasses.asdict` + `json.dumps`/`json.loads`. Claves ausentes en el JSON persistido caen
  al valor por defecto del campo (permite añadir campos nuevos sin migrar `plantilla_json`
  existente — es TEXT libre, no una tabla).
- Validación (`ErrorValidacion`, canal en línea del editor): `tamano ∈ {A4, Carta, A5}`,
  `orientacion ∈ {vertical, horizontal}`, `cartones_por_hoja ∈ {1, 2, 4, 6}`, colores
  `#RRGGBB` válidos, opacidades en `[0, 1]`, `margen_mm > 0`.
- `restablecer_marca_desde_organizacion(plantilla, organizacion) -> PlantillaCarton`: el botón
  de D5, función pura que devuelve una copia con `marca.*` reemplazado.

Constantes nuevas en `config/ajustes.py`:
```python
# impresion/plantilla.py, impresion/render_pdf.py
TAMANOS_HOJA_SOPORTADOS = ("A4", "Carta", "A5")
CARTONES_POR_HOJA_SOPORTADOS = (1, 2, 4, 6)
LONGITUD_HMAC_QR = 8  # coincide con dominio/firma.py::LONGITUD_HMAC
HOJAS_POR_ARCHIVO_DEFECTO = 500
```

### 4.4 `impresion/render_pdf.py` (contrato §3.2)

Clase `MotorRenderCarton` (no funciones sueltas): construida una vez por lote de impresión con
`(plantilla: PlantillaCarton, organizacion: Organizacion, clave_evento: str)`, precarga y
cachea las imágenes (`ImageReader`) en `__init__` — logo principal, logo secundario, fondo,
marca de agua — una sola vez por objeto, reutilizadas en `drawImage` a lo largo de todas las
páginas y de todas las particiones (requisito explícito §3.2.4 del contrato).

```python
class MotorRenderCarton:
    def __init__(self, plantilla: PlantillaCarton, organizacion: Organizacion, clave_evento: str): ...
    def calcular_disposicion(self) -> list[tuple[float, float, float, float]]:
        """Posiciones (x, y, ancho, alto) en la hoja según cartones_por_hoja,
        tamaño, orientación y márgenes. 1/2/4/6 son los únicos casos: no hace
        falta un algoritmo de bin-packing genérico, una tabla de disposición
        fija por valor de cartones_por_hoja basta y es más fácil de verificar
        a mano contra una hoja impresa (nota de riesgo del propio contrato)."""
    def dibujar_carton(self, canvas: Canvas, carton: Carton, x: float, y: float,
                        ancho: float, alto: float) -> None:
        """La unidad básica que pide el contrato. Dibuja logo(s), título,
        subtítulo, encabezado B-I-N-G-O, cuadrícula con números, libre,
        código, QR (dominio.firma.contenido_qr + reportlab.graphics.barcode.qr),
        marca de agua, textos superior/inferior, contacto — todo controlado
        por self._plantilla."""
    def dibujar_marcas_corte(self, canvas: Canvas, posiciones: list[...]) -> None:
        """Solo si cartones_por_hoja > 1 (contrato)."""
    def renderizar_pagina(self, canvas: Canvas, cartones_de_la_hoja: list[Carton]) -> None:
        """Coloca hasta N cartones (calcular_disposicion) + marcas de corte, y
        hace canvas.showPage(). Una llamada = una hoja física."""
```

Registro de fuentes (verificación pendiente de D0/riesgo variable-font): al construir el motor,
`pdfmetrics.registerFont(TTFont("Merriweather", ruta))` / `"OpenSans"`; si la plantilla pide una
de las dos y el registro falla o el resultado visual no es aceptable (ver §5), cae a
`Helvetica`/`Helvetica-Bold` con aviso, nunca una excepción que rompa el lote completo.

### 4.5 Vista previa — `ui/vistas/vista_plantilla.py` (contrato §3.4, decisión D4)

Registrada en `registro_vistas.py` reemplazando `fabrica=None` de
`"espacio_evento.seccion.plantilla"`.

- Formulario agrupado en `QGroupBox` por sección (marca, textos, identificación, estructura,
  hoja) dentro de un `QScrollArea` — el formulario es largo, no cabe cómodo sin scroll; no hace
  falta ningún framework nuevo, son controles Qt nativos (`QLineEdit`, `QComboBox`, `QSpinBox`,
  `QCheckBox`, selector de archivo para logos que reutiliza
  `utilidades/imagenes.validar_y_normalizar` + `config/rutas.dir_medios_organizacion`, igual
  que el formulario de organización de la fase 1).
- Guardado: cada cambio de campo actualiza un `PlantillaCarton` en memoria y llama
  `repo_evento.actualizar_plantilla(con, evento.id, plantilla.a_json())` (ya existe, sin
  transacción explícita — es un autocommit de una sola sentencia, igual que hace ya
  `vista_organizaciones.py` para campos sueltos).
- Vista previa (`QLabel` con `QPixmap`, panel derecho, igual esquema maestro-detalle que
  `VistaCartones`): al cambiar cualquier campo, arranca/reinicia un `QTimer` de un solo disparo
  (~500ms) que, al vencer, construye un `Carton` de ejemplo con
  `dominio/carton.generar_carton(Random("vista-previa"))` (semilla fija: la vista previa no
  necesita variar entre refrescos), corre `MotorRenderCarton` sobre un `Canvas` de una sola
  página escrito a `io.BytesIO`, y carga ese buffer con `QPdfDocument` → `QImage` → `QPixmap`
  (decisión D4). Ningún I/O a disco para la vista previa.
- Si `Organizacion` no tiene logo todavía, la plantilla por defecto (4.3) ya contempla
  `logo=None` sin romper el render (recuadro vacío o se omite el bloque, según
  `dibujar_carton`).

### 4.6 `servicios/servicio_impresion.py` (contrato §3.5)

```python
def generar_pdf_lote(
    con: sqlite3.Connection,
    evento_id: int,
    lote_id: int,
    carpeta_destino: Path,
    *,
    hojas_por_archivo: int = HOJAS_POR_ARCHIVO_DEFECTO,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
) -> list[Path]:
    """Genera el/los PDF de un lote. Un archivo nuevo cada `hojas_por_archivo`
    hojas — eso es lo que acota la memoria del Canvas en curso, no una API de
    streaming de ReportLab (Canvas retiene el documento abierto hasta save());
    ver nota de riesgo en §5. Nombres: '<prefijo_lote>_parte_01.pdf', etc."""
```

Flujo: `servicio_eventos.asegurar_clave_evento` → construir `MotorRenderCarton` una sola vez →
paginar `repo_carton.listar_por_evento(con, evento_id, estado=None, ...)` filtrado al `lote_id`
(nueva query `repo_carton.listar_por_lote` si no existe ya — **verificar antes de escribirla**,
podría bastar con filtrar en memoria dado que un lote cabe en RAM, igual que hace
`VistaCartones`) → agrupar de `cartones_por_hoja` en `cartones_por_hoja` → `renderizar_pagina`
por hoja → nuevo `Canvas`/archivo cada `hojas_por_archivo` hojas.

Cancelación: mismo convenio que `generar_lote` — comprobar `debe_cancelar()` cada N hojas;
al cancelar, cerrar el `Canvas` en curso igualmente (un PDF parcial válido no es un problema:
es una impresión más corta, no un archivo corrupto) y no seguir con el resto.

**Ajuste correctivo en `repo_carton.actualizar_estado_por_lote`** (hallazgo de §0): añadir
`AND estado = 'generado'` al `WHERE` — o, más explícito, una función nueva
`actualizar_estado_por_lote_desde(con, lote_id, estado_actual, estado_nuevo)` genérica que la
firma vieja delegue. Se prueba con un cartón `anulado` a mano en el lote y se confirma que
sobrevive la llamada de "marcar lote impreso".

`servicio_cartones.regenerar_lote(con, lote_id) -> Lote` (decisión D6):
```python
def regenerar_lote(con: sqlite3.Connection, lote_id: int, *, al_progresar=None, debe_cancelar=None) -> Lote:
    """Reproduce un lote perdido/corrupto con la misma semilla. Precondición:
    el lote original debe eliminarse primero (mismo prefijo, unicidad de
    evento_id+prefijo) — decisión de UX para la vista: botón 'Reimprimir'
    junto a un lote ya 'impreso' que ofrece regenerar solo el PDF sin tocar
    la base (ruta feliz) o, si de verdad se perdieron también las filas de
    `carton`, borrar+regenerar con la semilla guardada (ruta de recuperación).
    Este servicio cubre la segunda; la primera es simplemente volver a llamar
    a generar_pdf_lote sobre el lote_id existente."""
```

### 4.7 Pruebas (contrato §3.6)

Nueva dependencia **de desarrollo únicamente** (no se empaqueta en la app): `pypdf>=5,<6`
en `[project.optional-dependencies].dev` — necesaria para que la prueba de "el archivo abre"
sea real (contar páginas, leer metadata) en vez de solo comprobar la cabecera `%PDF-`.

- `tests/impresion/test_plantilla.py`: `por_defecto`, roundtrip `a_json`/`desde_json`,
  validación de cada campo fuera de rango, `restablecer_marca_desde_organizacion`.
- `tests/impresion/test_render_pdf.py`: `calcular_disposicion` para 1/2/4/6 (posiciones no se
  solapan, caben dentro del margen), marcas de corte solo si `cartones_por_hoja > 1`,
  `dibujar_carton` no lanza con una plantilla mínima (sin logos) ni con una completa.
- `tests/dominio/test_firma.py`: `verificar_qr` acepta lo que `contenido_qr` generó, rechaza un
  código alterado, un HMAC alterado, y texto sin `|`.
- `tests/servicios/test_servicio_impresion.py`:
  - marcado `lento`: lote de ~2.000 cartones, `hojas_por_archivo` pequeño (p. ej. 50) para
    forzar varias particiones en la prueba sin esperar minutos; cada archivo abre con `pypdf`
    (`len(reader.pages) > 0`), y las páginas totales entre archivos suman lo esperado según
    `cartones_por_hoja`.
  - crecimiento lineal: generar N y 4N cartones (ambos con el mismo logo, mismo caché de
    imagen), comprobar que el tamaño de archivo de 4N es ≈4× el de N con margen, no un salto
    cuadrático — esto es lo que confirma que el caché de `ImageReader` funciona.
  - cancelación a mitad: el/los PDF generados hasta el punto de cancelación abren igual.
  - `regenerar_lote` produce exactamente los mismos `numeros`/`firma` que el lote original
    (mismo `random.Random(semilla)`).
  - `actualizar_estado_por_lote` corregido no reescribe un cartón `anulado`.
- `tests/ui/test_vista_plantilla.py`: guardar un campo llama `actualizar_plantilla` con el JSON
  esperado; cambiar un campo reinicia el `QTimer` de la vista previa (usar `QTest.qWait` o
  monkeypatch del temporizador, patrón ya usado en `tests/ui/conftest.py`).

---

## 5. Riesgos y notas (del propio contrato, más lo encontrado en esta lectura)

- **Imprime pronto, de verdad, en papel** (nota explícita del contrato): no cerrar la fase sin
  al menos una hoja de cada formato (1/2/4/6) impresa y revisada a tamaño real. Esto conecta
  con el spike de imprenta ya anotado en `TODOS.md` ("cotización y prueba de impresión... si
  rechazan el PDF por sangrado, resolución o CMYK, hay que saberlo antes de escribir el motor
  de render de la fase 3, no después") — **correrlo antes de invertir tiempo en el `dibujar_carton`
  completo**, con un cartón de una sola página hecho a mano, no con el motor todavía sin
  terminar.
- **Fuentes variables + ReportLab**: `pdfmetrics.registerFont` no lanzó error al registrar
  `OpenSans-Variable.ttf` (§0), pero eso no prueba que el peso Bold salga correcto en el PDF.
  Primera tarea real de 4.4: render de una palabra en negrita con cada fuente empaquetada,
  comparación visual. Si el resultado es malo, el plan ya tiene salida (Helvetica/Helvetica-Bold
  por defecto para números, D5 no depende de las variables para nada estructural).
- **`Canvas` de ReportLab no libera memoria página a página dentro de un mismo archivo** — el
  requisito "20MB no 800MB" del contrato lo logran dos mecanismos combinados, no uno: (a) el
  particionado (`hojas_por_archivo`, cierra y reabre `Canvas` cada N hojas, acotando cuánto
  retiene en memoria un único documento abierto) y (b) el caché de `ImageReader` (evita
  recodificar el mismo logo miles de veces). Vale la pena medir memoria real con
  `tracemalloc`/`psutil` durante la prueba `lento`, no solo inferirlo.
- **10.000 cartones es el criterio de aceptación, no un techo de diseño arbitrario** — Gabriel
  confirmó en esta sesión que ya hay una organización con evento agendado y volumen estimado;
  vale la pena, antes de cerrar la fase, correr la prueba de rendimiento con el volumen real
  esperado de ese evento además de con 10.000.
- **`repo_carton.actualizar_estado_por_lote` sin filtro de estado actual** (§0): corregido en
  4.6, pero si algún código futuro (fase 4/5) vuelve a llamarla asumiendo "todos los cartones
  del lote pasan al estado X sin importar en cuál estaban", el bug reaparece. Vale un
  comentario explícito en el repo, no solo el `WHERE`.

---

## 6. Mapeo a criterios de aceptación del contrato

| Criterio | Cubierto por |
|---|---|
| PDF de 10.000 cartones sin congelar, progreso visible, cancelable | `Tarea` + `servicio_impresion.generar_pdf_lote` (4.6) |
| Archivo pesa lo razonable, abre en lector estándar | Caché de `ImageReader` + particionado (4.4/4.6), prueba con `pypdf` (4.7) |
| Legible a tamaño real, cortes cuadran | `calcular_disposicion` + `dibujar_marcas_corte` (4.4) + prueba impresa real (§5) |
| Cambiar logo/colores de organización se refleja sin tocar código | Botón "restablecer desde organización" (D5, 4.5) |
| Vista previa coincide con el PDF final | Mismo `MotorRenderCarton`/`Canvas`, `QPdfDocument` para mostrarlo (D4, 4.5) |

---

## 7. Entregable

Etiqueta `v0.3.0` (contrato). Al cerrar: PDF de cartones personalizado, probado en papel en los
4 formatos, con QR verificable y lote marcable como `impreso`.

---

## 8. Notas de la implementación real (post-hoc)

Este plan se implementó completo el mismo día. Diferencias con lo escrito arriba, para que
quien lea el plan después no se confunda con el código:

- **`recursos/` se movió a `src/bingo/recursos/`.** No estaba en el plan original: vivía en la
  raíz del repositorio, fuera de `[tool.setuptools.package-data]`, así que las fuentes del
  combo cerrado (G24) no habrían viajado en un `.exe` de PyInstaller. Se corrigió como parte de
  4.4 (registro de fuentes en ReportLab), con `__init__.py` en `recursos/` y `recursos/fuentes/`
  (mismo patrón que `persistencia/migraciones/`).
- **Bug real encontrado y corregido durante 4.4:** la primera versión de `_dibujar_textos_pie`
  contaba `textos.superior` para reservar espacio pero nunca lo dibujaba en ningún lado — se
  perdía sin avisar. Corregido: `textos.superior` lo dibuja `_dibujar_marca` (arriba del
  cartón, junto al logo/título); `_dibujar_textos_pie` quedó solo para `inferior`/`contacto`
  (abajo). Cubierto por `tests/impresion/test_render_pdf.py::test_dibujar_carton_no_lanza_con_plantilla_completa`.
- **`repo_carton.listar_por_lote` y `repo_carton.contar_por_lote`** (nuevos, no estaban en el
  plan): `generar_pdf_lote` necesita los cartones de un lote específico, no de todo el evento;
  no existía ese filtro en `repo_carton.py`.
- **Interfaz de impresión añadida a `ui/vistas/vista_cartones.py`, no a un archivo nuevo.** El
  plan (§4.6) dejó la superficie de UI implícita en el servicio. Se añadió un botón "Imprimir"
  junto a "Generar lote" (mismo panel de progreso/cancelación, generalizado para servir a las
  dos tareas) y un modal `FormularioImprimir` (elegir lote completo + carpeta destino). Al
  terminar, ofrece marcar el lote como `impreso` (`confirmar()`), tal como pide el contrato
  §3.5.6.
- **Medido, no solo estimado: el QR es ~93% del tiempo de render por cartón.** 10.000 cartones
  tarda ~6-7 minutos, no segundos — documentado en `TODOS.md` como posible optimización futura,
  no bloqueó el cierre porque el criterio de aceptación es "no se congela, con progreso y
  cancelación", no un tiempo límite.
- **Pendiente real, no resuelto en esta sesión:** la prueba impresa en papel de los 4 formatos
  que el propio contrato pide antes de cerrar la fase (sección "Riesgos y notas") — es un paso
  manual de Gabriel, no algo que el código pueda verificar. Tampoco se verificó visualmente el
  peso Bold de las fuentes variables empaquetadas (`TODOS.md`).
