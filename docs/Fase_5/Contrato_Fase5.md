# Proyecto BINGO — FASE 5 — Sorteo en vivo y cierre

**Autor:** Gabriel  
**Fecha:** septiembre 2026  
**Plan general:** `docs/Plan_Fases_Bingo.md`  
**Documentos base:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)  
**Fase anterior:** `docs/Fase_4/Contrato_Fase4.md` · **Fase siguiente:** —

---

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