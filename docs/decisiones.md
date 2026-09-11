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
- **Bug real encontrado al escribir `servicio_respaldos.restaurar()`: el
  `.zip` vive por defecto en `dir_respaldos()`, que es una subcarpeta de
  `raiz_datos()`.** Mover `raiz_datos()` entera a `*.pre-restauracion-*`
  antes de leer el `.zip` se llevaría el propio `.zip` con ella. Se copia
  siempre a un archivo temporal fuera de `raiz_datos()` antes de mover
  nada — sin esto, restaurar habría fallado siempre que el operador usara
  la ubicación por defecto (el caso normal).
- **`exportar()` no recibe `con` (hallazgo B2, crítico): es la única función
  de la fase que rompe "`con` va siempre primero"**, documentado como
  excepción explícita porque corre en otro hilo (`Tarea`) y
  `check_same_thread=True` no permite compartir la conexión entre hilos.
- **`restaurar()` valida el `.zip` entero (zip-slip incluido, hallazgo E-2;
  versión de esquema, hallazgo B4) antes de mover un solo archivo real.**
  `Path.is_relative_to()` sobre la ruta ya resuelta rechaza rutas absolutas,
  `..` y letras de unidad sin necesitar lógica de comparación de cadenas.
- **`--restaurar` corre antes de `QLockFile`, del log y de `abrir_conexion`
  (hallazgo E-11), con un sondeo de bloqueo previo:** si otra instancia
  sigue corriendo sobre los datos que se van a reemplazar, se niega a
  continuar en vez de mover una base que otro proceso tiene abierta.
- **Copia previa a aplicar cualquier migración pendiente (tarea 4.22,
  corrección S5-14, hallazgo B5, crítico).** `aplicar_migraciones` corre
  `PRAGMA wal_checkpoint(TRUNCATE)` y copia `bingo.db` a
  `bingo.db.pre-<version_actual>` antes de tocar el esquema — si la
  migración nueva falla en el equipo del operador la noche del evento, la
  base ya migró a medias y el instalador anterior no la entiende. El
  checkpoint no es opcional: en WAL los datos confirmados pueden vivir
  solo en `bingo.db-wal`, y copiar solo `bingo.db` daría una foto vacía o
  rancia. Una sola copia por versión (si `.pre-N` ya existe, no se pisa) y
  sin efecto sobre `:memory:` u otra base sin archivo real en
  `PRAGMA database_list` — ahí no hay nada que copiar, y eso no es un
  error.
- **Bloqueo de venta con ronda en curso, cinco funciones no tres (tarea
  4.23, corrección S5-4, hallazgo C5).** `servicio_compradores.
  registrar_manual/aplicar_importacion/marcar_vendidos_por_rango/
  anular_venta` y `servicio_cartones.cambiar_estado_carton` rechazan con
  `ErrorValidacion` si el evento tiene una ronda `en_curso`. Sin esto, un
  cartón vendido o anulado a mitad de ronda queda desincronizado del
  índice inverso en memoria del motor (`EstadoPartida`, construido una
  sola vez al iniciar la ronda): pagó y no puede ganar, **en silencio** —
  el peor fallo posible del producto.
- **El bloqueo es solo con `en_curso`, nunca con `pausada` (hallazgo C4).**
  Bloquear también con `pausada` crea un escenario peor que el que arregla:
  se vende en la puerta, no da tiempo a registrar, se inicia la ronda, y ya
  no se puede registrar a nadie hasta cerrarla. Con la ronda `pausada` sí
  se registra, y al reanudar el motor reconstruye el índice inverso sobre
  los cartones vendidos en ese momento (D13 ya hace exactamente eso). El
  helper `servicio_rondas.hay_ronda_en_curso` centraliza el criterio para
  las cinco llamadas.
- **`iniciar_ronda` con cero cartones elegibles siempre lanza
  `ErrorValidacion` (hallazgo C4).** `validar_evento_listo` marca "sin
  vendidos" como aviso no bloqueante a propósito (se vende en la puerta),
  pero arrancar un sorteo donde nadie puede ganar no es un caso de uso.
- **Cierre del evento (tarea 4.13) y respaldo manual (parte de UI de la
  tarea 4.12 que había quedado sin escribir) viven los dos en
  `ui/sorteo/vista_sorteo.py`, junto al selector de rondas.** "Finalizar
  evento" solo se habilita con **todas** las rondas `cerrada` (el mismo
  criterio de `servicio_eventos.finalizar_evento`, comprobado dos veces —
  una en la UI para no ofrecer un botón que va a fallar, otra en el
  servicio porque nada garantiza que la UI corra primero); tras finalizar,
  ofrece generar el reporte del evento y un respaldo, **nunca los obliga**:
  que uno de los dos falle no debe deshacer una finalización ya válida.
- **`_boton_respaldo` ("Generar respaldo ahora") corre
  `servicio_respaldos.exportar` en una `Tarea` (`QThread`), con
  `QProgressDialog` y cancelación cooperativa — se deshabilita con el
  motivo (tooltip) mientras `EspacioEvento.hay_ronda_viva()` sea cierto
  (hallazgo E-1: en_curso **o** pausada, a diferencia del bloqueo de venta
  de 4.23 que a propósito solo mira en_curso).** Recordatorio (franja no
  modal con acción, nunca modal ni siquiera fuera de `modo_vivo`): al
  iniciar la PRIMERA ronda del evento, y al finalizar el evento.
- **"Restaurar desde respaldo…" (Ajustes, tarea 4.12, hallazgo B4) no
  restaura desde ahí: cierra la conexión, suelta el `QLockFile` y los
  manejadores de log, y relanza el proceso con `--restaurar <zip>`.**
  `VistaAjustes` solo pide el `.zip` y confirma; el gancho que de verdad
  hace ese cierre-y-relanzamiento lo arma `__main__.principal()` (es quien
  tiene la conexión, el `QLockFile` y el `QApplication` reales) y se lo
  entrega a `VentanaPrincipal.establecer_gancho_restaurar()`, que añade la
  única regla que le corresponde a la cáscara: bloquear con un espacio de
  evento abierto encima.
- **Bug real encontrado al escribir esto: capturar `self` (la ventana) en
  el gancho reventaba `test_arranque_limpia_lote_huerfano_de_una_sesion_anterior`
  con un `QLockFile` que nunca se soltaba.** Guardar el gancho en
  `VistaAjustes` (una hija de la ventana) que a su vez captura la ventana
  cierra un ciclo ventana → hijo → gancho → ventana; `establecer_gancho_restaurar`
  usa `weakref.ref(self)` para no añadirlo. Pero la ventana YA tenía un
  ciclo propio y anterior a esta tarea (`i18n.registrar_para_retraduccion`
  conecta `destroyed` a un método ligado de sí misma) que vive del lado de
  Qt, no del de Python — ni `weakref` ahí ni `gc.collect()` a mano lo
  rompen, porque el `QLockFile` capturado por el gancho quedaba vivo
  mientras la ventana lo estuviera, y la ventana nunca se recolectaba sola.
  La corrección real no depende de que la ventana se recolecte nunca:
  `principal()` llama `lockfile.unlock()` explícitamente justo después de
  que `app.exec()` retorna — el mismo punto donde, antes de esta tarea, la
  variable local simplemente salía de ámbito y el archivo se soltaba solo.
  `unlock()` no hace nada si ya estaba suelto, así que llamarlo de más (tras
  un "Restaurar" que ya lo soltó él mismo) es inocuo.
- **Integración continua (tarea 4.26, corrección M7).**
  `.github/workflows/ci.yml` corre `ruff check` + `ruff format --check` +
  `pytest -m "not lento"` sobre `windows-latest` (el único sistema objetivo)
  en cada push/PR a `main` y `dev`. `dev` estaba sin publicar desde la fase
  1 (era un ancestro puro de `main`, sin commits propios) — se avanzó al
  tip de `main` y se publicó.
- **`modo_vivo` (tarea 4.27, corrección §B.5) verificada, no reimplementada:
  ya se cumplía por construcción.** El plan pedía degradar de modal a
  franja los errores no terminales, con `confirmar`/`mostrar_error_modal`
  recibiendo `modo_vivo: bool = False`. Al revisar el código no hay ningún
  camino de modal para `ErrorPersistencia`/`ErrorIntegridad`/
  `ErrorBaseBloqueada`: cada vista atrapa `ErrorBingo` y lo pinta con
  `self._franja.mostrar_error`, siempre, en cualquier modo — no hace falta
  una bandera en tiempo de ejecución para algo que el tipo de excepción y
  el `except` que la atrapa ya deciden estáticamente. Y
  `dialogos.mostrar_error_modal` (canal 3) solo se llama dos veces, ambas
  en `__main__.principal()`, antes de que exista ningún `EspacioEvento` —
  estructuralmente no hay forma de que "esté en directo" cuando ese modal
  puede aparecer. Añadir el parámetro habría sido código muerto; se dejó
  sin añadir y se escribió la prueba que el plan pedía
  (`test_modo_vivo_degrada_error_no_terminal_pero_no_uno_terminal`,
  `tests/ui/test_espacio_evento.py`) para fijar la garantía como
  regresión.
- **Fondo transparente / croma para OBS (tarea 4.18, expansión E2).**
  `ConfigColores.fondo` acepta el valor especial `dominio.tema.
  FONDO_TRANSPARENTE` ("transparente"), y `ConfigColores.croma` (verde
  `#00ff00` por defecto) es el color plano que de verdad se pinta ahí —
  para quien componga en OBS con un filtro de croma. `QColor("transparente")`
  sería un color inválido en silencio (Qt no lanza, pinta negro); un
  `_color_fondo(tema)` en `ui/transmision/bloques.py` (duplicado en
  `vista_tema.py::_LienzoPrevia` hasta que la tarea 4.21 unifique ambos
  consumidores de `dominio.tema`) resuelve al croma cuando corresponde,
  igual que `advertencias_contraste()` cuando mide contra un fondo
  transparente. En el editor, una casilla decide qué se guarda —
  `BotonColor` nunca necesita saber mostrar "transparente": conserva
  siempre el último hexadecimal elegido, para no perderlo si se destilda
  más tarde.
- **Borrado de datos de compradores, alcanzable desde la interfaz (tarea
  4.25, corrección C4, LOPDP).** `servicio_compradores.
  eliminar_todos_del_evento` existía desde la fase 4 y ningún archivo de
  `ui/` lo llamaba — mientras eso siguiera así, la política de retención
  de `TODOS.md` P1 era inejecutable por diseño aunque se decidiera hoy
  mismo. Botón en la sección Compradores, deshabilitado salvo con el
  evento `finalizado`, con confirmación escrita vía `QInputDialog.getText`
  comparada byte a byte contra `evento.nombre` (no un `confirmar()` de
  Sí/No: es la única operación de la fase que borra datos personales sin
  vuelta atrás, y merece más fricción que cerrar una ronda). El estado del
  botón se recalcula en cada `cargar()` contra la base (`repo_evento.
  obtener`), no contra el objeto `Evento` en memoria de la vista — el
  mismo motivo por el que 4.13 refresca `self._evento` tras finalizar:
  nada garantiza que la sección Compradores se reabra después de que
  Sorteo finalice el evento.
- **Panel de auditoría del evento (tarea 4.19, expansión E3 — cierra deuda
  de la fase 4).** `repo_auditoria.listar_por_evento` ya existía desde la
  fase 4 sin ninguna pantalla que lo leyera; nueva sección "Auditoría" de
  solo lectura en el riel, grupo "evento", la **última** — nunca hace
  falta cruzarla con las flechas para llegar a otra sección, que es
  justo la razón por la que Sorteo iba último antes de esta tarea
  (comentario de `registro_vistas.py`). Filtro por prefijo de acción **en
  memoria** (el volumen por evento no justifica SQL nuevo — el propio
  plan lo señala), nuevo `servicio_auditoria.py` (no existía) que
  centraliza ese filtro y delega la exportación a `.xlsx` en
  `impresion/reporte.py::reporte_auditoria_excel` (único módulo que
  escribe Excel, hallazgo A4 de la fase 4) — "exportar" trae exactamente
  las filas que el panel está mostrando, nunca más.
- **Cuenta regresiva de reclamo, con el reloj único en `VistaSorteo` (tarea
  4.24, alcance §6.2).** Los campos de dominio (`segundos_reclamo`,
  `sin_reclamo`, `canal_reclamo`) y los métodos manuales de
  `MaquinaEstadoTransmision` (`reclamo_vencido`/
  `continuar_tras_reclamo_vencido`) ya existían desde 4.9; nadie los
  llamaba con un temporizador real, y `ContextoTransmision.
  segundos_restantes_reclamo` recibía siempre el total configurado del
  tema, nunca un valor que bajara. Ahora `VistaSorteo` arranca un único
  `QTimer` de 1 s al detectar ganador (`segundos_reclamo == 0` = sin
  límite, nunca arranca) y en cada tic empuja el valor a
  `VentanaTransmision.actualizar_segundos_restantes_reclamo()` — la
  ventana **no cuenta el tiempo por su cuenta**: dos relojes
  independientes divergirían tarde o temprano. Al agotarse:
  `sin_reclamo="continuar"` (defecto D8) pinta "reclamo vencido" 5 s y
  vuelve sola al juego; `sin_reclamo="cerrar"` cierra la ronda
  **directamente vía el motor**, nunca por el botón manual
  `_cerrar_ronda()` — ese pide confirmación si quedan bolas (hallazgo C7),
  y esperar un clic que nadie va a dar congelaría la transmisión en
  "reclamo vencido" para siempre.
- **Modo ensayo (tarea 4.17, expansión E1, criterio de aceptación §5.12):
  `python -m bingo --ensayo` reutiliza servicios existentes de punta a
  punta, cero SQL propio.** Nuevo `servicio_ensayo.py`: crea (si no
  existe) una organización y evento fijos por nombre, genera 200
  cartones, los marca "impreso" uno por uno (paso que el ensayo se salta
  de verdad, pero `marcar_vendidos_por_rango` exige un estado vendible) y
  los vende por rango con compradores provisionales, y arma tres rondas
  con patrones del sistema distintos. **Idempotente por diseño**
  (criterio de aceptación explícito del plan: correr `--ensayo` dos veces
  deja exactamente un evento de prueba) — busca por nombre fijo antes de
  crear nada, y si el evento ya existe devuelve el mismo sin tocar la
  base. Llama a `servicio_patrones.asegurar_patrones_sistema` por su
  cuenta en vez de asumir que `__main__.principal()` ya la corrió antes —
  un servicio no debe depender del orden de quien lo invoca.
- **`dominio.tema.BLOQUES` como fuente única, consumida también por
  `vista_tema.py` (tarea 4.21, corrección S5-1).** El editor tenía su
  propia tupla local con solo 4 de los 8 bloques del modelo (faltaban
  `numero_actual`, `patron_activo`, `imagen_premio`, `logo` — los cuatro
  que añadió la fase 5); ahora `_LienzoPrevia` y el formulario iteran
  directamente `dominio.tema.BLOQUES`, así que un bloque nuevo se
  registra una sola vez y aparece en los dos consumidores a la vez.
- **Bug real encontrado al escribir esta tarea: cada autoguardado de
  `VistaTema` reescribía `ConfigJuego` (y `idioma_publico`/
  `pantalla_bienvenida`/`pantalla_cierre`) enteros con los valores por
  defecto de la clase — no los del tema vigente.** Mover un bloque un
  centímetro en el editor borraba en silencio `modo`, `intervalo_seg`,
  `sonido_bola`, `voz`, `idioma_voz` y `volumen_musica` (los campos "de
  directo", decisión DU-7, que la sección Sorteo persiste sueltos con
  `repo_evento.actualizar_juego`) apenas la organización volviera a tocar
  la pestaña Tema. `_leer_formulario()` ahora parte de
  `dataclasses.replace(self._tema.juego, ...)` y de los mismos campos de
  nivel superior de `self._tema`, tocando solo lo que el formulario
  controla de verdad.
- **Los cinco campos "de preparación" de `ConfigJuego`
  (`pausa_al_ganador`, `confirmar_extraccion`, `sin_reclamo`,
  `segundos_reclamo`, `canal_reclamo`) y el color de `numero_actual`
  ganan controles en el editor de Tema.** Antes de esta tarea existían en
  el modelo y en la validación desde 4.1/4.24, pero no había ninguna
  manera de cambiarlos sin editar `tema_json` a mano.
