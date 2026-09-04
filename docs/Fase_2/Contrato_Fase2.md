# Proyecto BINGO — FASE 2 — Generación de cartones

**Autor:** Gabriel  
**Fecha:** septiembre 2026  
**Plan general:** `docs/Plan_Fases_Bingo.md`  
**Documentos base:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)  
**Fase anterior:** `docs/Fase_1/Contrato_Fase1.md` · **Fase siguiente:** `docs/Fase_3/Contrato_Fase3.md`

---

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