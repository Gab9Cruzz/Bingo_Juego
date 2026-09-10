# TODOS — Proyecto BINGO

Diferidos durante `/gstack-autoplan` sobre `docs/Fase_1/Contrato_Fase1.md` el 2026-09-04.
Formato: **qué** · por qué · esfuerzo (humano / CC) · prioridad · depende de.

## P1 — antes del primer evento pagado

- **Consulta legal sobre premios en efectivo en Ecuador.**
  El alcance §8 lo llama "el punto más expuesto de la operación" y dice
  explícitamente "consultar a un abogado antes del primer evento pagado". Ninguna
  de las cinco fases contiene una tarea para esto. Si la respuesta es mala,
  invalida las cinco fases retroactivamente.
  Esfuerzo: 1 semana de calendario / — · Depende de: nada. Se puede empezar hoy.

- **Lectura de las políticas de Facebook y YouTube sobre juegos con premio.**
  El alcance §8 advierte que el canal de la organización puede ser suspendido.
  Entregable: lectura escrita de los términos de servicio más una transmisión de
  prueba en un canal privado.
  Esfuerzo: 2 días / — · Depende de: nada.

- **Política de retención de datos de compradores (LOPDP).**
  El alcance §9 la deja pendiente. La fase 1 fija la forma de los datos que hará
  fácil o difícil el borrado, y por defecto la fija en la dirección difícil (una
  fila `comprador` por cartón, en una base global). Propuesta del alcance: se
  conservan mientras dure el evento y hasta 30 días después, se entrega el reporte
  a la organización y luego se eliminan.
  Esfuerzo: M / S · Depende de: nada, pero cuanto antes se decida menos cuesta.

## P1 — spikes que de-riesgan las fases 3 y 5

- **Spike de OBS y dos monitores.** Un script de 30 líneas con PySide6 que saca
  una ventana sin bordes a pantalla completa en un segundo monitor y se captura en
  OBS. Responde a la vez la política de DPI (E16) y la viabilidad de la fase 5.
  Esfuerzo: medio día / — · Depende de: nada.

- **Spike de imprenta.** Un cartón de una página hecho a mano, enviado a una
  imprenta real para cotización y prueba de impresión. Si rechazan el PDF por
  sangrado, resolución o CMYK, hay que saberlo antes de escribir el motor de
  render de la fase 3, no después.
  Esfuerzo: medio día + espera / — · Depende de: nada.

- **Spike de latencia de transmisión.** Medir el retraso real en una emisión
  privada. El alcance §6.1 dice que ese número va **impreso en el cartón**, o sea
  que es una entrada de la fase 3.
  Esfuerzo: 2 horas / — · Depende de: nada.

## P2 — durante o después de la fase 1

- ~~**Carga de los patrones del sistema en la tabla `patron`.**~~ Resuelto
  (fase 4): `servicio_patrones.asegurar_patrones_sistema`, llamado desde
  `__main__.py` tras las migraciones; idempotente por `clave_i18n`.

- ~~**Verificar la API de `reportlab` 5.x.**~~ Resuelto (fase 3): la 5.0.1 es la
  que instala `.venv`, `MotorRenderCarton` (`impresion/render_pdf.py`) ya la
  ejercita de punta a punta (canvas, `ImageReader`, QR nativo vía
  `reportlab.graphics.barcode.qr`). Pendiente real distinto: verificar
  visualmente el peso Bold de las fuentes variables empaquetadas (ver más
  abajo, "Verificar el peso Bold...").

- **Plan de segunda máquina.** El alcance §8 acepta "equipo único" como punto de
  fallo y ninguna fase lo mitiga. Mínimo aceptable: probar que un respaldo `.zip`
  restaura en un segundo equipo y abre el evento donde quedó.
  Esfuerzo: M / S · Depende de: fase 5 (respaldos).

- **Integración continua.** `ruff` + `pytest -m "not lento"` en cada push. No hay
  repositorio remoto todavía; se crea el workflow cuando lo haya.
  Esfuerzo: S / S · Depende de: repositorio remoto.

## P3 — v2 y más allá

- **Una base de datos por evento.** Haría trivial el borrado LOPDP y la entrega a
  la organización. Contradice el `datos/bingo.db` único del documento técnico y
  complica organizaciones y patrones, que son transversales.
  Esfuerzo: L / M.

- **Cifrado del respaldo.** El `.zip` lleva datos personales de compradores.
  Esfuerzo: M / S · Depende de: fase 5.

- ~~**Vista previa del cartón junto al formulario de organización.**~~ Resuelto
  (fase 3), pero no donde DG-3 lo imaginaba: la plantilla (y por tanto la
  vista previa) es del **evento**, no de la organización
  (`evento.plantilla_json`), así que vive en `ui/vistas/vista_plantilla.py`
  (sección "Plantilla" del evento), no en el formulario de organización.

- **Filtro en la vista de organizaciones.** En la fase 1 son quince filas; no lo
  necesita todavía. La vista de eventos sí lo lleva desde ya.
  Esfuerzo: S / S.

- **Textos de organización por idioma.** Hoy una columna por texto. Si un cliente
  quiere cartones bilingües, hará falta una migración. Revisado en la fase 3:
  ningún criterio de aceptación de esa fase lo pide: sigue diferido.
  Esfuerzo: S / S.

- **`.pre-commit-config.yaml`.** Una dependencia más que empaquetar, para una sola
  persona. Por ahora basta la línea del README.
  Esfuerzo: S / S.

## Añadidos por la revisión de ingeniería

- **`docs/esquema-actual.sql` con prueba de instantánea.** Se difiere: mientras la
  001 sea editable (política E4e) fallaría en cada edición intencionada, que es
  como una prueba de instantánea acaba actualizándose por reflejo. Se introduce el
  día que la 001 se congela, o sea en el primer evento real. Nota técnica:
  `.schema` es un comando del cliente `sqlite3`, no de la API; hay que leer
  `sqlite_master`.
  Esfuerzo: S / S · Depende de: primer evento real.

- **Bandera `modo_vivo` para suprimir modales durante la transmisión.** Cortada de
  la fase 1 por no tener consumidor. La define la fase 5, cuando exista la interfaz
  de sorteo contra la que medirla.
  Esfuerzo: S / S · Depende de: fase 5.

- **Registro central de acciones y atajos.** En la fase 1 basta un diccionario de
  módulo. Se convierte en registro cuando haya más de una superficie manejada por
  teclado, o sea en la fase 5.
  Esfuerzo: S / S · Depende de: fase 5.

- **Fuentes personalizadas cargadas por la organización.** Decisión abierta del
  §16.3 del documento técnico: licencias y registro doble en Qt y ReportLab. La
  fase 1 empaqueta dos familias de licencia abierta y ofrece un combo cerrado;
  la fase 3 registra esas dos en ReportLab también
  (`impresion/render_pdf.py::_asegurar_fuente_registrada`, movidas a
  `src/bingo/recursos/fuentes/` para empaquetar correctamente con PyInstaller).
  Cargar una fuente arbitraria subida por la organización sigue diferido.
  Esfuerzo: M / S.

- **Verificar el peso Bold de las fuentes variables empaquetadas en ReportLab.**
  `Merriweather-Variable.ttf`/`OpenSans-Variable.ttf` son *variable fonts*;
  `pdfmetrics.registerFont(TTFont(...))` las registra sin lanzar, pero un
  `TTFont` de ReportLab asume una fuente estática — probablemente solo accede
  a la instancia Regular. No verificado visualmente todavía. No bloquea: la
  plantilla por defecto usa `Helvetica-Bold` (fuente estándar del PDF) para
  los números, que es el elemento más denso del cartón; el riesgo es solo si
  un operador elige Merriweather/Open Sans para título/subtítulo y el peso
  Bold no se ve bien.
  Esfuerzo: S / S · Depende de: nada, es una prueba visual de una hoja impresa.

- **Acelerar la generación de QR de `servicio_impresion.generar_pdf_lote`.**
  Medido (fase 3): el QR (`reportlab.graphics.barcode.qr`, codificador
  Reed-Solomon puro Python) es ~93% del tiempo de render por cartón (~24ms de
  ~26ms medidos). 10.000 cartones tarda ~6-7 minutos en vez de segundos. El
  criterio de aceptación de la fase 3 ("no se congela, con progreso y
  cancelación") se cumple igual — corre en `Tarea`/`QThread` — así que no
  bloqueó el cierre de la fase. Si un evento real con lotes de 10.000+
  encuentra el tiempo molesto, revisar: cachear la codificación del QR (el
  contenido cambia por cartón, no cachea directo), o evaluar una librería de
  QR con extensión C si el proyecto decide que vale la pena la dependencia
  nueva.
  Esfuerzo: M / M · Depende de: que un evento real lo note.

## Añadidos por `/gstack-autoplan` sobre `docs/Fase_2/Contrato_Fase2.md` (2026-09-04)

- **Exportar el listado de cartones a Excel/PDF desde la vista de la Fase 2.**
  Candidato de expansión (E5) surgido en la revisión CEO: sería cómodo tenerlo ya
  en la vista de consulta de cartones, pero es exactamente el trabajo de
  impresión (fase 3) y conciliación (fase 4) — construirlo ahora duplicaría
  esfuerzo cuando esas fases lleguen con su propio motor de render/Excel.
  Esfuerzo: M / S · Depende de: fase 3 (impresión) y fase 4 (conciliación).

## Añadidos por `/gstack-autoplan` sobre `docs/Fase_4/Contrato_Fase4.md` (2026-09-09)

- **Cifrado del respaldo — sube de P3 a P1.** Ya estaba anotado abajo, pero la fase 4 es la que
  crea la primera tabla con datos personales. La revisión de ingeniería enumeró **cinco copias
  sin cifrar** en el disco del operador: `bingo.db`, `bingo.db-wal`, el `.xlsx` de conciliación
  (que se manda por WhatsApp), el `.xlsx` del informe de errores, y el `.xlsx` de plantilla que
  devuelve la organización. Deja de ser teórico el día que se implemente esta fase.
  Esfuerzo: M / S · Depende de: fase 5 (respaldos).

- **`ui/espacio_evento.py` deja de escalar por apéndice.** La fase 4 lo lleva a siete u ocho
  secciones en el riel del evento; la fase 5 añade Transmisión. Anotado por la revisión de
  diseño: no hace falta resolverlo ahora, pero conviene no encontrárselo por sorpresa.
  Esfuerzo: M / S · Depende de: fase 5.

- **Historial de conciliación entre eventos.** Fuera del contrato de la fase 4, que solo pide
  el reporte por evento. Útil para una organización que hace bingos periódicos.
  Esfuerzo: M / S · Depende de: fase 4.

- **Detección de comprador duplicado por teléfono.** Misma cédula en 30 cartones es normal (una
  persona compra 30). Mismo teléfono con nombres distintos puede ser un tecleo. Descartado en la
  revisión CEO por ruidoso y de valor poco claro.
  Esfuerzo: S / S.

- ~~**Huérfanos de imagen de premio.**~~ Resuelto (fase 4):
  `servicio_rondas.eliminar_ronda` borra el archivo de `premio_imagen` si
  existe, en vez de dejarlo huérfano en `dir_medios_evento`.

- ~~**`servicio_cartones.regenerar_lote(con, lote_id)`.**~~ Resuelto (fase 3,
  decisión D6 de `docs/Fase_3/Plan_Implementacion_Fase3.md`): borra el lote y
  sus cartones y vuelve a llamar `generar_lote` con la misma semilla,
  prefijo y cantidad. Sin caso de uso de UI todavía (ningún botón la llama);
  eso queda para cuando la vista de impresión ofrezca "reimprimir" sobre un
  lote existente.

## Añadidos durante la implementación de la Fase 4 (2026-09-09)

Simplificaciones deliberadas del plan, para que la fase entrara en una sola
sesión de implementación sin sacrificar el núcleo (compradores, atomicidad,
elegibilidad, conciliación). Ninguna afecta a un criterio de aceptación del
contrato; todas son mejoras de robustez o de pulido que quedan pendientes.

- **Aceptar `.csv` en la importación (decisión R5).** Hoy `validar_importacion`
  solo acepta `.xlsx`; un `.csv` sale como "formato no soportado" en vez de
  aceptarse. `.xls` sí tiene mensaje específico y accionable.
  Esfuerzo: S / S · Depende de: nada.

- **Heurística de fórmulas sin cachear (decisión R5, "exportado de Google
  Sheets").** El contrato pide avisar si >30% de los nombres vienen vacíos
  (síntoma de un `.xlsx` con fórmulas no evaluadas). Hoy esas filas caen en
  `sin_nombre` sin ningún aviso agregado que oriente al operador sobre la causa.
  Esfuerzo: S / S · Depende de: nada.

- **Categoría `continuacion_de_fila_anterior` (decisión R4).** Un Excel con un
  comprador y varios cartones en filas sucesivas (código repetido, nombre solo
  en la primera) hoy no tiene categoría propia — cae en duplicado o sin_nombre
  según el caso, en vez de ofrecer "aplicar el comprador anterior a estas N filas".
  Esfuerzo: M / S · Depende de: nada.

- **Arrastrar y soltar para reordenar rondas.** `vista_rondas.py` solo tiene
  botones Subir/Bajar (`servicio_rondas.reordenar` ya soporta cualquier
  permutación); `QAbstractItemView.InternalMove` sobre la lista es una mejora
  de interacción, no de alcance.
  Esfuerzo: S / S · Depende de: nada.

- **Modo ráfaga completo en el alta manual (decisión DS10).** El diálogo de
  alta manual tiene orden de tabulación y guarda con el botón por defecto,
  pero no "guardar y limpiar con el foco de vuelta al código" para encadenar
  altas de la noche del evento sin tocar el ratón.
  Esfuerzo: S / S · Depende de: nada.

- **Selector de patrón con miniaturas visuales reales (decisión DS17).** El
  selector de `vista_rondas.py` lista los patrones por nombre agrupados
  Sistema/Organización; el editor de patrones sí pinta la rejilla 5x5, pero el
  propio selector de la lista todavía no pinta una miniatura por fila.
  Esfuerzo: S / S · Depende de: nada.

- **`vista_rondas.py` no sigue la regla de guardado explícito (decisión DS14,
  ahora en `docs/convenciones-codigo.md`).** El formulario de ronda guarda
  cada cambio de campo al vuelo (mismo `_marcar_cambio` de un editor de
  registro único), en vez de exigir Guardar/Cancelar como corresponde a una
  entidad de colección. No pierde datos, pero no pide confirmación al
  cambiar de ronda con cambios sin guardar — corregirlo significa añadir
  estado "sucio" y los dos botones.
  Esfuerzo: S / S · Depende de: nada.

- **Panel de auditoría del evento (T9 del gate CEO).** `repo_auditoria.
  listar_por_evento` ya existe desde antes de esta fase y la importación/venta
  por rango/anulación ya registran ahí; falta la vista de solo lectura que lo
  muestre en el espacio del evento.
  Esfuerzo: S / S · Depende de: nada.

- **Recaudado real editable desde la interfaz.** El backend
  (`servicio_conciliacion.declarar_recaudado_real`,
  `evento.recaudado_real_centavos`) y el reporte (que ya muestra la diferencia
  si el valor está declarado) están completos; falta el campo en
  `vista_compradores.py` para que el operador lo teclee sin pasar por código.
  Esfuerzo: S / S · Depende de: nada.

- **Medir la importación con 10.000 filas en disco lento (riesgo operativo
  del plan).** `test_importacion_de_mil_filas_marcada_lento` cubre el criterio
  de aceptación literal (1.000 filas); medir el troceo de TD-3 contra
  `BUSY_TIMEOUT_MS` con un escritor concurrente de verdad, en un disco lento,
  sigue pendiente antes de dar la fase por cerrada con datos de un evento real.
  Esfuerzo: S / S · Depende de: nada, es medición.

- **Decisiones de gusto TD-5, TD-6, TD-7 (ANEXO D del plan), sin decidir.**
  TD-5: tres `.xlsx` reales de ~20 KB como fixtures (hoy las pruebas
  construyen el Excel con `openpyxl` en la propia prueba, que ya cubre los
  casos sucios del contrato §4.9). TD-6: modo escáner de QR para la venta de
  puerta. TD-7: pegar un bloque tabulado del portapapeles como tercera vía de
  entrada.
  Esfuerzo: S/S, S/M, S/S respectivamente · Depende de: nada.
