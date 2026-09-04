# Proyecto BINGO — FASE 1 — Cimientos

**Autor:** Gabriel  
**Fecha:** septiembre 2026  
**Plan general:** `docs/Plan_Fases_Bingo.md`  
**Documentos base:** `docs/Proyecto_Alcance.md` (alcance), `docs/Documento_Tecnico.md` (arquitectura y algoritmos)  
**Fase anterior:** — · **Fase siguiente:** `docs/Fase_2/Contrato_Fase2.md`

---

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