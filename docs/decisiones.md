# Registro de decisiones

Una entrada corta por decisión, añadida al cerrar cada fase. Sin este registro,
una fase futura mira una columna o un módulo y no sabe por qué existe así.

## Fase 1 — Cimientos

- **DU-1 — Tema del operador neutro, no de marca.** Decidido por Gabriel en la
  puerta final del plan de fase 1 (2026-09-04): la interfaz del operador usa un
  tema oscuro neutro fijo (`ui/tema.py::aplicar_tema_operador`). Los colores de
  la organización (`color_primario`, `color_secundario`, `color_texto`) no
  repintan botones ni fondos de la app; aparecen como identidad (logo, franja de
  4 px, muestras en la tarjeta) y son la **semilla** de la plantilla del cartón y
  del tema de transmisión de las fases 3 y 5, donde el valor que manda es el del
  evento, no el de la organización.
- **E1 — Desarrollo sobre Python 3.12, no el 3.14 instalado.** Es el piso que se
  promete (`requires-python = ">=3.12"`) y la versión con más kilometraje en la
  cadena PyInstaller + Inno Setup de la fase 5.
- **E2 — `synchronous=FULL` por defecto.** El contrato lo manda. El parámetro
  existe para que la fase 2 pruebe `NORMAL` en el trabajador de generación de
  cartones, no para cambiar el comportamiento por defecto.
- **E4a — Sin `UNIQUE` en `evento.nombre` por organización.** Una organización
  repite el nombre de su bingo anual con toda naturalidad. El duplicado
  accidental se avisa en el formulario (`existe_nombre`), no se bloquea en la
  base.
- **E4b — Dinero en centavos enteros** (`precio_tabla_centavos INTEGER`, no
  `REAL`). Alimenta un comprobante que se entrega a la organización; coma
  flotante ahí es un error que se descubre sumando mil cartones.
- **E4c — Columnas de texto legal en `organizacion`** (`eslogan`, `pie_pagina`,
  `condiciones`, `aviso_legal`): las exige el alcance y el esquema del documento
  técnico no las traía.
- **E4d — `evento.fecha` y `evento.hora` separadas.** La hora del evento es hora
  local del lugar; no tiene sentido convertirla a UTC ni fundirla con la fecha.
- **E4e — La migración `001_inicial.sql` es editable hasta el primer evento con
  datos reales.** A partir de ahí rige "nunca se edita una migración publicada"
  y todo cambio va en `002_*.sql`.
- **`ronda.estado` sin `CHECK`.** Su máquina de estados sigue abierta (ver §16
  del documento técnico); un `CHECK` en SQLite no se puede quitar sin
  reconstruir la tabla entera. Si se congela detrás de esa restricción antes de
  diseñarla, la fase 5 paga el costo. Los `CHECK` de `evento.estado`,
  `carton.estado` y `ronda.premio_tipo` sí se mantienen: sus conjuntos de
  valores están cerrados.
- **E13 — Instancia única con `QLockFile`**, no con `msvcrt`/`fcntl` a mano.
  Detecta bloqueos rancios (proceso muerto tras un cierre brusco) sin código por
  sistema operativo.
- **Medios en disco (`medios/<id>/`), no como BLOB.** `medios/` va a guardar
  también imágenes de premios y fondos de escena (megabytes) en las fases 4 y 5;
  meterlos en el `.db` infla lo que se respalda en caliente.
- **E14 — Navegación de dos niveles, eje evento.** Nivel global (Eventos,
  Organizaciones, Ajustes) y espacio de trabajo del evento, con un riel de
  secciones que las fases 2-5 amplían sin tocar la cáscara.
- **Corrección de implementación — el runner de migraciones vive en
  `persistencia/migraciones/__init__.py`, no en `persistencia/migraciones.py`.**
  El árbol de archivos del plan (§4) lista ambos como hermanos, pero un módulo
  y un paquete no pueden coexistir con el mismo nombre en el mismo directorio
  en Python: `persistencia.migraciones` tiene que ser un paquete (para que
  `importlib.resources.files()` encuentre los `.sql` que viven a su lado), así
  que el código del runner (`version_actual`, `aplicar_migraciones`, etc.) se
  escribió en su `__init__.py`. Mismas funciones, misma API pública, mismo
  import (`from bingo.persistencia.migraciones import aplicar_migraciones`).
- **G24 — Tipografía como combo cerrado.** `recursos/fuentes/` empaqueta dos
  familias de licencia abierta (OFL): Merriweather (con serifa) y Open Sans (sin
  serifa). Cargar una fuente propia de la organización queda para la fase 3.

## Fase 3 — Plantilla e impresión

Decisiones D1-D7 completas, con su razón, en
`docs/Fase_3/Plan_Implementacion_Fase3.md` §3. Resumen para quien no vaya a
leer el plan completo:

- **Migración `002_fase3.sql`, no editar `001_inicial.sql`.** A partir de esta
  fase hay una organización con evento real agendado — frontera natural para
  dejar de tocar la 001 ("editable hasta el primer evento con datos reales",
  `docs/convenciones-codigo.md`). Añade `evento.clave_evento`.
- **`recursos/` se movió a `src/bingo/recursos/`.** Vivía en la raíz del
  repositorio, fuera del árbol empaquetable por `pyproject.toml`
  (`[tool.setuptools.package-data]` solo declaraba `bingo.persistencia.migraciones`
  y `bingo.i18n`); las fuentes del combo cerrado (G24) habrían quedado fuera de
  un `.exe` de PyInstaller. Mismo patrón que `persistencia/migraciones/`:
  paquete real con `__init__.py`, resuelto vía `importlib.resources`.
- **`impresion/` es un paquete nuevo, no un submódulo de `dominio/`.** El
  contrato lo nombra así explícitamente; `render_pdf.py` importa ReportLab,
  que `dominio/` nunca importa. `dominio/firma.py` (HMAC del QR) sí vive en
  `dominio/`: es lógica pura que la fase 5 también necesita, sin arrastrar
  ReportLab a esa fase.
- **La vista previa de la plantilla usa el `Canvas` real vía `PySide6.QtPdf`,
  no un renderer aparte.** `MotorRenderCarton.dibujar_carton` es la única
  rutina de dibujo; la vista previa genera un PDF de una carta en memoria y lo
  rasteriza con `QPdfDocument` (ya viene con `PySide6>=6.7`, sin dependencia
  nueva) — literalmente la misma página que saldría impresa, como exige el
  contrato.
- **`marca.*` de la plantilla se siembra desde `Organizacion` al crear o
  restablecer, no se lee en vivo en cada render.** Evita que reimprimir un
  lote viejo cambie de logo silenciosamente porque la organización actualizó
  su marca para un evento distinto. Botón "Restablecer desde organización" en
  el editor para sincronizar a mano.
- **QR con `reportlab.graphics.barcode.qr`, sin el paquete `qrcode`.**
  Verificado en esta fase que ya lo trae la dependencia pineada. Medido
  también: es ~93% del tiempo de render por cartón (codificador Reed-Solomon
  puro Python) — 10.000 cartones tarda minutos, no segundos; no bloqueó el
  cierre de la fase porque el criterio de aceptación es "no se congela, con
  progreso y cancelación" (`Tarea`/`QThread`), no un tiempo límite. Ver
  `TODOS.md` si algún evento real lo nota.
- **`servicio_cartones.regenerar_lote`.** Resuelve la decisión D1 del gate de
  la fase 2: borra el lote y sus cartones y vuelve a llamar `generar_lote` con
  la misma semilla. Sin botón en la interfaz todavía (nadie lo llama desde la
  UI); la reimpresión normal es solo volver a llamar
  `servicio_impresion.generar_pdf_lote` sobre un lote que ya existe.

## Fase 4 — Compradores, rondas y premios

Decisiones D1-D11, ANEXOS A-E completos, con su razón, en
`docs/Fase_4/Plan_Implementacion_Fase4.md`. Resumen para quien no vaya a leer
el plan completo:

- **Migración `003_fase4.sql` reconstruye `patron` y `comprador` enteras.**
  SQLite no permite quitar un `NOT NULL` (`patron.mascara`) ni añadir un
  `UNIQUE` parcial con `ALTER TABLE`; era el único momento para hacerlo, con
  cero filas reales en cualquier base hasta esta fase. `ronda.premio_valor`
  (REAL, enmienda E4b incumplida desde la 001) sí queda como columna muerta:
  ahí solo hacía falta `ADD COLUMN`, no justificaba reconstruir la tabla.
- **`patron.mascaras`: lista JSON de enteros, no filas relacionadas.** Un
  patrón gana con cualquiera de sus máscaras (`dominio/patron.py::
  es_ganador`). Resuelve la decisión pendiente del documento técnico §16.1.
- **Elegibilidad estricta se mantiene (decisión de Gabriel, User Challenge
  UC-1 rechazado).** Solo un cartón `vendido` **con** fila `comprador` viva
  participa. Consecuencia: la venta por rango (`marcar_vendidos_por_rango`)
  crea un comprador **provisional** — sin datos de contacto — para que un
  cartón vendido en la puerta no quede vendido y sin poder ganar.
- **`TRANSICIONES_CARTON` gana `impreso → vendido` y `vendido → impreso`.**
  La organización vende talonarios que nunca pasan por "entregado"; anular
  una venta (`servicio_compradores.anular_venta`) devuelve el cartón a
  `comprador.estado_carton_previo`, no siempre a "entregado" a ciegas.
  `servicio_cartones.cambiar_estado_carton` bloquea `-> vendido` a propósito:
  la única vía es `servicio_compradores`, que crea el comprador en la misma
  transacción — invariante: ningún cartón `vendido` sin comprador vivo.
- **Anular una venta es borrado lógico (`comprador.anulado_en`), no
  `DELETE`.** El índice único de `carton_id` es parcial
  (`WHERE anulado_en IS NULL`) para que el cartón se pueda revender. El
  borrado físico real (`eliminar_todos_del_evento`) es el mecanismo de
  retención LOPDP — la *política* (qué plazo, quién la ejecuta) sigue sin
  decidir, ver `TODOS.md` P1.
- **TD-3 (decisión de Gabriel): la importación trocea la escritura en bloques
  de `TAMANO_BLOQUE_IMPORTACION` filas, no una sola transacción.** Renuncia a
  la atomicidad total de "todo o nada" a cambio de no sostener el lock de
  escritor de SQLite más allá de `BUSY_TIMEOUT_MS` con un archivo de miles de
  filas. Cada bloque es atómico; `ResultadoImportacion.detenida_en_fila`
  informa dónde se detuvo un fallo real.
- **Cédula como columna opcional, no exportada por defecto (User Challenge
  UC-3, parcial).** El reporte de conciliación en Excel solo lleva teléfono
  /cédula/correo con la casilla "incluir datos de contacto" marcada
  (desmarcada al reabrir); el PDF nunca los lleva.
- **El editor de tema del dashboard se queda en esta fase (User Challenge
  UC-2, rechazado).** Vista previa deliberadamente no-WYSIWYG: rectángulos
  etiquetados a escala de un lienzo 1920x1080, nunca el contenido en vivo. Los
  colores pintan la pantalla de transmisión de la fase 5, nunca el tema fijo
  del operador (`ui/tema.py`, decisión DU-1).
- **Orden del riel: Compradores sube al tercer puesto (decisión de gusto
  TD-1).** Plantilla no se toca nunca más una vez impresos los cartones;
  Compradores es la sección de la noche del evento.
