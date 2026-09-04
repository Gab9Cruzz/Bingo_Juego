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
