# Proyecto BINGO — Plan de desarrollo en 5 fases

**Autor:** Gabriel
**Fecha:** septiembre 2026
**Documentos relacionados:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)

Cada fase arranca con el contexto de lo que ya existe, para que puedas retomar el proyecto después de días o semanas sin releer todo. Las fases son secuenciales por dependencia real, no por preferencia: no se puede probar el sorteo sin cartones, ni imprimir cartones sin una organización configurada.

**Cómo leer cada fase:** el bloque *Punto de partida* dice qué hay hecho. *Objetivo* dice a dónde llegas. *Tareas* es lo que programas. *Criterios de aceptación* es cómo sabes que terminaste, sin autoengaño. *Queda listo para la siguiente fase* enlaza con lo que viene.

---


## Archivos de este plan

| Fase | Archivo |
|---|---|
| FASE 1 — Cimientos | `docs/Fase_1/Contrato_Fase1.md` |
| FASE 2 — Generación de cartones | `docs/Fase_2/Contrato_Fase2.md` |
| FASE 3 — Plantilla e impresión | `docs/Fase_3/Contrato_Fase3.md` |
| FASE 4 — Compradores, rondas y premios | `docs/Fase_4/Contrato_Fase4.md` |
| FASE 5 — Sorteo en vivo y cierre | `docs/Fase_5/Contrato_Fase5.md` |

El presente documento es la vista general; cada archivo de fase es autocontenido y puede trabajarse por separado.

---

# FASE 1 — Cimientos

## Punto de partida

Nada. Repositorio vacío.

## Objetivo

Tener una aplicación de escritorio que abre, con base de datos funcionando, sistema de migraciones, gestión de organizaciones y creación de eventos en borrador. Al final de esta fase no hay bingo todavía, pero existe el esqueleto sobre el que se monta todo lo demás.

Esta es la fase menos vistosa y la que más determina si el resto del proyecto avanza cómodo o a los tropezones.

## Tareas

### 1.1 Preparación del entorno
- Crear el repositorio Git con `main` y `dev`.
- Estructura de carpetas según la sección 2.2 del documento técnico.
- `pyproject.toml` con las dependencias: PySide6, reportlab, pillow, openpyxl, pytest, ruff.
- Entorno virtual y archivo `.gitignore` (excluir `.db`, `__pycache__`, `dist/`, `build/`, medios).
- Configuración de ruff con línea de 100 caracteres.
- `README.md` con instrucciones de instalación y ejecución.

### 1.2 Capa de persistencia
- `persistencia/conexion.py`: función que abre la conexión, aplica `PRAGMA journal_mode=WAL`, `foreign_keys=ON` y `synchronous=FULL`, y devuelve la conexión configurada con `row_factory` para acceder por nombre de columna.
- Resolución de rutas: crear `%LOCALAPPDATA%\Bingo\` con las subcarpetas `datos`, `logs`, `respaldos`, `medios` si no existen.
- Sistema de migraciones: tabla `schema_version`, lector de archivos `NNN_*.sql` ordenados, aplicación dentro de una transacción, registro de la versión aplicada.
- Migración `001_inicial.sql` con el esquema completo de la sección 3.1 del documento técnico. Se crea todo el esquema desde ya, aunque las tablas de rondas y extracciones no se usen hasta la fase 4 y 5.

### 1.3 Repositorios base
- `repo_organizacion.py`: crear, obtener por id, listar, actualizar, eliminar (con validación de que no tenga eventos asociados).
- `repo_evento.py`: crear, obtener, listar por organización, actualizar estado, actualizar los JSON de plantilla y tema.
- Patrón repositorio estricto: ninguna consulta SQL fuera de estos archivos. Es la regla que te permitiría migrar a otra base en el futuro sin reescribir la aplicación.
- Escribir de una vez `repo_auditoria.py` con un método `registrar(evento_id, accion, detalle)`.

### 1.4 Sistema de idiomas
- `i18n/es.json` y `i18n/en.json` con las claves que se vayan necesitando.
- Función `t(clave, **parametros)` que resuelve la traducción y sustituye marcadores.
- Ajuste de idioma persistido en preferencias locales.
- Regla desde el día uno: **ninguna cadena visible se escribe directamente en el código**. Cuesta el doble arreglarlo después.

### 1.5 Interfaz base
- Ventana principal con barra lateral o menú de navegación: Organizaciones, Eventos, Ajustes.
- Vista de organizaciones: lista, formulario de alta y edición con carga de logo (copiar el archivo a `medios/<organizacion>/`), selectores de color, campo de contacto.
- Vista de eventos: lista filtrada por organización, formulario con nombre, fecha, lugar y precio de la tabla.
- Vista de ajustes: idioma, rutas, versión de la aplicación.
- `ui/tema.py` en su versión mínima: aplicar colores de la organización activa a la interfaz.

### 1.6 Utilidades transversales
- Módulo de manejo de errores: captura de excepciones no controladas con diálogo legible y escritura a un log de aplicación.
- Módulo de fechas: todo se guarda en formato ISO 8601 en texto.
- Validación y normalización de imágenes con Pillow: convertir a PNG, limitar dimensiones máximas, rechazar archivos corruptos.

## Criterios de aceptación

- La aplicación arranca en un equipo limpio y crea su estructura de carpetas sola.
- Se puede crear una organización con logo y colores, cerrarla, reabrir la aplicación y ahí sigue.
- Se puede crear un evento en estado borrador asociado a esa organización.
- Cambiar el idioma cambia todos los textos visibles.
- Las migraciones se aplican solas al primer arranque y no se vuelven a aplicar al segundo.
- `ruff check` pasa sin errores.

## Riesgos y notas

El error típico de esta fase es apurarla para llegar rápido a la parte divertida. Si los repositorios quedan mal hechos o el SQL se riega por la aplicación, lo pagas en la fase 5 con intereses.

## Entregable

Etiqueta `v0.1.0`. Aplicación navegable con organizaciones y eventos persistidos.

## Queda listo para la siguiente fase

Base de datos con el esquema completo, repositorios de organización y evento, ventana principal donde colgar nuevas vistas, y sistema de idiomas.

---

# FASE 2 — Generación de cartones

## Punto de partida

Tienes una aplicación que abre, con base de datos migrada y esquema completo. Puedes crear organizaciones con su marca y eventos en borrador. Existe la capa de repositorios y el sistema de idiomas. Todavía no hay nada relacionado con el bingo en sí.

## Objetivo

Que la aplicación genere lotes de cartones de 75 bolas, únicos, con código correlativo, y que puedas consultarlos en pantalla. Toda esta fase es dominio puro: se puede probar sin abrir una ventana.

## Tareas

### 2.1 Dominio del cartón
- `dominio/carton.py`: constantes de rangos por columna, constante `BIT_LIBRE = 12`, función `indice_bit(fila, columna)`.
- Función `generar_carton(rng)` según la sección 4.2 del documento técnico: extracción sin reemplazo por columna, espacio libre en el centro, retorno como matriz 5x5.
- Función `orden_canonico(carton)` que serializa los 24 números en orden de columna, de arriba a abajo, separados por comas.
- Función `firma(carton)` que devuelve el SHA-256 del orden canónico.
- Función `numeros_por_bit(carton)` que devuelve el diccionario `{numero: bit}` usado luego en la partida.
- El generador aleatorio se recibe como parámetro, nunca se instancia dentro. En producción `secrets.SystemRandom()`, en pruebas `random.Random(semilla)`.

### 2.2 Servicio de generación de lotes
- `servicios/servicio_cartones.py` con `generar_lote(evento_id, cantidad, prefijo_codigo)`.
- Registro del lote con su semilla, para poder reproducirlo.
- Generación con control de unicidad: si la firma ya existe en el evento, se descarta y se genera otro. Registrar en el log cuántas colisiones hubo (esperado: cero).
- Códigos correlativos con formato configurable: `<PREFIJO>-<AÑO>-<SECUENCIA>`, con la secuencia rellenada con ceros según la cantidad del lote.
- Inserción por bloques de 500 cartones por transacción, no uno por uno ni todo en una sola transacción.
- Ejecución en `QThread` con señal de progreso y posibilidad de cancelar. Si se cancela, se revierte el lote completo.

### 2.3 Estados del cartón
- Implementar las transiciones válidas: `generado → impreso → entregado → vendido`, y `→ anulado` desde cualquiera.
- Métodos en el repositorio para cambiar el estado de un rango de códigos o de un lote completo.
- Rechazar transiciones inválidas con un error claro, no en silencio.

### 2.4 Repositorio de cartones
- `repo_carton.py`: inserción masiva, obtener por código, obtener por id, listar por evento con filtros de estado y paginación, contar por estado.
- Índices ya creados en la migración inicial. Verificar con `EXPLAIN QUERY PLAN` que la búsqueda por código los usa.

### 2.5 Interfaz de generación y consulta
- Vista dentro del evento: botón de generar lote con campo de cantidad, prefijo de código, y barra de progreso.
- Listado paginado de cartones con filtro por estado y búsqueda por código.
- Visor de un cartón: dibujar la cuadrícula 5x5 con sus números y el espacio libre. Este widget se reutiliza en la fase 5 para validar ganadores, así que conviene hacerlo bien: recibe un cartón y opcionalmente un conjunto de números marcados y un patrón a resaltar.
- Panel de resumen: total generado, por estado.

### 2.6 Pruebas del dominio
- Un cartón nunca tiene números repetidos en una columna.
- Cada columna respeta su rango (B entre 1 y 15, etcétera).
- La columna N tiene 4 números y el centro es el espacio libre.
- El orden canónico y la firma son deterministas con la misma semilla.
- Generar 50.000 cartones y verificar que no hay firmas repetidas.
- Reproducibilidad: la misma semilla produce el mismo lote.

## Criterios de aceptación

- Generar 10.000 cartones toma segundos y muestra progreso real, no una barra falsa.
- No existen dos cartones con la misma firma dentro de un evento; el índice único lo garantiza a nivel de base de datos.
- Se puede buscar un cartón por su código y verlo dibujado en pantalla.
- Cancelar la generación a mitad no deja cartones huérfanos.
- Todas las pruebas del dominio pasan.

## Riesgos y notas

Cuidado con generar el lote en el hilo de la interfaz: la ventana se congela y Windows la marca como "no responde". Va en hilo aparte desde el principio.

## Entregable

Etiqueta `v0.2.0`. Generación de lotes únicos con consulta y visor de cartones.

## Queda listo para la siguiente fase

Cartones reales en base de datos con los que alimentar el motor de impresión, y el widget de cuadrícula reutilizable.

---

# FASE 3 — Plantilla e impresión

## Punto de partida

La aplicación gestiona organizaciones y eventos, y genera lotes de cartones únicos con código, que puedes listar y ver en pantalla. Existe el widget que dibuja una cuadrícula 5x5. Los cartones están en estado `generado` y nadie los ha impreso.

## Objetivo

Convertir esos cartones en un PDF listo para imprenta, completamente personalizado con la marca de la organización, en los formatos de 1, 2, 4 o 6 cartones por hoja. Esta fase es la que hace que el producto sirva para algo tangible.

## Tareas

### 3.1 Modelo de plantilla
- `impresion/plantilla.py`: clase que representa el JSON de la sección 5.1 del documento técnico, con valores por defecto sensatos y validación.
- Serialización y deserialización desde `evento.plantilla_json`.
- Plantillas guardadas como preajustes reutilizables entre eventos de la misma organización.

### 3.2 Motor de render
- `impresion/render_pdf.py` con ReportLab.
- Función que dibuja **un cartón** en un lienzo, en una posición y tamaño dados. Es la unidad básica: todo lo demás la reutiliza.
- Elementos del cartón, todos configurables desde la plantilla: logo principal, logo secundario, título, subtítulo, encabezado B-I-N-G-O con letras personalizables, cuadrícula con grosor y color, números con fuente y tamaño, contenido del espacio libre (texto, estrella o logo), código del cartón, código QR, marca de agua, textos superior e inferior, datos de contacto.
- Cálculo de disposición: dado el tamaño de hoja, la orientación, los márgenes y la cantidad de cartones por hoja, calcular las posiciones y tamaños.
- Marcas de corte cuando hay más de un cartón por hoja.

### 3.3 Código QR con firma
- Generar el contenido `CODIGO|HMAC8`, con HMAC calculado sobre una clave derivada del evento.
- Guardar la clave del evento en la base de datos.
- Función de verificación que se usará en la fase 5: dado un texto de QR, validar la firma y devolver el código.

### 3.4 Vista previa en la interfaz
- Editor de plantilla con controles para cada opción, agrupados por secciones (marca, textos, identificación, estructura, hoja).
- Vista previa que renderiza un cartón de ejemplo **con el mismo motor** que produce el PDF. No una aproximación dibujada con Qt: eso garantiza que lo que se ve es lo que se imprime.
- La vista previa se actualiza con un pequeño retardo tras cada cambio, para no re-renderizar en cada tecla.

### 3.5 Generación por lotes
- Servicio `servicio_impresion.py` que recorre los cartones de un lote y produce el PDF.
- Ejecución en `QThread` con progreso y cancelación.
- Cargar logos e imágenes **una sola vez** y reutilizar el objeto de imagen de ReportLab en todas las páginas. Esta es la diferencia entre un PDF de 20 MB y uno de 800 MB.
- Escritura incremental por página, liberando memoria.
- Particionado configurable: dividir el PDF cada X hojas, por defecto 500, con nombres numerados.
- Al terminar, ofrecer marcar el lote como `impreso`.

### 3.6 Pruebas
- Que un lote grande termine sin agotar memoria y que el archivo resultante abra.
- Que el tamaño del PDF crezca de forma lineal y razonable con la cantidad de cartones.
- Que la verificación del QR acepte los códigos generados y rechace uno alterado.

## Criterios de aceptación

- Un PDF de 10.000 cartones se genera sin que la aplicación se congele, con progreso visible y opción de cancelar.
- El archivo pesa lo razonable y abre en un lector estándar.
- Impreso a tamaño real, el cartón es legible y los cortes cuadran.
- Cambiar el logo o los colores de la organización se refleja en el siguiente PDF sin tocar código.
- La vista previa coincide con el PDF final.

## Riesgos y notas

Prueba impresa temprano y de verdad, en papel. Los problemas de márgenes, tamaño de fuente y contraste no se ven en pantalla. Imprime una hoja de cada formato antes de dar la fase por cerrada.

## Entregable

Etiqueta `v0.3.0`. PDF de cartones personalizado y listo para imprenta.

## Queda listo para la siguiente fase

Cartones impresos que se entregan a la organización, lo que habilita el flujo de venta y registro de compradores.

---

# FASE 4 — Compradores, rondas y premios

## Punto de partida

El sistema genera cartones únicos y los imprime personalizados. Los cartones físicos ya están en manos de la organización, que los está vendiendo. Los registros en base de datos están en estado `impreso` o `entregado`. Todavía no hay forma de saber quién compró qué, ni de configurar cómo se va a jugar.

## Objetivo

Cerrar la brecha entre el cartón impreso y la partida: registrar compradores desde el Excel de la organización, y dejar el evento completamente configurado con sus rondas, patrones y premios. Al terminar esta fase, el evento está listo para jugarse, solo falta el motor que lo juegue.

## Tareas

### 4.1 Exportación de la plantilla de Excel
- Generar un `.xlsx` con una fila por cartón del evento: columna de código (protegida) y columnas vacías de nombre, teléfono, cédula y correo.
- Hoja de instrucciones dentro del mismo archivo, en el idioma configurado.
- Formato de las celdas para evitar que Excel convierta teléfonos y cédulas en números y les coma los ceros iniciales.

### 4.2 Importación con validación en seco
- Lectura del archivo con openpyxl.
- **Primer paso, sin escribir nada:** producir un informe con filas correctas, códigos inexistentes, códigos duplicados dentro del archivo, cartones ya asignados a otro comprador, y filas sin nombre.
- Mostrar el informe en pantalla con la posibilidad de exportarlo.
- **Segundo paso, tras confirmación explícita:** escribir dentro de una única transacción. Los cartones con comprador pasan a estado `vendido`.
- Permitir reimportar: un segundo archivo con más ventas no debe romper lo ya cargado.

### 4.3 Gestión manual de compradores
- Alta manual de un comprador para un código concreto, para las ventas de último minuto.
- Edición y corrección de datos.
- Anulación de una venta con registro en auditoría.

### 4.4 Conciliación
- Reporte que compara generados, impresos, entregados, vendidos y anulados.
- Recaudación teórica según el precio de la tabla.
- Exportable a PDF y Excel.

### 4.5 Dominio de patrones
- `dominio/patron.py`: función `mascara(celdas)` que construye el entero de 25 bits, y las constantes de los patrones del sistema.
- Catálogo precargado en la primera ejecución: líneas horizontales, verticales, diagonales, cuatro esquinas, X, cruz, marco, diamante, postage stamp, letras T, L, H y E, escalera, y cartón lleno.
- Resolver la decisión pendiente de los patrones con variantes ("cualquier línea horizontal" son cinco máscaras, gana quien complete cualquiera). Modelo propuesto: un patrón puede tener una o varias máscaras, guardadas como lista serializada; la validación comprueba si alguna se cumple.
- Indicador por patrón de si el espacio libre participa.

### 4.6 Editor de patrones
- Grilla 5x5 clicable que enciende y apaga celdas y produce la máscara.
- Nombre, guardado como patrón propio de la organización.
- Vista previa de cómo se verá en la pantalla de transmisión.
- Los patrones del sistema no se pueden borrar, solo duplicar y modificar.

### 4.7 Configuración de rondas
- CRUD de rondas dentro del evento: nombre, orden, patrón, premio.
- Premio con nombre, descripción, tipo (efectivo o bien), valor e imagen. Carga y normalización de la imagen con Pillow.
- Reordenar rondas arrastrando o con botones.
- Validación antes de permitir iniciar el evento: todas las rondas tienen patrón y premio, hay al menos un cartón vendido.

### 4.8 Editor del tema del dashboard
- Interfaz que produce el `tema_json` de la sección 7 del documento técnico: colores, imagen de fondo, visibilidad y posición de cada bloque, y ajustes de juego (intervalo, modo, pausa al ganador, voz, sonidos).
- Vista previa estática de cómo quedará la pantalla de transmisión.

### 4.9 Pruebas
- Importación con archivos deliberadamente sucios: códigos inventados, filas vacías, duplicados, columnas movidas de lugar.
- Máscaras de todos los patrones del sistema: verificar bit por bit.
- Que un patrón con variantes se cumpla con cualquiera de sus máscaras.

## Criterios de aceptación

- Importar un Excel de 1.000 compradores produce un informe correcto antes de escribir, y la escritura es atómica.
- Un archivo con errores no deja la base a medio llenar.
- Se puede crear un patrón propio desde la grilla y asignarlo a una ronda.
- Un evento con rondas incompletas no deja iniciar el sorteo, y dice exactamente qué falta.
- El reporte de conciliación cuadra con lo que hay en base de datos.

## Riesgos y notas

Los Excel que devuelven las organizaciones siempre vienen peor de lo que uno espera: columnas renombradas, filas en blanco en medio, nombres en mayúsculas y minúsculas mezcladas. La validación en seco no es un lujo, es lo que evita corregir datos a mano la noche del evento.

## Entregable

Etiqueta `v0.4.0`. Evento completamente configurado y listo para jugarse.

## Queda listo para la siguiente fase

Cartones vendidos con comprador, rondas con patrón y premio, y el tema visual del dashboard definido. El motor de sorteo ya tiene todo lo que necesita como entrada.

---

# FASE 5 — Sorteo en vivo y cierre

## Punto de partida

Todo lo anterior. El evento tiene cartones generados, impresos y vendidos con sus compradores registrados; rondas configuradas con patrón y premio; y el tema visual definido. Existe el widget que dibuja un cartón con números marcados y un patrón resaltado, hecho en la fase 2. Falta lo único que el público llega a ver: el juego.

## Objetivo

Ejecutar el bingo en vivo con dos pantallas, detectar ganadores, validarlos, manejar empates, sobrevivir a un cierre inesperado, y cerrar el evento con sus actas y reportes. Al terminar esta fase existe la versión 1.0 instalable.

## Tareas

### 5.1 Dominio del bombo
- `dominio/bombo.py` según la sección 4.7 del documento técnico: extracción sin reposición de 1 a 75, con `secrets.SystemRandom()`.
- Constructor que acepta las bolas ya extraídas, para reconstruir el bombo al reanudar.
- Excepción clara cuando el bombo se agota.

### 5.2 Dominio de la partida
- `dominio/partida.py`: clase `CartonEnJuego` con su entero `marcado` inicializado con el bit del espacio libre.
- Índice inverso `{numero: [cartones]}` construido al iniciar la ronda. Al salir una bola solo se tocan los cartones que la contienen, no los mil.
- Función `es_ganador(marcado, patron)` y función `faltan(marcado, patron)` para la alerta de "a una bola".
- Evaluación tras cada bola únicamente sobre los cartones que se marcaron en esa jugada.

### 5.3 Servicio de sorteo
- Máquina de estados de la ronda según la sección 6.1: pendiente, en curso, pausada, cerrada.
- **Persistencia por bola dentro de una transacción única:** insertar la extracción, insertar los ganadores detectados con `confirmado = 0`, actualizar el estado de la ronda, y escribir la línea en el archivo de log con `flush()` forzado.
- El commit ocurre **antes** de que la interfaz muestre la bola. Es lo que hace real la promesa de retomar otro día.
- Señales de Qt según la tabla de la sección 6.4: `bola_extraida`, `cartones_a_una_bola`, `ganadores_detectados`, `ganador_confirmado`, `ronda_cambiada`.
- Modo manual y modo automático con intervalo configurable.
- Pausa automática al detectar ganador, si está activada.

### 5.4 Ventana de transmisión
- Ventana sin bordes, a pantalla completa en el monitor seleccionado.
- Lienzo de referencia 1920x1080, escalado al monitor de salida.
- Bloques configurables según el `tema_json`: bombo animado, número actual en grande, tablero de las 75 bolas con las cantadas resaltadas, patrón activo, imagen del premio, logo, contador de bolas, reloj, banner de texto corrido.
- Animación de extracción: no tiene que ser espectacular, tiene que ser fluida y no bloquear.
- Aviso de "¡BINGO!" al detectar ganador, mostrando el patrón completado **sin revelar código ni nombre** hasta que el operador confirme.
- Pantalla de bienvenida y pantalla de cierre con textos configurables.

### 5.5 Ventana de operador
- Controles: iniciar ronda, extraer bola, pausar, reanudar, cerrar ronda, siguiente ronda.
- Tablero de números cantados y contador.
- Panel de cartones a una bola, con código y comprador.
- Panel de ganadores detectados con todos sus datos y botones de confirmación.
- Buscador por código de cartón, disponible en todo momento: muestra la cara del cartón con los números marcados y el patrón resaltado, y dice si cumple o no. Reutiliza el widget de la fase 2.
- Selector de monitor de transmisión y botón para mostrar u ocultar esa ventana.

### 5.6 Validación y registro de ganadores
- Flujo de confirmación: el reclamante da su código, el operador lo ingresa, el sistema muestra la cara del cartón y confirma si cumple el patrón con las bolas extraídas hasta ese momento.
- Rechazar cartones que no estén en estado `vendido`.
- Manejo de empate: listado de todos los ganadores, selección de uno para el desempate externo, o marcado de reparto entre varios. La decisión queda registrada en la tabla `ganador` y en auditoría.
- Resolver la decisión pendiente de qué hacer si nadie reclama: implementar como ajuste configurable (continuar la ronda, cerrarla igual y contactar después).

### 5.7 Reanudación
- Al abrir un evento con una ronda en curso o pausada, ofrecer reanudar.
- Reconstrucción: cargar extracciones ordenadas, reconstruir el bombo con las restantes, recargar los cartones vendidos y reproducir las marcas aplicando las bolas en orden.
- Verificar que el estado reconstruido coincide exactamente con el que había antes del cierre.

### 5.8 Sonido y locución
- Efectos: extracción de bola, alerta de ganador, música de fondo con control de volumen.
- Locución de los números, en español o inglés, independiente del idioma de la interfaz.
- Resolver la decisión pendiente entre audio pregrabado (mejor calidad, 150 archivos por idioma) o síntesis de voz del sistema.
- Todo desactivable.

### 5.9 Actas y reportes
- Acta del sorteo por ronda en PDF: datos del evento y la organización, patrón, premio, secuencia completa de bolas en orden, ganadores con su código, y hash SHA-256 del contenido.
- Reporte del evento en PDF y Excel: cartones generados, vendidos y recaudación, rondas con sus ganadores, datos de contacto de cada ganador.
- Log de partida en texto plano, escrito en tiempo real durante el juego.

### 5.10 Respaldos
- Botón de exportar respaldo del evento: copia de la base con la API de respaldo en línea de SQLite, más medios y logs, en un `.zip` fechado.
- Recordatorio automático antes de iniciar el sorteo y al cerrar el evento.

### 5.11 Empaquetado y distribución
- PyInstaller en modo `--onedir`.
- Inno Setup: instalador, accesos directos, creación de la estructura en `%LOCALAPPDATA%`.
- Versión visible en ajustes y registrada en auditoría al abrir un evento.
- Verificar que las migraciones se aplican bien al actualizar sobre una instalación existente con datos.

### 5.12 Pruebas
- Bombo: no repite, se agota en 75, se reconstruye correctamente desde extracciones previas.
- Detección de ganador: positivos, negativos, patrón que incluye el espacio libre y patrón que no.
- Alerta de "a una bola": cuenta correcta en todos los casos.
- Reanudación: interrumpir en la bola N y verificar que el estado reconstruido es idéntico.
- **Ensayo completo manual:** evento de prueba con 200 cartones, tres rondas con patrones distintos, las dos pantallas conectadas, OBS capturando, y un cierre forzado a mitad de ronda para probar la reanudación en condiciones reales.

## Criterios de aceptación

- Un sorteo completo de tres rondas corre de principio a fin sin trabas ni congelamientos.
- Matar el proceso a mitad de ronda y reabrir devuelve el juego exactamente donde estaba.
- La pantalla de transmisión se ve limpia en OBS y es legible en un celular.
- Los ganadores se detectan en el instante correcto y no se revelan antes de la validación.
- Un cartón no vendido nunca puede ganar.
- El acta y el reporte del evento se generan y cuadran con lo ocurrido.
- El instalador deja la aplicación funcionando en un equipo limpio sin Python.

## Riesgos y notas

Esta es la fase donde más tienta improvisar en vivo. No estrenes en un evento real: haz el ensayo completo con OBS y una transmisión de prueba a un canal privado, midiendo el retraso real de la plataforma, antes de comprometerte con una organización.

## Entregable

Etiqueta `v1.0.0`. Aplicación instalable, probada en ensayo completo.

---

## Resumen de fases

| Fase | Foco | Entregable | Etiqueta |
|---|---|---|---|
| 1 | Cimientos | Aplicación navegable con organizaciones y eventos | `v0.1.0` |
| 2 | Generación de cartones | Lotes únicos con visor | `v0.2.0` |
| 3 | Plantilla e impresión | PDF listo para imprenta | `v0.3.0` |
| 4 | Compradores y configuración | Evento listo para jugarse | `v0.4.0` |
| 5 | Sorteo en vivo | Versión instalable | `v1.0.0` |

## Decisiones que hay que cerrar durante el desarrollo

| Decisión | Se necesita en |
|---|---|
| Modelo de patrones con variantes múltiples | Fase 4 |
| Qué pasa si nadie reclama el premio | Fase 5 |
| Tipografías personalizadas: catálogo cerrado o carga libre | Fase 3 |
| Locución: audio pregrabado o síntesis de voz | Fase 5 |
| Política de retención de datos de compradores | Fase 4 |
