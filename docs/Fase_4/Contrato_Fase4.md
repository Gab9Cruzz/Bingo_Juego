# Proyecto BINGO — FASE 4 — Compradores, rondas y premios

**Autor:** Gabriel  
**Fecha:** septiembre 2026  
**Plan general:** `docs/Plan_Fases_Bingo.md`  
**Documentos base:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)  
**Fase anterior:** `docs/Fase_3/Contrato_Fase3.md` · **Fase siguiente:** `docs/Fase_5/Contrato_Fase5.md`

---

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