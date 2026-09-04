# Proyecto BINGO — FASE 3 — Plantilla e impresión

**Autor:** Gabriel  
**Fecha:** septiembre 2026  
**Plan general:** `docs/Plan_Fases_Bingo.md`  
**Documentos base:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)  
**Fase anterior:** `docs/Fase_2/Contrato_Fase2.md` · **Fase siguiente:** `docs/Fase_4/Contrato_Fase4.md`

---

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