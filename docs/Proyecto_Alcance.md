# Proyecto BINGO — Definición de alcance (v1)

**Autor:** Gabriel
**Fecha:** septiembre 2026
**Estado:** alcance cerrado, pendiente de desglose en tareas

---

## 1. Qué es el producto

Un software de escritorio que permite a un operador (Gabriel) montar y ejecutar bingos de 75 bolas para organizaciones que lo contratan como servicio. El software cubre el ciclo completo: generar y personalizar las tablas, imprimirlas, registrar quién las compró, configurar los juegos y premios, y correr el sorteo en vivo frente a cámara mientras se transmite.

**Modelo de negocio:** servicio prestado por Gabriel a la organización. El precio lo define él por evento. La venta o licenciamiento del software a terceros queda como posibilidad futura, fuera del alcance de la v1.

**Escala de diseño:** la cantidad de tablas a generar la define siempre el operador al momento de crear el lote. No hay un límite fijo en el sistema. Un evento típico ronda las 10.000 tablas generadas para imprimir, de las cuales se venden alrededor de 1.000, pero se puede solicitar más sin problema. El generador y la exportación a PDF deben estar diseñados para crecer: generación por lotes, barra de progreso y PDF particionado en varios archivos cuando el volumen lo amerite.

---

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Formato de bingo | 75 bolas, cartón 5x5, encabezado B-I-N-G-O |
| Distribución de cartones | Impresos, entregados a la organización, que los vende |
| Identificación | Cada cartón tiene un ID único impreso |
| Registro de compradores | Importación de Excel que llena la organización |
| Arquitectura | Aplicación de escritorio local. Nube en una fase posterior |
| Premios | Efectivo o bienes, según lo defina la organización contratante |
| Idiomas | Español e inglés |
| Personalización | Alta: tabla y dashboard adaptables a la marca de cada organización |
| Transmisión | En vivo por plataforma externa (Facebook, YouTube, etc.), capturada con OBS |

---

## 3. Flujo de un evento de punta a punta

1. **Alta de la organización.** Se crea el perfil: nombre, logo, colores, datos de contacto, textos legales.
2. **Configuración del evento.** Fecha, cantidad de tablas a generar, precio de la tabla, número de rondas.
3. **Generación de tablas.** El sistema genera N cartones únicos con ID, aplicando la plantilla visual de la organización.
4. **Exportación e impresión.** Se genera el PDF (1, 2, 4 o 6 cartones por hoja) y se manda a imprenta.
5. **Entrega.** Los cartones físicos van a la organización, que los vende.
6. **Registro de ventas.** La organización llena el Excel (ID de cartón → datos del comprador) y lo devuelve. Gabriel lo importa al sistema.
7. **Configuración de rondas.** Por cada ronda: patrón/modalidad, premio (nombre + imagen + tipo), orden.
8. **Ejecución en vivo.** Pantalla de operador + pantalla de transmisión. Se extraen bolas, se muestra el tablero, se detectan ganadores.
9. **Validación del ganador.** El reclamante da su ID, el operador lo ingresa y el sistema muestra la cara del cartón con el patrón resaltado.
10. **Cierre.** Se registra el ganador, se pasa a la siguiente ronda.
11. **Post-evento.** Reporte de la noche: bolas cantadas por ronda, ganadores, cartones vendidos, acta del sorteo en PDF.

---

## 4. Módulos funcionales

### 4.1 Módulo de organizaciones (marca blanca)
- CRUD de organizaciones.
- Carga de logo (principal y secundario), colores de marca, tipografía.
- Textos personalizables: nombre del evento, eslogan, pie de página, contacto, condiciones.
- La organización activa determina la apariencia de toda la app y de los cartones.

### 4.2 Módulo de generación de cartones
- Generación de N cartones únicos de 75 bolas (columnas B 1–15, I 16–30, N 31–45 con espacio libre, G 46–60, O 61–75).
- Sin números repetidos dentro de una columna.
- Verificación de unicidad: se guarda una firma/hash canónica por cartón y se rechazan duplicados exactos.
- Asignación de ID único legible y correlativo por evento (ej. `ORG-2026-000001`).
- Estado por cartón: `generado → impreso → entregado → vendido → anulado`.
- Semilla de generación registrada para poder reproducir el lote si hace falta.

### 4.3 Módulo de diseño e impresión de la tabla
- Editor de plantilla del cartón con vista previa.
- Exportación a PDF listo para imprenta, con 1 / 2 / 4 / 6 cartones por hoja, tamaño Carta o A4.
- Marcas de corte y márgenes configurables.
- (Ver catálogo completo de personalizables en la sección 5.)

### 4.4 Módulo de compradores
- Exportación de una plantilla Excel con los IDs generados, para que la organización la llene.
- Importación del Excel devuelto, con validación: IDs que no existen, IDs duplicados, filas incompletas.
- Reporte de conciliación: impresos vs. vendidos vs. sin registrar.
- Solo los cartones marcados como vendidos participan en el juego.
- Datos mínimos por comprador: nombre, teléfono, y opcionalmente cédula y correo.

### 4.5 Módulo de juegos y premios
- Un evento contiene varias rondas. Cada ronda tiene: nombre, patrón, premio y orden.
- Catálogo de patrones precargados: línea horizontal, vertical, diagonal, cuatro esquinas, X, cruz, marco, diamante, postage stamp, letras (T, L, H, E), escalera, y cartón lleno.
- Editor de patrones: grilla 5x5 clicable para crear patrones propios, con opción de indicar si el espacio libre cuenta.
- Premio por ronda: nombre, descripción, tipo (efectivo / bien), valor e **imagen**.
- Un premio puede tener varias imágenes (galería) si es un combo.

### 4.6 Módulo de sorteo en vivo
- **Dos pantallas separadas:** pantalla de operador (controles, lista de cartones, búsqueda por ID, alertas) y pantalla de transmisión (limpia, para capturar con OBS).
- Extracción de bola con animación de bombo y sonido.
- Número actual en grande, tablero de las 75 bolas con las cantadas resaltadas.
- Patrón activo visible, imagen del premio, logo de la organización, contador de bolas y de ronda.
- Modo manual (el operador presiona para sacar cada bola) y modo automático con intervalo configurable.
- Detección automática de cartones ganadores tras cada bola, con pausa automática.
- Manejo de múltiples ganadores: se listan todos con su ID y comprador; el operador puede seleccionar uno (desempate externo) o marcarlos a todos como ganadores para repartir.
- Búsqueda y verificación de un cartón por ID en cualquier momento: muestra la cara del cartón, qué números tiene marcados y si cumple el patrón activo.

### 4.7 Módulo de persistencia y auditoría
- Base de datos local SQLite; todo se guarda tras cada acción.
- Estado de la partida persistido después de **cada bola**: si la app se cierra, al abrirla ofrece reanudar la ronda exactamente donde quedó.
- Archivo de log de la partida que se va escribiendo en tiempo real (secuencia de bolas con hora, ronda, patrón, ganadores).
- Exportación del acta del sorteo en PDF por ronda y del reporte completo del evento.
- Respaldo manual del archivo de base de datos con un botón ("Exportar respaldo del evento").

### 4.8 Módulo de configuración general
- Idioma de la interfaz: español / inglés.
- Configuración de audio: activar/desactivar locución de números, volumen, efectos.
- Configuración de pantalla: resolución de la vista de transmisión, selección de monitor.
- Preferencias de impresión por defecto.

---

## 5. Catálogo de elementos personalizables

### 5.1 En la tabla (cartón impreso)

**Identidad y marca**
- Logo principal de la organización (posición, tamaño).
- Logo secundario o de patrocinador (uno o varios, en pie de página).
- Nombre de la organización.
- Título del evento (ej. "Bingo Solidario 2026").
- Subtítulo o eslogan.
- Colores: fondo del cartón, encabezado B-I-N-G-O, líneas de la grilla, texto.
- Imagen o color de fondo, con control de opacidad para no restar legibilidad.
- Marco/borde decorativo.

**Contenido de texto**
- Fecha y hora del evento.
- Lugar o plataforma de transmisión.
- Precio de la tabla.
- Texto libre superior y texto libre inferior (para condiciones, agradecimientos, mensaje de la organización).
- Datos de contacto (teléfono, WhatsApp, redes).
- Aviso legal o de deslinde.

**Identificación y control**
- ID del cartón: posición, tamaño y formato del correlativo.
- Código QR o de barras con el ID (opcional, activable).
- Serie o lote del cartón.
- Marca de agua con el logo (opacidad configurable) como antifraude básico.
- Numeración de talón desprendible (opcional, si la organización quiere quedarse con una colilla).

**Estructura y tipografía**
- Mostrar u ocultar el encabezado B-I-N-G-O.
- Etiquetas del encabezado personalizables (permite cambiar B-I-N-G-O por otras 5 letras o palabras en la versión en inglés / o el nombre corto de la organización).
- Contenido del espacio libre: texto "LIBRE"/"FREE", una estrella, o el logo de la organización.
- Tipografía y tamaño de los números.
- Grosor de líneas y espaciado de la grilla.

**Formato de hoja**
- Cartones por hoja: 1, 2, 4 o 6.
- Tamaño de papel: Carta o A4.
- Orientación: vertical u horizontal.
- Márgenes y marcas de corte.
- Cartones por hoja con disposiciones distintas (en columna, en cuadrícula).

### 5.2 En el programa (dashboard de sorteo)

**Identidad visual**
- Logo en la pantalla principal y en la pantalla de transmisión.
- Tema de color completo (fondo, acentos, color del número cantado).
- Imagen de fondo de la escena de transmisión.
- Tipografía general.

**Composición de la pantalla de transmisión**
- Mostrar/ocultar y reposicionar cada bloque: bombo, número actual, tablero de 75, patrón activo, imagen del premio, logo, contador de bolas, reloj, banner de texto.
- Tamaño del número actual (pensando en quien mira desde el celular).
- Banner de texto corrido (para mensajes de la organización o patrocinadores durante el juego).
- Mostrar u ocultar el nombre del ganador al detectarlo.

**Comportamiento del juego**
- Intervalo entre bolas en modo automático.
- Pausa automática al detectar ganador (sí/no).
- Anunciar por voz el número cantado (sí/no) e idioma de la locución.
- Sonidos: extracción de bola, alerta de ganador, música de fondo.
- Confirmación obligatoria antes de cada extracción (para eventos más ceremoniosos).

**Contenido del evento**
- Nombre y orden de cada ronda.
- Patrón por ronda (incluidos patrones creados por el usuario).
- Premio por ronda: nombre, imagen, tipo y valor.
- Textos de la pantalla de bienvenida y de cierre.

---

## 6. Reglas de negocio que hay que fijar antes de programar

1. **Ganador según las bolas extraídas por el sistema**, no según lo que el jugador ve en la transmisión. La transmisión tiene entre 7 y 30 segundos de retraso; sin esta regla escrita habrá disputas. Debe aparecer en la pantalla de bienvenida y en el cartón.
2. **Canal y ventana de reclamo.** Definir por dónde canta bingo el jugador (WhatsApp, comentario en el live) y cuántos segundos tiene. Al detectar un ganador el sistema pausa y espera el reclamo.
3. **Validación obligatoria por ID.** Ningún premio se entrega sin que el operador ingrese el ID y el sistema confirme que ese cartón está vendido y cumple el patrón.
4. **Empate.** Se muestran todos los ganadores; el operador elige uno o marca reparto. La decisión queda registrada.
5. **Cartón no vendido que "gana".** No procede: solo participan cartones en estado vendido con comprador registrado.
6. **Falla técnica en vivo.** Si la aplicación o el equipo falla, se comunica y el bingo se retoma otro día desde la ronda pendiente, reanudando el estado guardado.

---

## 7. Fuera del alcance de la v1

- Marcado digital del cartón por el jugador desde su celular.
- Venta y cobro de cartones dentro de la app.
- Sincronización y respaldo automático en la nube.
- Portal web de verificación pública de cartones.
- Semilla verificable publicada (commit-reveal).
- Licenciamiento y activación del software para terceros.
- Multi-usuario o multi-operador simultáneo.

---

## 8. Riesgos y supuestos vigentes

- **Legal.** Los premios en efectivo son el punto más expuesto de la operación en Ecuador. El riesgo lo asume principalmente la organización contratante, pero conviene dejarlo por escrito en el contrato de servicio y consultar a un abogado antes del primer evento pagado.
- **Plataforma de transmisión.** Facebook y YouTube tienen políticas explícitas contra la transmisión de juegos con premio sin autorización. El canal de la organización puede ser suspendido; esto también debe estar en el contrato.
- **Equipo único.** Al ser todo local, la máquina del evento es un punto único de falla. Mitigación mínima aceptada: guardado tras cada bola, log en archivo y respaldo manual antes y después del evento.
- **Datos de compradores.** Aplica la LOPDP. Se recogen datos mínimos, se guardan en el equipo del operador y se borran o entregan a la organización al cierre del evento.
- **Volumen variable.** La cantidad de tablas la fija el operador en cada lote, sin tope definido. El punto de tensión no es la base de datos ni la validación de ganadores (SQLite maneja cientos de miles de filas sin esfuerzo), sino la generación del PDF de impresión, que consume memoria y tiempo de forma proporcional. Por eso se genera por lotes, con progreso visible y con opción de dividir el PDF en varios archivos.

---

## 9. Decisión pendiente

- Definir la política concreta de retención de datos de compradores: cuánto tiempo se guardan tras el evento y quién se queda con el archivo. Propuesta: se conservan en el sistema mientras dure el evento y hasta 30 días después para reclamos, se entrega el reporte a la organización y luego se eliminan del equipo del operador.