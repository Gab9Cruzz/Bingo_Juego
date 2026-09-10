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

## Fase 5 — Sorteo en vivo y cierre

- **`ronda.premio_valor` (REAL, 001) queda muerta como estado permanente
  aceptado, no como deuda (decisión D3, corrección del hallazgo M3).** E4b ya
  se cumple desde la 003 con `premio_valor_centavos`; reconstruir `ronda`
  entera solo para borrar una columna que nadie lee es riesgo puro a cambio
  de estética, sobre una tabla que ya puede tener filas reales de un evento.
  La próxima vez que `ronda` se reconstruya por una razón de verdad, se
  elimina de paso.
- **El índice único de `ganador(ronda_id, carton_id)` es total, no parcial
  (corrección del hallazgo V1, crítico).** Un cartón solo puede ganar una
  ronda una vez, anulado o no: la anulación es un hecho sobre esa misma fila,
  no una invitación a que la reanudación cree otra viva.
- **`preferencias.ventana.monitor_transmision` se guarda por
  `QScreen.name()`, no por índice (hallazgo V7).** Windows reordena los
  monitores entre arranques. Un `preferencias.json` de antes de la fase 5 con
  un entero se descarta al leer, no revienta.
- **`TRANSICIONES_RONDA` incluye `cerrada -> en_curso` (hallazgo V5).** Cerrar
  una ronda por error en directo tiene que tener deshacer, y el alcance §6.6
  promete retomar un bingo otro día desde la ronda pendiente. La reapertura
  exige confirmación escrita y va a auditoría; si la ronda ya tenía acta
  generada, invalida el hash (tarea 4.11).
- **Las cuatro columnas nuevas de `ronda` (fase 5) nunca se escriben con
  `repo_ronda.actualizar()` (hallazgo A1, crítico).** Ese verbo reescribe
  *todas* las columnas de `_COLUMNAS` desde el objeto en memoria; una `Ronda`
  cargada al abrir una vista de preparación borraría en silencio el
  `acta_hash` que otra pantalla acaba de escribir. Se usan verbos puntuales:
  `actualizar_inicio`, `actualizar_cierre`, `actualizar_acta`.
- **`Bombo.siguiente()`/`confirmar()` en dos pasos, nunca un `extraer()`
  mutante (hallazgo B1, crítico).** `confirmar()` solo se llama después del
  commit de la transacción de la bola: si esa transacción falla, el número
  sigue disponible, no desaparece del juego en silencio.
- **`repo_ganador.crear()` es el verbo normal, sin `INSERT OR IGNORE`
  (hallazgo C3, corrige lo que decía la tarea 4.4 original).** Con la
  reanudación en solo lectura (D13) nadie reinserta un ganador ya
  persistido; si el índice único salta, es un bug y debe llegar como
  `ErrorIntegridad`, no tragárselo.
- **Detección de ganador vs. registro (decisión D8, hallazgo C1, crítico):**
  el motor solo persiste y notifica las detecciones de la primera
  `extraccion.orden` que produjo un ganador. Con `sin_reclamo="continuar"`
  la ronda sigue extrayendo bolas, pero ningún cartón que complete el
  patrón en una bola posterior se registra ni dispara `ganadores_detectados`
  otra vez — evita cientos de filas y que la cuenta de reclamo se reinicie
  en bucle delante del público.
- **Reanudación (D13): solo lectura, nunca reinserta.** La reproducción
  reconstruye `marcado` y el bombo desde `extraccion`; la verificación
  compara el conjunto detectado por bits (excluyendo lo que el operador ya
  anuló o rechazó) contra lo persistido vigente. Solo una incoherencia real
  dispara `ErrorReanudacion` (modal terminal); hay una vía explícita
  ("reanudar de todos modos", `forzar=True`) que registra
  `sorteo.reanudacion_incoherente` en auditoría en vez de bloquear el
  evento en vivo.
- **Reclamo por código o por QR firmado, nunca degradando uno al otro
  (hallazgo S1, alto).** Si el texto contiene `|` se trata como QR: una
  firma inválida es rechazo duro (`ganador.error.qr_invalido`), nunca cae a
  tratar la parte anterior al `|` como código tecleado — eso dejaría pasar
  `"A-0142|00000000"` sin que el HMAC validara nada. El QR (`LONGITUD_HMAC`
  de 32 bits) es un antifaltas de tipeo, no una prueba de posesión.
- **El panel de ganadores detectados nunca confirma nada por su cuenta.**
  `ganadores_detectados` solo pinta la lista; la confirmación (`unico` /
  `reparto` / `rechazado`) ocurre al registrar un reclamo desde el
  buscador de código o al resolver un empate desde el diálogo — nunca en el
  instante de la detección, porque el contrato exige un hueco real de
  reclamo (estado `HAY_CARTON_GANADOR` de la fase 5, tarea 4.9) antes de
  revelar quién ganó.
- **`EspacioEvento` es el dueño de `MotorSorteo` (hallazgo S5-3).** Vive ahí,
  no en `VistaSorteo`: cambiar de sección del riel a mitad de ronda no
  destruye la partida. Las secciones reciben `(con, evento, espacio)` desde
  la fase 5 (antes `(con, evento)`); las que no son Sorteo ignoran el
  tercer argumento.
- **DU-11: los dos botones que cierran `EspacioEvento` exigen confirmación
  explícita con una ronda `en_curso` o `pausada`.** Antes se conectaban
  directo a la señal `cerrado`, sin aviso — con una partida en vivo,
  cerrar la pantalla no debería sentirse como un clic reversible por
  accidente aunque los datos ya estén a salvo en la base.
- **`i18n.t_en(idioma, clave, **parametros)` (decisión DU-13).** `t()`
  siempre resuelve contra el idioma activo de la interfaz; la transmisión
  necesita su propio idioma (`tema_json.idioma_publico`), independiente de
  con qué idioma esté probando algo el operador. Se añadió sin tocar `t()`.
- **La máquina de nueve estados de la transmisión (decisión DU-3) es una
  clase Python pura** (`ui/transmision/estado_transmision.py`), sin Qt: la
  conduce `VentanaTransmision` desde las señales de `PuenteSorteo`, pero se
  prueba entera sin `QApplication`. Ni una bola nueva ni un cambio de "a
  una bola" interrumpen `HAY_CARTON_GANADOR`/`GANADOR_CONFIRMADO` — la
  ronda sigue extrayendo (`sin_reclamo="continuar"`) sin que la pantalla
  vuelva a EN_JUEGO por su cuenta.
- **La regla de "nunca código ni nombre antes de `ganador_confirmado`" se
  prueba sobre el texto y sobre el código fuente del pintor, no sobre
  píxeles** (`ui/transmision/contenido.py` + `test_bloques.py`): más
  robusto que comparar imágenes, y detecta el error incluso si alguien
  cambia el tamaño de fuente o el layout.
- **`elegir_pantalla()` (hallazgo E-9) es una función pura** sobre una
  lista de nombres, sin Qt — cubre los cuatro casos de DU-17 (una sola
  pantalla, monitor guardado presente/ausente, ninguno guardado) sin un
  monitor real, algo que `QT_QPA_PLATFORM=offscreen` no permitiría probar
  de otro modo.
- **La ventana de transmisión ignora las señales del puente tras cerrarse
  mediante una bandera (`_cerrada`), no `disconnect()`.** PySide6 no
  reconoce de forma fiable el mismo método ligado entre el `connect()`
  original y un `disconnect()` posterior sobre señales `Signal(object)` /
  `Signal(list)` — falla en silencio (un aviso, no una excepción) y deja la
  ventana escuchando igual. La bandera es robusta independientemente de esa
  limitación.
- **`ui/sonido.py` es un solo módulo (hallazgo S5-2), no un paquete.**
  `Efectos`, `Musica` y la locución comparten ciclo de vida. Ninguna
  instancia su objeto de Qt (`QSoundEffect`/`QMediaPlayer`/`QTextToSpeech`)
  cuando está desactivada — evita el aviso de consola de instanciar audio
  en un equipo sin tarjeta de sonido, y lo hace comprobable sin hardware
  real.
- **Locución: TTS del sistema por defecto, con carpeta pregrabada que lo
  sustituye si está completa (decisión D5).** El locale se fija *antes* de
  pedir voces (`availableVoices()` solo devuelve las del locale activo).
  Sin motor o sin voces para el idioma elegido, se desactiva sola sin
  lanzar.
- **Corrección real encontrada al implementar 4.11 (actas): `VistaSorteo`
  no tenía ninguna forma de moverse a la ronda 2 tras cerrar la 1, ni de
  reabrir una cerrada.** Solo mostraba "la ronda en juego, o si no la
  primera pendiente" — cerrar la única ronda visible dejaba la vista sin
  salida. Se añadió `_selector_ronda` (todas las rondas del evento) y
  `servicio_rondas.reabrir_ronda` (hallazgo V5/E-16): cerrar avanza sola a
  la siguiente pendiente, y una ronda cerrada se puede volver a abrir desde
  el selector, invalidando el acta si ya se había generado.
- **El hash del acta se calcula sobre una carga canónica, nunca sobre los
  bytes del PDF (decisión D7).** `dominio/acta.py::carga_canonica` ordena
  los ganadores por código antes de serializar — leerlos de la base en
  otro orden no puede cambiar el hash. Empieza por `"acta/v1"` (hallazgo
  E-5): el verificador (`servicio_actas.verificar_acta`) queda listo para
  una v2 futura sin invalidar las actas ya emitidas.
- **El nombre de archivo del acta va por `ronda_id`, no por `orden`
  (hallazgo C6).** `orden` es mutable (`servicio_rondas.reordenar`); nombrar
  por él haría que reordenar rondas sobrescribiera el acta de una con la de
  otra.
- **El reporte del evento (fase 5) extiende el de conciliación (fase 4) en
  vez de duplicar la infraestructura de Excel/PDF.**
  `servicio_conciliacion.generar_reporte_evento_excel/pdf` reutiliza
  `_resumen`/`_filas_detalle` y solo añade `_filas_rondas` (ganadores no
  anulados, agrupados por ronda); `impresion/reporte.py` gana
  `reporte_evento_excel/pdf` con una hoja/sección "Rondas" más, mismo
  `_escribir_seguro`.
