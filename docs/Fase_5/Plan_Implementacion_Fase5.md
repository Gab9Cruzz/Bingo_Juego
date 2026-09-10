<!-- /autoplan restore point: ~/.gstack/projects/Bingo_App/main-autoplan-restore-20260909-234655.md -->

# Plan de implementación — FASE 5: Sorteo en vivo y cierre

**Autor:** Gabriel (con `/gstack-autoplan`)
**Fecha:** 2026-09-09
**Contrato:** `docs/Fase_5/Contrato_Fase5.md`
**Documentos base:** `docs/Proyecto_Alcance.md`, `docs/Documento_Tecnico.md`,
`docs/convenciones-codigo.md`, `docs/decisiones.md`
**Fase anterior:** Fase 4 (cerrada, commit `bca3b9a`) · **Fase siguiente:** —
**Entregable:** etiqueta `v1.0.0`, aplicación instalable.

---

## 0. Contexto verificado (leído en el código, no asumido)

Todo lo que sigue se comprobó abriendo el archivo, no recordando el plan de la
fase anterior.

| Hecho | Dónde se verificó |
|---|---|
| Suite verde antes de empezar: **433 pruebas pasan**, 5 marcadas `lento` deseleccionadas, 22.6 s | `pytest -q -m "not lento"` |
| PySide6 instalado es **6.11.2**; `QtMultimedia`, `QtTextToSpeech`, `QtPdf` importan sin error | probe directo sobre `.venv` |
| Motores TTS disponibles en el equipo: `winrt`, `sapi`, `mock`. Voces es_ES: Pablo, Laura, Helena. **`sapi` sí expone `en_US`**; `winrt` solo `es_ES` | `QTextToSpeech.availableEngines()` / `availableLocales()` |
| `dominio/` no puede importar PySide6 ni sqlite3; `servicios/` **no puede importar PySide6**; `ui/` no puede importar sqlite3; SQL solo en `persistencia/` | `tests/arquitectura/test_arquitectura.py` (7 pruebas) |
| `dominio/carton.py` ya expone `numeros_por_bit()`, `indice_bit()`, `BIT_LIBRE=12`, `carton_desde_orden_canonico()` — escritos en la fase 2 **para esta fase** | `src/bingo/dominio/carton.py` |
| `dominio/patron.py` ya expone `es_ganador(marcado, mascaras)` y `faltan(marcado, mascaras)` con soporte multi-máscara | `src/bingo/dominio/patron.py` |
| `ui/widgets/cuadricula_carton.py` ya acepta `marcados` y `patron_resaltado`; nadie los pasa todavía | `src/bingo/ui/widgets/cuadricula_carton.py` |
| `ui/tarea.py` (`Tarea(QThread)`) existe con `progreso/terminado/fallado` y `cancelar()` cooperativo | `src/bingo/ui/tarea.py` |
| `config/preferencias.py` ya reserva `ventana.monitor_transmision: int \| None` | `src/bingo/config/preferencias.py` |
| `dominio/tema.py` (`TemaDashboard`) existe con bloques `bombo`, `tablero_75`, `contador_bolas`, `reloj`, `banner_texto` y `ConfigJuego(mostrar_ultimas_bolas, sonido_activado)`. **Faltan** `numero_actual`, `patron_activo`, `imagen_premio`, `logo` y casi todo `juego` del doc técnico §7 | `src/bingo/dominio/tema.py` |
| `_combinar()` de `tema.py` ignora claves desconocidas y rellena las ausentes: **añadir bloques nuevos no requiere migrar ningún `tema_json` guardado** | `src/bingo/dominio/tema.py::_combinar` |
| Tablas `extraccion` y `ganador` ya existen desde la 001, sin tocar. `extraccion` tiene `UNIQUE(ronda_id, orden)` y `UNIQUE(ronda_id, numero)` — el "no repite" del bombo está garantizado también en la base | `001_inicial.sql` |
| `ganador` **no** tiene `UNIQUE(ronda_id, carton_id)`, ni `confirmado_en`, ni forma de registrar reparto/desempate/no-reclamado más allá de `reparte_premio` | `001_inicial.sql` |
| `ronda.estado` es `TEXT NOT NULL DEFAULT 'pendiente'` **sin `CHECK`**, a propósito, esperando `TRANSICIONES_RONDA` de esta fase | `001_inicial.sql` + `docs/decisiones.md` |
| `ronda.premio_valor` es `REAL` y está **muerta** (incumple E4b, dinero en centavos); la fase 4 la dejó así por no justificar reconstruir la tabla | `docs/decisiones.md` (Fase 4) |
| `servicio_rondas.validar_evento_listo(con, evento_id) -> list[PendienteEvento]` ya existe y está pensada para que la fase 5 la llame antes de `preparado -> en_curso` | `src/bingo/servicios/servicio_rondas.py` |
| `TRANSICIONES_EVENTO` permite `preparado -> en_curso -> finalizado` | `src/bingo/dominio/estados.py` |
| Elegibilidad estricta (fase 4, UC-1): solo cartón `vendido` **con** `comprador` vivo. `repo_comprador.mapa_por_evento` da `{carton_id: Comprador}` de una | `docs/decisiones.md`, `repo_comprador.py` |
| `impresion/reporte.py` ya escribe `.xlsx` (con `_escribir_seguro` anti-inyección de fórmulas) y PDF tabular; es el único módulo que abre `openpyxl.Workbook()` | `src/bingo/impresion/reporte.py` |
| `impresion/render_pdf.py` ya registra fuentes en ReportLab y dibuja el cartón; `dominio/firma.py` tiene el HMAC del QR | `src/bingo/impresion/` |
| `config/rutas.py` ya tiene `dir_logs_evento`, `dir_medios_evento`, `dir_respaldos`, `dir_impresos_evento` | `src/bingo/config/rutas.py` |
| `ui/registro_vistas.py::SECCIONES_ESPACIO_EVENTO` es una lista: añadir una sección **no toca** `espacio_evento.py` ni `ventana_principal.py` | `src/bingo/ui/registro_vistas.py` |
| `ui/atajos.py` es un diccionario de módulo; su propio docstring dice que la fase 5 lo convierte en registro cuando haya más de una superficie de teclado | `src/bingo/ui/atajos.py` |
| `__main__.py` corre migraciones, barrido de huérfanos y `asegurar_patrones_sistema`, todos tolerantes a fallo. Códigos de salida 0/2/3/4/5 ocupados | `src/bingo/__main__.py` |
| `bingo.__version__ = "0.1.0"` y `pyproject.toml version = "0.1.0"` — **dos fuentes**, hoy sincronizadas a mano | `src/bingo/__init__.py`, `pyproject.toml` |
| i18n: 478 claves en `es.json` y 478 en `en.json`, misma cantidad | probe sobre los dos JSON |

### Deuda de `TODOS.md` que esta fase tiene que resolver o cerrar

Estos cuatro puntos dicen literalmente "depende de: fase 5". Entran en el plan:

1. `modo_vivo` para suprimir modales durante la transmisión.
2. Registro central de acciones y atajos (más de una superficie de teclado).
3. `ui/espacio_evento.py` deja de escalar por apéndice (el riel llega a 7 entradas).
4. Cifrado del respaldo — subido a **P1** por la revisión de la fase 4 (cinco copias sin
   cifrar de datos personales en el disco del operador).

Y tres que la fase 5 habilita pero no ejecuta: plan de segunda máquina, política de
retención LOPDP, consulta legal. Se mantienen en `TODOS.md`.

---

## 1. Alcance (del contrato, para trazabilidad)

| § | Entregable |
|---|---|
| 5.1 | `dominio/bombo.py` — extracción sin reposición 1-75, `secrets.SystemRandom()`, reconstrucción |
| 5.2 | `dominio/partida.py` — `CartonEnJuego`, índice inverso, `es_ganador`, `faltan` |
| 5.3 | Servicio de sorteo — máquina de estados, persistencia por bola, señales, manual/automático |
| 5.4 | Ventana de transmisión — sin bordes, monitor elegible, lienzo 1920x1080, bloques del tema |
| 5.5 | Superficie de operador — controles, tablero, a-una-bola, ganadores, buscador, monitor |
| 5.6 | Validación y registro de ganadores — reclamo, no-vendidos, empate, reparto, nadie reclama |
| 5.7 | Reanudación — ofrecer, reconstruir, verificar |
| 5.8 | Sonido y locución — efectos, música, voz es/en, todo desactivable |
| 5.9 | Actas y reportes — acta por ronda (PDF + SHA-256), reporte de evento (PDF + Excel), log de partida |
| 5.10 | Respaldos — `.zip` fechado, recordatorios |
| 5.11 | Empaquetado — PyInstaller `--onedir`, Inno Setup, versión visible, migración sobre instalación con datos |
| 5.12 | Pruebas — bombo, ganador, a-una-bola, reanudación, ensayo completo manual |

---

## 2. Qué ya existe (leverage map)

Lo que **no** hay que escribir, y de dónde sale:

| Necesidad de la fase 5 | Ya resuelto por | Nota |
|---|---|---|
| Marcar bits de un cartón | `dominio/carton.numeros_por_bit()` | escrito en la fase 2 para esto |
| Reconstruir la matriz desde `carton.numeros` | `dominio/carton.carton_desde_orden_canonico()` | idem |
| Ganador y a-una-bola con multi-máscara | `dominio/patron.es_ganador/faltan` | fase 4, ya probado |
| Pintar cartón con marcas + patrón resaltado | `ui/widgets/cuadricula_carton.py` | la API `marcados`/`patron_resaltado` ya está |
| Pintar una rejilla 5x5 de patrón | `ui/widgets/rejilla_patron.py` | para el bloque `patron_activo` |
| Trabajo largo sin congelar | `ui/tarea.py::Tarea` | respaldo, reporte de evento |
| Transacción atómica, traducción de errores SQLite | `persistencia/conexion.transaccion`, `errores_sqlite` | la persistencia por bola se apoya entera aquí |
| Excel seguro contra inyección de fórmulas | `impresion/reporte._escribir_seguro` | el reporte del evento lleva nombres de personas |
| PDF tabular + fuentes registradas | `impresion/reporte.reporte_conciliacion_pdf`, `render_pdf._asegurar_fuente_registrada` | el acta reusa el patrón |
| Dinero en centavos | `dominio/dinero.py` | el acta imprime el premio |
| Validación "¿se puede jugar?" | `servicio_rondas.validar_evento_listo` | puerta de `preparado -> en_curso` |
| Cartones elegibles | `repo_carton.listar_por_evento(estado="vendido")` + `repo_comprador.mapa_por_evento` | invariante de la fase 4 |
| Modelo y editor del tema de transmisión | `dominio/tema.py`, `ui/vistas/vista_tema.py` | hay que **ampliarlos**, no crearlos |
| Sección nueva en el riel sin tocar la cáscara | `ui/registro_vistas.SECCIONES_ESPACIO_EVENTO` | apéndice de una línea |
| Auditoría | `repo_auditoria.registrar` | cada decisión de ganador va aquí |

---

## 3. Decisiones de diseño

### D1 — El servicio de sorteo no importa Qt. Un adaptador en `ui/` emite las señales.

El contrato §5.3 pide "señales de Qt según la tabla §6.4".
`tests/arquitectura/test_arquitectura.py::test_servicios_no_importan_pyside6` lo
prohíbe, y esa regla es la que mantiene el núcleo probable sin `QApplication`.

Resolución: `servicios/servicio_sorteo.py` define `MotorSorteo`, Python puro, que
publica los cinco eventos por **callbacks** (`al_extraer`, `al_detectar_a_una_bola`,
`al_detectar_ganadores`, `al_confirmar_ganador`, `al_cambiar_ronda`), mismo convenio
que `al_progresar`/`debe_cancelar` de `ui/tarea.py`. `ui/sorteo/puente_sorteo.py`
define `PuenteSorteo(QObject)` que envuelve el motor y emite exactamente las señales
de la tabla §6.4 con sus nombres del documento (`bola_extraida`, `cartones_a_una_bola`,
`ganadores_detectados`, `ganador_confirmado`, `ronda_cambiada`). Las dos ventanas se
suscriben al puente, nunca al motor.

Coste: una clase de ~60 líneas. Beneficio: el motor de sorteo entero se prueba sin Qt.

### D2 — La extracción se persiste en el hilo de la interfaz, no en un `QThread`.

El contrato es explícito: *"el commit ocurre antes de que la interfaz muestre la
bola"*. Con un trabajador eso obliga a un ida y vuelta de señales por bola, con la
interfaz esperando de todos modos. Sin trabajador es una transacción corta
(1 `INSERT` en `extraccion`, 0-N en `ganador`, 0-1 `UPDATE` de `ronda`; el log de
partida queda **fuera**, ver S5-6) dentro de una vuelta del bucle de eventos, que es
exactamente lo que
`docs/convenciones-codigo.md` permite ("la interfaz no mantiene nunca una transacción
abierta **entre dos vueltas** del bucle").

Con `synchronous=FULL` eso es un `fsync` por bola. Se mide en la prueba
`test_extraccion_persiste_en_menos_de_50ms` (marcada `lento`): si en el equipo real
supera 50 ms se revisa; a 6 segundos por bola en modo automático hay margen de sobra.
Nada más de la fase 5 corre en el hilo de la interfaz: respaldo y reporte de evento
van en `Tarea`.

### D3 — Migración `004_fase5.sql`: solo `ADD COLUMN` e índices. Ninguna tabla se reconstruye.

**Nota de corrección.** La voz dual planteó (hallazgo M3) reconstruir `ronda` en esta
migración para cumplir E4b, y la revisión primaria lo aceptó. **Las dos se
equivocaban, por el mismo dato mal leído.** Verificado después contra el código:
`003_fase4.sql:95-96` ya añadió `premio_valor_centavos INTEGER` y
`premio_descripcion TEXT`, `dominio/modelos.py::Ronda` ya expone
`premio_valor_centavos`, y `repo_ronda._COLUMNAS` ya lo lee y lo escribe. E4b **ya
se cumple desde la fase 4**. Lo único que quedaría por hacer reconstruyendo la tabla
es **borrar la columna muerta `premio_valor` (REAL)**, que nadie lee.

Reconstruir `ronda` entera —sobre una tabla que ahora sí puede tener filas reales—
para borrar una columna que nadie lee es riesgo puro a cambio de estética. Se
mantiene el `ADD COLUMN`, y la convivencia con la columna muerta se escribe en
`docs/decisiones.md` como **estado permanente aceptado**, no como deuda que alguien
pagará: la próxima vez que `ronda` se reconstruya por una razón de verdad, se
elimina de paso.

```sql
-- ronda: solo columnas nuevas. estado sigue SIN CHECK a propósito (decisión de la
-- fase 1, todavía vigente: el conjunto puede crecer — ver V5 — y un CHECK no se
-- quita en SQLite sin reconstruir la tabla).
ALTER TABLE ronda ADD COLUMN iniciada_en      TEXT;
ALTER TABLE ronda ADD COLUMN cerrada_en       TEXT;
ALTER TABLE ronda ADD COLUMN acta_hash        TEXT;
ALTER TABLE ronda ADD COLUMN acta_generada_en TEXT;

-- ganador: también basta ADD COLUMN.
ALTER TABLE ganador ADD COLUMN confirmado_en TEXT;
ALTER TABLE ganador ADD COLUMN decision      TEXT;   -- unico | reparto | desempate_externo | no_reclamado | rechazado
ALTER TABLE ganador ADD COLUMN anulado_en    TEXT;
ALTER TABLE ganador ADD COLUMN nota          TEXT;
CREATE UNIQUE INDEX idx_ganador_ronda_carton ON ganador(ronda_id, carton_id);
CREATE INDEX idx_ganador_ronda ON ganador(ronda_id);
CREATE INDEX idx_extraccion_ronda ON extraccion(ronda_id, orden);
```

**El índice único NO es parcial (corrección del hallazgo V1).** La versión original
llevaba `WHERE anulado_en IS NULL`, copiando el patrón de `comprador` de la fase 4.
Ahí era correcto (un cartón anulado se revende, así que necesita otra fila viva);
aquí es un fallo grave: un ganador anulado quedaría **fuera** del índice, y el
`INSERT OR IGNORE` de una reanudación lo reinsertaría vivo. Un cartón solo puede
ganar una ronda una vez, anulado o no — la anulación es un hecho sobre esa misma
fila, no una invitación a crear otra. Índice total.

`servicio_rondas` y `vista_rondas.py` migran de `premio_valor` a
`premio_valor_centavos`, usando `dominio/dinero.py` como manda la convención.

### D4 — La configuración de juego vive en `tema_json.juego`, no en columnas nuevas.

El documento técnico §7 ya la define ahí (`intervalo_seg`, `modo`, `pausa_al_ganador`,
`voz`, `idioma_voz`, `sonido_bola`, `confirmar_extraccion`). `_combinar()` rellena lo
ausente, así que **ningún `tema_json` guardado necesita migrarse**. Se amplía
`ConfigJuego` con esos campos más `sin_reclamo` (D8) y `volumen_musica`.

Se añaden además los cuatro bloques que faltan (`numero_actual`, `patron_activo`,
`imagen_premio`, `logo`) y `pantalla_bienvenida` / `pantalla_cierre` con sus textos.

**Contrapeso al hallazgo V6.** La misma propiedad que hace cómodo ampliar
`tema_json` — `_combinar()` ignora claves desconocidas — convierte un error de tipeo
en silencio permanente: la clave mal escrita se ignora para siempre, sin error, sin
log, sin prueba que lo detecte. Y esta decisión convierte `tema_json` en el objeto de
configuración más grande del proyecto (colores, quince bloques, dos pantallas, once
ajustes de juego). Dos defensas baratas:

- `tema_json` gana un campo `version` (entero, hoy `1`).
- Una prueba compara el conjunto de claves de los dataclasses contra un fixture
  guardado: ampliar el modelo pasa a ser un cambio consciente que actualiza el
  fixture, no un accidente que nadie ve.

### D5 — Locución: TTS del sistema por defecto, con carpeta de audio pregrabado que la sustituye.

Decisión pendiente del contrato §5.8, resuelta con evidencia medida en este equipo:
`QTextToSpeech` funciona, el motor `sapi` expone `es_ES` **y** `en_US`, y hay tres
voces en español instaladas de fábrica en Windows. 150 archivos por idioma serían 300
assets, un locutor y un instalador más pesado, para un problema que el sistema
operativo ya resuelve.

Pero la calidad del TTS de Windows es la que es, y esto se oye en vivo. Así que la
arquitectura es un protocolo, no un motor fijo:

```
ui/sonido/locucion.py
  class ProveedorLocucion(Protocol):  decir(numero, idioma) / detener() / disponible()
  class LocucionTTS(ProveedorLocucion)          # QTextToSpeech, por defecto
  class LocucionPregrabada(ProveedorLocucion)   # medios/locucion/<idioma>/NN.wav
  def crear_proveedor(idioma) -> ProveedorLocucion   # pregrabado si la carpeta está completa, si no TTS
```

Si `%LOCALAPPDATA%\Bingo\medios\locucion\es\01.wav … 75.wav` existe completa, se usa;
si falta un archivo, se cae a TTS y se avisa una vez en el log. No se empaqueta ningún
audio de voz. El día que Gabriel quiera grabarse, copia 75 archivos y no toca código.

**Degradación:** si `QTextToSpeech.availableEngines()` viene vacío o el idioma elegido
no tiene voz, la locución se desactiva sola, se registra en el log y la casilla de
la vista queda deshabilitada con un texto explicando por qué. Nunca revienta el sorteo.

### D6 — Efectos de sonido: tres WAV sintetizados, no assets con licencia.

`recursos/sonidos/{bola,ganador,alerta}.wav`, generados una sola vez con el módulo
`wave` de la biblioteca estándar (un blip corto, envolvente suave) y versionados. Cero
dudas de licencia, ~20 KB en total, reproducidos con `QSoundEffect` (baja latencia,
pensado para esto). La **música de fondo** no se empaqueta: el operador apunta a un
archivo suyo desde ajustes, se reproduce con `QMediaPlayer` con control de volumen.

### D7 — El hash del acta se calcula sobre una carga canónica, no sobre los bytes del PDF.

Los bytes de un PDF de ReportLab incluyen la fecha de creación: dos actas del mismo
sorteo darían hashes distintos y el hash impreso no podría estar dentro de su propio
PDF. Se define `dominio/acta.py::carga_canonica(...) -> str`, una serialización
determinista (evento, organización, ronda, patrón, premio, secuencia de bolas en
orden, ganadores con código y decisión), y el hash es su SHA-256. Ese hash se imprime
en el acta, se guarda en `ronda.acta_hash` y se registra en auditoría. Regenerar el
acta del mismo sorteo da el mismo hash — que es lo que lo hace un comprobante.

### D8 — "Nadie reclama" es un ajuste de dos valores, con registro obligatorio.

Decisión pendiente del contrato §5.6. `tema_json.juego.sin_reclamo`:

- `"continuar"` (por defecto) — la ronda sigue extrayendo bolas hasta que alguien
  reclame o se agote el bombo. Es lo que hace un bingo de salón cuando el ganador
  fue al baño.
- `"cerrar"` — la ronda se cierra con el ganador detectado marcado
  `decision = 'no_reclamado'`, y el reporte del evento lo lista aparte para que la
  organización lo contacte.

En los dos casos la fila de `ganador` se escribe igual: la detección es un hecho
objetivo del sorteo y no se borra porque nadie aparezca.

**Pero solo se registran las detecciones de la primera bola ganadora (hallazgo C1,
crítico).** La versión anterior de esta decisión la presentaba como "un ajuste de dos
valores", y no lo es. Con `"continuar"` la ronda **sigue detectando en cada bola**:
con patrón "línea" y 200 cartones, tras la primera línea en la bola ~22 entran decenas
de cartones nuevos a `ganador` en cada extracción. Para la bola 45 puede haber cien
filas. Consecuencias que nadie quiere en directo:

- `resolver_empate` deja a todos los detectados con `decision` explícita → cien
  decisiones manuales, en cámara.
- El acta lista "ganadores con código y decisión" → cinco páginas de perdedores.
- Cada detección nueva re-dispara `ganadores_detectados` → la transmisión vuelve a
  `HAY_CARTON_GANADOR` y **la cuenta regresiva de reclamo se reinicia cada seis
  segundos**, en bucle, delante del público.

Resolución: se separa **detección** de **registro**. El motor guarda
`_orden_ganador` — el `extraccion.orden` de la primera bola que produjo ganador — y
persiste y notifica **solo** las detecciones de esa bola, que es exactamente la
definición de empate de V2. A partir de ahí la ronda sigue extrayendo (eso es lo que
`"continuar"` significa) pero no registra ni notifica más. Si el operador rechaza a
todos los de esa bola, abre explícitamente la siguiente con una acción propia. Se
escribe como decisión y se prueba.

**Y el ciclo de vida de `ganador` se dibuja antes de escribir
`servicio_ganadores.py`.** Entre C1, la reanudación (C2), el empate por orden (V2),
`no_reclamado` (D8) y la reapertura de ronda (V5 + C6), esta es la máquina de estados
más complicada de la fase y no estaba diagramada en ninguna parte. El diagrama es un
entregable de la tarea 4.7, no un adorno.

### D9 — El operador es una sección del riel, no una tercera ventana.

El contrato §5.5 dice "ventana de operador" en oposición a "ventana de transmisión".
Hacerla ventana de verdad significa una tercera superficie con su propio menú, su
geometría, su cierre y su retraducción. La navegación de dos niveles (E14) ya da todo
eso: `SECCIONES_ESPACIO_EVENTO` gana **Sorteo**, y esa sección tiene un botón
**Modo en vivo** que oculta riel y cabecera y deja la pantalla entera al juego
(y activa la bandera `modo_vivo` de `TODOS.md`, que suprime modales no terminales).
La única ventana nueva de la fase es la de transmisión, que sí es otra ventana porque
va en otro monitor.

### D10 — El riel se agrupa en dos bloques. `espacio_evento.py` deja de escalar por apéndice.

Con Sorteo son siete secciones. `EntradaSeccionEvento` gana un campo `grupo`
(`"preparacion" | "evento"`), y `espacio_evento.py` pinta un encabezado no
seleccionable por grupo. Cambio pequeño, cierra el punto de `TODOS.md`, y hace obvio
de un vistazo qué se toca antes del evento y qué durante.

Orden final: **Preparación** — Datos, Cartones, Plantilla, Tema · **Evento** —
Compradores, Rondas, Sorteo.

### D11 — El respaldo se cifra si el operador pone contraseña. Por defecto avisa.

`TODOS.md` subió el cifrado a P1. Cifrar de verdad un `.zip` (AES) exige una
dependencia nueva (`pyzipper`), justo lo que la escalera de reutilización desaconseja.
La biblioteca estándar (`zipfile`) solo **lee** ZipCrypto, no lo escribe, y ZipCrypto
está roto de todos modos.

Resolución sin dependencia nueva y sin criptografía casera: el respaldo escribe
`RESPALDO_LEEME.txt` dentro del `.zip` diciendo en una frase que contiene datos
personales de compradores, y la vista muestra un aviso al exportar con la ruta y la
recomendación de guardarlo en un disco cifrado con BitLocker. El cifrado real queda en
`TODOS.md` como P1 con una nota que ahora dice qué dependencia haría falta y por qué no
entró. Es una decisión de alcance consciente, no un olvido: cifrar mal es peor que no
cifrar y decirlo.

**Dos matices que aporta la voz dual (hallazgo C4):**

- *El respaldo sí lleva la tabla `comprador`.* Se evaluó la propuesta contraria
  (excluirla por defecto) y se rechaza: un `.zip` sin compradores restaurado en un
  segundo equipo deja el evento sin poder determinar quién es elegible, que es
  exactamente el escenario que la restauración de 4.12 existe para salvar. El
  respaldo es una copia **operativa**. Lo que se entrega a la organización es el
  reporte del evento, no el respaldo — y ese reporte ya tiene su casilla de datos
  de contacto desmarcada por defecto (criterio UC-3 de la fase 4).
- *El argumento "una dependencia nueva" es más débil de lo que parecía.* Este
  proyecto ya empaqueta PySide6, ReportLab, openpyxl y Pillow; `pyzipper` (AES-ZIP
  en Python puro) es ruido frente a eso y PyInstaller lo maneja sin drama. La razón
  real para no cifrar hoy es de alcance, no técnica, y así queda escrito en
  `docs/decisiones.md`: **riesgo asumido**, no limitación. Junto con la tarea 4.25,
  que es la que hace ejecutable la política de retención.

### D12 — `ui/atajos.py` pasa a registro. La versión pasa a fuente única.

Dos deudas menores que esta fase toca de todos modos:

- `ATAJOS` se convierte en `RegistroAtajos` con `registrar(accion, secuencia, ambito)`
  y `secuencia(accion, ambito)`, porque ahora hay tres ámbitos de teclado (global,
  sorteo, transmisión) y el mismo `Ctrl+N` ya significa dos cosas distintas según la
  vista.
- `pyproject.toml` deja de declarar `version` a mano: `[project] dynamic = ["version"]`
  con `[tool.setuptools.dynamic] version = {attr = "bingo.__version__"}`. Una sola
  fuente, que es la que lee la pantalla de ajustes, la auditoría de apertura de evento
  y el instalador.

### D13 — La reanudación reproduce en memoria, **no escribe nunca**, y si no cuadra no miente.

Reconstruir es determinista: `extraccion` ordenada por `orden`, cartones vendidos con
comprador vivo, aplicar bolas en orden.

**Corrección del hallazgo V1 (crítico).** La versión original de esta decisión decía
que la reproducción "vuelve a detectar" ganadores y que el `INSERT OR IGNORE` la hacía
idempotente. Dos consecuencias, las dos malas: un ganador que el operador **anuló**
volvía a insertarse vivo (con el índice parcial que llevaba D3), y la comparación
"detectados por reproducción" contra "filas no anuladas" difería **por construcción**,
disparando un modal terminal de incoherencia por un caso perfectamente normal, en
mitad de un evento en vivo.

La reanudación queda así:

- La reproducción es **solo lectura**: reconstruye el `marcado` de cada cartón y el
  estado del bombo. No hace ni un `INSERT`.
- La verificación compara dos conjuntos **normalizados en los dos lados**: se
  excluyen las filas con `anulado_en IS NOT NULL` y las que tengan
  `decision = 'rechazado'`. Un ganador anulado no se espera y no se reclama.
- Solo si los conjuntos difieren tras esa normalización hay incoherencia real:
  modal terminal con el detalle, opción de reanudar de todos modos (que escribe
  `sorteo.reanudacion_incoherente` en auditoría con los dos conjuntos) y opción de
  cancelar. El log de partida en texto plano es la tercera fuente para dirimir.
- **`ResultadoReanudacion` incluye el conjunto de `carton_id` ya persistidos**
  —anulados y rechazados incluidos— y el motor lo carga como `_ya_detectados`
  (hallazgo C2, crítico). Sin eso, la reproducción reconstruye el `marcado` pero no
  *qué se notificó ya*: en la siguiente bola, un cartón que ya ganó y que contiene esa
  bola vuelve a cumplir el patrón, `al_detectar_ganadores` se dispara otra vez, la
  transmisión vuelve a `HAY_CARTON_GANADOR` con su cuenta regresiva, y el
  `INSERT OR IGNORE` **se traga la anomalía sin dejar rastro**. Si el operador ya lo
  había anulado, reaparece en pantalla.
- **Se retira el `INSERT OR IGNORE` de `ganador` (hallazgo C3).** Con la reanudación
  en solo lectura nadie reinserta nunca: el `OR IGNORE` deja de ser idempotencia y
  pasa a ser un supresor de `ErrorIntegridad` para el caso C2 — peor que no tenerlo.
  `INSERT` normal; si el índice único salta, es un bug y llega como `ErrorIntegridad`
  a la franja. (Corrige también el verbo de E-3: `crear` normal, sin
  `crear_si_no_existe`.)
- Pruebas obligatorias: anular un ganador, matar el proceso, reanudar, verificar que
  **no reaparece** y que **no** se declara incoherencia; y tras reanudar, extraer una
  bola que ese cartón contiene → **cero** callbacks de ganador.

### D14 — La transmisión se pinta a mano sobre un lienzo lógico 1920x1080.

**Contingente al spike de OBS (corrección de la discrepancia H6).** La ruta por
defecto es la nativa, por DRY contra el editor de tema de la fase 4. Pero la decisión
se **cierra con el resultado del spike**, no antes: si OBS captura la ventana Qt en
negro (aceleración por hardware) o el DPI fraccional con `PassThrough` desalinea el
lienzo, la ruta web (servidor HTTP local + OBS Browser Source, que además regala
canal alfa y no necesita segundo monitor) deja de ser una preferencia y pasa a ser la
salida. Escribir `ui/transmision/` antes de correr el spike es apostar 4.9 entera a
una premisa no medida.

Ruta nativa, si el spike la valida:

Un `QWidget` con `paintEvent` y una `QTransform` de escala, no `QGraphicsView` ni QML.
Los bloques son objetos con `pintar(painter, rect)` en `ui/transmision/bloques.py`, uno
por bloque del tema, con la misma tabla de posiciones fraccionarias que ya usa la vista
previa de `vista_tema.py` — así lo que se configura es literalmente lo que sale. La
animación de extracción es un `QTimer` a 60 Hz que invalida **solo** el rectángulo del
bombo y el del número actual, nunca la pantalla entera.

---

## 3-bis. Decisiones de interfaz

Las decisiones D1-D14 son de arquitectura. Estas son de interfaz, y llevan números
por la misma razón: la superficie del operador y la de transmisión son lo único que
alguien ve, y describirlas con inventarios de componentes ("panel de ganadores con
datos y botones") no es delegar en el implementador, es aplazar la decisión hasta la
noche anterior al evento. Todas salen de la Fase 2 de la revisión (ANEXO B).

### DU-2 — Jerarquía de tres zonas en la superficie del operador, con proporciones fijas

El §4.8 original enumeraba trece elementos en un párrafo, todos con el mismo peso.
Eso se convierte, sin falta, en una rejilla de `QGroupBox` equitativos — el patrón de
`vista_rondas.py` y `vista_tema.py`, que son formularios de preparación, no un panel
de vuelo. Bajo presión, hablando a cámara, el orden real es: el número que acabo de
cantar, si hay ganador ahora mismo, y el botón de extraer.

```
  ZONA A — ~35% del alto.  El número actual: letra BINGO + cifra, a
                           min(220 px, 18% del alto de la sección). A su derecha,
                           estado de la ronda y cuenta regresiva de reclamo.
                           NADA MÁS entra en esta zona.

  ZONA B — ~45% del alto.  Izquierda: tablero de 75 + contador N/75.
                           Derecha: ganadores / a-una-bola, COLAPSADO A ALTURA CERO
                           cuando está vacío (no un marco vacío ocupando sitio).
                           Esquina: monitor de confianza (DU-8).

  ZONA C — ~20% del alto.  Barra de acciones fija: [ EXTRAER ] (ancho doble,
                           ≥ 48 px de alto), Pausar, Cerrar ronda. Buscador de
                           código. El resto plegado tras "Ajustes de la ronda".
```

Los paneles de a-una-bola y de ganadores **no se pintan cuando están vacíos**. Nada
de "Ningún ganador todavía" en gris: que aparezcan *es* la señal. Un contenedor
permanente vacío entrena al ojo a ignorar justo la zona donde luego aparece lo único
urgente.

### DU-3 — La pantalla de transmisión es una máquina de estados de nueve estados, no un lienzo con bloques

Esta es la decisión que más cambia el producto, y sale del hallazgo más agudo de la
revisión: **el motor canta bingo antes que el jugador.** El patrón se completa en el
instante de la bola; el humano tarda entre tres y cuarenta segundos en darse cuenta,
más el retraso de la plataforma. Con `sin_reclamo="continuar"` (el defecto de D8), si
nadie reclama la ronda **sigue extrayendo bolas después de haber gritado ¡BINGO! en
pantalla**. Para el espectador eso es incomprensible; para la organización es un
problema de credibilidad.

| Estado | Qué ve el público | Disparador |
|---|---|---|
| `BIENVENIDA` | Texto configurable, logo, patrón y premio de la ronda 1 | Antes de iniciar |
| `EN_JUEGO` | Número actual, últimas bolas, tablero, patrón, premio, contador | `bola_extraida` |
| `A_UNA_BOLA_CRITICA` | Igual, más "N cartones a una bola" con tratamiento dramático si N ≤ 3 | `cartones_a_una_bola` |
| `HAY_CARTON_GANADOR` | **"Hay un cartón ganador. Reclama por ‹canal› · 0:47"** + patrón completado parpadeando. **Sin la palabra BINGO. Sin datos.** | `ganadores_detectados` |
| `RECLAMO_VENCIDO` | Tarjeta de 4-6 s: "Nadie reclamó a tiempo. El juego continúa." | Cuenta agotada, `sin_reclamo="continuar"` |
| `GANADOR_CONFIRMADO` | **Aquí y solo aquí el ¡BINGO! grande**, con código y nombre | `ganador_confirmado` |
| `ENTRE_RONDAS` | Patrón y premio de la ronda siguiente, en grande, texto configurable | Ronda cerrada |
| `PAUSA` | Marca "EN PAUSA" + reloj corriendo, para que se note que el sistema vive | `pausar` |
| `CIERRE` | Texto configurable de cierre, resumen de ganadores | Evento finalizado |

`ENTRE_RONDAS` y `PAUSA` no son adorno: los huecos entre rondas duran entre dos y
cinco minutos mientras el operador habla, cobra y ordena. Es el **mayor porcentaje de
tiempo de pantalla del evento** y en la versión anterior del plan no existía.

La regla del contrato ("no revelar antes de confirmar") ya estaba bien resuelta; lo
que faltaba era que el estado intermedio **se llamara lo que es**.

### DU-4 — `BLOQUES` lleva posiciones por defecto, y `validar()` detecta solapes

Verificado en el código: `dominio/tema.py::ConfigBloque` tiene `pos_x=0.0, pos_y=0.0`
y **solo `tablero_75` está sembrado** (`_tablero_75_por_defecto`, `pos_x=0.72`). Hoy
`bombo`, `contador_bolas` y `reloj` ya nacen apilados en la esquina superior
izquierda. D4 añade cuatro bloques más. Consecuencia literal de aplicar el plan tal
como estaba: un evento nuevo abre la transmisión y muestra **siete bloques
superpuestos en el origen**. Y `validar()` no lo detecta — comprueba rango 0-1 y
formato de color, nada más.

- `dominio/tema.py::BLOQUES` lleva `(clave, clave_i18n, pos_x, pos_y, ancho_frac,
  alto_frac)`. **Posición por defecto incluida**, no solo dimensiones.
- Composición por defecto sobre 1920x1080: `numero_actual` centro-izquierda ocupando
  ≥ 22% del alto; `bombo` encima; `ultimas_bolas` debajo; `tablero_75` columna
  derecha (ya sembrado en 0.72); `patron_activo` bajo el tablero; `contador_bolas` y
  `reloj` en la franja superior; `logo` esquina superior derecha; `imagen_premio`
  inferior izquierda; `banner_texto` franja inferior.
- `validar(tema)` gana **detección de solape** entre bloques visibles. No bloqueante
  (un `ErrorValidacion` al mover un bloque sería insoportable): advertencia que
  `vista_tema.py` pinta con `FranjaError.mostrar_info` y que el lienzo de vista previa
  dibuja con borde de aviso.
- Botón "Restablecer composición", mismo gesto que el "Restablecer desde
  organización" de la fase 3.

### DU-5 — Política de foco y teclado, escrita antes de que colisione

Tres colisiones garantizadas que la versión anterior del plan no veía:

1. **`Espacio`, `P` y `R` con un buscador de texto siempre activo en la misma
   pantalla.** En cuanto el foco está en el `QLineEdit` —y va a estarlo, acaba de
   validar un reclamo— la barra espaciadora escribe un espacio y no extrae bola. El
   operador pulsa tres veces, no pasa nada, y está en cámara.
2. **`showFullScreen()` en Windows roba la activación.** A partir de ahí ningún atajo
   del operador funciona hasta que se haga clic en la ventana principal.
3. **`Ctrl+Enter` "confirma el ganador seleccionado"** sin que exista un estado de
   selección definido.

Reglas:

- La ventana de transmisión se crea con `Qt.WA_ShowWithoutActivating` **y**
  `Qt.WindowDoesNotAcceptFocus`; tras `showFullScreen()` se devuelve el foco con
  `activateWindow()` sobre la principal. **Se prueba con `pytest-qt`.** Efecto
  colateral bueno: un `Alt+F4` accidental en directo no puede matarla.
- Los atajos de ámbito `sorteo` son `QShortcut` con
  `Qt.ShortcutContext.WidgetWithChildrenShortcut` sobre la sección, y **los de una
  sola tecla se inhiben mientras un campo de texto tiene el foco**. Extraer se enlaza
  además a `F5`, que no colisiona nunca.
- `Ctrl+Enter` con más de un ganador detectado y ninguno seleccionado **no hace nada**
  y avisa. Nunca elige el primero por defecto: es dinero.
- Orden de tabulación por recorrido, no por orden de código: Extraer → ganadores →
  buscador → controles secundarios.

### DU-6 — Mínimos de legibilidad y contraste, con números

`ui/atajos.py` define `TIPOGRAFIA_MINIMA_PX = 13` y
`OBJETIVO_PULSACION_MINIMO_PX = 32` desde la fase 1, con el comentario "Gabriel lee
esto de reojo, con la cámara delante". Solo los usa `rejilla_patron.py`. Esta es
literalmente la fase para la que se escribieron.

**Superficie del operador:**
- Todo control de la sección Sorteo ≥ `OBJETIVO_PULSACION_MINIMO_PX`.
- Botones críticos (Extraer, Pausar, Confirmar) ≥ 48 px de alto.
- Número actual y contador ≥ 24 px.
- Prueba `pytest-qt` que recorre los `QPushButton` de la sección y comprueba
  `sizeHint().height()`.

**Superficie de transmisión** (el público la ve en un móvil, con vídeo comprimido y
20 s de retraso):
- `numero_actual` ≥ 14% del alto del lienzo. Por debajo, `ErrorValidacion`.
- **`contraste()` se mueve de `ui/tema.py` a `dominio/`** — es matemática pura, no
  tiene nada de Qt, y hoy está mal ubicada. `validar()` avisa cuando
  `texto/fondo < 4.5`, `numero_actual/fondo < 4.5`, o cuando `tablero_marcado` se
  parece demasiado a `fondo`. **Umbral propio 7:1, no 4.5:1**: la compresión de vídeo
  se come el contraste.
- `ConfigColores` gana **`numero_actual`** (el doc técnico §7 ya lo definía como
  `#ffd60a`; el modelo de la fase 4 lo perdió). Y los defectos de `acento` y
  `tablero_marcado` dejan de ser **el mismo `#5b8def`**: hoy el resaltado de bola
  cantada y el color de acento son indistinguibles.
- Nada de texto fino sobre imagen de fondo; el número actual lleva fondo sólido u
  opaco detrás. Cifras tabulares y peso alto de la familia ya empaquetada (G24): el
  número cambia cada seis segundos y no debe bailar.
- El tablero de 75 marca la cantada con **relleno + inversión de texto + negrita**
  (tres señales, no solo color: daltonismo y compresión). La **última** cantada lleva
  además borde de 4 px en `numero_actual` y no comparte tratamiento con las demás.
- Preset **"Legible en celular"** por defecto, con botón para volver a él, y vista
  previa **"Ver como celular"** en el editor.

### DU-7 — Quién es dueño de `tema_json.juego` (pérdida de datos silenciosa)

Verificado: `vista_tema.py::_guardar` **escribe el objeto de tema completo**
(`repo_evento.actualizar_tema(con, id, self._tema.a_json())`) con un `QTimer` de
retardo, y no recarga nunca. Si la sección Sorteo también toca `juego.modo`,
`intervalo_seg` o `voz` —y tiene que hacerlo, son controles de directo— hay **dos
editores del mismo documento con escritura diferida de objeto completo: el último que
guarde borra lo del otro, en silencio.** Y ese `QTimer` puede dispararse entre dos
bolas, compitiendo por el lock de escritor con la transacción por bola de D2.

- Los controles **de directo** (`modo`, `intervalo_seg`, `sonido_bola`, `voz`,
  `volumen_musica`) viven **solo** en la sección Sorteo. Se aplican en memoria de
  inmediato y se persisten con escritura de campo puntual
  (`repo_evento.actualizar_juego(con, evento_id, clave, valor)` con `json_set`),
  nunca reescribiendo el tema completo.
- La sección Tema conserva solo lo que es **preparación**: `pausa_al_ganador`,
  `segundos_reclamo`, `sin_reclamo`, `confirmar_extraccion`,
  `mostrar_ultimas_bolas`, `idioma_publico`.
- `vista_tema` **para su `QTimer` mientras haya ronda en juego**
  (`repo_ronda.obtener_en_juego`), igual que la fase 4 exigió pararlo durante una
  `Tarea`.
- **Tercer caso de la convención DS14.** El plan cita `vista_rondas.py` como el
  antipatrón a no repetir y luego no decía cuál de los dos patrones sigue Sorteo. No
  sigue ninguno: los controles de directo son *aplicación inmediata en memoria +
  persistencia puntual*, un tercer caso que se declara en
  `docs/convenciones-codigo.md` en vez de dejar que se resuelva por imitación.

### DU-8 — Monitor de confianza: el operador tiene que ver lo que ve el público

La transmisión vive en el monitor 2, que en un salón está detrás o de lado. Si el
bloque `logo` quedó encima del `numero_actual`, o la pantalla de bienvenida no se
quitó, el operador se entera por el chat de Facebook, con veinte segundos de retraso.

Miniatura en vivo del lienzo de transmisión en la Zona B, pintada con **los mismos
pintores de `bloques.py`** sobre un `QPixmap` escalado a ~320x180, refrescada solo
cuando cambia el estado (nunca a 60 Hz). Cuesta unas treinta líneas porque los
pintores ya existen por la tarea 4.21, y es la única forma de verificar la salida sin
girar la cabeza.

### DU-9 — Un solo campo de código, dos acciones distintas

El §4.8 define un "buscador por código siempre activo" y el §4.7 define
`validar_reclamo(con, ronda_id, codigo)`. En ningún punto se decía si son el **mismo
campo**. Si son dos, el operador teclea en el equivocado con el cronómetro corriendo.

Un solo campo (pega, escanea o teclea; acepta código o QR firmado, ver V4). Debajo,
la cara del cartón y el veredicto. Y **dos botones distintos**:

- **"Solo consultar"** — no escribe nada. Es la pregunta de todo el evento ("¿este
  cartón va bien?").
- **"Registrar reclamo"** — primario, escribe `reclamado_en` en auditoría. Solo se
  habilita si hay un ganador detectado pendiente.

Sin esta decisión el implementador hace un buscador que además confirma, y la hora
del reclamo —que es la defensa de la tarea 4.24 ante una disputa— se pierde.

### DU-10 — El caso masivo de "a una bola"

Con "cuatro esquinas" o "línea" y 200 cartones, en la bola 40 puede haber sesenta
cartones a una bola. Una lista de sesenta nombres es ruido puro, y aparece
exactamente en el momento de máxima tensión. Y en transmisión, "37" no emociona a
nadie.

- Operador: **cantidad grande siempre**; lista nominal solo cuando `n ≤ 8`. Por
  encima, colapsada tras "Ver los 37".
- Transmisión: el bloque cambia de comportamiento por umbral. `n ≥ 10` → "37 cartones
  a una bola". `n ≤ 3` → tratamiento dramático (número enorme, parpadeo lento). Ahí
  es donde vive la tensión del juego.

### DU-11 — La ronda en curso no se puede destruir con un clic

Verificado: `espacio_evento.py:107` y `:114` conectan **dos** botones
(`_boton_volver`, `_boton_cerrar`) a `cerrado.emit()` **sin ninguna confirmación**, y
`ventana_principal.py:101` y `:116` hacen `deleteLater()` sobre `EspacioEvento`. El
plan resuelve muy bien S5-3 (el motor vive en `EspacioEvento` para sobrevivir al
cambio de sección del riel) y no veía que los dos botones que están tres centímetros
por encima del riel destruyen ese mismo objeto en un clic.

- `EspacioEvento` consulta `repo_ronda.obtener_en_juego` antes de emitir `cerrado`;
  con ronda `en_curso` o `pausada` exige confirmación explícita ("Hay una ronda en
  curso. Se guardará y podrás reanudarla").
- `closeEvent` de la ventana principal hace lo mismo.
- En `modo_vivo`, los dos botones **no se pintan**.

### DU-12 — `modo_vivo`: qué se oculta y qué sobrevive

| Se oculta | Sobrevive |
|---|---|
| Riel de secciones | Franjas de error y de éxito |
| Cabecera del evento (con sus dos botones, DU-11) | Diálogo de empate |
| Franja de marca de la organización | Diálogo de reclamo |
| Selector de monitor y controles de tema | Confirmaciones destructivas (reabrir ronda, cerrar evento) |
| Modales de `ErrorPersistencia`, `ErrorIntegridad`, `ErrorBaseBloqueada` → pasan a franja | Modales **terminales**: base corrupta, migración fallida, sin permisos, `ErrorReanudacion` |

Un modal feo en cámara es mejor que seguir jugando sobre una base rota.

- Se sale con **`F11` o `Esc`**, y se avisa en pantalla la primera vez.
- **Sin estado global.** La bandera es un atributo de `EspacioEvento`;
  `dialogos.confirmar` y `dialogos.mostrar_error_modal` reciben `modo_vivo: bool =
  False` como parámetro explícito. `ui/dialogos.py` son funciones de módulo sin
  estado hoy, y esta fase no va a introducir la primera pieza de estado global de
  interfaz del proyecto sin decirlo en voz alta.

### DU-13 — La transmisión tiene su propio idioma

El §4.15 resuelve el idioma de la locución (`idioma_voz`, independiente de la
interfaz) y no decía nada del **texto pintado** en transmisión (¡BINGO!, "a una
bola", bienvenida, cierre, cuenta regresiva). Si sale por `t()` hereda el idioma de
la interfaz del operador: Gabriel pone la app en inglés para probar algo y el público
ecuatoriano ve "WINNER".

`tema_json.idioma_publico` (por defecto `es`). `ui/transmision/` traduce con ese
idioma, no con el activo.

**Corolario de `retraducir()`:** la ventana de transmisión pinta texto en
`paintEvent`, no en widgets, así que su `retraducir()` es `self.update()` (igual que
`CuadriculaCarton`). Eso **solo funciona si el texto se resuelve en el pintado**, no
cacheado en el constructor. Va escrito, o saldrá una ventana que se queda en el
idioma con el que arrancó.

### DU-14 — Estados de éxito: toda acción de escritura dice qué pasó y dónde

`FranjaError.mostrar_exito` existe desde la fase 4 (`#franjaExito`, decisión DS6) y
la versión anterior del plan no la invocaba ni una vez. El silencio tras una acción
irreversible en directo es el peor estado de todos: el operador la repite.

| Acción | Canal | Texto |
|---|---|---|
| Confirmar ganador | franja éxito | "Ganador confirmado: A-0142 · María Chávez" |
| Cerrar ronda | franja éxito | "Ronda 2 cerrada. Siguiente: Cuatro esquinas" |
| Reabrir ronda | franja info | "Ronda 2 reabierta" (y va a auditoría) |
| Generar acta | franja éxito | "Acta guardada en ‹ruta›" + botones Abrir / Verificar |
| Generar reporte | franja éxito | "Reporte guardado en ‹ruta›" + Abrir carpeta |
| Exportar respaldo | franja éxito | "Respaldo en ‹ruta›" + Abrir carpeta |
| Restaurar respaldo | modal | "Restaurado desde ‹zip›. Copia previa en ‹ruta›" |
| Borrar compradores | franja éxito | "Se eliminaron N registros de compradores" |

### DU-15 — Estados de ocupado en los dos puntos que sí bloquean

- `iniciar_ronda` carga los cartones elegibles, el mapa de compradores y construye el
  índice inverso **en el hilo de interfaz** (D2 solo exime la extracción). Con mil
  cartones eso se ve. Si supera 150 ms: cursor de espera y botón deshabilitado con
  texto "Preparando ronda...".
- `restaurar` (4.12) copia un `%LOCALAPPDATA%` entero y extrae un `.zip`: puede tardar
  minutos. Va en `Tarea` con el patrón exacto de `vista_cartones.py` (barra +
  progreso + cancelar), y con pantalla de resultado que diga qué se restauró, desde
  qué `.zip` y dónde quedó la copia previa. Es especialmente importante porque para
  entonces los datos vivos ya se movieron a `datos.pre-restauracion-‹fecha›`.

### DU-16 — Orden final del riel (ocho secciones, no siete)

D10 enumeraba siete y la tarea 4.19 añade Auditoría, que nadie colocó. Y el orden de
hoy en `registro_vistas.py` no coincide con el de D10.

```
  PREPARACIÓN            EVENTO
  ───────────            ──────
  Datos del evento       Compradores
  Cartones               Rondas
  Plantilla              Sorteo
  Tema                   Auditoría
```

Sorteo es el **último antes de Auditoría** a propósito: bajando con las flechas se
llega a Sorteo sin pasar por encima de una sección de solo lectura.

### DU-17 — Un solo monitor

La degradación cubría "el monitor guardado ya no existe" y no cubría "solo hay una
pantalla" — el portátil del salón, el ensayo, el desarrollo. Un
`FramelessWindowHint` + `showFullScreen()` sobre la única pantalla tapa la interfaz
del operador sin borde, sin barra de tareas y sin salida obvia, en directo.

- Con una sola pantalla, el botón ofrece **modo ventana** (960x540, con borde,
  movible) en vez de pantalla completa.
- Nunca pantalla completa sobre la pantalla que contiene la ventana principal sin
  confirmación explícita.
- `Esc` siempre sale de la pantalla completa de transmisión, documentado en pantalla
  la primera vez.

### DU-18 — Datos personales en la pantalla del operador

El panel de ganadores del §4.8 decía "con datos". La pantalla del operador **se
comparte a veces por OBS**, y la fase 4 ya decidió (UC-3) que teléfono, cédula y
correo solo salen en el Excel con casilla marcada. La misma regla aplica aquí:

- El panel de ganadores muestra **código de cartón y nombre**. Nada más.
- Teléfono, cédula y correo solo tras pulsar "Ver datos de contacto", que los muestra
  en un diálogo y registra la consulta en auditoría.
- El acta lleva **código de cartón**, no nombre (ya estaba en S5-7).


---

## 4. Plan de implementación (task breakdown)

Orden pensado para que cada paso deje la suite verde y algo demostrable.

### 4.0 Semana 0 — los tres spikes, antes de escribir código de la fase (decisión D-gate-1)

Prerrequisito, no riesgo. Los tres llevan dos fases pospuestos y los tres pueden
invalidar trabajo ya escrito o por escribir. Medio día cada uno.

| Spike | Qué produce | Puerta |
|---|---|---|
| **OBS + dos monitores** | 30 líneas de PySide6: ventana sin bordes a pantalla completa en el segundo monitor, capturada por OBS | Si captura en negro o el DPI fraccional desalinea el lienzo, **D14 cambia de ruta antes de escribir 4.9** |
| **Latencia de transmisión** | Emisión privada a Facebook y a YouTube, cronómetro contra el reloj de la pantalla | El número **va impreso en el cartón** (alcance §6.1); alimenta `TEXTO_INFERIOR_DEFECTO`, que hoy dice "que tiene retraso" sin cifra |
| **Imprenta** | Un cartón de una página enviado a cotizar y a prueba de impresión | Este ya llega tarde: debía correr antes del motor de render de la fase 3, ya cerrada. Un rechazo por sangrado, resolución o CMYK es retrabajo de una fase cerrada |

### Hitos de la fase (decisión D-gate-3)

Una sola Fase 5 y un solo entregable (`v1.0.0`, como manda el contrato), con tres
hitos internos etiquetados para que un recorte por calendario sea una decisión escrita
y no la que tome el cansancio a las dos de la mañana.

| Hito | Contenido | Puerta de salida |
|---|---|---|
| **v0.9.0 — jugable** | 4.0 · 4.1-4.9 · 4.17 · 4.21-4.24 · las correcciones críticas (B1, C1-C6, A1-A5) · **humo del `.exe`** | Tres rondas de principio a fin y una reanudación real |
| **v0.9.5 — comprobable** | 4.11 actas · 4.12 respaldos **con restauración probada en un segundo equipo** · 4.19 · 4.20 · 4.25 · 4.26 | El acta verifica y el respaldo restaura |
| **v1.0.0 — presentable** | 4.10 sonido y locución · animación del bombo · bienvenida y cierre · banner · 4.14 instalador definitivo | Ensayo completo firmado |

**El único candidato declarado a recorte es 4.10 (sonido).** El empaquetado no: es
criterio de aceptación, y su prueba de humo sube a v0.9.0.

### 4.1 Migración y modelos (contrato §5.3, §5.6, §5.9)

- `004_fase5.sql` según D3 (sin `BEGIN`/`COMMIT` propios).
- `dominio/modelos.py`: `Extraccion`, `Ganador` con los campos nuevos; `Ronda` gana
  `premio_valor_centavos`, `iniciada_en`, `cerrada_en`, `acta_hash`, `acta_generada_en`.
- `dominio/estados.py`: `TRANSICIONES_RONDA = {pendiente: {en_curso}, en_curso:
  {pausada, cerrada}, pausada: {en_curso, cerrada}, cerrada: {en_curso}}`.
  **`cerrada -> en_curso` existe (hallazgo V5):** cerrar una ronda por error en vivo
  (botón mal pulsado, `Ctrl+Enter` en el panel equivocado) tiene que tener deshacer.
  La reapertura pide confirmación escrita y se registra en auditoría
  (`sorteo.ronda_reabierta`). El alcance §6.6 además promete que un bingo se retoma
  otro día desde la ronda pendiente: sin esta transición, esa promesa es falsa.
- `config/preferencias.py`: `ventana.monitor_transmision` pasa de `int | None` a
  **`str | None`** (hallazgo V7): el §5 promete guardar el monitor por
  `QScreen.name()` porque Windows reordena los índices entre arranques, y el campo
  reservado era un entero. Un `preferencias.json` viejo con un entero se descarta al
  leer y se vuelve a preguntar; no revienta.
- **`_COLUMNAS` de `repo_ronda` NO gana las cuatro columnas nuevas** (hallazgo A1,
  crítico). `repo_ronda.actualizar` escribe *todas* las columnas de `_COLUMNAS` desde
  el objeto en memoria, y `vista_rondas.py` guarda al vuelo con una `Ronda` cargada al
  abrir la sección: tocar el premio de la ronda 3 reescribiría `acta_hash = NULL` de
  la ronda 2 con un valor viejo. Es el mismo fallo de DU-7 (dos editores del mismo
  documento) pero sobre `ronda`. Las cuatro se escriben **solo** con verbos puntuales:
  `actualizar_inicio`, `actualizar_cierre`, `actualizar_acta`.
- `utilidades/errores.py`: **`ErrorReanudacion`** (usada por D13 y DU-12) con su clave
  `sorteo.error.reanudacion_incoherente` en `es.json` **y** `en.json` —
  `test_arquitectura.py::test_claves_i18n_de_errores_existen_en_es_json` falla si no.
- Pruebas: `test_migraciones` sube a la 004 sobre una base con datos de la 003;
  `test_estados` cubre la tabla nueva incluida la reapertura; `test_preferencias`
  cubre el `int` viejo descartado; y **cargar ronda → generar acta →
  `actualizar_ronda` con el objeto viejo → `acta_hash` sigue ahí** (A1).

### 4.2 `dominio/bombo.py` (contrato §5.1)

- `Bombo(rng, ya_extraidas=None)`, **`siguiente() -> int`** (elige sin mutar) y
  **`confirmar(numero)`** (lo saca del bombo), `restantes`, `extraidas`, `agotado`.
- **Por qué en dos pasos, y no un `extraer()` que muta (hallazgo B1, crítico).** Si la
  transacción de la bola falla —`ErrorBaseBloqueada` con `BUSY_TIMEOUT_MS` agotado,
  disco lleno, `ErrorIntegridad`— el `rollback` deja la base sin la bola pero un
  `extraer()` mutante ya la habría eliminado del bombo en memoria: **el número
  desaparece del juego en silencio**, y al reanudar volvería al bombo — dos estados
  distintos según si el operador reinició o no. Peor con `modo_vivo`, que degrada esos
  errores a franja: el operador ve un aviso, vuelve a pulsar Extraer, y el acta que se
  entrega firmada tiene una bola evaporada. `confirmar()` ocurre **después** del
  commit. Prueba obligatoria: inyectar `ErrorBaseBloqueada` en `repo_extraccion.crear`
  y verificar que `bombo.restantes` no cambió.
- `BomboVacio(ErrorBingo)` con clave `sorteo.error.bombo_vacio` queda como **red de
  seguridad de programación, no como camino de usuario** (hallazgo C7): agotar el
  bombo sin ganador es un final de ronda legítimo, no un error. El motor expone
  `bombo.agotado`, la interfaz deshabilita Extraer y ofrece "Cerrar ronda sin
  ganador".
- El `rng` se recibe siempre, nunca se instancia dentro (mismo convenio que
  `dominio/carton.py`): producción `secrets.SystemRandom()`, pruebas `random.Random(1)`.
- Validación del constructor: bolas fuera de 1-75 o repetidas → `ErrorValidacion`.
- Pruebas: no repite en 75 extracciones, se agota exactamente en 75, reconstrucción
  desde una lista previa deja disponibles exactamente el complemento.

### 4.3 `dominio/partida.py` (contrato §5.2)

- `CartonEnJuego(carton_id, codigo, numeros_por_bit)` con `marcado` iniciado en
  `1 << BIT_LIBRE`, `marcar(numero) -> bool`.
- `EstadoPartida`: construye el índice inverso `{numero: [CartonEnJuego]}`,
  `aplicar(numero) -> list[CartonEnJuego]` (solo los tocados),
  `ganadores(mascaras) -> list[CartonEnJuego]`.
- **`a_una_bola` se mantiene incrementalmente, no es un barrido** (hallazgos E-8 y C8).
  Un cartón solo puede *entrar* en "a una bola" si esa bola lo tocó, así que se
  reevalúan solo los tocados y se añaden o se quitan de un conjunto vivo. Un barrido
  completo por bola contradice el contrato §5.2 literal ("evaluación tras cada bola
  únicamente sobre los cartones que se marcaron en esa jugada"). La prueba `lento`
  asserta el **número de evaluaciones**, no solo el tiempo.
- `es_ganador` y `faltan` se **reexportan** de `dominio/patron.py`, no se reescriben.
- Detalle del espacio libre: si el patrón no usa el bit 12 (`usa_libre=False`) el bit
  libre encendido sobra y no estorba — `marcado & m == m` lo ignora. Ya cubierto por
  `usa_libre_incoherente`.
- Pruebas: índice inverso toca solo los cartones que contienen la bola; ganador
  positivo/negativo con y sin espacio libre; `a_una_bola` cuenta bien con multi-máscara.

### 4.4 Persistencia (contrato §5.3, §5.6, §5.7)

- `repo_extraccion.py`: `crear(con, extraccion)`, `listar_por_ronda(con, ronda_id)`
  (ordenado por `orden`), `contar_por_ronda`, `numeros_por_ronda -> list[int]`,
  `eliminar_por_ronda`.
- `repo_ganador.py`: **`crear_si_no_existe(con, ganador) -> Ganador | None`** (`None`
  cuando ya existía), no `crear`: con `INSERT OR IGNORE`, `lastrowid` no corresponde a
  nada cuando la fila se ignora, y la tabla de verbos de `docs/convenciones-codigo.md`
  promete que `crear` devuelve el modelo con `id` asignado (hallazgo E-3). El verbo
  nuevo se añade a esa tabla, que es la fuente de verdad. Además `listar_por_ronda`,
  `listar_por_evento`, `obtener`, `actualizar_decision`, `anular`,
  `contar_confirmados_por_ronda`.
- `repo_ronda.py`: `actualizar_estado(con, ronda_id, estado)`, `listar_por_estado`,
  `obtener_en_juego(con, evento_id) -> Ronda | None` (la que esté `en_curso`/`pausada`).
- `repo_evento.py`: `actualizar_juego(con, evento_id, clave, valor)` — escritura de
  campo puntual sobre `tema_json` con `json_set` (DU-7). **Con
  `COALESCE(tema_json, '{}')`** (hallazgo E-13): un evento que nunca abrió la sección
  Tema tiene `tema_json` a `NULL`, y `json_set(NULL, ...)` devuelve `NULL` — el ajuste
  se perdería en silencio. Verificado que SQLite 3.49.1 trae `json_set`.
- Verbos exactamente los de la tabla de `docs/convenciones-codigo.md`; SQL solo aquí.

### 4.5 `utilidades/log_partida.py` (contrato §5.9)

- `LogPartida(ruta)` con `abrir()`, `linea(texto)` que hace `write` + `flush()` +
  `os.fsync()`, `cerrar()`. Formato: `ISO8601\torden\tnumero\tevento`.
- Ruta: `dir_logs_evento(evento_id)/ronda-<id>.log`.
- Es la tercera fuente de verdad (doc técnico §10): si la base falla, el acta se puede
  reconstruir de aquí. Por eso `fsync` y no solo `flush`.
- **Enmienda al doc técnico §6.2 (hallazgo S5-6):** el documento lista la escritura
  del log como paso 4 *dentro* de la transacción de la bola. Se cambia a **después
  del commit**. Razón: `fsync` sobre un disco lleno o una carpeta borrada lanza
  `OSError` dentro de la transacción y tumbaría el commit — el respaldo de última
  instancia haría caer la fuente primaria. Un `OSError` del log se registra como
  advertencia, se avisa una vez por ronda con una franja, y el sorteo sigue.
- Prueba: matar el objeto sin `cerrar()` y verificar que las líneas escritas están en
  disco; simular `OSError` en `linea()` y verificar que la extracción ya está
  persistida y el sorteo continúa.

### 4.6 `servicios/servicio_sorteo.py` (contrato §5.3, §5.7) — el corazón

`MotorSorteo`, sin Qt, con callbacks (D1):

- `iniciar_ronda(con, ronda_id)`: valida transición, carga cartones elegibles
  (`vendido` + comprador vivo), construye `EstadoPartida` y `Bombo`, `UPDATE ronda`
  a `en_curso` con `iniciada_en`, abre el `LogPartida`, dispara `al_cambiar_ronda`.
- `extraer(con)`: **una** `transaccion()` con `INSERT extraccion` → detectar →
  `INSERT OR IGNORE ganador` (confirmado=0) → `UPDATE ronda` si corresponde. Commit.
  **Después** del commit: `LogPartida.linea()` (S5-6) y luego los callbacks
  `al_extraer`, `al_detectar_a_una_bola`, `al_detectar_ganadores`.
- **Dueño del motor (hallazgo S5-3):** la instancia vive en `EspacioEvento`, no en
  `VistaSorteo`. Cambiar de sección del riel a mitad de ronda no puede destruir la
  partida. `VistaSorteo` la recibe por constructor, igual que recibe `con` y `evento`.
- `pausar` / `reanudar` / `cerrar_ronda(con, ronda_id)` validando `TRANSICIONES_RONDA`.
- `reanudar_ronda(con, ronda_id)`: la reconstrucción y la verificación de D13.
  Devuelve `ResultadoReanudacion(coherente: bool, detectados, persistidos)`.
- Modo automático: **no** hay `QTimer` aquí (sería Qt). El motor expone
  `intervalo_seg` y el puente de `ui/` es quien tiene el temporizador.

Pruebas (sin `QApplication`): sorteo completo de 75 bolas; matar el proceso simulado
(cerrar la conexión) tras la bola N y comprobar que `extraccion` tiene exactamente N
filas; reanudar y comprobar que el `marcado` de cada cartón es idéntico al de antes;
un cartón no `vendido` nunca aparece en `ganadores`.

### 4.7 `servicios/servicio_ganadores.py` (contrato §5.6)

- `validar_reclamo(con, ronda_id, codigo) -> Reclamo` con
  `(carton, comprador, marcado, cumple: bool, motivo_rechazo: clave_i18n | None)`.
  Rechaza: código inexistente, cartón no `vendido`, sin comprador vivo, patrón no
  cumplido con las bolas extraídas **hasta ese momento**.
- `confirmar(con, ganador_id, decision, nota=None)` — `unico` | `reparto` |
  `desempate_externo` | `no_reclamado` | `rechazado`. Escribe `confirmado`,
  `confirmado_en`, `decision`, y **siempre** `repo_auditoria.registrar`.
- **Reclamo por QR además de por código tecleado (hallazgo V4).**
  `dominio/firma.py::verificar_qr` existe desde la fase 3 y su docstring dice
  literalmente que la fase 5 lo necesita. `validar_reclamo` acepta las dos entradas.
  **La regla de desempate es por el separador `|`, no por el resultado (hallazgo S1,
  alto):** `verificar_qr` devuelve `None` tanto para "no tiene formato de QR" como
  para "la firma es inválida". Si el fallback ante `None` fuese "tratarlo como código
  tecleado", entonces `A-0142|00000000` **pasaría igual** usando la parte anterior al
  `|`, y el HMAC no validaría nada. Por tanto: si el texto **contiene `|`**, una firma
  inválida es **rechazo duro** con motivo propio (`ganador.error.qr_invalido`), nunca
  degradación a código tecleado. Si no contiene `|`, es código tecleado.
  **Y se escribe en `docs/decisiones.md` qué NO prueba el QR:** `LONGITUD_HMAC = 8`
  son 32 bits, y el código tecleado se acepta igual de todos modos, así que el QR es
  un **antifaltas de tipeo**, no una prueba de posesión. Que nadie lo presente ante
  una disputa como si autenticara al reclamante.
- **Empate := misma `extraccion.orden` (hallazgo V2).** Con `sin_reclamo="continuar"`
  (el valor por defecto de D8) la ronda sigue extrayendo, así que quien completa el
  patrón en la bola 51 acaba en la misma tabla que quien lo completó en la 42.
  `resolver_empate` **rechaza** repartir entre detecciones de bolas distintas salvo
  confirmación explícita del operador, que se registra en auditoría con el motivo. La
  UI agrupa la lista de ganadores por bola de detección, con encabezado, y ordena de
  la más temprana a la más tardía.
- `resolver_empate(con, ronda_id, ids_reparto | id_ganador)` en una transacción:
  todos los detectados quedan con su `decision` explícita, ninguno en limbo.
- Pruebas: cada motivo de rechazo, reclamo por QR válido y por QR de otro evento,
  empate real (misma bola) con reparto entre tres, empate real con desempate externo,
  intento de reparto entre bolas distintas (debe exigir confirmación), no reclamado
  según los dos valores de `sin_reclamo`.

### 4.8 `ui/sorteo/` — la superficie del operador (contrato §5.5, §5.6)

- `puente_sorteo.py`: `PuenteSorteo(QObject)` con las cinco señales de §6.4 y el
  `QTimer` del modo automático. **De un solo disparo, rearmado al terminar cada
  extracción** (hallazgo E-14), no de intervalo fijo: con un disco lento, un
  temporizador periódico encola disparos mientras la extracción anterior sigue en
  curso. El patrón de rearme elimina el encolado por construcción.
- `vista_sorteo.py`: sección del riel (D9). **Jerarquía explícita, no una lista plana
  de paneles** (ver el diagrama del §B.1): dos columnas, no una pila de `QGroupBox`.
  - *Primario:* la bola actual (~96 px) con las cuatro anteriores debajo, y el botón
    **Extraer** con el objetivo de pulsación más grande de la aplicación (≥ 64 px de
    alto: se pulsa a ciegas, mirando a la cámara) más el contador `N / 75`.
  - *Secundario:* panel de a-una-bola (cantidad + códigos + compradores) y panel de
    ganadores, que **se apodera del área y cambia el borde a `_EXITO`** cuando
    aparece. Debajo, el tablero de 1-75 con las cantadas.
  - *Terciario:* cabecera con ronda/patrón/premio, buscador por código **siempre
    activo** que pinta `CuadriculaCarton` con `marcados` y `patron_resaltado` y dice
    si cumple, selector de monitor, mostrar/ocultar transmisión, **Modo en vivo**.
  - **Los paneles vacíos no se pintan.** Ni el de a-una-bola ni el de ganadores
    existen mientras estén vacíos — nada de "Ningún ganador todavía" en gris. Que
    aparezcan *es* la señal; un contenedor permanente vacío entrena al ojo a ignorar
    justo la zona donde luego aparece lo único urgente.
  - **La sección Sorteo no lleva Guardar/Cancelar.** No edita entidades, ejecuta
    acciones: la convención DS14 no le aplica. Se escribe para que nadie herede por
    inercia el atajo de `vista_rondas.py`.
  - Botones Iniciar / Pausar / Reanudar / Cerrar / Siguiente ronda, agrupados aparte
    del de Extraer para que no se pulsen por error en directo.
- `dialogo_empate.py`: listado de ganadores, elegir uno o repartir entre varios.
- Atajos (registro de D12, ámbito `sorteo`): `Espacio` extraer, `P` pausar/reanudar,
  `Ctrl+F` buscar, `Ctrl+Enter` confirmar ganador seleccionado, `F11` modo en vivo,
  `R` repetir la locución del número actual.
- **Estado vacío (hallazgo S5-16):** si no hay ninguna ronda jugable (evento en
  borrador, sin cartones vendidos, sin rondas configuradas), la sección no muestra
  controles muertos: reusa `servicio_rondas.validar_evento_listo` y lista qué falta,
  con el mismo texto que el chip de la cabecera del evento.
- **Doble clic (hallazgo S5-9):** "Extraer bola" se deshabilita al pulsar y se
  rehabilita cuando termina la animación. Además `tema_json.juego.confirmar_extraccion`
  añade una confirmación explícita para quien la quiera.
- Prueba `pytest-qt`: iniciar ronda, extraer diez bolas, verificar que el tablero y el
  contador coinciden; buscar un código y verificar el veredicto; pulsar Extraer dos
  veces seguidas y verificar que sale **una** bola.

### 4.9 `ui/transmision/` — la ventana pública (contrato §5.4)

- `ventana_transmision.py`: `Qt.FramelessWindowHint`, `showFullScreen()` sobre el
  `QScreen` elegido (fijar `setGeometry(screen.geometry())` **antes** de
  `showFullScreen()`; poner solo `setScreen()` no reubica en Windows).
- **`pantallas.py::elegir_pantalla(nombres_disponibles, nombre_guardado) -> Decision`
  (hallazgo E-9).** Función **pura**, sobre una lista de nombres, sin Qt. La vista la
  llama con `[s.name() for s in QGuiApplication.screens()]`. Sin esta costura, toda la
  lógica de DU-17 (una sola pantalla, monitor guardado que desapareció, modo ventana)
  quedaría sin cubrir: `tests/conftest.py` fija `QT_QPA_PLATFORM=offscreen` y no hay
  pantallas reales que elegir. Con ella, los cuatro casos se prueban sin un monitor.
- `bloques.py`: un pintor por bloque — bombo animado, número actual, tablero 75,
  patrón activo (reusa `rejilla_patron`), imagen del premio, logo, contador, reloj,
  banner corrido, aviso de ¡BINGO!, pantalla de bienvenida, pantalla de cierre.
- **Regla que no se negocia:** el aviso de BINGO muestra el patrón completado y nada
  más. Código y nombre solo tras `ganador_confirmado`. Se prueba.
- **Suelo de legibilidad (§B.1).** El público no ve 1920x1080: ve unos 400 px de
  ancho en un teléfono, comprimidos por la plataforma. A ese tamaño solo cabe **un**
  elemento primario, y es el número actual.
  - `dominio/tema.py::validar` exige que `numero_actual` no baje del 14% del alto del
    lienzo (≈150 px sobre 1080). Por debajo, `ErrorValidacion`.
  - El editor trae un preset **"Legible en celular"** como valor por defecto, con
    botón para volver a él.
  - La vista previa gana **"Ver como celular"**: la reescala a la proporción de un
    móvil viendo la transmisión. Es la única forma de que el operador vea el problema
    antes del evento y no durante.
  - Nada de texto fino sobre la imagen de fondo: el bloque del número actual lleva
    fondo sólido u opaco detrás. La compresión de vídeo destruye texto delgado sobre
    textura.
  - Números con **cifras tabulares** y peso alto de la familia ya empaquetada (G24):
    el número cambia cada seis segundos y no debe bailar.
- **La ventana de transmisión nunca recibe foco de teclado**
  (`Qt.WindowDoesNotAcceptFocus`): un `Alt+F4` accidental en directo no puede
  matarla, y el foco no se escapa de la superficie del operador.
- **Contraste (§B.5):** `ui/tema.py::contraste()` ya está escrita y no la llama nadie.
  El editor de tema la usa para avisar en línea si `texto` sobre `fondo` o
  `numero_actual` sobre `fondo` bajan de 4.5:1. Avisa, no bloquea (puede haber una
  imagen de fondo detrás); el preset por defecto siempre pasa.
- **El tablero de 75 no distingue las cantadas solo por color:** cambia fondo **y**
  peso tipográfico. Daltonismo, y compresión de vídeo.
- `escala.py`: `QTransform` de 1920x1080 al tamaño real, con barras si la relación no
  es 16:9.
- **Rendimiento (hallazgo S5-11):** el tablero de 75 celdas se pinta en un `QPixmap`
  cacheado que solo se regenera cuando cambia una bola; la animación a 60 Hz invalida
  únicamente los rectángulos del bombo y del número actual, nunca la pantalla entera.
- Cierre de la ventana de transmisión no cierra el sorteo, y cerrar la principal sí
  cierra la de transmisión.
- Prueba: con `ganadores_detectados` emitido, el texto pintado no contiene ni el código
  ni el nombre (se verifica sobre el modelo del bloque, no sobre píxeles).

### 4.10 Sonido y locución (contrato §5.8)

- **Un solo `ui/sonido.py`** (hallazgo S5-2), no un paquete de tres módulos: son tres
  clases pequeñas con el mismo ciclo de vida (nacen al entrar en modo vivo, mueren al
  salir) y ninguna se usa sin las otras.
  - `Efectos`: `QSoundEffect` para los tres WAV de D6, con volumen y `activado`.
    Esperar `statusChanged == Ready` antes del primer `play()` — un `QSoundEffect`
    recién construido no suena.
  - `Musica`: `QMediaPlayer` + `QAudioOutput`, archivo elegido por el operador,
    bucle, volumen independiente.
  - `ProveedorLocucion` / `LocucionTTS` / `LocucionPregrabada` de D5. Fijar el
    **locale antes** de pedir voces: `availableVoices()` solo devuelve las del locale
    activo (medido: con `winrt` en es_ES no aparece ninguna voz inglesa, con `sapi`
    tras fijar en_US sí).
- `scripts/generar_sonidos.py`: genera los tres WAV con `wave` + `math`. Se corre una
  vez; los `.wav` se versionan y se declaran en `package-data`.
- Todo desactivable desde `tema_json.juego` y desde la vista de sorteo.
- Prueba: con `sonido_bola=False` y `voz=False` no se instancia ningún objeto de audio
  (importante: en un equipo sin tarjeta de sonido, instanciar `QSoundEffect` avisa por
  consola).

### 4.11 Actas y reportes (contrato §5.9)

- `dominio/acta.py`: `carga_canonica(...)` y `hash_acta(...)` según D7. Dominio puro.
  **La carga empieza por `acta/v1` (hallazgo E-5):** si el formato cambia en una v1.1,
  todas las actas ya emitidas dejarían de verificar y el verificador empezaría a decir
  "no coincide" sobre documentos legítimos. El verificador lee la versión del propio
  documento para elegir el serializador. Es una línea hoy y una crisis evitada
  después.
- `impresion/acta.py`: `escribir_acta_pdf(ruta, datos, textos)` — cabecera con
  organización y evento, patrón dibujado, premio, secuencia completa de bolas en
  cuadrícula, ganadores con código y decisión, hash al pie en monoespaciada.
- `impresion/reporte.py`: `reporte_evento_excel` y `reporte_evento_pdf` — cartones
  generados/vendidos/recaudación, rondas con ganadores, contactos de ganadores.
  Reusa `_escribir_seguro`; la casilla "incluir datos de contacto" se hereda del
  criterio de la fase 4 (UC-3), desmarcada al abrir.
- `servicios/servicio_actas.py`: orquesta, guarda `acta_hash`/`acta_generada_en`,
  registra en auditoría. Ruta: `dir_impresos_evento(evento_id)/acta-ronda-<orden>.pdf`.
- **Reabrir una ronda cuyo acta ya se generó (hallazgos E-16 y C6).** V5 permite
  `cerrada -> en_curso`; si se reabre y se extraen más bolas, el verificador de 4.20
  diría **"no coincide"** sobre un documento que la organización ya tiene firmado en
  la mano, sin explicar por qué. Reabrir con `acta_hash` no nulo: confirmación con
  texto explícito ("Ya se generó el acta de esta ronda. Si la reabres, el acta impresa
  dejará de corresponder"), **pone `acta_hash = NULL`**, registra
  `sorteo.acta_invalidada` en auditoría, y la franja lo dice.
- **El nombre del archivo va por `ronda_id`, no por `orden` (hallazgo C6).** `orden`
  es mutable (`repo_ronda.actualizar_orden`, `servicio_rondas.reordenar`): con
  `acta-ronda-<orden>.pdf`, reordenar rondas hace que el acta de una **sobrescriba**
  la de otra. Formato: `acta-<ronda_id>-<AAAAMMDD-HHMMSS>.pdf`, y nunca se borra la
  anterior.
- Prueba: el acta de la misma ronda generada dos veces da el mismo hash; el PDF abre
  con `pypdf` y tiene las páginas esperadas; el Excel no interpreta un nombre que
  empieza por `=`.

### 4.12 Respaldos (contrato §5.10)

- `servicios/servicio_respaldos.py`: **`exportar(evento_id, destino, *,
  al_progresar=None, debe_cancelar=None)` — sin `con` (hallazgo B2, crítico).**
  `conexion.py` abre con `check_same_thread=True` y el convenio de `ui/tarea.py` dice
  que **el invocable abre su propia conexión dentro de la llamada**. Pasar `con` a un
  `Tarea` revienta con *"SQLite objects created in a thread can only be used in that
  same thread"* — justo en la única función cuyo propósito es salvar el evento. Es la
  única función de la fase que rompe la regla de "`con` va siempre primero", y la
  rompe **porque corre en otro hilo**; se documenta como excepción explícita en
  `docs/convenciones-codigo.md`. `sqlite3.Connection.backup()` a un archivo temporal (seguro con la
  base abierta y en WAL), luego `.zip` con la base, `medios/<evento>/`,
  `logs/<evento>/`, `impresos/<evento>/` y el `RESPALDO_LEEME.txt` de D11.
  Nombre: `respaldo-<clave_evento>-<AAAAMMDD-HHMMSS>.zip` en `dir_respaldos()`.
- Corre en `Tarea`.
- **Bloqueado mientras haya ronda `en_curso` o `pausada` (hallazgo E-1, crítico).** La
  API de respaldo en línea de SQLite **reinicia la copia** cuando la base de origen se
  modifica desde otra conexión. Un respaldo lanzado en un `Tarea` (conexión propia, por
  convención) mientras la interfaz escribe una bola cada seis segundos es una copia que
  se reinicia indefinidamente sobre una base de decenas de MB: no falla, no termina.
  El botón se deshabilita con el motivo. No es una limitación molesta: los dos
  recordatorios ya caen donde no hay ronda viva.
- Recordatorios: al pulsar Iniciar ronda de la primera ronda del evento, y al cerrar el
  evento. No modal bloqueante en `modo_vivo` — franja con acción.
- **`restaurar(ruta_zip)` — hallazgo C1, crítico.** Sin esto el respaldo no es un
  respaldo, es un archivo. Y no es teórico: `docs/runbook.md:9` **ya le promete al
  operador**, en el código de salida 3 (base corrupta), "restaurar el `.zip` más
  reciente de `respaldos\`" — una instrucción que hoy no tiene forma de ejecutarse.
  El alcance §8 acepta "equipo único" con la mitigación "guardado tras cada bola,
  log en archivo y respaldo manual": dos tercios son reales, el tercero no existe.
  - `python -m bingo --restaurar <zip>`: valida el `.zip`, comprueba que la versión
    de esquema de la base contenida es **menor o igual** que la que el binario sabe
    migrar, hace copia de lo que haya en `%LOCALAPPDATA%\Bingo` a
    `datos.pre-restauracion-<fecha>`, extrae, y arranca normal (las migraciones
    corren solas si la base venía de una versión anterior).
  - **Contra zip-slip (hallazgo E-2, crítico).** El `.zip` es un archivo que el
    operador pudo recibir por WhatsApp. Nada de `extractall` a secas: extracción
    miembro a miembro, y cada uno se acepta solo si
    `Path(destino, nombre).resolve()` queda **dentro** de `destino.resolve()`. Se
    rechazan rutas absolutas, `..`, letras de unidad y todo miembro que no sea archivo
    regular. Prueba con un `.zip` malicioso construido en la propia prueba.
  - **Validar el `.zip` ENTERO antes de tocar un solo archivo (hallazgo B4, crítico).**
    El orden original era el peligroso: mover los datos vivos y *después* validar, con
    lo que un `.zip` corrupto dejaba al operador sin datos y sin restauración.
    Secuencia correcta: abre con `zipfile` → contiene `datos/bingo.db` → ese archivo
    abre con `abrir_conexion` → su `schema_version` es **≤** la máxima que este
    binario sabe aplicar → solo entonces se mueve nada.
  - **Solo desde la CLI, con la aplicación cerrada (hallazgo B4).** "Sin evento
    abierto" no basta: el proceso sigue teniendo `bingo.db` abierto, `.bingo.lock`
    tomado por `QLockFile` y `aplicacion.log` abierto por el `RotatingFileHandler`.
    En Windows eso es `WinError 32` a mitad de camino, con la base movida y los medios
    no. El botón de Ajustes **no restaura**: cierra la conexión, suelta el
    `QLockFile`, cierra los handlers de log y **relanza el proceso** con `--restaurar`.
  - **Orden en `__main__.py` (hallazgo E-11).** `--restaurar` corre **antes** del
    `QLockFile` y **antes** de `abrir_conexion`. Secuencia: argumentos →
    `asegurar_estructura` → **validar el zip** → **restaurar** → log → preferencias →
    i18n → `QLockFile` → `abrir_conexion` → migraciones. Si el `QLockFile` ya está
    tomado por otra instancia, `--restaurar` se niega a continuar.
  - **`__main__.py` necesita `argparse` y un código de salida nuevo (hallazgo B4).**
    Hoy solo comprueba banderas con `in argv`, y no sabe leer `--restaurar <valor>`.
    Los códigos 0/2/3/4/5 están ocupados: la restauración fallida sale con **6**, y se
    documenta en `docs/runbook.md` junto a los otros cinco.
  - **`asegurar_estructura()` no crea `impresos/` ni `logs/<evento_id>/`** (hallazgo
    P5): crea `datos`, `logs`, `respaldos` y `medios` y nada más. `LogPartida` (4.5) y
    el acta (4.11) escriben ahí. Un `mkdir(parents=True, exist_ok=True)` olvidado es un
    `OSError` en la primera bola.
  - También desde la interfaz, en Ajustes, con la aplicación sin evento abierto.
  - **Criterio de aceptación nuevo, que el contrato no traía:** el `.zip` de un
    evento tomado a mitad de ronda se restaura en un segundo equipo limpio y el
    sorteo continúa en la bola N+1. Esto es lo que cierra el punto de fallo "equipo
    único" y lo que `TODOS.md` P2 pide desde la fase 1.
- Prueba: el `.zip` contiene la base; abrirla con `abrir_conexion` da las mismas filas
  de `carton` que la original; cancelar a mitad no deja `.zip` parcial; exportar a
  mitad de ronda y restaurar en un `BINGO_HOME` limpio deja `extraccion` con las
  mismas N filas y el `marcado` reconstruido idéntico.

### 4.13 Cierre del evento (contrato §5.9, criterios de aceptación)

- `servicio_eventos.finalizar_evento(con, evento_id)`: exige todas las rondas
  `cerrada`, escribe `en_curso -> finalizado`, registra en auditoría, ofrece generar
  reporte y respaldo.
- Pantalla de cierre en transmisión con su texto configurable.

### 4.14 Empaquetado y distribución (contrato §5.11)

- `empaquetado/bingo.spec` — PyInstaller `--onedir`. `datas` explícitos: `*.sql` de
  migraciones, `i18n/*.json`, `recursos/fuentes/**`, `recursos/sonidos/*.wav`.
  `hiddenimports` para los módulos de PySide6 que se cargan por nombre
  (`QtMultimedia`, `QtTextToSpeech`, `QtPdf`).
- `empaquetado/instalador.iss` — Inno Setup: accesos directos, desinstalador,
  **no** crea `%LOCALAPPDATA%\Bingo` (lo hace `asegurar_estructura()` en el primer
  arranque, que ya existe y ya está probado; duplicarlo en el instalador crea dos
  dueños de la misma estructura).
- Versión: fuente única de D12, visible en Ajustes, registrada en auditoría al abrir
  un evento (`app.version`).
- `docs/runbook.md`: sección de instalación y actualización.
- **`empaquetado/humo.py` — prueba de humo del binario, en la SEMANA 1** (hallazgo
  E-12). Todo el plan de pruebas corre sobre el árbol de fuentes; el criterio de
  aceptación "el instalador deja la aplicación funcionando en un equipo limpio sin
  Python" no lo cubre ni una sola prueba automática. El script arranca el `.exe` con
  `BINGO_HOME` en una carpeta temporal y verifica: código de salida 0, la base llegó a
  la versión de esquema esperada, las fuentes y los `.wav` se cargaron, y
  `QtMultimedia`/`QtTextToSpeech`/`QtPdf` importan **dentro** del binario. Va en la
  semana 1 y no en la última: PyInstaller con estos módulos es célebre por fallar
  tarde, y empaquetar es criterio de aceptación.
- **`empaquetado/actualizacion.py` — prueba de actualización sobre datos**: crea una
  base con la 003 y datos, corre el binario nuevo, verifica que llega a la 004 sin
  perder filas y que dejó la copia `pre-3`. Es el criterio de aceptación "las
  migraciones se aplican bien al actualizar sobre una instalación existente con datos"
  y no se puede cubrir con `pytest` sobre el árbol de fuentes.

### 4.15 i18n

- Claves nuevas bajo `sorteo.*`, `transmision.*`, `acta.*`, `respaldo.*`, `ganador.*`.
  Estimación: ~120 claves, en `es.json` **y** `en.json` (hoy 478/478; el desbalance lo
  detecta `tests/test_i18n.py`).
- Los números de la locución **no** son claves i18n: los dice el TTS con el locale, no
  `t()`.

### 4.16 Pruebas (contrato §5.12)

Además de las de cada tarea:

- `tests/dominio/test_bombo.py`, `test_partida.py`, `test_acta.py`.
- `tests/servicios/test_servicio_sorteo.py` — incluye la reanudación interrumpida en
  la bola N (parametrizada N ∈ {1, 15, 40, 74}).
- `tests/servicios/test_servicio_ganadores.py`, `test_servicio_respaldos.py`,
  `test_servicio_actas.py`.
- `tests/ui/test_vista_sorteo.py`, `test_ventana_transmision.py` (no revela datos).
- `tests/persistencia/test_repo_extraccion.py`, `test_repo_ganador.py`.
- Marcadas `lento`: sorteo de 75 bolas con 1.000 cartones (medir la bola), respaldo de
  una base con 10.000 cartones.
- **Ensayo completo manual**, con guion escrito en `docs/Fase_5/Ensayo.md`: evento de
  prueba (`--ensayo`, tarea 4.17), 200 cartones, tres rondas con patrones distintos,
  dos monitores, OBS capturando, cierre forzado a mitad de ronda. Es un criterio de
  aceptación, no un extra. **Corregido por el hallazgo V9:** la versión anterior de
  esta tarea había perdido dos cosas que el contrato sí pide y que no son detalles:
  - **Emisión privada real** a un canal de Facebook y otro de YouTube, no solo "OBS
    capturando" en local.
  - **Medir el retraso de la plataforma** con cronómetro contra el reloj de la
    pantalla de transmisión. Ese número, según el alcance §6.1, **va impreso en el
    cartón**; hoy `impresion/plantilla.py::TEXTO_INFERIOR_DEFECTO` dice "que tiene
    retraso" sin cifra, con un comentario que reconoce que el spike sigue pendiente.
    El resultado del ensayo alimenta ese texto.
  - **Gabriel presenta de verdad**, no solo opera. El diseño entero de 4.8 (una
    sección del riel, modo en vivo, atajos) descansa sobre la premisa no declarada
    de que una sola persona puede presentar frente a cámara, operar la app, vigilar
    WhatsApp, validar códigos y decidir empates a la vez. El ensayo es el único sitio
    donde esa premisa se puede probar.
  - **Restauración en un segundo equipo** (criterio nuevo de 4.12) y **caso de
    evento suspendido y retomado** (hallazgo V5).
  - **Legibilidad en celular (hallazgo V8):** el guion fija el alto mínimo del número
    actual como fracción del lienzo, y exige adjuntar una captura del móvil viendo
    la emisión privada como evidencia. Es el único criterio del contrato que depende
    de una percepción; sin método escrito, no es verificable.

### 4.17 Modo ensayo — expansión E1 (criterio de aceptación §5.12)

- `python -m bingo --ensayo` crea (si no existe) una organización y un evento de
  prueba, genera 200 cartones, los marca vendidos por rango con compradores
  provisionales, y configura tres rondas con patrones distintos. Idempotente.
- Reusa `servicio_organizaciones`, `servicio_cartones.generar_lote`,
  `servicio_compradores.marcar_vendidos_por_rango` y `servicio_rondas.crear_ronda`.
  No escribe SQL propio.
- Es lo que hace que el ensayo completo del contrato se pueda repetir en un minuto en
  vez de montarse a mano una sola vez.
- Prueba: correr `--ensayo` dos veces deja exactamente un evento de prueba.

### 4.18 Fondo transparente / croma — expansión E2

- `tema_json.colores.fondo` acepta el valor especial `"transparente"`, y un campo
  `croma` con el color plano (verde por defecto) para quien componga en OBS con
  filtro de croma.
- Un bloque adicional de una casilla en `vista_tema.py`.

### 4.19 Panel de auditoría del evento — expansión E3 (cierra deuda de la fase 4)

- Sección de solo lectura en el riel (grupo *Evento*): tabla con momento, acción y
  detalle, filtro por prefijo de acción, exportable a `.xlsx` con `_escribir_seguro`.
- `repo_auditoria.listar_por_evento` ya existe; no hace falta SQL nuevo.
- Es la respuesta de la Sección 8 (observabilidad) a "un problema reportado tres
  semanas después, ¿se puede reconstruir?".

### 4.20 Verificador de acta — expansión E4

- Botón "Verificar acta" en la sección Sorteo: recalcula `carga_canonica` desde la
  base y la compara con `ronda.acta_hash`. Tres resultados posibles: coincide, no
  coincide (con el detalle de qué cambió), o no hay acta generada.
- Sin esto el hash del acta es decoración. Con esto, la organización puede verificar
  el documento que tiene en la mano.

### 4.21 `dominio/tema.py::BLOQUES` — corrección S5-1 (DRY)

- La tabla de bloques (clave, `clave_i18n`, ancho y alto fraccionarios por defecto)
  se declara **una vez** en `dominio/tema.py` y la consumen tanto
  `vista_tema.py::_LienzoPrevia` como `ui/transmision/bloques.py`.
- Sin esto, la vista previa del tema y la pantalla real divergen el día que alguien
  añada un bloque en un solo sitio. Es literalmente la promesa del editor de tema
  ("lo que configuras es lo que sale").

### 4.22 Copia previa a la migración — corrección S5-14 (reversión)

- Antes de aplicar cualquier migración pendiente, `aplicar_migraciones` hace
  **`PRAGMA wal_checkpoint(TRUNCATE)` y luego** copia `bingo.db` a
  `bingo.db.pre-<version_actual>` (una sola copia por versión; si ya existe, no la
  pisa).
- **El checkpoint no es opcional (hallazgo B5, crítico).** En WAL los datos
  confirmados pueden estar íntegramente en `bingo.db-wal`; copiar solo `bingo.db`
  produce **una copia de seguridad vacía o rancia** — precisamente el mecanismo de
  reversión que existe para la noche del evento. El propio repositorio ya lo tiene
  documentado: `tests/conftest.py:60-63` lo hace y explica por qué. El `.execute` del
  PRAGMA vive en `persistencia/`, que es donde la prueba de arquitectura lo permite.
- Prueba: base con tres filas insertadas y sin cerrar → copia previa → **la copia
  tiene las tres filas**.
- Sin esto no hay vuelta atrás: si la 004 corre y la versión nueva falla en el equipo
  del operador la noche del evento, la base ya migró y el instalador anterior no la
  entiende.
- `docs/runbook.md` documenta el procedimiento de reversión en tres pasos.
- Prueba: aplicar la 004 sobre una base con datos de la 003 deja el archivo
  `pre-3` con el contenido íntegro anterior.

### 4.23 Bloqueo de venta con ronda en curso — corrección S5-4

- **Cinco funciones, no tres (hallazgo C5).** Además de `registrar_manual`,
  `aplicar_importacion` y `marcar_vendidos_por_rango`, también
  `servicio_compradores.anular_venta` y `servicio_cartones.cambiar_estado_carton`.
  Anular una venta a mitad de ronda deja el cartón fuera de la elegibilidad **en la
  base** pero dentro del índice inverso **en memoria**: podría ganar un cartón que ya
  no está vendido, que es justo el criterio de aceptación del contrato. El §6 compra
  ese criterio con "carga solo elegibles", y eso solo es cierto en el instante de
  `iniciar_ronda`.
- Sin esto, un cartón vendido a mitad de ronda queda fuera del índice inverso: pagó
  y no puede ganar, **en silencio**. Es el peor tipo de fallo que puede tener este
  producto.
- **Bloqueo solo con ronda `en_curso`, NO con `pausada` (hallazgo C4).** La versión
  anterior bloqueaba las dos, y eso creaba un escenario peor que el que arregla: se
  vende en la puerta, no da tiempo a registrar, se inicia la ronda, y **ya no se
  puede registrar a nadie hasta cerrarla**; quien reclame será rechazado por "no
  vendido". Con la ronda `pausada` sí se registra, y al **reanudar** el motor
  reconstruye el índice inverso y aplica las bolas ya extraídas a los cartones
  nuevos — es determinista, D13 ya hace exactamente eso.
- **Y `iniciar_ronda` con cero cartones elegibles lanza `ErrorValidacion`, siempre**
  (hallazgo C4). `servicio_rondas.validar_evento_listo` marca "sin vendidos" como no
  bloqueante a propósito (se vende en la puerta), pero arrancar un sorteo donde nadie
  puede ganar no es un caso de uso.
- Pruebas: vender con ronda `en_curso` falla en las cinco funciones; con `pausada`
  funciona y el cartón nuevo participa tras reanudar; con `cerrada` funciona;
  `iniciar_ronda` con cero elegibles falla.

### 4.24 Ventana de reclamo — corrección V3 (regla de negocio §6.2 del alcance)

El alcance §6.2 la enumera entre las reglas que hay que fijar **antes de programar**:
por dónde canta bingo el jugador y cuántos segundos tiene. No está ni en el código
ni en la versión anterior de este plan. Lo único que había era `pausa_al_ganador`,
que es una pausa indefinida — y con 7-30 s de retraso de plataforma más el tiempo de
escribir por WhatsApp, "el operador pausa y espera" no es una regla, es improvisar
con dinero sobre la mesa y una cámara encendida.

- `tema_json.juego.segundos_reclamo` (60 por defecto, 0 = sin límite).
- Al detectar ganador, cuenta regresiva visible **en la pantalla de transmisión**
  (junto al aviso de BINGO, que sigue sin revelar código ni nombre) y en la del
  operador.
- El instante del reclamo se registra en auditoría (`ganador.reclamado_en`), para que
  una disputa posterior tenga una hora, no un recuerdo.
- Al agotarse la cuenta, se aplica `sin_reclamo` (D8).
- El canal de reclamo (WhatsApp, en persona, teléfono) es un texto configurable que
  se pinta en la pantalla de transmisión: el público tiene que saber a dónde gritar.
- **Y resuelve el hueco emocional del §B.3.** Entre "¡BINGO!" y "ganador confirmado"
  pasan de treinta segundos a dos minutos mientras el reclamante escribe y el
  operador valida. Sin esta tarea, la pantalla del público se queda congelada en un
  cartel estático: aire muerto en directo, que es lo que mata una transmisión. Con
  ella, el público ve un reloj bajando, el patrón completado parpadeando y a dónde
  reclamar. La misma pieza que arregla una regla de negocio arregla el peor momento
  del arco.

### 4.25 Borrado de datos de compradores — corrección C4 (LOPDP)

`servicio_compradores.eliminar_todos_del_evento` existe desde la fase 4 y
**ningún archivo de `ui/` lo llama** (verificado con `grep`): hoy la política de
retención solo se puede ejecutar desde una consola de Python. Mientras eso siga así,
la política de retención de `TODOS.md` P1 es inejecutable por diseño.

- Botón "Eliminar datos de compradores de este evento" en la sección Compradores,
  con confirmación escrita (teclear el nombre del evento, como cualquier operación
  irreversible), registro en auditoría y un resumen de cuántas filas se borraron.
- Deshabilitado si el evento no está `finalizado`.
- Media hora de trabajo, y es la única forma de que la política de retención se
  pueda cumplir cuando se escriba.

### 4.26 Integración continua — corrección M7

`TODOS.md` dice "no hay repositorio remoto todavía". Sí lo hay:
`github.com/Gab9Cruzz/Bingo_Juego.git`, con `main` y `feature/fase-2-cartones`
publicadas y `dev` sin publicar. 433 pruebas que solo existen como promesa en un
portátil.

- `.github/workflows/ci.yml`: `ruff check` + `ruff format --check` +
  `pytest -m "not lento"` en cada push y cada PR, sobre Python 3.12 en
  `windows-latest` (es el único sistema objetivo; probar en Linux daría verde en un
  entorno que nadie usa).
- Publicar `dev`.
- Actualizar la nota de `TODOS.md`, que quedó obsoleta.

### 4.27 `modo_vivo` — regla explícita (deuda de `TODOS.md`, corrección §B.5)

`TODOS.md` define la bandera desde la fase 1 y dice que la fase 5 la implementa
"cuando exista la interfaz de sorteo contra la que medirla". Existe ahora, así que
la regla se escribe en vez de dejarla al criterio del momento:

- `modo_vivo` degrada de **modal** a **franja no modal** únicamente los errores **no
  terminales**: `ErrorPersistencia`, `ErrorIntegridad`, `ErrorBaseBloqueada`.
- **Sigue siendo modal incluso en directo:** base corrupta, migración fallida, sin
  permisos. Un modal feo en cámara es mejor que seguir jugando sobre una base rota.
- **La bandera NO es estado de módulo** (contradicción con DU-12, resuelta a favor de
  DU-12): es un atributo de `EspacioEvento`, y `dialogos.confirmar` /
  `dialogos.mostrar_error_modal` reciben `modo_vivo: bool = False` como parámetro
  explícito. `ui/dialogos.py` son hoy funciones de módulo sin estado, y esta fase no
  introduce la primera pieza de estado global de interfaz del proyecto.
- `EspacioEvento` la baja en su teardown, para que un fallo no deje la aplicación muda
  para siempre.
- Prueba: con `modo_vivo` activo, un `ErrorPersistencia` no abre modal y un
  `ErrorBaseCorrupta` sí.


---

## 5. Riesgos y notas

| Riesgo | Impacto | Mitigación |
|---|---|---|
| `fsync` por bola en un disco lento del equipo del evento | La bola tarda en aparecer | Medido en prueba `lento`; si supera 50 ms se evalúa `synchronous=NORMAL` **solo** durante el sorteo, documentando la pérdida (WAL + NORMAL pierde como mucho la última transacción ante corte de energía, no corrupción) |
| Voz TTS pobre o ausente en el equipo del evento | Se pierde la locución en vivo | Degradación explícita de D5 + carpeta de audio pregrabado sin tocar código |
| Segundo monitor que Windows reordena entre arranques | La transmisión sale en el monitor equivocado | Guardar el monitor por nombre (`QScreen.name()`), no por índice; si no aparece, preguntar |
| OBS captura la ventana en negro (aceleración por hardware) | La transmisión no se ve | Documentar en el runbook: capturar por "Captura de ventana" con método Windows 10 (WGC); probarlo en el ensayo |
| El ensayo completo se salta por falta de tiempo | Se estrena en un evento real | Es un criterio de aceptación del contrato; sin él la fase no se cierra |
| Alcance: son diecinueve grupos de tareas tras la revisión, el triple que la fase 4 | La fase se alarga o **se recorta en silencio** | El precedente lo confirma: las fases 3 y 4 entraron en un solo commit de 12.209 líneas el mismo día, y `TODOS.md` cierra con **doce** recortes hechos "para que la fase entrara en una sola sesión". Orden del §4 pensado para que 4.1-4.9 sea demostrable solo. **Orden de recorte corregido:** el único candidato es 4.10 (sonido). El empaquetado **no** se recorta ni se deja para el final (ver fila siguiente) |
| Empaquetado de PySide6 con QtMultimedia y QtTextToSpeech | El `.exe` arranca pero no suena, y se descubre la última semana | `hiddenimports` explícitos + **prueba de humo del `.exe` en la semana 1**, no en la última. PyInstaller con estos módulos es célebre por fallar tarde, y empaquetar es criterio de aceptación del contrato: dejarlo al final es apostar la fase al riesgo peor estimado |
| **Punto de fallo humano: una sola persona presenta frente a cámara, opera la app, vigila WhatsApp, valida códigos y decide empates** | Un reclamo mal resuelto en directo, o un bloqueo del operador | Es el riesgo peor mitigado del proyecto y no tiene arreglo de software. Mitigación sin código: **una segunda persona con el runbook impreso**, que sabe pausar y sabe dónde está el `.zip`. Y el ensayo de 4.16 se corrige para que Gabriel presente de verdad, que es la única forma de probar la premisa |
| Los tres bloqueadores P1 legales de `TODOS.md` siguen sin empezar, con una organización ya agendada | Puede invalidar las cinco fases retroactivamente, o costarle el canal a la organización | No son software y no dependen de ninguna línea de código: corren **en paralelo** al desarrollo. Ver desafío UC-2 del gate |
| Los tres spikes P1 de de-riesgo (OBS + dos monitores, latencia de transmisión, imprenta) siguen sin correr, dos fases después de cuando tocaban | 4.9 se escribe entera sobre una premisa no medida; un rechazo de la imprenta es retrabajo de una fase cerrada | Ver desafío UC-1 del gate. D14 ya se hizo contingente al resultado del spike de OBS |

---

## 6. Mapeo a criterios de aceptación del contrato

| Criterio | Cubierto por |
|---|---|
| Tres rondas de principio a fin sin trabas | 4.6, 4.8, ensayo de 4.16 |
| Matar el proceso a mitad y volver donde estaba | D13, 4.6 (`reanudar_ronda`), prueba parametrizada |
| Transmisión limpia en OBS, legible en celular | 4.9, D14, runbook + ensayo |
| Ganadores en el instante correcto, no revelados antes | 4.6 (detección tras cada bola), 4.9 (prueba de no revelación) |
| Un cartón no vendido nunca gana | 4.6 (carga solo elegibles) + 4.7 (`validar_reclamo`), dos pruebas |
| Acta y reporte cuadran con lo ocurrido | 4.11, D7 (hash reproducible) |
| Instalador deja la app funcionando sin Python | 4.14 + `empaquetado/humo.py` (semana 1) + `empaquetado/actualizacion.py` |

### Criterios de aceptación añadidos por la revisión (no estaban en el contrato)

| Criterio | Por qué se añade | Cubierto por |
|---|---|---|
| El `.zip` de un evento tomado a mitad de ronda se restaura en un segundo equipo limpio y el sorteo continúa en la bola N+1 | Es la única mitigación real del punto de fallo "equipo único", y `runbook.md:9` ya se la promete al operador | 4.12 |
| Un cartón vendido a mitad de ronda no queda fuera del juego en silencio | Es el peor fallo posible de este producto: pagó y no puede ganar | 4.23 |
| Reanudar una ronda con un ganador anulado no lo resucita ni declara incoherencia | Modal terminal en directo por un caso normal | D13, prueba obligatoria |
| El ensayo mide el retraso real de la plataforma en una emisión privada | El número va impreso en el cartón (alcance §6.1) y hoy el texto no lo lleva | 4.16 |
| La pantalla pública nunca dice "BINGO" antes de que alguien reclame | Con `sin_reclamo="continuar"` la ronda seguía extrayendo tras haberlo gritado | DU-3 |

---

## 7. Entregable

- Etiqueta `v1.0.0`, `CHANGELOG.md` con la fase.
- `docs/decisiones.md` con las decisiones D1-D14 resumidas.
- `docs/convenciones-codigo.md` ampliado: convenio de callbacks del motor de sorteo,
  regla del lienzo 1920x1080, registro de atajos.
- `docs/runbook.md` con instalación, actualización, dos monitores y OBS.
- `docs/Fase_5/Ensayo.md` con el guion del ensayo y su resultado firmado.
- `TODOS.md` actualizado: cerrados `modo_vivo`, registro de atajos, riel, panel de
  auditoría y plan de segunda máquina; corregida la nota obsoleta de integración
  continua (sí hay repositorio remoto); cifrado del respaldo sigue P1, ahora con la
  dependencia nombrada (`pyzipper`) y la razón real escrita (alcance, no técnica).
- `docs/convenciones-codigo.md` ampliado con: el verbo `crear_si_no_existe`, el
  convenio de callbacks del motor de sorteo, el tercer caso de DS14 (aplicación
  inmediata en memoria + persistencia puntual, DU-7), la regla del lienzo 1920x1080 y
  el registro de atajos por ámbito.
- Corrección del documento técnico §4.5 (el índice inverso toca un tercio de los
  cartones, no la vigésima parte) y enmienda al §6.2 (el log de partida se escribe
  **después** del commit, no dentro de la transacción).

### Puerta de salida de la fase

- `pytest -m "not lento"` en verde con las ~120 pruebas nuevas; `pytest -m lento` en
  verde al menos una vez antes de etiquetar.
- `ruff check` y `ruff format --check` limpios.
- `empaquetado/humo.py` y `empaquetado/actualizacion.py` en verde **sobre el binario**.
- `docs/Fase_5/Ensayo.md` completo, firmado, con la captura del móvil adjunta.
- CI en verde en `windows-latest`.

El plan de pruebas completo está en
`~/.gstack/projects/Bingo_App/gabriel-main-test-plan-20260910.md`.

---

# ANEXO A — Revisión CEO (`/gstack-autoplan` Fase 1)

Modo: **SELECTIVE EXPANSION** (auto-seleccionado: iteración sobre un sistema
existente de cuatro fases cerradas). Voces duales: Claude subagente + Codex.
**Codex no está instalado en este equipo** (`[codex-unavailable: binary not found]`),
así que la fase corre etiquetada `[subagent-only]`.

## A.0 Chequeos previos

**Retrospectiva (git log).** Ocho commits, ninguno de reversión ni de refactor
motivado por una revisión previa. Los archivos más tocados a lo largo de las cuatro
fases son `dominio/estados.py`, `dominio/modelos.py`, `ui/registro_vistas.py`,
`i18n/es.json`/`en.json`, `pyproject.toml`, `TODOS.md` y
`tests/persistencia/test_migraciones.py` — tres ediciones cada uno. **No es olor
arquitectónico**: son exactamente los puntos de extensión que la fase 1 diseñó para
que las fases siguientes crecieran sin tocar la cáscara, y esta fase los toca por el
mismo motivo. Es la señal contraria: el diseño de la fase 1 aguantó cuatro fases.

**Detección de alcance de interfaz.** DESIGN_SCOPE = **sí** (16 coincidencias de
términos de vista en el contrato: pantalla, ventana, panel, tablero, selector,
botón). La Fase 2 de `/autoplan` corre.
Alcance de experiencia de desarrollador = **no** (una coincidencia de "API", que es
la API de respaldo de SQLite, y un "rest" que es substring de "restantes"). Fase 2.5
saltada.

**Calibración de gusto.** Referencias de estilo del propio repositorio, para imitar:
`dominio/patron.py` (dominio puro, docstring que explica el *porqué* y no el *qué*,
multi-máscara resuelto sin tabla relacional), `persistencia/errores_sqlite.py` (un
único punto de traducción en la frontera, `__cause__` conservado) y
`impresion/reporte.py::_escribir_seguro` (una defensa concreta contra un vector
concreto, documentada con el vector). Anti-patrón a no repetir: `vista_rondas.py`,
que guarda al vuelo sin Guardar/Cancelar contra su propia convención DS14 — la vista
de sorteo no debe heredar ese atajo.

**Landscape check (Layer 1 / 2 / 3).**

- *Layer 1 (lo probado):* el nicho de "software cantador de bingo" está resuelto y
  es viejo. TBBingo, Bingo Rose Caller, apps de iPad — todos hacen bombo, tablero de
  75 y salida a segunda pantalla, algunos desde hace veinte años.
- *Layer 2 (lo que dice la búsqueda):* BINGAZO va un paso más allá y publica el
  tablero por WiFi a los dispositivos del público, con **plugin para OBS**. La ruta
  "navegador como pantalla de transmisión" existe y tiene mercado.
- *Layer 3 (primeros principios):* **el cantador es una mercancía; la cadena
  administrativa no.** Ninguno de esos productos genera cartones únicos con firma,
  los imprime con QR firmado, lleva el registro de compradores, concilia lo
  recaudado y emite un acta con hash verificable. Eso es exactamente lo que las
  fases 1-4 ya construyeron. La conclusión operativa para esta fase es incómoda y
  útil: **no hay que dorar el cantador**, hay que proteger la cadena auditable.
  El bloque de sorteo tiene que ser sólido y aburrido; el acta y la reanudación son
  donde vive la diferencia.

Fuentes: [TBBingo](https://www.tbbingo.com/) ·
[BINGAZO](https://bingazo.bingo/) ·
[Bingo Rose Caller](https://www.bingorose.biz/programs/caller.htm) ·
[Best Bingo Caller Software 2026](https://gitnux.org/best/bingo-caller-software/)

## A.1 Premisas evaluadas (0A)

| # | Premisa del plan | Veredicto | Nota |
|---|---|---|---|
| P1 | El operador tiene dos monitores y OBS captura la ventana nativa | **NO VERIFICADA** | `TODOS.md` P1 pide un spike de medio día para esto "antes de la fase 5". No consta que se haya hecho. Es la premisa que sostiene D14 y la tarea 4.9 entera → **cola al gate como desafío UC-1** |
| P2 | Un `fsync` por bola es tolerable | Razonable, medible | El plan ya la instrumenta (D2 + prueba `lento`). Aceptada |
| P3 | La locución con TTS del sistema es suficiente | **Verificada parcialmente** | Medida en *este* equipo: `sapi` da es_ES y en_US. No medida en el equipo del evento. La degradación de D5 la cubre. Aceptada |
| P4 | Todo el evento cabe en un equipo, un operador | **Aceptada con reservas** | El alcance §8 ya la asume ("equipo único como punto de fallo"). Pero la fase 5 es la primera que la vuelve *crítica en vivo*: hasta ahora un fallo se recuperaba con tiempo, ahora hay público mirando. El respaldo sin ruta de restauración no la mitiga → ver expansión E5 |
| P5 | El sorteo con `secrets.SystemRandom()` es defendible ante la organización | Aceptada | El acta con hash y la secuencia completa es la respuesta al "¿estuvo amañado?", no el generador. Bien resuelto |
| P6 | v1.0.0 = listo para un evento real | **FALSA** | Es la premisa más peligrosa del contrato. `TODOS.md` P1 tiene tres bloqueadores legales sin empezar (premios en efectivo en Ecuador, políticas de Facebook/YouTube sobre juegos con premio, retención LOPDP). Ninguna fase los contiene. v1.0.0 significa "el software está listo", no "puedes cobrar entradas" → **cola al gate como desafío UC-2** |
| P7 | El problema a resolver es el sorteo en vivo | Aceptada, con matiz del Layer 3 | El sorteo es lo único que falta, sí. Pero es la parte *mercantilizada*. La ambición debe ir al acta, la reanudación y el respaldo, no a la animación del bombo |

**¿Qué pasa si no se hace nada?** Las fases 1-4 quedan como un generador de cartones
caro. Sin la fase 5 no hay producto. Dolor real, no hipotético.

## A.2 Delta de estado soñado (0C)

```
  ESTADO ACTUAL                    ESTA FASE                    IDEAL A 12 MESES
  ─────────────                    ─────────                    ────────────────
  Cartones generados,        ──▶   El juego corre, se       ──▶  Varias organizaciones
  impresos, vendidos,              detectan y validan            operan sus propios
  rondas configuradas,             ganadores, sobrevive          bingos; el operador es
  tema definido.                   a un corte, emite acta        reemplazable porque el
  El evento no se puede            con hash, respalda y          respaldo restaura en
  jugar.                           se instala en un              cualquier equipo en
                                   equipo limpio.                minutos; el acta es un
                                                                 comprobante que la
                                                                 organización acepta sin
                                                                 discutir.
```

El plan **mueve hacia** el ideal en dos de tres ejes (jugabilidad, comprobante) y
**deja parado** el tercero: el respaldo se exporta pero no se restaura, así que
"cualquier equipo en minutos" sigue sin existir. Es el hueco más grande del plan tal
como está escrito, y es el que la expansión E5 propone cerrar.

## A.3 Aprovechamiento de código existente (0B)

El mapa completo está en el §2 del plan (leverage map), producido antes de esta
revisión. Verificado sub-problema por sub-problema: **no hay nada en el plan que
reconstruya algo que ya existe.** Los tres candidatos a duplicación se revisaron
uno a uno:

- *Detección de ganador*: el plan reexporta `dominio/patron.es_ganador`, no la
  reescribe (§4.3). Correcto.
- *Visor de cartón en el buscador del operador*: reusa `CuadriculaCarton` con la
  API que la fase 2 dejó preparada. Correcto.
- *Reporte del evento en Excel*: se añade a `impresion/reporte.py` en vez de crear
  un módulo nuevo, respetando "único módulo que abre `openpyxl.Workbook()`"
  (hallazgo A4 de la fase 4). Correcto.

Un cuarto candidato **sí** es duplicación potencial y el plan no lo dice: la tabla
de posiciones de bloques de `ui/vistas/vista_tema.py::_BLOQUES` y la que necesitará
`ui/transmision/bloques.py`. Si se escriben dos veces, la vista previa y la pantalla
real divergen el día que alguien toque una. → hallazgo S5-1, ver §A.6.

## A.4 Alternativas de implementación (0C-bis)

```
APPROACH A: Núcleo jugable
  Resumen: solo 4.1-4.9 + pruebas. Sin sonido, sin acta, sin respaldo, sin instalador.
           Se ejecuta desde el árbol de fuentes con `python -m bingo`.
  Esfuerzo: L        (humano ~3 semanas / CC ~4-5 h)
  Riesgo:   Bajo
  Pros:     - Entrega lo único que el público ve, y lo entrega antes.
            - Cada pieza posterior es aditiva y no toca el motor.
            - El ensayo completo se puede hacer con esto.
  Contras:  - No hay comprobante: la organización no recibe nada firmado.
            - Sin respaldo, un disco muerto se lleva el evento entero.
            - No es v1.0.0 por definición del contrato.
  Reusa:    todo el leverage map del §2.
  Completitud: 6/10

APPROACH B: El plan tal como está escrito  (RECOMENDADO)
  Resumen: los doce grupos de tareas, ventana de transmisión nativa PySide6
           capturada por OBS como "Captura de ventana", instalador Inno Setup.
  Esfuerzo: XL       (humano ~6-7 semanas / CC ~10-14 h)
  Riesgo:   Medio (concentrado en 4.9 y 4.14, las dos no verificadas)
  Pros:     - Cumple los siete criterios de aceptación del contrato.
            - Una sola pila de render (Qt), coherente con las cuatro fases previas.
            - El acta con hash es la pieza que ningún competidor tiene.
  Contras:  - Doce grupos en una fase es el doble que la fase 4; el riesgo de
              recorte mal hecho es real.
            - 4.9 depende de una premisa no medida (spike de OBS pendiente).
  Reusa:    todo el leverage map + `Tarea`, `reporte.py`, `render_pdf.py`.
  Completitud: 10/10

APPROACH C: Transmisión como página web local consumida por OBS Browser Source
  Resumen: en vez de una ventana Qt en el segundo monitor, un servidor HTTP local
           sirve el tablero y OBS lo consume con Browser Source (la ruta de BINGAZO).
  Esfuerzo: XL+      (humano ~8 semanas / CC ~16 h)
  Riesgo:   Alto
  Pros:     - Compositing nativo en OBS, sin problemas de DPI ni de orden de monitores.
            - Funciona con un solo monitor.
            - El público podría ver el tablero en su celular sin nada más.
  Contras:  - Una segunda pila de render (HTTP + HTML/CSS/JS + websocket) dentro de
              un proyecto cuyo documento técnico §7 define el tema como posiciones de
              widgets Qt. Duplica el editor de tema y su vista previa.
            - Abre un puerto en el equipo del operador: superficie de ataque nueva
              en una máquina con datos personales.
            - Un bingo de salón con proyector (sin transmisión) sigue necesitando
              una ventana nativa: habría que mantener las dos.
  Reusa:    el modelo `TemaDashboard`; nada del render.
  Completitud: 9/10
```

**RECOMENDACIÓN: Approach B.** Completitud máxima y una sola pila de render. C es
mejor producto a dos años y peor decisión hoy: viola DRY contra el editor de tema
que la fase 4 acaba de entregar y duplica el trabajo de render para ganar
flexibilidad que nadie ha pedido todavía. C se anota en `TODOS.md` como camino de la
v2, con su razón escrita. A no es aceptable como entregable de fase (no cumple el
contrato) pero **sí es el orden interno correcto** de B, y así está escrito el §4.

*Auto-decisión (P1 completitud + P3 pragmatismo): B. Sin decisión de gusto — la
distancia entre B y C es grande y en la dirección esperada.*

## A.5 Análisis de modo (0D — SELECTIVE EXPANSION)

**Chequeo de complejidad.** El plan toca más de 8 archivos y crea más de 2 clases
nuevas, así que la regla obliga a desafiarlo. Desafiado: el plan crea 16 módulos
nuevos y toca ~14 existentes. ¿Se puede con menos piezas? Se revisaron las tres
fusiones plausibles:

- `servicio_ganadores.py` dentro de `servicio_sorteo.py` → **no**. El sorteo corre
  durante la ronda; la validación de reclamos corre también *después* de cerrarla
  (alguien aparece con su cartón tarde). Son ciclos de vida distintos y el archivo
  fusionado pasaría de 400 líneas.
- `dominio/partida.py` dentro de `dominio/carton.py` → **no**. `carton.py` es
  generación y representación; `partida.py` es estado mutable de una ronda. La
  convención del proyecto (`docs/convenciones-codigo.md`, "entidades con
  comportamiento propio van en su propio módulo") ya lo decide.
- `ui/sonido/{efectos,musica,locucion}.py` en un solo `ui/sonido.py` → **sí**, y el
  plan se corrige: son tres clases pequeñas con el mismo ciclo de vida (se crean al
  entrar en modo vivo, se destruyen al salir) y ninguna se usa sin las otras.
  → hallazgo S5-2.

**Conjunto mínimo que logra el objetivo declarado.** 4.1-4.9 + 4.15 + el subconjunto
de 4.16 que cubre bombo/partida/reanudación. Es el Approach A. Todo lo demás
(4.10-4.14) es diferible *técnicamente*, pero 4.11 (acta) y 4.12 (respaldo) son
criterios de aceptación del contrato y son, por el Layer 3 del landscape check, la
parte diferenciada del producto. No se difieren.

**Escaneo de expansión (candidatos, no alcance todavía).**

*Chequeo 10x:* la versión 10x de esta fase no es una animación mejor del bombo. Es
que **la organización pueda auditar el sorteo sin creerle a nadie**: acta con hash,
secuencia completa, log en texto plano, y un botón que verifica que el acta que
tienen en la mano corresponde a lo que hay en la base. Eso convierte "confía en
Gabriel" en "verifica el documento". Es media hora de código sobre lo que el plan ya
hace (E4) y cambia la conversación comercial entera.

*Oportunidades de deleite (mínimo cinco):*
1. Modo ensayo con un comando (`--ensayo`) que arma un evento de prueba completo.
2. Fondo transparente / croma en la transmisión, para componer en OBS.
3. Panel de auditoría del evento, de solo lectura.
4. Verificador de acta contra la base.
5. Restauración de un respaldo `.zip` en un equipo limpio.
6. "Últimas cinco bolas" en grande, que es lo que pide el que llegó tarde a mirar.
7. Atajo de una tecla para repetir la locución del número actual.

*Potencial de plataforma:* el `LogPartida` con `fsync` y el acta canónica son
infraestructura, no adorno: cualquier función futura de verificación, de disputa o
de auditoría externa se apoya en ellos. Vale la pena que estén bien escritos.

### A.5.1 Ceremonia de cherry-pick (auto-decidida)

Siete candidatos, presentados uno a uno. Regla P2: dentro del radio de impacto y
menos de un día de CC → aceptar; fuera → diferir; duplicado → rechazar; 3-5
archivos o radio ambiguo → decisión de gusto al gate.

| # | Expansión | Esfuerzo (humano / CC) | Radio | Decisión | Razón |
|---|---|---|---|---|---|
| E1 | **Modo ensayo `--ensayo`**: crea un evento de prueba con 200 cartones, 3 rondas y compradores provisionales, listo para el ensayo del contrato §5.12 | 1 d / ~20 min | 2 archivos nuevos, reusa `servicio_cartones` + `marcar_vendidos_por_rango` | **ACEPTADA** (P2) | El ensayo completo es criterio de aceptación. Sin esto, montarlo a mano cuesta media hora cada vez y se hará una sola vez, que es exactamente cómo se salta |
| E2 | **Fondo transparente / croma en transmisión** | 0.5 d / ~10 min | 1 archivo + una opción de tema | **ACEPTADA** (P2) | Es un color y una bandera. Convierte la ventana en una capa componible en OBS en vez de un fondo opaco |
| E3 | **Panel de auditoría del evento** (solo lectura) | 1 d / ~20 min | 1 vista nueva; `repo_auditoria.listar_por_evento` ya existe | **ACEPTADA** (P2) | Ya estaba en `TODOS.md` desde la fase 4. La fase 5 multiplica por diez lo que se escribe en auditoría (cada ganador, cada empate, cada reanudación incoherente) y hoy nadie puede leerlo sin abrir la base con un cliente SQL |
| E4 | **Verificador de acta**: recalcula la carga canónica desde la base y la compara con `ronda.acta_hash` | 0.5 d / ~10 min | dentro de `servicio_actas.py` + un botón | **ACEPTADA** (P2) | Es lo que hace que el hash signifique algo. Sin verificador, el hash es decoración |
| E5 | **Restaurar un respaldo `.zip`** en una instalación limpia | 3 d / ~1 h | 3-5 archivos (servicio, vista, arranque) | **PROMOVIDA A ALCANCE** tras la voz dual | Empezó como decisión de gusto al gate. La voz independiente la calificó de **crítica** con una evidencia que la revisión primaria no tenía: `docs/runbook.md:9` **ya se la promete al operador**. Un respaldo que nadie ha restaurado nunca no es un respaldo. Entra en 4.12 |
| E6 | **Grabar la locución desde la app** (75 números, micrófono) | 3 d / ~1 h | módulo nuevo + almacenamiento | **DIFERIDA a `TODOS.md`** (P3) | Fuera del radio. D5 ya deja la puerta abierta: copiar 75 `.wav` a una carpeta no necesita código |
| E7 | **Tablero web para el celular del público** | 8 d / ~2 h | pila nueva completa | **DIFERIDA a `TODOS.md`** (P3) | Es el Approach C por la puerta de atrás. Se anota con su razón |

Aceptadas (E1-E4) → tareas 4.17 a 4.20. E5 → tarea 4.12. E6, E7 → `TODOS.md`.

## A.6 Interrogatorio temporal (0E)

Decisiones que el implementador va a encontrarse y que se resuelven **aquí**, no
"sobre la marcha". Escalas duales: equipo humano / CC + gstack.

```
  HORA 1 (cimientos)        ¿La migración 004 reconstruye alguna tabla? → NO, solo
  humano ~1 d / CC ~10 min  ADD COLUMN e índices (D3, tras verificar que E4b ya se
                            cumple desde la 003). ¿`ronda.estado` gana un CHECK ahora que
                            TRANSICIONES_RONDA existe? → NO. La decisión de la fase 1
                            sigue vigente: el conjunto puede crecer (V5) y un CHECK no
                            se quita sin reconstruir otra vez. Se documenta para que
                            nadie lo "arregle" en una revisión futura.

  HORAS 2-3 (núcleo)        ¿Quién es dueño del objeto de partida entre extracciones?
  humano ~1.5 sem / CC ~4 h → `EspacioEvento`, no `VistaSorteo` (S5-3). Vive mientras
                            el evento esté abierto.
                            ¿El índice inverso se reconstruye al vender un cartón a
                            mitad de ronda? → no se permite vender con ronda en curso
                            (S5-4, tarea 4.23).
                            ¿La reanudación escribe? → nunca (D13 enmendada, V1).

  HORAS 4-5 (integración)   Lo que sorprende, y por eso va escrito en 4.9 y 4.10:
  humano ~1.5 sem / CC ~4 h `showFullScreen()` sin `setGeometry` previo abre en el
                            monitor equivocado; `QSoundEffect` no suena la primera vez
                            si no se espera `statusChanged == Ready`; `QTextToSpeech`
                            solo lista las voces del locale activo, así que hay que
                            fijar el idioma **antes** de pedir voces (medido: `winrt`
                            en es_ES no muestra ninguna voz inglesa; `sapi` tras fijar
                            en_US sí).

  HORAS 6+ (pulido/pruebas) Lo que se va a desear haber planeado: un modo de ensayo
  humano ~1 sem / CC ~3 h   (E1), un verificador de acta (E4), y el spike de OBS, que
                            debería haber corrido hace dos fases (UC-1 del gate).
```

## A.7 Hallazgos de las secciones 1-10

Las once secciones se corrieron completas. Lo que sigue son los hallazgos, con su
decisión automática. Las secciones sin hallazgos se declaran explícitamente en §A.8.

| # | Sección | Hallazgo | Severidad | Decisión (principio) |
|---|---|---|---|---|
| S5-1 | 1 Arquitectura | La tabla de bloques del tema existiría dos veces: `vista_tema._BLOQUES` (vista previa) y `ui/transmision/bloques.py` (real). Divergen en cuanto alguien toque una | Alta | **Corregido en el plan** (P4 DRY): la tabla se extrae a `dominio/tema.py::BLOQUES` (nombre, dimensiones fraccionarias por defecto) y la consumen las dos. Tarea 4.21 |
| S5-2 | 5 Calidad | `ui/sonido/` con tres módulos para tres clases pequeñas del mismo ciclo de vida | Media | **Corregido**: un solo `ui/sonido.py` (P5 explícito, menos piezas) |
| S5-3 | 1 Arquitectura | El plan no dice **quién es dueño** del `MotorSorteo` entre extracciones. Si lo tiene `VistaSorteo`, cambiar de sección del riel destruiría la partida en curso | **Crítica** | **Corregido**: el motor lo tiene `EspacioEvento` (vive tanto como el evento abierto) y `VistaSorteo` lo recibe. Tarea 4.8 lo especifica |
| S5-4 | 4 Flujo de datos | Vender un cartón con una ronda en curso lo dejaría fuera del índice inverso: pagó y no puede ganar, en silencio | **Crítica** | **Corregido**: `servicio_compradores` consulta `repo_ronda.obtener_en_juego` y lanza `ErrorValidacion("compradores.error.ronda_en_curso")`. Se prueba |
| S5-5 | 2 Errores | `BomboVacio` no tiene rescate definido: pasa cuando salen las 75 bolas sin ganador (patrón "cartón lleno" con pocos cartones) | Alta | **Corregido**: lo captura `VistaSorteo`, cierra la ronda como `sin_ganador` y lo registra en auditoría. Entra en el registro de errores §A.9 |
| S5-6 | 2 Errores | `LogPartida` con `fsync`: si el disco se llena o la carpeta desaparece, el `write` lanza `OSError` **dentro** de la transacción de la bola y tumbaría el commit | **Crítica** | **Corregido**: el log se escribe **después** del commit, no dentro. Si falla, se registra como advertencia y el sorteo sigue — la base es la fuente primaria, el log es respaldo. Contradice la lectura literal del doc técnico §6.2 (que lista el log como paso 4 de la transacción) y se documenta como enmienda |
| S5-7 | 3 Seguridad | El reporte del evento lleva teléfono/cédula/correo de los ganadores. El contrato §5.9 dice "datos de contacto de cada ganador" sin matizar | Alta | **Corregido**: se hereda el criterio UC-3 de la fase 4 — casilla "incluir datos de contacto", desmarcada al abrir, solo en Excel, nunca en el PDF del acta. El acta lleva **código de cartón**, no nombre |
| S5-8 | 3 Seguridad | El `.zip` de respaldo sin cifrar es la sexta copia de datos personales en el disco | Alta | **Aceptado con mitigación** (D11): aviso + `RESPALDO_LEEME.txt`. El cifrado real sigue P1 en `TODOS.md`. Se registra como riesgo asumido, no como resuelto |
| S5-9 | 4 Flujo de datos | Doble clic en "Extraer bola" extrae dos bolas | Media | **Corregido**: el botón se deshabilita durante la extracción y se rehabilita al terminar la animación; además `confirmar_extraccion` del tema §7 |
| S5-10 | 6 Pruebas | Ninguna prueba cubre "el patrón no usa el espacio libre y el cartón lo tiene encendido" | Media | **Corregido**: caso explícito en `test_partida.py` (ya estaba insinuado en 4.3, ahora es una prueba nombrada) |
| S5-11 | 7 Rendimiento | Repintar 1920x1080 a 60 Hz durante la animación, con 75 celdas de tablero, en el equipo del evento | Media | **Corregido**: invalidación por rectángulo (ya en D14) + el tablero se pinta en un `QPixmap` cacheado que solo se regenera cuando cambia una bola |
| S5-12 | 8 Observabilidad | Cada decisión de ganador va a auditoría, pero nadie puede leerla desde la app | Alta | **Corregido** por la expansión E3 (panel de auditoría) |
| S5-13 | 9 Despliegue | "Las migraciones se aplican al actualizar" no se puede probar con `pytest` sobre el árbol de fuentes: hay que probarlo sobre el binario | Alta | **Corregido**: la tarea 4.14 ya lo pide; se sube a criterio de salida de la fase, con guion escrito |
| S5-14 | 9 Despliegue | No hay plan de reversión del instalador: si la 004 corre y la versión nueva falla, la base ya migró | **Crítica** | **Corregido**: el arranque copia `bingo.db` a `bingo.db.pre-<version>` antes de aplicar cualquier migración pendiente, y el runbook documenta cómo revertir. Tarea 4.22 |
| S5-15 | 10 Trayectoria | `ronda.premio_valor` (REAL) queda muerta una fase más | Baja | **Aceptado**: D3 ya lo justifica. Se anota en `docs/decisiones.md` para que la próxima reconstrucción de `ronda` la elimine |
| S5-16 | 11 Diseño | El plan no dice qué ve el operador cuando **no** hay ninguna ronda jugable (evento en borrador, sin cartones vendidos) | Media | **Corregido**: estado vacío de la sección Sorteo que reusa `validar_evento_listo` y lista qué falta, igual que el chip de la cabecera |

## A.8 Secciones sin hallazgos (declaradas, no saltadas)

- **Sección 3 (Seguridad), sub-eje "inyección".** Se revisó el conjunto entero de
  entradas nuevas: código de cartón tecleado en el buscador, nota de decisión de
  ganador, texto del banner y textos de bienvenida/cierre, ruta del archivo de
  música. Ninguna llega a SQL sin parámetros (todo el SQL vive en `persistencia/`
  con `?`), ninguna llega a un `subprocess`, y la única que llega a un `.xlsx` pasa
  por `_escribir_seguro`. La ruta de música se abre con `QMediaPlayer`, que no
  ejecuta nada. Sin hallazgos.
- **Sección 5 (Calidad), sub-eje "sobre-ingeniería".** El único candidato era el
  protocolo `ProveedorLocucion` con dos implementaciones cuando hoy solo hay una
  fuente real. Se examinó y se mantiene: la segunda implementación no es
  especulativa, es la respuesta explícita a una decisión pendiente del contrato
  (§5.8), y son ~40 líneas. Sin hallazgo.
- **Sección 7 (Rendimiento), sub-eje "N+1".** No hay ORM ni travesía de asociaciones:
  la carga de cartones elegibles es una consulta más `mapa_por_evento`, ambas
  existentes y ambas de una sola pasada. El índice inverso convierte la evaluación
  por bola de O(1000) a O(50). Sin hallazgo.
- **Sección 10 (Trayectoria), sub-eje "ajuste al ecosistema".** PySide6, SQLite,
  ReportLab, openpyxl, PyInstaller e Inno Setup son la cadena estándar y la que el
  proyecto ya usa. Ninguna dependencia nueva (D6 y D11 evitan las dos que estaban
  tentando). Sin hallazgo.

**Reversibilidad (Sección 10, escala 1-5):** 4. Casi todo es aditivo. La única
puerta de un solo sentido es la migración 004 sobre una base con datos reales
(por eso S5-14 añade la copia previa). El formato del acta y su hash también son
de un solo sentido una vez que una organización tenga un acta en la mano.

## A.9 Registro de errores y rescate

| Codepath | Qué puede salir mal | Clase de excepción |
|---|---|---|
| `Bombo.extraer` | Bombo agotado (75 bolas, sin ganador) | `BomboVacio` |
| `Bombo.__init__` | Bolas previas fuera de 1-75 o repetidas (base manipulada) | `ErrorValidacion` |
| `MotorSorteo.iniciar_ronda` | Transición inválida (`cerrada -> en_curso`) | `ErrorValidacion` |
| `MotorSorteo.iniciar_ronda` | Cero cartones elegibles | `ErrorValidacion` |
| `MotorSorteo.extraer` | Base bloqueada por otro escritor | `ErrorBaseBloqueada` |
| `MotorSorteo.extraer` | Disco lleno al hacer commit | `ErrorPersistencia` |
| `MotorSorteo.reanudar_ronda` | Reconstrucción incoherente con lo persistido | `ErrorReanudacion` (nueva) |
| `LogPartida.linea` | Disco lleno / carpeta borrada | `OSError` (fuera de la transacción) |
| `servicio_ganadores.validar_reclamo` | Código inexistente / no vendido / sin comprador | `ErrorValidacion` |
| `servicio_actas.generar` | Ruta sin permisos, PDF no escribible | `ErrorPersistencia` |
| `servicio_respaldos.exportar` | Sin espacio para el `.zip` | `ErrorPersistencia` |
| `LocucionTTS.decir` | Sin motor TTS / sin voz para el idioma | degradación, no excepción |
| `Efectos.reproducir` | Sin dispositivo de audio | degradación, no excepción |
| `VentanaTransmision.mostrar` | El monitor guardado ya no existe | degradación → pregunta |

| Clase | ¿Rescatada? | Acción de rescate | Qué ve el operador |
|---|---|---|---|
| `BomboVacio` | Sí | Cierra la ronda como `sin_ganador`, auditoría | Franja: "Se agotaron las 75 bolas sin ganador. Ronda cerrada." |
| `ErrorValidacion` | Sí | Mensaje en línea, foco al campo | Texto bajo el campo |
| `ErrorBaseBloqueada` | Sí | Reintento automático (`BUSY_TIMEOUT_MS`), luego franja con "Reintentar" | Franja no modal con acción |
| `ErrorPersistencia` | Sí | Franja con ruta del log; **la bola NO se muestra** (el commit no ocurrió) | Franja con reintentar |
| `ErrorReanudacion` | Sí | Modal terminal con los dos conjuntos, opción de reanudar igual (auditoría) o cancelar | Modal con detalle copiable |
| `OSError` del log | Sí | Advertencia al log de aplicación, el sorteo continúa | Franja una sola vez por ronda |
| Degradaciones de audio | Sí | Se desactiva la casilla con el motivo | Casilla gris con explicación |
| Monitor inexistente | Sí | Vuelve a la lista de monitores | Selector abierto con aviso |

**Sin `except Exception` en ningún punto de esta fase.** La regla de
`docs/convenciones-codigo.md` ("la vista no captura nunca `Exception`") se mantiene:
lo que no sea `ErrorBingo` va al manejador global.

## A.10 Registro de modos de fallo

| Modo de fallo | ¿Silencioso hoy? | Detección | Respuesta |
|---|---|---|---|
| Cartón vendido a mitad de ronda que no participa | **Sí (S5-4)** | Bloqueado en el servicio | `ErrorValidacion` en la venta |
| Ganador duplicado al reanudar | **Sí** | Índice único `idx_ganador_ronda_carton` | `INSERT OR IGNORE`, sin ruido |
| Bola mostrada sin haberse persistido | **Sí** | El orden de D2 lo hace imposible | — |
| Ganador revelado en pantalla antes de validar | **Sí** | Prueba automatizada sobre el modelo del bloque | Falla la prueba |
| Acta que no corresponde a la base | **Sí** | Verificador de acta (E4) | Aviso explícito |
| Respaldo que no se puede restaurar | **Sí, y grave** | Solo se detecta al necesitarlo | **Cerrado**: `servicio_respaldos.restaurar` entra en el alcance (4.12) con su propio criterio de aceptación — restaurar en un segundo equipo y seguir en la bola N+1 |
| Locución muda sin que nadie se entere | **Sí** | `disponible()` al entrar en modo vivo | Casilla gris + log |
| Migración aplicada sobre una versión que luego falla | **Sí (S5-14)** | Copia `pre-<version>` | Runbook de reversión |
| Log de partida que dejó de escribirse | **Sí (S5-6)** | Franja al primer `OSError` | Aviso una vez por ronda |

## A.11 Fuera de alcance de esta fase (diferido, con razón escrita)

- **E6 — Grabar la locución desde la app.** Fuera del radio de impacto. D5 permite
  copiar 75 `.wav` a una carpeta sin escribir código.
- **E7 / Approach C — Transmisión como página web local + OBS Browser Source.**
  Segunda pila de render, puerto abierto en el equipo del operador, y duplica el
  editor de tema que la fase 4 acaba de entregar. Camino claro para la v2.
- **Cifrado real del respaldo (AES).** Exige `pyzipper`. Sigue P1 en `TODOS.md`,
  ahora con la dependencia concreta anotada.
- **Sincronización con nube, multiusuario, segunda máquina en caliente.** El alcance
  §8 ya los deja fuera de la v1.
- **Estadísticas del evento** (bolas más frecuentes, duración media de ronda).
  Métrica autorreferencial: nadie la pidió y no cambia ninguna decisión.
- **Los tres bloqueadores legales de `TODOS.md` P1.** No son software. Siguen ahí, y
  el desafío UC-2 pide que el plan lo diga en voz alta.

## A.12 Resumen de cierre — Fase CEO

| Eje | Resultado |
|---|---|
| Modo | SELECTIVE EXPANSION (auto) |
| Enfoque elegido | Approach B (el plan escrito), completitud 10/10 |
| Premisas evaluadas | 7 · 5 aceptadas · 1 no verificada (P1 → UC-1) · 1 falsa (P6 → UC-2) |
| Expansiones aceptadas | 5 (E1 ensayo, E2 croma, E3 auditoría, E4 verificador de acta, E5 restauración de respaldo — promovida por la voz dual) |
| Expansiones al gate | 0 — E5 dejó de ser decisión de gusto al aparecer la evidencia de `runbook.md:9` |
| Expansiones diferidas | 2 (E6, E7) |
| Hallazgos | 16 primarios (4 críticos, 6 altos, 5 medios, 1 bajo) + 9 de la voz dual (2 críticos, 3 altos, 4 medios) = **25** |
| Corregidos en el plan | 23 |
| Aceptados con riesgo escrito | 2 (S5-8 cifrado, S5-15 columna muerta) |
| Voces duales | Codex no disponible; subagente Claude ejecutado |

## A.13 Voces duales — CEO

**Codex:** no disponible (`[codex-unavailable: binary not found]`). La fase corre
etiquetada `[subagent-only]`.

**Claude subagente (independencia estratégica):** revisión completa, sin haber visto
la revisión primaria. 4 hallazgos críticos, 6 altos, 8 medios. Sus afirmaciones
materiales se **verificaron una por una contra el código** antes de incorporarlas:

| Afirmación del subagente | Verificación | Resultado |
|---|---|---|
| No existe función de restauración de respaldo | `grep -rn restaurar src/` | **Confirmada.** Cero implementaciones |
| `docs/runbook.md` ya promete "restaurar el `.zip` más reciente" en el código de salida 3 | `docs/runbook.md:9` | **Confirmada.** La promesa está escrita y no tiene forma de ejecutarse |
| `servicio_compradores.eliminar_todos_del_evento` no tiene ningún llamador en `ui/` | `grep -rn` sobre `src/` | **Confirmada.** Solo la definición y una mención en un docstring |
| `dominio/firma.py::verificar_qr` existe y el plan valida reclamos por código tecleado sin usarlo | `src/bingo/dominio/firma.py:45` | **Confirmada** |
| `TEXTO_INFERIOR_DEFECTO` dice "que tiene retraso" sin número, porque el spike de latencia sigue pendiente | `impresion/plantilla.py:37-40` | **Confirmada** |
| Sí hay repositorio remoto; `TODOS.md` dice que no | `git remote -v` → `github.com/Gab9Cruzz/Bingo_Juego.git`; `main` y `feature/fase-2-cartones` publicadas, `dev` no | **Confirmada.** La nota de `TODOS.md` está obsoleta |
| `config/preferencias.py` reserva `monitor_transmision: int`, y el §5 del plan promete guardarlo por nombre | `preferencias.py:26` vs. §5 del plan | **Confirmada.** Contradicción real, introducida por esta revisión |

```
CEO DUAL VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════════════
  Dimensión                              Primaria  Subagente  Codex  Consenso
  ─────────────────────────────────────  ────────  ─────────  ─────  ────────
  1. Premisas válidas                    parcial   parcial    N/A    ACUERDO
     (P1 spike OBS y P6 "v1.0.0 = listo
      para evento pagado" señaladas por
      las dos voces, por separado)
  2. ¿Problema correcto?                 sí, con   sí, con    N/A    ACUERDO
     (las dos llegan al mismo Layer 3:    matiz     matiz            FUERTE
      el cantador es mercancía, la
      cadena auditable es el activo)
  3. Calibración de alcance              riesgo    mal        N/A    DISCREPA
     (primaria: 12 grupos con orden       anotado   calibrado         → gate
      interno de recorte; subagente:
      partir en tres etiquetas)
  4. Alternativas exploradas             A/B/C     falta H6   N/A    DISCREPA
     (Approach C sí se evaluó en §A.4;    evaluadas                   parcial
      el subagente aporta el canal alfa
      y "sin segundo monitor", que la
      primaria no había pesado)
  5. Riesgos de mercado cubiertos        parcial   no         N/A    DISCREPA
     (el subagente añade el competidor                                → gate
      real: "bombo de plástico y grupo
      de WhatsApp", y el techo de
      escala: la agenda de una persona)
  6. Trayectoria a 6 meses sana          sí        sí, con    N/A    ACUERDO
                                                   3 bombas
═══════════════════════════════════════════════════════════════════════
Consenso: 3/6 confirmadas · 3 discrepancias → decisiones al gate.
Codex ausente = N/A, nunca CONFIRMED.
Hallazgo crítico de una sola voz = se marca igual (regla del pipeline).
```

### A.13.1 Hallazgos del subagente incorporados al plan

Nueve hallazgos que la revisión primaria **no** había encontrado, todos verificados
y todos corregidos en el cuerpo del plan:

| # | Hallazgo | Severidad | Corrección |
|---|---|---|---|
| V1 | **La reanudación resucita ganadores anulados.** El índice único de D3 es parcial (`WHERE anulado_en IS NULL`), así que un ganador anulado ya no está cubierto: el `INSERT OR IGNORE` de la reproducción **no lo ignora, lo reinserta vivo**. Y la verificación de D13 compara "detectados" contra "no anulados", así que declara incoherencia por un caso normal, con modal terminal, en vivo | **Crítica** | D13 se reescribe: la reproducción de reanudación **no escribe nunca**, solo reconstruye `marcado`. La comparación excluye `anulado_en IS NOT NULL` y `decision='rechazado'` de los dos lados. Prueba obligatoria |
| V2 | **"Empate" no está definido en el tiempo.** Con `sin_reclamo="continuar"` (el defecto de D8), quien completa el patrón en la bola 51 entra en la misma tabla que quien lo completó en la 42, y `resolver_empate` los trata como conjunto plano. El operador puede repartir el premio entre un ganador legítimo y tres tardíos, en cámara | Alta | Empate := **misma `extraccion.orden`**. La UI agrupa y ordena por bola de detección. `resolver_empate` rechaza repartir entre bolas distintas salvo confirmación explícita registrada en auditoría |
| V3 | **La regla de negocio §6.2 del alcance ("canal y ventana de reclamo") no está en ninguna parte.** Ni en el código ni en el plan. Solo hay `pausa_al_ganador`, que es una pausa indefinida. Con 7-30 s de retraso más el tiempo de escribir por WhatsApp, "el operador pausa y espera" no es una regla, es improvisar con dinero sobre la mesa | Alta | `tema_json.juego.segundos_reclamo` (60 por defecto), cuenta regresiva visible en transmisión al detectar ganador, instante del reclamo en auditoría. Tarea 4.24 |
| V4 | **`verificar_qr` existe y el plan no lo usa.** `dominio/firma.py:45` se escribió en la fase 3 declarando en su docstring que la fase 5 lo necesita para validar reclamos; §4.7 valida solo por código tecleado | Alta | `validar_reclamo` acepta **también** el contenido de un QR: si el texto pegado/escaneado parece un QR firmado, se pasa por `verificar_qr` y se extrae el código. Un dígito mal tecleado deja de ser un modo de fallo |
| V5 | **No hay marcha atrás en `TRANSICIONES_RONDA`, ni estado para un evento partido en dos noches.** El alcance §6.6 promete "el bingo se retoma otro día desde la ronda pendiente", pero `cerrada` es terminal y §4.13 exige todas las rondas cerradas para finalizar | Media | `cerrada -> en_curso` bajo confirmación con auditoría (`reabrir_ronda`). Caso de uso "evento suspendido y retomado" escrito en el guion del ensayo |
| V6 | **`_combinar()` convierte un error de tipeo en silencio permanente.** La misma propiedad que permite ampliar `tema_json` sin migrar hace que una clave mal escrita se ignore para siempre, sin error, sin log, sin prueba | Media | `tema_json` gana `version`, y una prueba compara el conjunto de claves de los dataclasses contra un fixture: ampliar el modelo pasa a ser un cambio consciente |
| V7 | **Contradicción `monitor_transmision: int` vs. "guardar por nombre".** El §5 del plan promete `QScreen.name()`; el campo reservado es `int` | Media | Cambia a `str \| None` en 4.1, con tolerancia de lectura del `preferencias.json` viejo (un `int` guardado se descarta y se vuelve a preguntar) |
| V8 | **El criterio "legible en un celular" no tiene método de verificación.** Es el único criterio del contrato que depende de una percepción | Media | `docs/Fase_5/Ensayo.md` fija el alto mínimo del número actual como fracción del lienzo y exige una captura del móvil viendo la emisión privada, adjunta como evidencia |
| V9 | **El ensayo del plan perdió dos cosas que el contrato sí pide:** la emisión privada real y **medir el retraso de la plataforma** — número que, según el alcance §6.1, va impreso en el cartón | Alta | §4.16 se corrige: el ensayo incluye emisión a un canal privado y cronometrado contra el reloj de la pantalla. El resultado alimenta `TEXTO_INFERIOR_DEFECTO`, que hoy dice "que tiene retraso" sin número |

### A.13.2 Donde las dos voces discrepan (van al gate)

- **H6 / Approach C — overlay web en OBS Browser Source.** La primaria lo evaluó y
  lo rechazó por DRY (duplica el editor de tema de la fase 4) y por abrir un puerto
  en la máquina con datos personales. El subagente aporta dos argumentos que la
  primaria no había pesado: **canal alfa** (que una ventana Qt no tiene) y **no
  necesitar un segundo monitor**. Síntesis propuesta, que ninguna de las dos voces
  tenía sola: **la decisión se toma con el resultado del spike de OBS, no antes.**
  Si OBS captura la ventana Qt limpiamente, gana la nativa por DRY. Si captura en
  negro o el DPI fraccional desalinea el lienzo, la ruta web deja de ser una
  preferencia y pasa a ser la salida. Escrito así en D14.
- **Calibración del alcance.** La primaria acepta los doce grupos con un orden
  interno de recorte; el subagente exige partir en tres etiquetas y aporta el
  precedente más fuerte del repositorio: las fases 3 y 4 entraron en un solo commit
  de 12.209 líneas el mismo día, y `TODOS.md` cierra con **doce** recortes hechos
  "para que la fase entrara en una sola sesión". El argumento es bueno: este
  proyecto, cuando una fase se sobredimensiona, no se alarga — recorta en silencio.
  → **UC-3 al gate.**
- **Locución (M1 del subagente).** Propone eliminarla: el operador ya está frente al
  micrófono cantando el número, y su voz es mejor que cualquier SAPI. Quitarla se
  lleva `QtMultimedia`/`QtTextToSpeech` de PyInstaller, que es un riesgo declarado
  del §5. La primaria la mantiene porque el contrato §5.8 la pide explícitamente.
  → **UC-4 al gate.**
- **Commit-reveal de la semilla (H4 del subagente).** El alcance §7 lo excluye de la
  v1 explícitamente. El subagente desafía esa exclusión: se excluyó cuando parecía
  caro, y con el bombo recibiendo el `rng` por contrato (§4.2) cuesta un día.
  Anunciar `SHA-256(semilla)` antes de la primera bola y revelar la semilla en el
  acta permite que **cualquiera** recompute la secuencia. Es el mayor movimiento de
  confianza disponible, y la primaria coincide en que la confianza es el activo
  diferencial (Layer 3). → **UC-5 al gate.**
- **Orden de recorte del §5.** El subagente señala que está invertido: el plan dice
  "si algo se recorta, se recorta de 4.10 (sonido) y 4.14 (empaquetado)", pero
  empaquetar es criterio de aceptación y PyInstaller con `QtMultimedia` es célebre
  por fallar tarde. → **Corregido sin gate** (P1 completitud): el `.exe` de humo
  pasa a la **semana 1**, no a la última. Solo el sonido queda como candidato a
  recorte.

### A.13.3 Hallazgos del subagente aceptados como riesgo, no corregidos

- **C4(b) — el `.zip` de respaldo no debería incluir la tabla `comprador` por
  defecto.** Buena idea, pero cambia el significado de "respaldo": si el `.zip` no
  trae compradores, restaurarlo en un segundo equipo deja el evento sin poder
  determinar ganadores elegibles, que es justo el escenario de C1. Se resuelve al
  revés: el `.zip` **sí** lleva todo (es un respaldo operativo), y lo que se
  entrega a la organización es el reporte, no el respaldo. Se escribe así en D11.
- **El punto de fallo humano** ("una persona presenta, opera, vigila WhatsApp,
  valida códigos y decide empates"). No tiene arreglo de software. Entra en la tabla
  de riesgos del §5 con la mitigación sin código que propone el subagente: una
  segunda persona con el runbook impreso, que sabe pausar y sabe dónde está el
  `.zip`. Y el ensayo del §4.16 se corrige para que Gabriel **presente de verdad**,
  no solo opere.

---

# ANEXO B — Revisión de diseño (`/gstack-autoplan` Fase 2)

Alcance de interfaz detectado en la Fase 0 (16 coincidencias). Codex no disponible;
la fase corre `[subagent-only]` con una voz independiente de diseño.

## B.0 Evaluación de alcance de diseño

**Calificación inicial: 5/10.** El plan describe con detalle qué *hace* cada
superficie y con muy poco detalle qué *ve* el operador y qué *ve el público*.
Enumera ocho paneles del operador en una lista plana y once bloques de transmisión
sin decir cuál manda. Un 10 sería: jerarquía primaria/secundaria/terciaria escrita
para las dos superficies, tabla de estados de interacción completa, y el guion
emocional de una ronda de principio a fin.

**Clasificador de modo — es un híbrido, y tratarlo como una sola cosa es el error
de fondo:**

- **Superficie del operador = OPERATE (App UI).** El operador termina una tarea
  contra reloj. Manda la escaneabilidad. Reglas: jerarquía de superficie tranquila,
  tipografía fuerte, pocos colores, **nada de mosaico de tarjetas**.
- **Ventana de transmisión = EXPERIENCE.** El público está *dentro* de la obra: el
  juego llena el primer viewport y la interfaz se aparta. La regla dura que aplica
  aquí es "la obra llena la pantalla, el cromo se gana cada píxel".

Tratar las dos con la misma cabeza produce, en un lado, un operador convertido en
tablero de instrumentos, y en el otro, una transmisión llena de widgets. Las dos
fallas son la misma falla.

**DESIGN.md: no existe.** Pero el proyecto **sí tiene sistema de diseño de facto**,
y está en el código, no en un documento:

| Token / patrón | Dónde vive | Valor |
|---|---|---|
| Tema neutro fijo del operador | `ui/tema.py::aplicar_tema_operador` | decisión DU-1 |
| Base tipográfica | `ui/tema.py` | `font-size: 13px` |
| Radio | `ui/tema.py` | 6 px (8 px en tarjetas) |
| Anillo de foco | `ui/tema.py::_ANILLO_FOCO` | borde 2 px |
| Semántica de color | `_BORDE`, `_ACENTO`, `_PELIGRO`, `_EXITO` | 4 roles, no más |
| **Cálculo de contraste WCAG** | **`ui/tema.py::contraste()`** | ya escrito, sin consumidor |
| Mínimos de accesibilidad | `ui/atajos.py` | `TIPOGRAFIA_MINIMA_PX = 13`, `OBJETIVO_PULSACION_MINIMO_PX = 32` |
| Canales de error | `ui/dialogos.py` | en línea / franja / modal |
| Guardado explícito vs. autoguardado | convención DS14 | por tipo de entidad |
| Retraducción | `retraducir()` + `WeakSet` | obligatorio en todo widget |

Que `contraste()` exista y **no lo llame nadie** es el hallazgo de diseño más
aprovechable de esta fase: la herramienta para impedir una transmisión ilegible ya
está escrita.

## B.1 Pass 1 — Arquitectura de la información · **4/10 → 9/10**

**Por qué era un 4.** El §4.8 lista ocho superficies del operador en una lista plana
(cabecera, seis botones, tablero, contador, panel de a-una-bola, panel de ganadores,
buscador, selector de monitor, botón de modo en vivo) sin decir nunca cuál es
primaria. Una lista plana en un plan se convierte, sin falta, en un `QVBoxLayout` de
`QGroupBox` apilados: exactamente el "mosaico de tarjetas" que la regla de App UI
prohíbe, y exactamente lo peor para alguien que mira de reojo con una cámara delante.

**Prueba de la adoración por la restricción.** Si el operador solo pudiera ver tres
cosas mientras juega, son estas y en este orden:

1. **La bola que acabo de cantar** (y las últimas cuatro, porque la gente pregunta).
2. **Quién está a punto de ganar y quién ganó** — el número de tablas a una bola es
   la única señal de "esto se pone tenso"; la lista de ganadores es la que exige
   actuar.
3. **El botón de extraer**, con el contador de cuántas van.

Todo lo demás (buscador, selector de monitor, configuración de la ronda) es
secundario y puede vivir en una barra lateral estrecha o detrás de un atajo.

```
  SUPERFICIE DEL OPERADOR — jerarquía (modo en vivo, 1920x1080)
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Ronda 2 de 3 · Línea horizontal · Premio: canasta navideña   [○ EN VIVO]│  terciario
  ├──────────────────────────────────┬─────────────────────────────────────┤
  │                                  │  A UNA BOLA            3            │
  │            ┌───────┐             │  ─────────────────────────────────  │  SECUNDARIO
  │            │  B-7  │  ← 96 px    │  A-0142  María Chávez               │
  │            └───────┘             │  A-0311  Luis Ortega                │
  │      52  I-19  N-44  G-51        │  A-0077  (venta en puerta)          │
  │      ↑ las últimas cuatro        │                                     │
  │                                  ├─────────────────────────────────────┤
  │   [ EXTRAER BOLA ]   28 / 75     │  GANADORES                          │  PRIMARIO
  │   ↑ objetivo de pulsación grande │  (vacío hasta que haya)             │  cuando aparece
  ├──────────────────────────────────┴─────────────────────────────────────┤
  │ TABLERO 1-75, las cantadas resaltadas                                  │  secundario
  ├────────────────────────────────────────────────────────────────────────┤
  │ Buscar código: [________]  ·  Monitor: [HDMI-2 ▾]  [Ocultar transmisión]│  terciario
  └────────────────────────────────────────────────────────────────────────┘
```

Regla que se escribe en el plan: **el panel de ganadores está vacío casi todo el
tiempo y, cuando aparece, es lo más importante de la pantalla.** No es una tarjeta
más de la pila; es el elemento que se apodera del área secundaria y cambia de color
de borde (`_EXITO`). Un panel de ganadores que se ve igual vacío que lleno es un
fallo de jerarquía, no un detalle estético.

**Arquitectura de la información de la transmisión — el hallazgo más importante de
esta revisión.** El público no ve 1920x1080. Ve un teléfono en vertical, con el vídeo
ocupando unos 400 px de ancho, comprimido por la plataforma. A ese tamaño **solo
puede haber un elemento primario**, y solo puede ser el número actual.

El editor de tema de la fase 4 deja al operador colocar once bloques con posición y
escala libres entre 0.0 y 1.0. Es decir: **el producto permite configurar una
pantalla ilegible y no avisa.** Eso no es libertad, es una trampa. Correcciones:

- `dominio/tema.py::validar` exige que `numero_actual.escala` no baje de un mínimo
  que garantice ~14% del alto del lienzo (≈150 px sobre 1080, que sobreviven al
  reescalado a un teléfono). Por debajo, `ErrorValidacion`.
- El editor trae un **preset "Legible en celular"** que es el valor por defecto y al
  que se vuelve con un botón. La libertad se conserva; el defecto es seguro.
- La vista previa del editor gana un botón **"Ver como celular"** que la reescala a
  la proporción de un móvil viendo la transmisión. Es la única forma de que el
  operador vea el problema antes del evento y no durante.

## B.2 Pass 2 — Cobertura de estados de interacción · **3/10 → 9/10**

**Por qué era un 3.** Tras la revisión CEO el plan tiene el estado vacío de la
sección Sorteo (S5-16) y poco más. Faltaban la carga, lo parcial y varios errores
visibles. Los estados vacíos son funcionalidad, no relleno: son lo que el operador
ve la primera vez que abre la sección, con público esperando.

```
  FUNCIÓN                  | CARGANDO            | VACÍO                    | ERROR                      | ÉXITO                    | PARCIAL
  -------------------------|---------------------|--------------------------|----------------------------|--------------------------|---------------------------
  Sección Sorteo (entrar)  | —  (es instantáneo) | "Faltan N cosas para     | Franja + reintentar        | Controles activos        | —
                           |                     |  jugar: ..." con los     |                            |                          |
                           |                     |  pendientes de           |                            |                          |
                           |                     |  validar_evento_listo    |                            |                          |
  Iniciar ronda            | Barra indeterminada | "Esta ronda no tiene     | Franja con el motivo       | Tablero limpio, botón    | —
   (cargar 1.000 cartones) | + texto "Cargando   |  cartones elegibles"     | exacto                     | Extraer con foco         |
                           |  cartones..."       |  + enlace a Compradores  |                            |                          |
  Extraer bola             | Botón deshabilitado | —                        | Franja; **la bola NO se    | Número grande + sonido   | —
                           | hasta el commit     |                          | pinta** (no hubo commit)   | + locución               |
  Reanudar ronda           | "Reconstruyendo la  | —                        | Modal terminal con los     | "Reanudado en la bola N" | Modal de incoherencia
                           |  partida..."        |                          | dos conjuntos (D13)        |                          | con opción de seguir
  A una bola               | —                   | **No se pinta el panel** | —                          | Lista con código y       | —
                           |                     | (cero ruido cuando no    |                            | comprador                |
                           |                     |  hay tensión)            |                            |                          |
  Ganadores detectados     | —                   | Panel ausente            | —                          | Panel con borde `_EXITO` | Uno confirmado y otros
                           |                     |                          |                            | + cuenta regresiva       | pendientes: los pendientes
                           |                     |                          |                            |                          | siguen visibles
  Buscar código            | —                   | "Sin resultados para     | "Ese código no es de este  | Cartón pintado +         | Cartón vendido pero sin
                           |                     |  «A-9999»"               | evento"                    | veredicto Cumple/No      | comprador vivo: se dice
  Ventana de transmisión   | —                   | "No hay segundo monitor  | "El monitor guardado ya    | Chip EN VIVO en la       | Abierta pero en el mismo
                           |                     |  detectado" + qué hacer  | no existe" + selector      | cabecera del operador    | monitor: aviso explícito
  Generar acta             | Cursor de espera    | —                        | Franja con la ruta         | "Acta guardada en ..."   | —
                           |                     |                          |                            | + botón Abrir/Verificar  |
  Exportar respaldo        | `Tarea` con         | —                        | Franja                     | "Respaldo en ..." +      | Cancelado: ningún `.zip`
                           | progreso y cancelar |                          |                            | Abrir carpeta            | a medias en disco
  Restaurar respaldo       | Barra + "No cierres | —                        | Modal: zip inválido /      | "Restaurado. Abriendo    | —
                           | la aplicación"      |                          | versión de esquema mayor   | evento ..."              |
  Locución / sonido        | —                   | —                        | Casilla gris + motivo      | —                        | Pregrabado incompleto:
                           |                     |                          | ("sin voz para en_US")     |                          | cae a TTS y lo dice
```

Dos reglas de estado vacío que se escriben en el plan porque son decisiones, no
detalles: **el panel de a-una-bola y el de ganadores no existen cuando están
vacíos.** No se pintan en gris con "ningún ganador todavía". Que aparezcan *es* la
señal. En una pantalla que se mira de reojo, un contenedor permanente vacío es ruido
que entrena al ojo a ignorar la zona donde luego aparecerá lo único urgente.

## B.3 Pass 3 — Recorrido y arco emocional · **4/10 → 9/10**

```
  PASO | EL OPERADOR HACE        | SIENTE                  | ¿EL PLAN LO SOSTIENE?
  -----|-------------------------|-------------------------|----------------------------------
  1    | Abre la sección Sorteo  | "¿está todo listo?"     | Sí, tras S5-16: dice qué falta
  2    | Pulsa Iniciar ronda     | compromiso, sin retorno | **Faltaba**: recordatorio de
       |                         |                         | respaldo (4.12) sin bloquear
  3    | Extrae la primera bola  | alivio, arranca         | Sí: número grande, sonido
  4    | Extrae 20 más           | ritmo, aburrimiento     | Sí: modo automático con intervalo
  5    | Aparece "3 a una bola"  | tensión que sube        | Sí, y es lo que hace mirable la
       |                         |                         | transmisión sin ganador todavía
  6    | ¡BINGO! detectado       | adrenalina + carga      | Parcial: la pausa automática sí,
       |                         | mental de golpe         | pero el operador tiene que hablar
       |                         |                         | y validar a la vez → ver abajo
  7    | Recibe el reclamo       | duda: "¿es el suyo?"    | Sí, tras V3 (ventana de reclamo)
       | por WhatsApp            |                         | y V4 (QR además de código)
  8    | Confirma al ganador     | cierre, alivio          | Sí: `ganador_confirmado` revela
       |                         |                         | código y nombre en transmisión
  9    | Pasa a la ronda 2       | rutina                  | Sí
```

**Dónde se rompe el arco, y es en el paso 6-7.** Entre "¡BINGO!" y "ganador
confirmado" pasan entre treinta segundos y dos minutos: el reclamante escribe, el
operador teclea el código, mira el cartón, decide. Durante todo ese rato **la
pantalla que ve el público se queda congelada en un cartel de ¡BINGO! sin nombre**.
Eso es aire muerto en directo, que es lo que mata una transmisión.

Correcciones, que no cuestan casi nada porque las piezas ya están:

- La cuenta regresiva de reclamo de V3 **ocupa ese hueco**: el público ve un reloj
  bajando y el patrón completado parpadeando. Pasa de aire muerto a suspense.
- Mientras el operador valida, la transmisión muestra el **patrón completado y el
  premio**, no un cartel estático.
- El aviso de BINGO se acompaña del canal de reclamo ("Escribe al WhatsApp
  09xxxxxxx") — el público necesita saber a dónde gritar, y hoy no está en ninguna
  parte del plan.

**Arco del público en un teléfono (5 segundos / 5 minutos / 5 años).**

- *5 segundos (visceral):* abre el directo. Tiene que entender en un vistazo qué
  número salió y si le sirve. Si el número actual no es lo más grande de la pantalla,
  el producto falló en el primer segundo. Es la justificación del mínimo de escala
  de B.1.
- *5 minutos (conductual):* está marcando su cartón de papel. Necesita el tablero de
  75 para verificar lo que se perdió y el contador para saber cuánto lleva. Ese es
  el segundo nivel, y por eso el tablero es secundario y no terciario.
- *5 años (reflexivo):* recuerda que el bingo de su barrio se veía **serio**. La
  identidad de la organización (logo, colores, premio) es lo que sostiene ese
  recuerdo, y por eso el tema de transmisión sí lleva marca aunque el operador no
  (DU-1). El plan ya lo hace bien.

## B.4 Pass 4 — Riesgo de interfaz genérica · **6/10 → 9/10**

No aplica la lista de "slop" de páginas de marketing (no hay héroe, ni CTA, ni
rejilla de tres columnas). Sí aplican dos reglas duras de App UI, y una de ellas se
estaba incumpliendo:

| Regla dura | ¿Se incumple? | Evidencia / corrección |
|---|---|---|
| "Interfaz de aplicación hecha de tarjetas apiladas en vez de una disposición" | **Sí, riesgo alto** | Ocho paneles listados en plano en §4.8 se convierten en ocho `QGroupBox` apilados. Corregido con la disposición de B.1: dos columnas, jerarquía explícita, y los paneles vacíos que no se pintan |
| "Las tarjetas solo cuando la tarjeta *es* la interacción" | Parcial | El panel de ganadores sí es una tarjeta legítima (cada ganador es una unidad accionable con sus botones). El contador y el buscador no: son texto y un campo |
| "Superficie tranquila, tipografía fuerte, pocos colores" | Se cumple | `ui/tema.py` ya impone 4 roles de color. La regla se mantiene: la sección Sorteo **no** introduce colores nuevos; usa `_ACENTO` para la bola actual y `_EXITO` para el borde del panel de ganadores |
| "Encabezados que dicen qué es el área o qué puede hacer el usuario" | A verificar | "Ganadores", "A una bola", "Tablero" — correctos. Nada de "Panel de control" ni "Información de la ronda" |
| "Copia de utilidad: orientación, estado, acción" | Se cumple | Todo pasa por `t()`, y las claves nuevas van bajo `sorteo.*` |

**Prueba de calibración de las tres estéticas.** ¿Se podría adivinar la estética de
la ventana de transmisión sabiendo solo la categoría ("bingo")? Si la respuesta
fuese "bolas de colores primarios, tipografía redondeada y confeti", habríamos
dejado de mirar. No es el caso: **la estética la fija la organización**, no la
categoría — sus colores, su logo, su imagen de premio, sobre el lienzo que el
operador compone. Esa es la decisión correcta y ya está tomada (DU-1 + `tema_json`).
Lo que faltaba no era estética, era el suelo de legibilidad de B.1.

## B.5 Pass 5 — Alineación con el sistema de diseño · **5/10 → 9/10**

No hay `DESIGN.md`, pero sí sistema de facto (tabla de B.0). El plan reusa bien tres
cosas (widget de cartón, canales de error, `retraducir()`) y se le escapaban cuatro:

| Elemento | Estado en el plan | Corrección |
|---|---|---|
| `ui/tema.py::contraste()` | **No se usa** | El editor de tema valida el contraste de `texto` sobre `fondo` y de `numero_actual` sobre `fondo`: por debajo de 4.5:1 avisa en línea (no bloquea — puede haber una imagen de fondo detrás), y el preset "Legible en celular" siempre pasa |
| `atajos.TIPOGRAFIA_MINIMA_PX` / `OBJETIVO_PULSACION_MINIMO_PX` | No se mencionan | El botón Extraer es el objetivo de pulsación más grande de la aplicación (≥ 64 px de alto): se pulsa a ciegas, mirando a la cámara |
| Convención DS14 (guardar explícito vs. autoguardado) | Ambigua para la sección Sorteo | La sección Sorteo **no edita entidades**: ejecuta acciones. No le aplica DS14 ni necesita Guardar/Cancelar. Se escribe para que nadie herede el atajo de `vista_rondas.py` |
| Canales de error de `ui/dialogos.py` | Mencionados de pasada | Mapeados uno a uno en la tabla de B.2 y en el registro de errores del §A.9 |
| Bandera `modo_vivo` | Definida, sin regla | **Regla explícita:** `modo_vivo` degrada de modal a franja **solo** los errores no terminales. Base corrupta, migración fallida y sin permisos siguen siendo modales incluso en directo — un modal feo en cámara es mejor que seguir jugando sobre una base rota |

## B.6 Pass 6 — Adaptabilidad y accesibilidad · **4/10 → 9/10**

No hay móvil que soporte en el sentido habitual (la aplicación es de escritorio), pero
hay algo más difícil: **una de las dos superficies se consume en un teléfono ajeno,
comprimida por una plataforma de vídeo, y no podemos probarla en el navegador.**

| Eje | Especificación que se añade al plan |
|---|---|
| Legibilidad en celular | Número actual ≥ 14% del alto del lienzo (B.1). Verificado con captura real en el ensayo (V8) |
| Contraste en transmisión | `contraste()` en el editor; el preset por defecto pasa 4.5:1 sobre el fondo plano |
| Compresión de vídeo | Nada de texto fino sobre imagen de fondo: el bloque de número actual lleva un fondo sólido o un halo opaco detrás. La compresión destruye texto delgado sobre textura |
| Resoluciones de salida | 1920x1080 nativo; 1280x720 escalado; proyector 4:3 con barras. Los tres se prueban en el ensayo |
| Teclado, ámbito operador | `Espacio` extraer, `P` pausar, `Ctrl+F` buscar, `Ctrl+Enter` confirmar, `F11` modo en vivo, `R` repetir locución, `Esc` salir de modo en vivo |
| Teclado, ámbito transmisión | La ventana de transmisión **no recibe foco de teclado nunca** (`Qt.WindowDoesNotAcceptFocus`): un `Alt+F4` accidental en directo no puede matarla, y el foco no se escapa del operador |
| Orden de tabulación | Extraer → panel de ganadores → buscador → controles secundarios. El orden del recorrido, no el del código |
| Anillo de foco | Ya existe en `ui/tema.py`; obligatorio en los controles nuevos |
| Objetivo de pulsación | ≥ 32 px general (`atajos.py`), ≥ 64 px el botón Extraer |
| Daltonismo | El tablero de 75 no distingue cantadas solo por color: la celda cantada cambia de fondo **y** de peso tipográfico |
| Lector de pantalla | Fuera de alcance declarado: no hay usuario ciego operando un bingo en cámara, y prometerlo sin probarlo es peor que no prometerlo. Se escribe como decisión, no como olvido |

## B.7 Pass 7 — Decisiones de diseño sin resolver

| Decisión | Si se deja abierta, qué pasa | Resolución |
|---|---|---|
| ¿Qué ve el público entre BINGO y la confirmación? | Cartel estático, 90 s de aire muerto en directo | Cuenta regresiva de reclamo + patrón parpadeando + canal de reclamo (B.3) |
| ¿Cuál es el elemento primario de la transmisión? | El operador configura once bloques iguales y nadie lee nada en un teléfono | Número actual, con mínimo de escala validado (B.1) |
| ¿Los paneles vacíos se pintan? | Se ships "Ningún ganador todavía" en gris, y el ojo aprende a ignorar esa zona | No se pintan (B.2) |
| ¿La sección Sorteo lleva Guardar/Cancelar? | Se hereda el atajo de `vista_rondas.py` sin pensarlo | No: ejecuta acciones, no edita entidades (B.5) |
| ¿Qué pasa con un solo monitor? | El operador descubre en el evento que no puede transmitir | Estado explícito: "No hay segundo monitor" + la ventana se puede abrir igual en modo ventana para pruebas |
| ¿`modo_vivo` silencia todos los modales? | Se silencia una base corrupta en directo | Solo los no terminales (B.5) |
| Tipografía de los números de la transmisión | El implementador usa la del sistema y se ve a plantilla | Del combo cerrado ya empaquetado (G24): Open Sans para números, con `QFont` de peso alto y **cifras tabulares** — el número actual cambia cada seis segundos y no debe bailar |

## B.8 Voces duales — Diseño

**Codex:** no disponible. Fase etiquetada `[subagent-only]`.

**Claude subagente (diseño de producto, independiente):** revisión completa sin haber
visto la primaria, con lectura del código de `ui/`. Veredicto textual: *"es un plan de
ingeniería excelente con una capa de diseño que no existe"*. Media 3.4/10 en diseño
frente al 9 que sacaría la ingeniería del mismo documento. **La revisión primaria se
había quedado corta**: puntuó 4-6/10 de partida donde la voz independiente puntúa
2-3/10, y con razón — cinco de sus hallazgos son fallos en directo que la primaria no
vio.

Afirmaciones materiales, verificadas una por una contra el código antes de
incorporarlas:

| Afirmación del subagente | Verificación | Resultado |
|---|---|---|
| Los dos botones de la cabecera (`volver`, `cerrar`) emiten `cerrado` sin confirmación, y `ventana_principal` hace `deleteLater()` sobre `EspacioEvento` | `espacio_evento.py:107,114`; `ventana_principal.py:101,116` | **Confirmada.** Destruyen en un clic el objeto que S5-3 puso ahí para sobrevivir |
| `vista_tema._guardar` escribe el objeto de tema **completo** con `QTimer` de retardo y no recarga nunca | `vista_tema.py:398-410` (`actualizar_tema(..., self._tema.a_json())`) | **Confirmada.** Dos editores del mismo JSON = el último borra al otro |
| `FranjaError.mostrar_exito` existe y el plan no la invocaba ni una vez | `ui/dialogos.py:110` (`#franjaExito`) | **Confirmada** |
| `TIPOGRAFIA_MINIMA_PX` / `OBJETIVO_PULSACION_MINIMO_PX` existen desde la fase 1 y solo los usa `rejilla_patron.py` | `grep -rn` sobre `src/` | **Confirmada.** Se escribieron para esta fase |
| Todos los bloques del tema nacen en `pos (0,0)` salvo `tablero_75` | `dominio/tema.py::ConfigBloque` + `_tablero_75_por_defecto` | **Confirmada.** Siete bloques superpuestos en el origen en un evento nuevo |
| `ConfigColores` no tiene `numero_actual`, que el doc técnico §7 sí define | `dominio/tema.py::ConfigColores` vs. `Documento_Tecnico.md` §7 | **Confirmada** |
| `acento` y `tablero_marcado` tienen **el mismo** valor por defecto `#5b8def` | `dominio/tema.py::ConfigColores` | **Confirmada.** Resaltado y acento indistinguibles |
| `ConfigJuego.mostrar_ultimas_bolas = 5` existe desde la fase 4 y no hay bloque que lo pinte | `dominio/tema.py::ConfigJuego` vs. lista de bloques del §4.9 | **Confirmada** |

```
DESIGN DUAL VOICES — LITMUS SCORECARD:
═════════════════════════════════════════════════════════════════════════
  Dimensión                            Primaria  Subagente  Codex  Consenso
  ───────────────────────────────────  ────────  ─────────  ─────  ────────
  1. Jerarquía de información            4/10      3/10      N/A   ACUERDO
  2. Cobertura de estados                3/10      4/10      N/A   ACUERDO
  3. Recorrido y arco emocional          4/10      3/10      N/A   ACUERDO
  4. Especificidad / interfaz genérica   6/10      3/10      N/A   DISCREPA
     (la primaria juzgó "no aplica la                                → la
      lista de slop de marketing" y se                                subagente
      quedó ahí; la independiente midió                               tiene razón
      la especificidad *dentro* del
      propio documento: D3 trae SQL
      literal y la superficie del
      operador cabe en cinco renglones)
  5. Alineación con el sistema           5/10      6/10      N/A   ACUERDO
  6. Accesibilidad y legibilidad         4/10      2/10      N/A   DISCREPA
     (la primaria no vio que las                                     → la
      constantes de la fase 1 llevan                                  subagente
      cuatro fases sin usarse, ni que                                 tiene razón
      acento == tablero_marcado)
  7. Consistencia con las 4 fases        —         6/10      N/A   N/A
═════════════════════════════════════════════════════════════════════════
Consenso: 4/7 acuerdo, 2 discrepancias resueltas a favor de la voz
independiente (con evidencia de código), 1 dimensión que la primaria no
había evaluado por separado.
Media tras las correcciones de §3-bis: 8.5/10.
```

### B.8.1 Hallazgos de la voz independiente incorporados

Dieciocho hallazgos, todos verificados. Los cinco críticos y los altos se convierten
en las decisiones DU-2 a DU-18 del **§3-bis**, que es la sección que la voz
independiente pedía explícitamente ("el plan necesita una sección de decisiones de
interfaz con el mismo nivel de dureza que D1-D14").

| # | Hallazgo | Sev. | Dónde queda |
|---|---|---|---|
| D-01 | Superficie del operador como lista de trece componentes sin jerarquía | **Crítica** | DU-2 (tres zonas con proporciones) |
| D-03 | Siete bloques de transmisión superpuestos en el origen; `validar()` no detecta solapes | **Crítica** | DU-4 |
| D-08 | **La máquina canta bingo antes que el jugador.** Con `sin_reclamo="continuar"` la ronda sigue extrayendo tras haber gritado ¡BINGO! | **Crítica** | DU-3 (nueve estados; `HAY_CARTON_GANADOR` sin la palabra BINGO) |
| D-12 | Dos botones a tres centímetros del riel destruyen `EspacioEvento` —y la partida— sin confirmación | **Crítica** | DU-11 |
| D-13 | `Espacio`/`P`/`R` colisionan con el buscador; `showFullScreen()` roba la activación en Windows | **Crítica** | DU-5 |
| D-15 | Dos editores de `tema_json` con autoguardado de objeto completo: pérdida de datos silenciosa | **Crítica** | DU-7 |
| D-02 | El operador no puede ver lo que ve el público | Alta | DU-8 (monitor de confianza) |
| D-04 | `mostrar_ultimas_bolas` existe desde la fase 4 y ningún bloque lo pinta | Alta | DU-4 (`ultimas_bolas` de primera clase) |
| D-05 | Ningún estado de éxito especificado, con `mostrar_exito` ya escrita | Alta | DU-14 (tabla de ocho acciones) |
| D-06 | Sin estado de ocupado en `iniciar_ronda` ni en `restaurar` | Alta | DU-15 |
| D-07 | "A una bola" sin diseño para sesenta cartones | Alta | DU-10 (umbrales) |
| D-09 | Sin diseño para los huecos entre rondas ni para la pausa — el mayor porcentaje de tiempo de pantalla del evento | Alta | DU-3 (`ENTRE_RONDAS`, `PAUSA`) |
| D-10 | El arco del público en un móvil no está considerado | Alta | DU-6 + guion del ensayo con tres medidas, no una |
| D-11 | Dos entradas de código y ninguna decisión de cuál es la del reclamo | Alta | DU-9 (un campo, dos botones) |
| D-14 | `modo_vivo` contradice sus propios casos de uso | Alta | DU-12 (tabla oculta/sobrevive) |
| D-16 | Un solo monitor no contemplado | Alta | DU-17 |
| D-19 | Constantes de accesibilidad de la fase 1 sin usar en la fase para la que se escribieron | Alta | DU-6 |
| D-20 | Cero validación de contraste; `acento == tablero_marcado` | Alta | DU-6 (`contraste()` a `dominio/`, umbral 7:1) |
| D-17 | Idioma del texto de transmisión sin decidir | Media | DU-13 |
| D-18 | El riel se contradice: D10 dice siete secciones, el plan crea ocho | Media | DU-16 |
| D-21 | Falta `colores.numero_actual` | Media | DU-6 |
| D-22 | El tablero codifica solo por color y no distingue la última cantada | Alta | DU-6 |
| D-23 | "Legible en celular" mide un solo elemento | Media | Guion del ensayo (§4.16) |
| D-24 | DS14 sin resolver para la superficie nueva | Alta | DU-7 (tercer caso, declarado en convenciones) |
| D-25 | `retraducir()` en una ventana que pinta en `paintEvent` | Media | DU-13 (corolario) |
| D-26 | `modo_vivo` sin dueño: primera pieza de estado global de interfaz del proyecto | Media | DU-12 (parámetro explícito, sin estado global) |

### B.8.2 Discrepancias con la voz independiente

Una sola, y menor: el subagente propone mover **todos** los controles de juego fuera
de la sección Tema. DU-7 los reparte en vez de moverlos: los de **directo** (modo,
intervalo, sonido, voz) a Sorteo; los de **preparación** (`pausa_al_ganador`,
`segundos_reclamo`, `sin_reclamo`, `confirmar_extraccion`, `mostrar_ultimas_bolas`,
`idioma_publico`) se quedan en Tema, que es donde el operador prepara el evento con
tiempo. Mover a Sorteo un ajuste que se decide una semana antes obligaría a abrir la
sección de directo para configurarlo, que es justo lo contrario de lo que DU-2 busca.

No genera decisión de gusto para el gate: es un reparto, no un desacuerdo de fondo.

---

# ANEXO C — Revisión de ingeniería (`/gstack-autoplan` Fase 3)

Corre **la última**, sobre el plan ya enmendado por las fases CEO y de diseño, porque
es la puerta de embarque: tiene que revisar lo que realmente se va a construir.
Codex no disponible; `[subagent-only]`.

## C.0 Desafío de alcance (leído en el código)

El §2 del plan mapea cada sub-problema a código existente. Se verificó fila por fila
abriendo los archivos; el mapa es honesto y no hay nada que se reconstruya. Lo que
esta revisión añade son los **tres puntos donde el plan asume una API que no se
comporta como cree**.

### C.0.1 Hechos medidos en este equipo

| Hecho | Comprobación | Consecuencia para el plan |
|---|---|---|
| SQLite **3.49.1**, con `json_set` funcionando | `select json_set('{"a":1}','$.b',2)` → `{"a":1,"b":2}` | DU-7 (escritura de campo puntual sobre `tema_json`) es viable sin dependencias |
| `sqlite3.Connection.backup` disponible | `hasattr(con,'backup')` | 4.12 es viable |
| **`secrets.SystemRandom().seed(1)` no lanza: es un no-op silencioso** | probe directo | Trampa real. Ver E-4 |
| `random.Random(secrets.randbits(256))` es determinista y reproducible | probe directo | Es la vía técnica del commit-reveal (UC-5) |

### C.0.2 Diagrama de arquitectura

```
                              ┌──────────────────────────────┐
                              │  ventana_principal.py        │
                              │  (cáscara, sin cambios)      │
                              └──────────────┬───────────────┘
                                             │
                              ┌──────────────▼───────────────┐
                              │  espacio_evento.py           │
                              │  ── DUEÑO del MotorSorteo ──│  S5-3
                              │  ── guarda modo_vivo ───────│  DU-12
                              │  ── confirma antes de cerrar│  DU-11
                              └──────┬─────────────────┬─────┘
                                     │                 │
              ┌──────────────────────▼──┐         ┌────▼──────────────────────┐
              │  ui/sorteo/             │         │  ui/transmision/          │
              │   vista_sorteo.py       │         │   ventana_transmision.py  │
              │   puente_sorteo.py ─────┼─señales─┤   bloques.py  escala.py   │
              │   dialogo_empate.py     │  Qt     │   (9 estados, DU-3)       │
              │   ui/sonido.py          │         │   sin foco de teclado     │
              └──────────┬──────────────┘         └───────────┬───────────────┘
                         │ callbacks                          │ lee
                         │ (nunca Qt hacia abajo)             │
       ┌─────────────────▼───────────────────────┐   ┌────────▼────────────┐
       │  servicios/                             │   │ dominio/tema.py     │
       │   servicio_sorteo.py   (MotorSorteo)    │   │  BLOQUES + validar  │
       │   servicio_ganadores.py                 │   │  + contraste  DU-6  │
       │   servicio_actas.py                     │   └─────────────────────┘
       │   servicio_respaldos.py  (Tarea)        │
       │   servicio_ensayo.py                    │
       └───┬──────────────┬───────────────┬──────┘
           │              │               │
   ┌───────▼──────┐  ┌────▼─────────┐  ┌──▼────────────────────┐
   │ dominio/     │  │ persistencia/│  │ impresion/            │
   │  bombo.py    │  │  repo_extrac │  │  acta.py              │
   │  partida.py  │  │  repo_ganador│  │  reporte.py (+evento) │
   │  acta.py     │  │  repo_ronda+ │  │                       │
   │  estados.py+ │  │  migr/004    │  │  (ReportLab, openpyxl)│
   └──────────────┘  └──────────────┘  └───────────────────────┘
   sin Qt, sin sqlite3   único SQL        sin Qt, sin sqlite3

   utilidades/log_partida.py  ──► escribe DESPUÉS del commit (S5-6)
```

**Acoplamientos nuevos y su justificación:**

| Nuevo acoplamiento | ¿Justificado? |
|---|---|
| `espacio_evento` → `servicio_sorteo` | Sí. Es el dueño del ciclo de vida; sin él la partida muere al cambiar de sección (S5-3) |
| `servicio_compradores` → `repo_ronda` | Sí, y es obligatorio: es la única forma de impedir la venta con ronda en curso (S5-4) |
| `ui/transmision` → `dominio/tema` | Sí. Es lectura de un modelo puro |
| `ui/sorteo` → `ui/transmision` | **Vigilar.** El operador crea y destruye la ventana de transmisión. Debe ser por una interfaz estrecha (`mostrar(pantalla)`, `ocultar()`, `estado(...)`), no manoseando bloques desde la vista del operador |
| `dominio/tema` ← `contraste()` desde `ui/tema` | Sí, y **corrige** una ubicación mala: es matemática pura (DU-6) |

## C.1 Hallazgos de ingeniería

| # | Hallazgo | Sev. | Decisión |
|---|---|---|---|
| E-1 | **`backup()` concurrente con el sorteo puede no terminar nunca.** La API de respaldo en línea de SQLite reinicia la copia cuando la base de origen se modifica desde **otra** conexión. Un respaldo lanzado en un `Tarea` (conexión propia, por convención) mientras la interfaz escribe una bola cada seis segundos es una copia que se reinicia indefinidamente sobre una base de decenas de MB | **Crítica** | El respaldo **se bloquea mientras haya ronda `en_curso` o `pausada`**: el botón se deshabilita con el motivo, y el recordatorio de 4.12 es *antes* de iniciar la primera ronda y *al cerrar* el evento, que es justo cuando no hay ronda viva. Se prueba: exportar con ronda en curso → `ErrorValidacion`, no una espera infinita |
| E-2 | **Zip-slip en `restaurar`.** El `.zip` es un archivo que el operador puede haber recibido por WhatsApp. `extractall` sobre una ruta de `%LOCALAPPDATA%` con miembros manipulados (`..\..\`, rutas absolutas, letra de unidad, enlaces) es escritura arbitraria en el disco del operador | **Crítica** | Extracción miembro a miembro con validación explícita: `Path(destino, nombre).resolve()` tiene que estar **dentro** de `destino.resolve()`; se rechazan rutas absolutas, `..`, letras de unidad y cualquier miembro que no sea archivo regular. Prueba con un `.zip` malicioso construido en la propia prueba |
| E-3 | **`INSERT OR IGNORE` rompe el contrato del verbo `crear`.** La tabla de verbos de `docs/convenciones-codigo.md` dice que `crear` devuelve el modelo persistido con `id` asignado. Con `OR IGNORE`, cuando la fila ya existe `lastrowid` no corresponde a nada y el servicio recibiría un `Ganador` con un `id` mentiroso | Alta | Verbo distinto: `repo_ganador.crear_si_no_existe(con, ganador) -> Ganador \| None` (`None` = ya existía). Se añade a la tabla de verbos de las convenciones, que es la fuente de verdad |
| E-4 | **`SystemRandom().seed()` es un no-op silencioso.** Medido. Cualquier intento de hacer el sorteo reproducible sembrando el generador del contrato "funciona" sin error y no siembra nada | Alta | Se documenta en `dominio/bombo.py`. Y es la restricción técnica de UC-5 (commit-reveal): **no se puede sembrar `SystemRandom`**. La vía correcta es `semilla = secrets.token_bytes(32)` y expansión determinista con `random.Random(int.from_bytes(semilla))`; la impredecibilidad la da `secrets` en la generación, y la verificabilidad la da que la secuencia queda fijada al publicar `SHA-256(semilla)`. El contrato §5.1 dice literalmente `secrets.SystemRandom()`: aceptar UC-5 **modifica el contrato**, y hay que decirlo al aceptarlo |
| E-5 | **La carga canónica del acta necesita versión.** Si el formato cambia en una v1.1, todas las actas emitidas dejan de verificar y el verificador (4.20) empieza a decir "no coincide" sobre documentos legítimos | Alta | `carga_canonica` empieza por `acta/v1\n`, y el verificador lee la versión del propio documento para elegir el serializador. Es una línea hoy y una crisis evitada después |
| E-6 | **`ErrorReanudacion` es una clase nueva y su clave i18n tiene que existir.** `tests/arquitectura/test_arquitectura.py::test_claves_i18n_de_errores_existen_en_es_json` falla si no | Media | Entra en `utilidades/errores.py` con `sorteo.error.reanudacion_incoherente` en `es.json` **y** `en.json` |
| E-7 | **El documento técnico §4.5 se equivoca en el factor del índice inverso: dice "la vigésima parte" y es un tercio.** Un cartón lleva 24 números de 75, así que la probabilidad de que contenga una bola concreta es 24/75 ≈ 0.32. Con mil cartones se tocan ~320 por bola, no 50 | Media | Sigue siendo trivial (320 operaciones de bits por bola, microsegundos), pero la estimación del documento está seis veces desviada y alguien la usará para dimensionar. Se corrige el documento |
| E-8 | **`a_una_bola` como barrido completo cada bola.** `EstadoPartida.a_una_bola(mascaras)` sugiere recorrer los mil cartones tras cada bola. Un cartón solo puede *entrar* en "a una bola" si esa bola lo tocó | Media | Conjunto mantenido incrementalmente: se reevalúan solo los cartones tocados, se añaden y se quitan del conjunto. No es rendimiento (5.000 `popcount` son ~1 ms), es claridad: el barrido completo invita a meter ahí lógica que no escala |
| E-9 | **La selección de monitor no es probable con `QT_QPA_PLATFORM=offscreen`.** `tests/conftest.py` lo fija antes de cualquier import, así que no hay pantallas reales que elegir, y toda la lógica de DU-17 (una pantalla, modo ventana, monitor guardado que desapareció) quedaría sin cubrir | Alta | Costura probable: `ui/transmision/pantallas.py::elegir_pantalla(nombres_disponibles, nombre_guardado) -> Decision` — función pura sobre una lista de nombres, sin Qt. La vista la llama con `[s.name() for s in QGuiApplication.screens()]`. Se prueban los cuatro casos sin necesitar un monitor |
| E-10 | **La migración 004 crea un índice único sobre `ganador` que puede fallar si hay filas duplicadas.** Hoy la tabla está vacía en cualquier base, pero la migración tiene que ser robusta el día que se corra sobre algo inesperado | Media | La 004 borra duplicados antes de crear el índice (`DELETE FROM ganador WHERE id NOT IN (SELECT MIN(id) FROM ganador GROUP BY ronda_id, carton_id)`), con un comentario que explica por qué está ahí |
| E-11 | **`--restaurar` tiene que correr antes del `QLockFile` y antes de abrir la base.** Si se ejecuta después, se restaura sobre una base abierta por el propio proceso, con WAL vivo | Alta | Orden explícito en `__main__.py`: parseo de argumentos → `asegurar_estructura` → **restaurar** → log → preferencias → i18n → `QLockFile` → `abrir_conexion` → migraciones. Y `--restaurar` rechaza continuar si el `QLockFile` ya está tomado por otra instancia |
| E-12 | **El `.exe` no ejecuta las pruebas.** Todo el plan de pruebas corre sobre el árbol de fuentes; el criterio de aceptación "el instalador deja la aplicación funcionando en un equipo limpio sin Python" no lo cubre ni una sola prueba automática | Alta | Prueba de humo del binario, en la **semana 1**: arrancar el `.exe` con `BINGO_HOME` a una carpeta temporal, verificar código de salida 0, que la base llegó a la versión esperada, que las fuentes y los `.wav` se cargaron, y que `QtMultimedia`/`QtTextToSpeech`/`QtPdf` importan dentro del binario. Es un script, no una prueba de `pytest`, y va en `empaquetado/humo.py` |
| E-13 | **`json_set` en `actualizar_juego` sobre un `tema_json` que puede ser `NULL`.** Un evento que nunca abrió la sección Tema tiene `tema_json` a `NULL`, y `json_set(NULL, ...)` devuelve `NULL`: el ajuste se pierde en silencio | Alta | `actualizar_juego` usa `json_set(COALESCE(tema_json, '{}'), ...)`. Prueba explícita con `tema_json IS NULL` |
| E-14 | **El `QTimer` del modo automático y el `QTimer` de autoguardado del tema pueden solaparse.** DU-7 ya para el del tema durante una ronda en juego; falta la simetría: si el modo automático dispara mientras una extracción anterior sigue en curso (disco lento), se encolan | Media | El temporizador del modo automático es de **un solo disparo**, y se rearma al final de cada extracción, no en intervalo fijo. Patrón estándar y elimina el encolado por construcción |
| E-15 | **Un cartón puede ganar dos rondas distintas y el plan no lo dice.** El índice único es `(ronda_id, carton_id)`, así que está permitido — correctamente, es un caso real (la misma persona gana dos veces) | Baja | Se documenta como comportamiento deseado, para que nadie lo "arregle" con un índice por evento. El reporte del evento lo lista dos veces, que es lo correcto |
| E-16 | **Reabrir una ronda cuya acta ya se generó (V5 + 4.20).** Si se reabre, se extraen más bolas y se regenera el acta, el hash cambia — y puede haber un acta impresa circulando con el hash viejo | Alta | Reabrir una ronda con `acta_hash` no nulo exige confirmación con texto explícito ("Ya se generó el acta de esta ronda. Si la reabres, el acta impresa dejará de corresponder"), se registra en auditoría, y el acta nueva lleva un número de revisión (`acta-ronda-2-rev2.pdf`) en vez de pisar la anterior |

## C.2 Diagrama de pruebas y huecos

```
  FLUJOS DE INTERFAZ NUEVOS                     TIPO      ¿EXISTE EN EL PLAN?
  ─────────────────────────                     ────      ───────────────────
  Entrar en Sorteo sin evento listo             UI        sí (4.8, estado vacío)
  Iniciar ronda / extraer / pausar / cerrar     UI        sí (4.8)
  Doble clic en Extraer                         UI        sí (S5-9)
  Buscar código: consultar vs. reclamar         UI        sí (DU-9)   ← NUEVO
  Confirmar ganador único / empate / reparto    UI        sí (4.7)
  Reabrir ronda con acta generada               UI        sí (E-16)   ← NUEVO
  Cerrar el evento con ronda viva               UI        sí (DU-11)  ← NUEVO
  Entrar y salir de modo vivo                   UI        sí (DU-12)
  Elegir monitor / una sola pantalla            UI        sí (E-9, vía costura pura)
  Restaurar respaldo                            UI        sí (4.12)

  FLUJOS DE DATOS NUEVOS                        TIPO      COBERTURA
  ─────────────────────                         ────      ─────────
  bola → extraccion → ganador → ronda → log     Integr.   sí (4.6) + caso OSError del log
  reanudar: extraccion → marcado → comparar     Integr.   sí (4.6, N ∈ {1,15,40,74})
  reclamo → validar → confirmar → auditoría     Integr.   sí (4.7)
  acta → carga canónica → hash → PDF            Unit      sí (4.11) + versión (E-5)
  respaldo → zip → restaurar → abrir            Integr.   sí (4.12) + zip malicioso (E-2)
  tema_json → json_set campo puntual            Unit      NUEVO (E-13, tema_json NULL)

  CAMINOS DE CÓDIGO NUEVOS SIN PRUEBA EN EL PLAN ORIGINAL
  ───────────────────────────────────────────────────────
  ✗ backup con ronda en curso                   → E-1
  ✗ zip con rutas maliciosas                    → E-2
  ✗ crear_si_no_existe cuando ya existe         → E-3
  ✗ json_set sobre tema_json NULL               → E-13
  ✗ elegir_pantalla en sus cuatro casos         → E-9
  ✗ reabrir ronda con acta generada             → E-16
  ✗ ganador anulado + reanudación               → V1 (ya cubierto tras la enmienda)
  ✗ venta con ronda en curso                    → S5-4 (ya cubierto)
  ✗ arranque del .exe empaquetado               → E-12 (script, no pytest)

  PRUEBAS QUE ESCRIBIRÍA UN QA HOSTIL
  ───────────────────────────────────
  · Extraer las 75 bolas con un patrón "cartón lleno" y cero cartones que lo cumplan.
  · Matar el proceso entre el commit de la bola y la escritura del log.
  · Reanudar una ronda cuyo ÚNICO ganador fue anulado.
  · Confirmar un ganador cuyo cartón fue anulado después de la detección.
  · Empate de cuatro cartones en la misma bola, repartir entre tres y rechazar uno.
  · Restaurar un respaldo de un evento que ya existe con el mismo id.
  · Restaurar un respaldo hecho con una versión de esquema MAYOR que la del binario.
  · Cambiar el idioma de la interfaz con la ventana de transmisión abierta (DU-13).
  · Desconectar el segundo monitor con la transmisión a pantalla completa.
```

## C.3 Rendimiento

| Punto | Medida | Veredicto |
|---|---|---|
| Índice inverso por bola | ~320 cartones tocados de 1.000 (no 50, E-7); operaciones de bits | Trivial |
| `a_una_bola` | 5.000 `popcount` si es barrido completo; ~1.600 si es incremental | Trivial, pero se hace incremental por claridad (E-8) |
| Transacción por bola | 1 `INSERT` + 0-N + 1 `UPDATE` + `fsync` con `synchronous=FULL` | Se mide (D2). Presupuesto 50 ms |
| Repintado de transmisión | 1920x1080 a 60 Hz durante la animación | Invalidación por rectángulo + tablero en `QPixmap` cacheado (S5-11) |
| Miniatura del monitor de confianza | 320x180 | Solo al cambiar de estado, nunca a 60 Hz (DU-8) |
| Reanudación | 75 bolas × 320 cartones = 24.000 operaciones de bits | Instantáneo |
| Respaldo | Copia de páginas + `.zip` de medios | En `Tarea`, y bloqueado durante ronda viva (E-1) |
| Generación de actas | Un PDF de 1-2 páginas | Directo, sin `Tarea` |
| Reporte del evento | Cientos de filas en Excel | Directo; si supera 1 s se pasa a `Tarea` |

**Consultas nuevas e índices:** `listar_por_ronda` de `extraccion` usa
`idx_extraccion_ronda(ronda_id, orden)`; `listar_por_ronda` de `ganador` usa
`idx_ganador_ronda`; `obtener_en_juego` filtra por `evento_id` y `estado` —
`ronda` ya tiene `UNIQUE(evento_id, orden)`, que sirve de índice por `evento_id`.
Ninguna consulta nueva queda sin índice.

## C.4 Voces duales — Ingeniería

**Codex:** no disponible. `[subagent-only]`.

**Claude subagente (ingeniería, independiente):** la revisión más dura de las tres.
Veredicto textual: *"cuatro defectos que pierden datos o corrompen el juego en vivo,
y un modelo de ciclo de vida del ganador que está sustancialmente sin diseñar"*.
Encontró además **cinco contradicciones internas** que las ediciones acumuladas de las
fases anteriores habían dejado en el plan. Afirmaciones verificadas antes de
incorporarlas:

| Afirmación | Verificación | Resultado |
|---|---|---|
| `repo_ronda.actualizar` escribe todas las columnas de `_COLUMNAS` desde el objeto en memoria | `repo_ronda.py:20-31, 97-104` | **Confirmada.** Con las cuatro columnas nuevas dentro, `vista_rondas` (que guarda al vuelo) borraría `acta_hash` |
| Toda la suite abre con `synchronous="OFF"` | `tests/conftest.py:58, 75, 83` | **Confirmada.** La prueba que justifica D2 mediría 2 ms y no probaría nada |
| El repositorio ya documenta que hay que hacer checkpoint WAL antes de copiar el archivo | `tests/conftest.py:60-63` | **Confirmada**, y con el comentario explicando por qué |
| `asegurar_estructura()` crea solo `datos`, `logs`, `respaldos`, `medios` | `config/rutas.py:89-92` | **Confirmada.** Ni `impresos/` ni `logs/<evento_id>/` |
| `preferencias.cargar` captura `TypeError` y renombra **el archivo entero** a `.corrupto` | `config/preferencias.py:50, 58-64` | **Confirmada.** Una clave desconocida en `ventana` pierde idioma, geometría y último evento |
| `verificar_qr` devuelve `None` tanto si no hay `\|` como si la firma es inválida | `dominio/firma.py:45-59` | **Confirmada.** El fallback ingenuo dejaba pasar `A-0142\|00000000` |
| `LONGITUD_HMAC = 8` (32 bits) | `dominio/firma.py:26` | **Confirmada** |
| `conexion.transaccion()` no es reentrante y lanza `ErrorPersistencia` al anidarse | `conexion.py:101-104` | **Confirmada.** El riesgo real no es el lock, es un bucle de eventos anidado |
| `__main__.py` parsea banderas con `in argv`, sin argparse | `__main__.py:26-28` | **Confirmada.** No sabe leer `--restaurar <valor>` |
| Códigos de salida 0/2/3/4/5 ocupados | `__main__.py` docstring | **Confirmada.** La restauración necesita el 6 |

```
ENG DUAL VOICES — CONSENSUS TABLE:
═══════════════════════════════════════════════════════════════════════
  Dimensión                          Primaria  Subagente  Codex  Consenso
  ─────────────────────────────────  ────────  ─────────  ─────  ────────
  1. Arquitectura sólida               sí        no        N/A   DISCREPA
     (la primaria validó las fronteras;                          → la
      la independiente encontró que los                          subagente
      callbacks corren dentro del stack                          tiene razón
      de extraer(), que _COLUMNAS borra
      acta_hash, y que nadie mueve el
      evento a en_curso)
  2. Cobertura de pruebas suficiente   sí        no        N/A   DISCREPA
     (T1: la prueba que justifica D2                             → la
      corre con synchronous=OFF;                                 subagente
      T2: "cerrar la conexión" es un                             tiene razón
      cierre limpio, no matar el proceso)
  3. Riesgos de rendimiento cubiertos  sí        parcial   N/A   ACUERDO
  4. Amenazas de seguridad cubiertas   parcial   no        N/A   DISCREPA
     (S1 el QR se salta con firma basura;                        → la
      S2 clave_evento viaja en el .zip                           subagente
      y permite fabricar QRs válidos)                            tiene razón
  5. Caminos de error manejados        sí        no        N/A   DISCREPA
     (B1: la bola se evapora si la                               → la
      transacción falla — el peor fallo                          subagente
      silencioso posible en este producto)                       tiene razón
  6. Riesgo de despliegue manejable    parcial   no        N/A   DISCREPA
     (P1: hiddenimports no trae los                              → la
      plugins nativos de Qt; P2: sin                             subagente
      firma de código, SmartScreen)                              tiene razón
═══════════════════════════════════════════════════════════════════════
Consenso: 1/6 acuerdo, 5 discrepancias — TODAS resueltas a favor de la voz
independiente, todas con evidencia de código verificada.
```

Esa tabla es incómoda y es la lectura correcta: **la revisión primaria de ingeniería
fue la más floja de las tres fases.** Validó fronteras arquitectónicas y se creyó sus
propias decisiones en vez de recorrer los caminos de fallo. Los cuatro críticos
(B1 bola evaporada, B2 conexión entre hilos, B4 restauración destructiva, B5 copia
previa vacía) son todos de la voz independiente.

### C.4.1 Hallazgos incorporados al plan

| # | Hallazgo | Sev. | Dónde queda |
|---|---|---|---|
| B1 | **El bombo pierde la bola si la transacción falla.** `extraer()` muta antes del commit; con `modo_vivo` degradando el error a franja, el operador reintenta y el acta se firma con una bola evaporada | **Crítica** | 4.2: `siguiente()` + `confirmar()` tras el commit |
| B2 | **`exportar(con, ...)` en un `Tarea` es `ProgrammingError` seguro** (`check_same_thread=True`), en la única función cuyo fin es salvar el evento | **Crítica** | 4.12: firma sin `con`, excepción documentada en convenciones |
| B4 | **`restaurar` mueve `%LOCALAPPDATA%` con la aplicación encima** y valida el `.zip` *después* de haber movido los datos | **Crítica** | 4.12: validar primero, solo CLI, relanzar el proceso, `argparse`, código de salida 6 |
| B5 | **La copia previa a la migración copia una base vacía**: en WAL los datos confirmados viven en `-wal`. Es el mecanismo de reversión de la noche del evento | **Crítica** | 4.22: `wal_checkpoint(TRUNCATE)` antes de copiar |
| C1 | **El ciclo de vida del ganador con `sin_reclamo="continuar"` no estaba diseñado**: cien filas de `ganador`, cuenta regresiva reiniciándose cada seis segundos en pantalla | **Crítica** | D8: solo se registra la primera bola ganadora; diagrama de estados exigido en 4.7 |
| C2 | **Al reanudar, un ganador ya detectado vuelve a cantar bingo** y el `INSERT OR IGNORE` se traga la anomalía | **Crítica** | D13: `_ya_detectados` en `ResultadoReanudacion` |
| C4 | **Cero elegibles arranca igual**, y 4.23 bloqueaba la venta también con ronda `pausada` — dejando sin registrar a quien compró en la puerta | **Crítica** | 4.23: bloqueo solo con `en_curso`; `iniciar_ronda` con cero elegibles falla |
| A1 | **`_COLUMNAS` borraría `acta_hash` e `iniciada_en`** desde `vista_rondas`, que guarda al vuelo | **Crítica** | 4.1: verbos puntuales, las cuatro fuera de `_COLUMNAS` |
| S1 | **La validación por QR se salta con una firma basura** | Alta | 4.7: si hay `\|`, firma inválida es rechazo duro |
| C5 | 4.23 cubría tres funciones y dejaba `anular_venta` y `cambiar_estado_carton` abiertas | Alta | 4.23: cinco funciones |
| C3 | Con la reanudación en solo lectura, `INSERT OR IGNORE` deja de ser idempotencia y pasa a ser un supresor de `ErrorIntegridad` | Media | 4.6: `INSERT` normal, se retira `crear_si_no_existe` |
| C6 | Reabrir invalida el acta, y el nombre por `orden` (mutable) hace que una sobrescriba a otra | Alta | 4.11: `acta_hash = NULL`, nombre por `ronda_id` + marca de tiempo |
| A2 | Los callbacks corren **dentro** del stack de `extraer()`: reentrada garantizada si un slot pausa, cierra o abre un modal | Alta | Ver C.4.2 |
| A3 | **Nadie mueve `evento: preparado -> en_curso`.** `finalizar_evento` lanzaría transición inválida al final del evento real | Media | Ver C.4.2 |
| A4 | DU-11 blinda los dos botones de la cabecera y deja abierto el tercer camino: abrir otro evento desde la lista | Media | Ver C.4.2 |
| A5 | Nadie cierra `LogPartida`; en Windows un descriptor abierto impide mover la carpeta, que es lo que hace `restaurar` | Media | Ver C.4.2 |
| B6 | El riesgo del `QTimer` de `vista_tema` **no es el lock** (misma conexión, mismo hilo): es la reentrancia de `transaccion()` con un bucle de eventos anidado | Media | Ver C.4.2 |
| B7 | `QShortcut.autoRepeat` es `True` por defecto: mantener `Espacio` extrae a 30 Hz | Media | Ver C.4.2 |
| C7 | `BomboVacio` como excepción convierte un final de ronda legítimo en un modal en directo | Media | 4.2: `bombo.agotado` + "Cerrar ronda sin ganador" |
| C8 | `a_una_bola` como barrido contradice el contrato §5.2 literal | Media | 4.3: incremental, con assert sobre el número de evaluaciones |
| T1 | **La prueba que justifica D2 corre con `synchronous="OFF"`**: mide 2 ms y no prueba la premisa | Alta | Ver C.4.2 |
| T2 | **La prueba de reanudación no prueba lo que dice**: "cerrar la conexión" es un cierre limpio | Alta | Ver C.4.2 |
| T4 | Con `offscreen` no hay `QScreen` múltiples, ni `showFullScreen` real, ni audio: la mitad de lo prometido con `pytest-qt` no es ejecutable en CI | Media | Ver C.4.2 |
| S2 | **`clave_evento` viaja en el `.zip`**: quien lo tenga puede fabricar QRs válidos de todos los cartones. Convierte una fuga en vía de fraude, no solo en un problema de LOPDP | Alta | Ver C.4.2 |
| S3 | El zip-slip real no está en `extractall` (que sanea desde 3.6.2) sino en el bucle manual que hará falta para el progreso | Media | Ver C.4.2 |
| S4 | El hash del acta es un checksum, no un comprobante: cualquiera con la app fabrica un acta y su hash | Media | Ver C.4.2 |
| S5 | La acción nueva de DU-18 debe nacer con prefijo `venta.*` o sobrevive al borrado LOPDP | Media | Ver C.4.2 |
| P1 | **`hiddenimports` no trae los plugins nativos de Qt.** El `.exe` arranca, importa, y `availableEngines()` devuelve lista vacía — y la degradación de D5 lo **enmascara** | **Crítica para el criterio de aceptación** | Ver C.4.2 |
| P2 | Sin firma de código, SmartScreen esconde el botón real tras "Más información" en un equipo limpio | Alta | Ver C.4.2 |
| P3 | Inno Setup no detecta la instancia: `QLockFile` no es un mutex nombrado | Media | Ver C.4.2 |
| P5 | `package-data` no declara `bingo.recursos.sonidos`; `asegurar_estructura` no crea `impresos/` ni `logs/<evento_id>/` | Baja | 4.12 |

### C.4.2 Correcciones que se añaden al plan

Todo lo de la tabla anterior marcado "ver C.4.2" se implementa así:

- **A2 — Callbacks encolados.** El puente convierte callback → señal con
  `Qt.QueuedConnection` (o `QTimer.singleShot(0, ...)`), y `MotorSorteo` lleva una
  bandera `_extrayendo` que hace de `extraer()` un no-op reentrante. Se escribe junto
  al convenio de callbacks en `docs/convenciones-codigo.md`.
- **A3 — `iniciar_ronda` mueve el evento** `preparado -> en_curso` en la **misma
  transacción** que el `UPDATE ronda`, idempotente si ya está `en_curso`.
- **A4 — La guarda de DU-11 va en `VentanaPrincipal.abrir_evento` y `cerrar_evento`,**
  no en los botones: el tercer camino (abrir otro evento desde la lista) tiene el
  mismo `deleteLater()`.
- **A5 — `MotorSorteo.cerrar()`** y un teardown explícito de `EspacioEvento`
  (`closeEvent`/`destroyed`) que cierra el `LogPartida` y suelta el `EstadoPartida`.
- **B6 — Regla escrita en `docs/convenciones-codigo.md`:** ningún diálogo, ni nada que
  pueda girar el bucle de eventos, **dentro de un `with transaccion()`**. Con prueba
  `pytest-qt` sobre el camino de extracción.
- **B7 — `setAutoRepeat(False)`** en todos los atajos de ámbito `sorteo`. Prueba:
  emitir el atajo diez veces en el mismo tick → una sola fila en `extraccion`.
- **T1 — Fixture propia con `synchronous="FULL"` sobre disco real**, y assert sobre el
  **percentil 95 de 75 extracciones**, no sobre una. Sin eso, D2 se apoya en una
  prueba que no mide lo que dice medir.
- **T2 — Tres pruebas donde había una:** (a) fallo inyectado (monkeypatch en
  `repo_ganador.crear` que lanza tras el `INSERT extraccion`) → assert **cero filas**
  en `extraccion`, que es el rollback real; (b) proceso real con `subprocess` y
  `BINGO_HOME`, que corre N bolas y hace `os._exit(1)`; (c) el caso "bola confirmada
  pero nunca anunciada" (el proceso murió entre el commit y los callbacks), con
  comportamiento definido: al reanudar **se re-anuncia**, porque el público no la oyó.
- **T4 — Declarar explícitamente qué se prueba con dobles** (un `ProveedorLocucion`
  falso, una lista de nombres de pantalla inyectada) **y qué queda solo en el guion
  del ensayo con evidencia**. Si no se declara, el ensayo manual absorbe en silencio
  lo que las pruebas prometían.
- **S2 — `clave_evento` en el `.zip`** entra en el análisis de D11 y en el
  `RESPALDO_LEEME.txt`. Es un argumento a favor del cifrado que D11 no había pesado:
  no es solo LOPDP, es la capacidad de fabricar QRs válidos.
- **S3 — Extraer con `zf.extract(info, destino)`** (que sanea) iterando `infolist()`
  solo para el progreso; nunca abrir y escribir a mano. Más: tope de tamaño
  descomprimido y de ratio de compresión —ya existe el precedente
  `LIMITE_TAMANO_XLSX_DESCOMPRIMIDO_MB` en `config/ajustes.py`, se reusa el patrón— y
  lista blanca de prefijos (`datos/`, `medios/`, `logs/`, `impresos/`,
  `RESPALDO_LEEME.txt`); cualquier otra entrada aborta.
- **S4 — El hash del acta pasa a `hmac.new(clave_evento, carga)`.** La clave ya existe
  y ya está en `dominio/firma.py`: coste cero, y entonces sí es verificable por el
  emisor. Se corrige además la redacción de D7 y de `docs/decisiones.md`, que
  prometían "comprobante" donde había un checksum.
- **S5 — La acción de DU-18 se llama `venta.datos_contacto_consultados`**, con prefijo
  `venta.*`, para que el barrido de `repo_auditoria.eliminar_por_evento_y_prefijo` se
  la lleve en el borrado LOPDP de 4.25. Con el nombre `sorteo.*` el detalle (que puede
  llevar el nombre de la persona) sobreviviría al borrado.
- **P1 — Plugins nativos, no solo `hiddenimports`.** `collect_dynamic_libs` /
  `collect_data_files` sobre PySide6 con `plugins/multimedia/ffmpegmediaplugin.dll` y
  sus DLLs de FFmpeg, `plugins/texttospeech/qtexttospeech_winrt.dll` y `_sapi.dll`, y
  el módulo de QtPdf. **Y el criterio de la prueba de humo deja de ser "arranca":**
  asserta `QTextToSpeech.availableEngines() != []` y que el WAV suena. Sin eso, la
  degradación de D5 enmascara el fallo (desactiva la locución sola y sigue) y se
  descubre en el evento.
- **P2 — Firma de código: decidir ahora, no en la semana final.** Un instalador sin
  firmar produce *"Windows protegió tu PC"* con el botón real escondido tras "Más
  información", y probablemente cuarentena de Defender sobre un binario PyInstaller.
  El criterio de aceptación es literalmente "un equipo limpio". O certificado (coste y
  plazo reales) o `docs/runbook.md` con capturas del diálogo exacto y el riesgo
  declarado en `docs/decisiones.md`. **Va al gate como decisión de gusto TD-1.**
- **P3 — Mutex nombrado adicional al arrancar**, declarado como `AppMutex` en el
  `.iss`: `QLockFile` no lo es, así que hoy Inno Setup no puede detectar la instancia
  y la actualización sobrescribe archivos en uso.
- **P4 — En el `.exe` congelado, la versión se lee de `bingo.__version__` directo**,
  nunca de `importlib.metadata.version("bingo")`, que no existirá.

### C.4.3 Contradicciones internas encontradas y resueltas

Las ediciones acumuladas de las tres fases dejaron cinco. Todas corregidas en el
cuerpo del plan:

1. **DU-12 vs. 4.27** — `modo_vivo` como parámetro explícito (DU-12) contra estado de
   módulo en `ui/dialogos.py` (4.27). Resuelto a favor de DU-12.
2. **D3 vs. 4.1** — D3 demuestra que `premio_valor_centavos` ya existe desde la 003, y
   4.1 seguía pidiendo una prueba de "la copia a centavos" que no ocurre. Retirada.
3. **§4.3 vs. contrato §5.2** — `a_una_bola` como barrido completo contra "evaluación
   únicamente sobre los cartones marcados en esa jugada". Ahora incremental.
4. **DU-4** describía `dominio/tema.py::BLOQUES` como si ya existiera; hoy es
   `_BLOQUES` en `vista_tema.py` con cuatro campos. La tarea 4.21 es la que lo mueve.
5. **`ErrorReanudacion`** aparecía en DU-12 y D13 sin estar declarada en ninguna
   tarea. Ahora está en 4.1.

Y una sexta que aporta el subagente sobre el campo `version` de D4: **con
`_combinar()` rellenando lo ausente, un `tema_json` viejo sin `version` se leería como
`version=1`, indistinguible de uno nuevo.** Para que el campo sirva, su valor por
defecto tiene que ser **`0`** y la versión actual `1`, escrita al guardar.

### C.4.4 Donde la voz independiente y la primaria discrepan sin resolver

Una sola, y va al gate: **el tamaño de la fase.** La voz de ingeniería dice
literalmente *"el alcance (27 grupos de tareas + 18 decisiones de UI, un
desarrollador) no es una fase; es dos"*. La voz CEO había dicho lo mismo con otras
palabras y proponiendo tres etiquetas. Dos de las tres voces independientes, por
caminos distintos, llegan a la misma conclusión sobre la calibración. → **UC-3.**

Y una recomendación de secuencia en la que las dos coinciden y que la primaria no
había ordenado así: antes de escribir `ui/transmision/` (4.9, la tarea más grande)
hay que tener resueltos el **spike de OBS** (D14 ya es contingente), la **prueba de
humo del `.exe` con audio y TTS** (P1), y el **diagrama de estados de `ganador`**
(C1). Los tres son baratos y los tres pueden invalidar semanas de trabajo si se
descubren tarde.

---

# ANEXO D — Gate final: decisiones tomadas

Gabriel dejó instrucción explícita al invocar `/gstack-autoplan`: *"si se debe tomar
una decisión tómala tú"*. Lo que sigue son las cinco decisiones que normalmente
pararían el pipeline para preguntar, resueltas con su razón. **Cada una es reversible
en una línea**, y la columna "para revertir" dice exactamente qué frase hace falta.

## D-gate-1 — Los tres spikes corren ANTES de escribir `ui/transmision/` · UC-1

**Lo que decía el plan:** los spikes son riesgos con mitigación escrita, y el ensayo
final los cubre.
**Lo que dicen las dos voces independientes:** el ensayo ocurre *después* de escribir
`ui/transmision/` entero. Si OBS captura la ventana en negro, o el DPI fraccional
desalinea el lienzo, se descubre con el 100% del subsistema escrito.

**Decidido: los tres spikes son Semana 0 y son prerrequisito, no riesgo.** Son medio
día cada uno, llevan dos fases pospuestos, y dos de ellos producen números que ya
deberían estar impresos en los cartones.

1. **OBS + dos monitores** — 30 líneas de PySide6, ventana sin bordes en el segundo
   monitor, OBS capturando. **Puerta:** si captura en negro, D14 cambia de ruta antes
   de escribir 4.9, no después.
2. **Latencia de transmisión** — emisión privada a Facebook y YouTube, cronómetro
   contra el reloj de la pantalla. El número va impreso en el cartón (alcance §6.1) y
   hoy `TEXTO_INFERIOR_DEFECTO` dice "que tiene retraso" sin cifra.
3. **Imprenta** — un cartón a cotizar. Este ya llega tarde: debía correr antes del
   motor de render de la fase 3, que está cerrada. Hoy un rechazo por sangrado o CMYK
   es retrabajo de una fase cerrada, y cuanto antes se sepa, menos cuesta.

*Para revertir:* "los spikes van al final, como estaban".

## D-gate-2 — `v1.0.0` significa "el software está listo", no "puedes cobrar entradas" · UC-2

**Lo que decía el contrato:** el entregable es la etiqueta `v1.0.0`, aplicación
instalable probada en ensayo completo.
**Lo que dicen las voces:** `TODOS.md` tiene tres bloqueadores P1 sin empezar —premios
en efectivo en Ecuador, políticas de Meta/YouTube sobre juegos con premio, retención
LOPDP— y `docs/decisiones.md` de la fase 3 dice que ya hay *"una organización con
evento real agendado"*. El propio `TODOS.md` dice de la consulta legal: *"si la
respuesta es mala, invalida las cinco fases retroactivamente"* y *"depende de: nada,
se puede empezar hoy"*.

**Decidido: se escribe la distinción, y los tres corren en paralelo al desarrollo.**
No cuesta tiempo de programación porque no son programación. Lo que cambia es que
`v1.0.0` deja de sugerir permiso: el `CHANGELOG` y `docs/decisiones.md` dicen
explícitamente que la etiqueta es un hito de software y que operar un evento pagado
depende de tres respuestas que no dependen de este repositorio.

No se toca el alcance técnico de la fase. Solo se deja de dar a entender algo que no
es cierto.

*Para revertir:* "quita la nota legal del CHANGELOG".

## D-gate-3 — Una sola Fase 5, con tres hitos internos etiquetados · UC-3

**Lo que decía el plan:** doce grupos de tareas (veintisiete tras las revisiones) y un
entregable, `v1.0.0`.
**Lo que dicen las voces:** las dos, por caminos distintos, dicen que está mal
calibrado. La de ingeniería es literal: *"no es una fase; es dos"*. Y la de CEO aporta
el precedente más fuerte del repositorio: las fases 3 y 4 entraron **en un solo commit
de 12.209 líneas el mismo día**, y `TODOS.md` cierra con **doce** recortes hechos
"para que la fase entrara en una sola sesión". Cuando una fase se sobredimensiona,
este proyecto no se alarga: **recorta en silencio**.

**Decidido: se conserva una sola Fase 5 y un solo entregable `v1.0.0` —el contrato no
se rompe— pero con tres hitos internos etiquetados**, cada uno con su puerta de
salida. Es la forma más suave que preserva lo que Gabriel escribió y responde a lo que
las dos voces temen: que el recorte lo decida el cansancio a las dos de la mañana en
vez de una decisión escrita.

| Hito | Contenido | Puerta de salida |
|---|---|---|
| **v0.9.0 — jugable** | Semana 0 (spikes) · 4.1-4.9 · 4.17 ensayo · 4.21-4.24 · las correcciones críticas B1, C1-C6, A1-A5 · **humo del `.exe` (P1)** | Tres rondas de principio a fin y una reanudación real |
| **v0.9.5 — comprobable** | 4.11 actas · 4.12 respaldos **con restauración probada en segundo equipo** · 4.19 auditoría · 4.20 verificador · 4.25 borrado LOPDP · 4.26 CI | El acta verifica y el respaldo restaura |
| **v1.0.0 — presentable** | 4.10 sonido y locución · animación del bombo · pantallas de bienvenida y cierre · banner · 4.14 instalador definitivo | Ensayo completo firmado |

**Corolario que corrige el propio plan:** el orden de recorte del §5 estaba invertido.
Decía "si algo se recorta, se recorta de 4.10 (sonido) y 4.14 (empaquetado)". El
empaquetado es criterio de aceptación y PyInstaller con `QtMultimedia`/`QtTextToSpeech`
es célebre por fallar tarde: la prueba de humo del `.exe` sube a **v0.9.0**, semana 1.
El único candidato a recorte es el sonido.

*Para revertir:* "una sola etiqueta, sin hitos".

## D-gate-4 — La locución se queda · UC-4, RECHAZADO

**Lo que propone la voz de ingeniería:** eliminar 4.10 entera. El operador ya está
frente al micrófono cantando el número —es literalmente su trabajo en un bingo— y su
voz es mejor que cualquier SAPI de Windows. Quitarla se lleva tres clases,
`QtMultimedia`/`QtTextToSpeech` de PyInstaller (uno de los riesgos declarados del §5),
el generador de WAV y la degradación de D5.

**Decidido: se rechaza.** El argumento es bueno pero el contrato §5.8 la pide
explícitamente, y ese contrato lo escribió Gabriel sabiendo que iba a presentar él.
Puede haber razones que el análisis no ve: transmisiones sin narrador, accesibilidad,
o simplemente que quiera descansar la voz en un evento de tres horas.

**Lo que sí se hace con el argumento:** la locución es lo último del último hito
(D-gate-3) y **el único candidato declarado a recorte**. Si el calendario aprieta, es
lo que se cae, por decisión escrita y no por cansancio.

*Para revertir:* "quita la locución de la fase 5".

## D-gate-5 — Commit-reveal de la semilla: recomendado, NO incluido · UC-5

**Lo que propone la voz CEO:** hoy el operador calcula, después del sorteo, un hash de
datos que él mismo controla, sobre una base que él mismo administra, y lo imprime en
un PDF que él mismo firma. Ante *"las bolas estaban arregladas"* eso no responde nada.
La alternativa: generar una semilla al iniciar la ronda, **anunciar `SHA-256(semilla)`
antes de la primera bola**, y revelar la semilla en el acta. Cualquiera recomputa la
secuencia. Y el bombo ya recibe el `rng` por contrato, así que cuesta un día.

**Verificado, y la vía técnica existe** (hallazgo E-4): `secrets.SystemRandom().seed()`
es un **no-op silencioso** —no se puede sembrar—, así que la implementación sería
`semilla = secrets.token_bytes(32)` con expansión determinista vía
`random.Random(int.from_bytes(semilla))`. La impredecibilidad la sigue dando `secrets`
en la generación; la verificabilidad la da que la secuencia queda fijada al publicar
el hash.

**Decidido: NO entra en la Fase 5.** El alcance §7 excluye explícitamente "semilla
verificable publicada (commit-reveal)" de la v1, y el contrato §5.1 dice literalmente
`secrets.SystemRandom()`. Son dos exclusiones escritas por Gabriel, y ampliar el
alcance por encima de una exclusión explícita no es una decisión que deba tomar una
revisión automática, por buena que parezca la idea.

**Pero es la decisión que más me gustaría que revirtieras.** El análisis de mercado
dice que el cantador es una mercancía y que el activo diferencial de este producto es
la cadena auditable; esto es el movimiento de confianza más grande disponible, por un
día de trabajo, sobre una arquitectura que ya lo permite. Queda en `TODOS.md` como P1
con la vía técnica escrita, no como una idea vaga.

*Para revertir:* "mete el commit-reveal en la fase 5".

## D-gate-6 — Sin firma de código para la v1.0.0 · decisión de gusto TD-1

Un instalador PyInstaller sin firmar produce en un equipo limpio *"Windows protegió tu
PC"*, con el botón real escondido tras "Más información", y probablemente cuarentena
de Defender. El criterio de aceptación es literalmente "un equipo limpio".

**Decidido: sin certificado.** Un certificado de firma tiene coste anual y plazo de
validación reales, para un operador que instala la aplicación en sus propios equipos y
los de organizaciones que ya lo conocen. En su lugar: `docs/runbook.md` con **capturas
del diálogo exacto** y el procedimiento de tres clics, y el riesgo declarado en
`docs/decisiones.md` como asumido, no como olvidado. Si algún día se distribuye a
terceros que no conocen a Gabriel, se compra el certificado ese día.

*Para revertir:* "compra certificado de firma".

---

## Resumen del gate

| # | Desafío | Decisión | Coste de equivocarme |
|---|---|---|---|
| UC-1 | Spikes antes de 4.9 | **Aceptado** | Día y medio "perdido" si todo funcionaba a la primera |
| UC-2 | `v1.0.0` ≠ permiso para cobrar | **Aceptado** | Ninguno: es una frase en el CHANGELOG |
| UC-3 | Partir la fase | **Aceptado en forma suave**: una fase, tres hitos | Ceremonia de tres etiquetas donde bastaba una |
| UC-4 | Quitar la locución | **Rechazado** | Se construye algo que quizá no se use, y se carga PyInstaller con dos módulos frágiles |
| UC-5 | Commit-reveal | **No incluido** (recomendado) | Se deja sobre la mesa el mayor diferenciador del producto por un día de trabajo |
| TD-1 | Firma de código | **Sin certificado** | Una instalación incómoda en un equipo ajeno |

---

## GSTACK REVIEW REPORT

**Pipeline:** `/gstack-autoplan` · 2026-09-10 · rama `main` · commit base `bca3b9a`
**Fases:** CEO (SELECTIVE EXPANSION) → Diseño → Ingeniería. DX saltada (sin alcance
de desarrollador: una coincidencia de "API", que es la de respaldo de SQLite).
**Voces duales:** Codex **no disponible** en este equipo (`binary not found`); las tres
fases corrieron `[subagent-only]` con un subagente Claude independiente por fase, sin
contexto de las fases previas.

| Fase | Hallazgos | Críticos | Consenso | Tareas |
|---|---|---|---|---|
| CEO | 25 | 6 | 3/6 confirmadas, 3 discrepancias | 24 |
| Diseño | 26 | 6 | 4/7 acuerdo, 2 discrepancias resueltas a favor de la voz independiente | 36 |
| Ingeniería | 31 + 5 contradicciones internas | 8 | **1/6 acuerdo, 5 discrepancias, todas a favor de la voz independiente** | 44 |
| **Total** | **82** | **20** | | **104** (45 P1 · 46 P2 · 13 P3) |

**Estado: APROBADO CON DECISIONES TOMADAS.** Gabriel autorizó explícitamente decidir
en su ausencia. Las seis decisiones del gate están en el ANEXO D, cada una con la
frase exacta que la revierte.

**Lo que hay que leer si solo se leen tres cosas:**
1. **ANEXO D** — las seis decisiones tomadas, y cuál conviene revertir (D-gate-5).
2. **§3-bis** — las diecisiete decisiones de interfaz. La capa que el plan original
   no tenía.
3. **§C.4** — la revisión de ingeniería independiente. Los ocho críticos que la
   revisión primaria no encontró.

**Honestidad sobre el proceso:** la revisión primaria de ingeniería fue la más floja
de las tres. Validó fronteras arquitectónicas y se creyó sus propias decisiones en vez
de recorrer los caminos de fallo; los cuatro peores críticos (la bola que se evapora,
la conexión entre hilos, la restauración destructiva, la copia previa vacía) los
encontró la voz independiente. Sin ella este plan habría entrado a implementación con
cuatro formas de perder datos en vivo.

**Plan de pruebas:** `~/.gstack/projects/Bingo_App/gabriel-main-test-plan-20260910.md`
**Punto de restauración:** `~/.gstack/projects/Bingo_App/main-autoplan-restore-20260909-234655.md`
