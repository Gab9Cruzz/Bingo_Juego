# Proyecto BINGO — Documento técnico

**Autor:** Gabriel
**Fecha:** septiembre 2026
**Versión:** 1.0
**Documento relacionado:** `docs/Proyecto_Alcance.md` (alcance funcional)

Este documento describe *cómo* se construye el sistema. El qué y el para qué están en el documento de alcance. Todo lo que se decida durante el desarrollo se registra aquí.

---

## 1. Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Lenguaje | Python 3.12+ | Es el lenguaje del desarrollador; ecosistema completo para todo lo que necesita el proyecto |
| Interfaz gráfica | PySide6 (Qt 6) | Soporte nativo de múltiples monitores, animaciones fluidas para el bombo, licencia LGPL sin costo |
| Base de datos | SQLite 3 (WAL) | Archivo único, cero configuración, transaccional, suficiente para un sistema monousuario |
| Acceso a datos | `sqlite3` estándar + patrón repositorio | Sin ORM: el esquema es pequeño y el control directo del SQL evita una capa de abstracción innecesaria |
| Generación de PDF | ReportLab | Control fino de posicionamiento, necesario para plantillas de cartón configurables |
| Imágenes | Pillow | Validación, redimensionado y normalización de logos e imágenes de premios |
| Excel | openpyxl | Lectura y escritura de `.xlsx` para el flujo de compradores |
| Audio | `QtMultimedia` (PySide6) | Efectos de sonido y locución sin dependencias externas |
| Empaquetado | PyInstaller | Genera el ejecutable de Windows |
| Instalador | Inno Setup | Instalador estándar de Windows, gratuito |
| Pruebas | pytest | Estándar de facto |
| Formato de código | ruff (linter + formateador) | Rápido, una sola herramienta |
| Control de versiones | Git | Repositorio privado |

**Plataforma objetivo:** Windows 10/11 de 64 bits. El código se escribe multiplataforma, pero solo se prueba y empaqueta para Windows en la v1.

**Dependencias externas mínimas.** El instalador debe dejar la aplicación funcionando sin que el usuario instale Python ni nada más.

---

## 2. Arquitectura

### 2.1 Principio rector

Separación estricta en tres capas. La regla es que **el dominio no importa nada de PySide6 ni de sqlite3**. Toda la lógica de bingo (generar cartones, evaluar patrones, decidir ganadores) tiene que poder ejecutarse desde un script de consola o desde una prueba automatizada, sin abrir una ventana.

Esto no es purismo académico: es lo que permite probar el motor del sorteo sin montar un evento, y lo que hace que una eventual versión con nube o marcado digital reutilice el mismo núcleo.

```
┌─────────────────────────────────────────┐
│  Presentación (PySide6)                 │
│  Ventana operador · Ventana transmisión │
│  Diálogos · Widgets · Temas             │
└───────────────┬─────────────────────────┘
                │ llama a servicios, escucha señales
┌───────────────▼─────────────────────────┐
│  Aplicación (servicios / casos de uso)  │
│  ServicioEvento · ServicioCartones       │
│  ServicioSorteo · ServicioImpresion      │
└───────────────┬─────────────────────────┘
                │
      ┌─────────┴─────────┐
      ▼                   ▼
┌───────────────┐  ┌──────────────────────┐
│  Dominio      │  │  Persistencia        │
│  (Python puro)│  │  Repositorios SQLite │
│  Carton       │  │  Migraciones         │
│  Patron       │  │  Respaldos           │
│  Bombo        │  └──────────────────────┘
│  Reglas       │
└───────────────┘
```

### 2.2 Estructura de carpetas

```
bingo/
├── src/
│   └── bingo/
│       ├── __main__.py            # punto de entrada
│       ├── dominio/
│       │   ├── carton.py          # entidad Carton, generación
│       │   ├── patron.py          # máscaras de 25 bits
│       │   ├── bombo.py           # extracción de bolas
│       │   ├── partida.py         # estado de una ronda
│       │   └── reglas.py          # validación de ganadores
│       ├── persistencia/
│       │   ├── conexion.py        # apertura, PRAGMA, WAL
│       │   ├── migraciones/       # 001_inicial.sql, 002_...
│       │   ├── repo_organizacion.py
│       │   ├── repo_evento.py
│       │   ├── repo_carton.py
│       │   ├── repo_comprador.py
│       │   └── repo_partida.py
│       ├── servicios/
│       │   ├── servicio_cartones.py
│       │   ├── servicio_impresion.py
│       │   ├── servicio_compradores.py
│       │   ├── servicio_sorteo.py
│       │   └── servicio_respaldo.py
│       ├── impresion/
│       │   ├── plantilla.py       # modelo de la plantilla del cartón
│       │   └── render_pdf.py      # ReportLab
│       ├── ui/
│       │   ├── ventana_operador.py
│       │   ├── ventana_transmision.py
│       │   ├── vistas/            # una por pantalla
│       │   ├── widgets/           # bombo, tablero, grilla de patrón
│       │   └── tema.py            # aplicación de colores y tipografías
│       ├── i18n/
│       │   ├── es.json
│       │   └── en.json
│       └── config/
│           └── ajustes.py         # rutas, preferencias, constantes
├── tests/
├── recursos/                      # iconos, sonidos, fuentes por defecto
├── docs/
├── pyproject.toml
└── README.md
```

### 2.3 Ubicación de datos en el equipo

| Contenido | Ruta |
|---|---|
| Base de datos | `%LOCALAPPDATA%\Bingo\datos\bingo.db` |
| Logs de partida | `%LOCALAPPDATA%\Bingo\logs\<evento>\` |
| Respaldos | `%LOCALAPPDATA%\Bingo\respaldos\` |
| Imágenes y logos | `%LOCALAPPDATA%\Bingo\medios\<organizacion>\` |
| PDF generados | Carpeta elegida por el usuario |

**Regla crítica:** el archivo `.db` nunca se ubica en una carpeta sincronizada (OneDrive, Google Drive, Dropbox) ni en una unidad de red. Es la causa más frecuente de corrupción en SQLite.

---

## 3. Modelo de datos

### 3.1 Esquema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = FULL;   -- durante el sorteo en vivo

CREATE TABLE organizacion (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL,
    logo_path         TEXT,
    logo_secundario   TEXT,
    color_primario    TEXT DEFAULT '#1a1a2e',
    color_secundario  TEXT DEFAULT '#e94560',
    color_texto       TEXT DEFAULT '#ffffff',
    tipografia        TEXT,
    contacto          TEXT,
    creada_en         TEXT NOT NULL
);

CREATE TABLE evento (
    id                INTEGER PRIMARY KEY,
    organizacion_id   INTEGER NOT NULL REFERENCES organizacion(id),
    nombre            TEXT NOT NULL,
    fecha             TEXT,
    lugar             TEXT,
    precio_tabla      REAL,
    estado            TEXT NOT NULL DEFAULT 'borrador',
                      -- borrador | preparado | en_curso | finalizado
    plantilla_json    TEXT,   -- configuración visual del cartón
    tema_json         TEXT,   -- configuración visual del dashboard
    creado_en         TEXT NOT NULL
);

CREATE TABLE lote (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    cantidad          INTEGER NOT NULL,
    semilla           TEXT NOT NULL,      -- para reproducibilidad
    generado_en       TEXT NOT NULL
);

CREATE TABLE carton (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    lote_id           INTEGER NOT NULL REFERENCES lote(id),
    codigo            TEXT NOT NULL,      -- ID visible: ORG-2026-000001
    numeros           TEXT NOT NULL,      -- 24 números, orden canónico
    firma             TEXT NOT NULL,      -- hash para unicidad
    estado            TEXT NOT NULL DEFAULT 'generado',
                      -- generado | impreso | entregado | vendido | anulado
    UNIQUE (evento_id, codigo),
    UNIQUE (evento_id, firma)
);

CREATE INDEX idx_carton_evento_estado ON carton(evento_id, estado);
CREATE INDEX idx_carton_codigo        ON carton(codigo);

CREATE TABLE comprador (
    id                INTEGER PRIMARY KEY,
    carton_id         INTEGER NOT NULL UNIQUE REFERENCES carton(id),
    nombre            TEXT NOT NULL,
    telefono          TEXT,
    cedula            TEXT,
    correo            TEXT,
    registrado_en     TEXT NOT NULL
);

CREATE TABLE patron (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL,
    mascara           INTEGER NOT NULL,   -- bitmask de 25 bits
    usa_libre         INTEGER NOT NULL DEFAULT 1,
    es_sistema        INTEGER NOT NULL DEFAULT 0,
    organizacion_id   INTEGER REFERENCES organizacion(id)
);

CREATE TABLE ronda (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER NOT NULL REFERENCES evento(id),
    orden             INTEGER NOT NULL,
    nombre            TEXT NOT NULL,
    patron_id         INTEGER NOT NULL REFERENCES patron(id),
    premio_nombre     TEXT,
    premio_tipo       TEXT,               -- efectivo | bien
    premio_valor      REAL,
    premio_imagen     TEXT,
    estado            TEXT NOT NULL DEFAULT 'pendiente',
                      -- pendiente | en_curso | pausada | cerrada
    UNIQUE (evento_id, orden)
);

CREATE TABLE extraccion (
    id                INTEGER PRIMARY KEY,
    ronda_id          INTEGER NOT NULL REFERENCES ronda(id),
    orden             INTEGER NOT NULL,
    numero            INTEGER NOT NULL,
    extraida_en       TEXT NOT NULL,
    UNIQUE (ronda_id, orden),
    UNIQUE (ronda_id, numero)
);

CREATE TABLE ganador (
    id                INTEGER PRIMARY KEY,
    ronda_id          INTEGER NOT NULL REFERENCES ronda(id),
    carton_id         INTEGER NOT NULL REFERENCES carton(id),
    bola_numero       INTEGER NOT NULL,   -- en qué bola completó
    confirmado        INTEGER NOT NULL DEFAULT 0,
    reparte_premio    INTEGER NOT NULL DEFAULT 0,
    registrado_en     TEXT NOT NULL
);

CREATE TABLE auditoria (
    id                INTEGER PRIMARY KEY,
    evento_id         INTEGER REFERENCES evento(id),
    momento           TEXT NOT NULL,
    accion            TEXT NOT NULL,
    detalle           TEXT
);
```

### 3.2 Notas de diseño

**`numeros` como texto.** Se guardan los 24 números en orden canónico (columna por columna, de arriba a abajo) separados por comas: `"3,7,12,14,15,18,..."`. Es legible, compacto y se reconstruye la cara del cartón sin ambigüedad. No se guarda el espacio libre porque es siempre la posición central.

**`firma` para unicidad.** Hash SHA-256 de la cadena `numeros`. Como el orden vertical importa (dos cartones con los mismos números de la columna B en distinto orden son cartones distintos), la firma del orden canónico distingue correctamente. El índice único sobre `(evento_id, firma)` deja que la base de datos garantice la no repetición: si se intenta insertar un duplicado, la inserción falla y se genera otro cartón.

**`semilla` en el lote.** Permite regenerar exactamente el mismo lote si se pierde el PDF, sin tener que reimprimir con cartones distintos.

**Sin ON DELETE CASCADE.** Borrar un evento con cartones vendidos debe ser una operación deliberada del servicio, no un efecto colateral.

### 3.3 Migraciones

Cada cambio de esquema es un archivo SQL numerado en `persistencia/migraciones/`. Una tabla `schema_version` guarda la última aplicada. Al arrancar, la aplicación aplica las migraciones pendientes en orden dentro de una transacción. Nunca se edita una migración ya publicada.

---

## 4. Algoritmos núcleo

### 4.1 Representación del cartón

Cuadrícula de 5x5. Las columnas van de B a O de izquierda a derecha, con sus rangos fijos.

| Columna | Índice | Rango |
|---|---|---|
| B | 0 | 1–15 |
| I | 1 | 16–30 |
| N | 2 | 31–45 (4 números + libre) |
| G | 3 | 46–60 |
| O | 4 | 61–75 |

**Índice de bit:** `bit = fila * 5 + columna`, con fila y columna de 0 a 4. El espacio libre es el bit 12.

### 4.2 Generación de un cartón

```python
import secrets

RANGOS = {0: (1, 15), 1: (16, 30), 2: (31, 45), 3: (46, 60), 4: (61, 75)}
BIT_LIBRE = 12

def generar_carton(rng) -> list[list[int | None]]:
    """Devuelve una matriz 5x5; None marca el espacio libre."""
    columnas = []
    for col in range(5):
        inicio, fin = RANGOS[col]
        disponibles = list(range(inicio, fin + 1))
        cantidad = 4 if col == 2 else 5
        seleccion = []
        for _ in range(cantidad):
            i = rng.randrange(len(disponibles))
            seleccion.append(disponibles.pop(i))
        if col == 2:
            seleccion.insert(2, None)   # espacio libre en el centro
        columnas.append(seleccion)
    # transponer a filas
    return [[columnas[c][f] for c in range(5)] for f in range(5)]
```

Se extrae sin reemplazo dentro de cada columna, por lo que nunca hay repetidos. El generador `rng` se inyecta: en producción es `secrets.SystemRandom()`; en las pruebas es un `random.Random(semilla)` para obtener resultados reproducibles.

### 4.3 Generación de un lote con unicidad

```
para i en 1..cantidad:
    intentos = 0
    repetir:
        carton = generar_carton(rng)
        firma  = sha256(orden_canonico(carton))
        intentos += 1
    hasta que firma no exista en el lote
    guardar carton con codigo correlativo
```

Con 552 septillones de combinaciones posibles, la probabilidad de colisión es despreciable incluso generando millones de cartones; el control existe por rigor, no porque se espere que dispare. Se genera en transacciones por bloques (por ejemplo, 500 cartones por commit) para no mantener una transacción abierta durante minutos.

**Rendimiento esperado:** la generación de 10.000 cartones debe tomar segundos. El costo real está en el PDF (sección 5).

### 4.4 Patrones como máscaras de bits

Un patrón es un entero de 25 bits. Ejemplos:

```python
def mascara(celdas: list[tuple[int, int]]) -> int:
    m = 0
    for fila, col in celdas:
        m |= 1 << (fila * 5 + col)
    return m

CUATRO_ESQUINAS = mascara([(0,0), (0,4), (4,0), (4,4)])
LINEA_HORIZONTAL_1 = mascara([(0,c) for c in range(5)])
EQUIS = mascara([(i,i) for i in range(5)] + [(i,4-i) for i in range(5)])
CARTON_LLENO = (1 << 25) - 1
```

Los patrones del sistema se cargan en la tabla `patron` en la primera ejecución. El editor de patrones de la interfaz produce exactamente el mismo entero a partir de una grilla clicable.

**Patrones con variantes.** "Cualquier línea horizontal" no es una máscara sino un conjunto de cinco. El modelo lo resuelve con un patrón que agrupa varias máscaras: gana quien complete **cualquiera** de ellas. En la tabla se guarda como varias filas relacionadas o como una lista de máscaras serializada; se decide al implementar la sección 4.6.

### 4.5 Estado marcado de un cartón

Cada cartón vendido mantiene en memoria durante la partida un entero `marcado`, que arranca con el bit 12 encendido (espacio libre) y se actualiza cuando sale una bola que ese cartón contiene.

```python
class CartonEnJuego:
    def __init__(self, carton_id, codigo, numeros_por_bit):
        self.carton_id = carton_id
        self.codigo = codigo
        self.numeros_por_bit = numeros_por_bit   # {numero: bit}
        self.marcado = 1 << BIT_LIBRE

    def marcar(self, numero: int) -> bool:
        bit = self.numeros_por_bit.get(numero)
        if bit is None:
            return False
        self.marcado |= 1 << bit
        return True
```

Se construye un índice inverso `{numero: [cartones que lo contienen]}` al iniciar la ronda. Así, al salir una bola no se recorren los mil cartones sino solo los que contienen ese número (en promedio, la vigésima parte).

### 4.6 Detección de ganador

```python
def es_ganador(marcado: int, patron: int) -> bool:
    return marcado & patron == patron
```

Una operación de bits. Después de cada bola se evalúan únicamente los cartones que fueron marcados en esa jugada, no todos.

**Alerta de "a una bola".** Mismo cálculo, contando los bits faltantes:

```python
def faltan(marcado: int, patron: int) -> int:
    return bin(patron & ~marcado).count('1')
```

Si `faltan == 1`, el cartón está a una bola. Este dato se muestra **solo en la pantalla del operador**, o en la de transmisión como cantidad agregada ("3 tablas a una bola"), nunca con los códigos visibles.

### 4.7 Bombo y aleatoriedad

```python
class Bombo:
    def __init__(self, rng, ya_extraidas: list[int] | None = None):
        self._rng = rng
        self._extraidas = list(ya_extraidas or [])
        self._disponibles = [n for n in range(1, 76)
                             if n not in self._extraidas]

    def extraer(self) -> int:
        if not self._disponibles:
            raise BomboVacio()
        i = self._rng.randrange(len(self._disponibles))
        numero = self._disponibles.pop(i)
        self._extraidas.append(numero)
        return numero
```

Se usa `secrets.SystemRandom()` como fuente. Extracción sin reposición: una bola que salió no vuelve al bombo. El constructor acepta las bolas ya extraídas, que es lo que permite reanudar una ronda interrumpida reconstruyendo el bombo exactamente donde estaba.

---

## 5. Generación de PDF de cartones

### 5.1 Modelo de plantilla

La personalización del cartón se guarda como JSON en `evento.plantilla_json`. Estructura:

```json
{
  "hoja": { "tamano": "A4", "orientacion": "vertical",
            "cartones_por_hoja": 4, "margen_mm": 10,
            "marcas_corte": true },
  "marca": { "logo": "logo.png", "logo_pos": "superior_izquierda",
             "logo_alto_mm": 18,
             "titulo": "Bingo Solidario 2026",
             "subtitulo": "A beneficio de ...",
             "color_encabezado": "#1a1a2e",
             "color_grilla": "#333333",
             "fondo": null, "opacidad_fondo": 0.1 },
  "encabezado": { "mostrar": true, "letras": ["B","I","N","G","O"] },
  "libre": { "tipo": "logo", "texto": "LIBRE" },
  "numeros": { "fuente": "Helvetica-Bold", "tamano_pt": 22 },
  "identificacion": { "mostrar_codigo": true, "pos": "inferior_derecha",
                      "qr": true, "marca_agua": true,
                      "opacidad_marca_agua": 0.08 },
  "textos": { "superior": "", "inferior": "Válido solo para el evento...",
              "contacto": "WhatsApp 09xxxxxxx" }
}
```

La interfaz del editor de plantilla escribe este JSON y muestra una vista previa renderizando un cartón de ejemplo con el mismo motor que produce el PDF final. Así lo que se ve en pantalla es lo que sale impreso.

### 5.2 Generación por lotes

El punto de mayor consumo del sistema. Reglas de implementación:

1. La generación corre en un hilo aparte (`QThread`), nunca en el hilo de la interfaz.
2. Se emite progreso cada N cartones para alimentar la barra.
3. Se escribe el PDF de forma incremental y se libera memoria por página; no se construye todo el documento en RAM.
4. Los logos e imágenes se cargan **una sola vez** y se reutilizan como objeto compartido de ReportLab. Incrustar la misma imagen 10.000 veces es el error que hace que el archivo pese cientos de MB.
5. Se ofrece particionado: PDF dividido cada X hojas (por defecto 500), lo que además facilita mandar a imprenta por tandas.
6. La operación es cancelable.

### 5.3 Código QR

Se codifica el código del cartón junto con una firma corta: `CODIGO|HMAC8`, donde el HMAC se calcula con una clave del evento. Impide que alguien fabrique códigos válidos a mano. La verificación es local, contra la base de datos.

---

## 6. Motor de sorteo

### 6.1 Máquina de estados de la ronda

```
pendiente ──iniciar──▶ en_curso ──bola──▶ en_curso
                          │                  │
                          │            (hay ganador)
                          │                  ▼
                          ├──pausar──▶  pausada ──reanudar──▶ en_curso
                          │                  │
                          │            confirmar ganador
                          ▼                  ▼
                       cerrada ◀─────────────┘
```

### 6.2 Persistencia por bola

Después de **cada** extracción, dentro de una única transacción:

1. `INSERT` en `extraccion`.
2. `INSERT` en `ganador` si se detectó alguno (con `confirmado = 0`).
3. `UPDATE` del estado de la ronda si corresponde.
4. Escritura de una línea en el archivo de log de la partida, con `flush()` forzado.

El commit ocurre antes de que la interfaz muestre la bola. Si el equipo se apaga en ese instante, al reabrir la aplicación el estado guardado es coherente.

### 6.3 Reanudación

Al abrir un evento con una ronda en estado `en_curso` o `pausada`, la aplicación ofrece reanudar. La reconstrucción es: cargar las extracciones ordenadas, reconstruir el bombo con las bolas restantes, recargar los cartones vendidos y reproducir las marcas aplicando las bolas en orden. Con mil cartones y setenta bolas esto es instantáneo.

### 6.4 Comunicación entre las dos ventanas

El servicio de sorteo emite señales de Qt; ambas ventanas están suscritas y reaccionan de forma distinta:

| Señal | Ventana operador | Ventana transmisión |
|---|---|---|
| `bola_extraida(numero)` | Actualiza tablero y contadores | Animación de bombo, número grande, tablero |
| `cartones_a_una_bola(lista)` | Lista con códigos y compradores | Solo la cantidad, si está activado |
| `ganadores_detectados(lista)` | Lista completa con datos, botones de confirmación | Aviso de "¡BINGO!" con el patrón completado, **sin datos del ganador** |
| `ganador_confirmado(datos)` | Registro y paso a siguiente ronda | Muestra código y nombre del ganador |
| `ronda_cambiada(ronda)` | Panel de configuración | Patrón activo, imagen del premio |

La separación de qué muestra cada pantalla es una decisión de negocio, no cosmética: la de transmisión no revela al ganador hasta que el operador valide el reclamo.

---

## 7. Personalización del dashboard

Análogo a la plantilla del cartón, se guarda en `evento.tema_json`:

```json
{
  "colores": { "fondo": "#0f0f1a", "acento": "#e94560",
               "numero_actual": "#ffd60a", "texto": "#ffffff" },
  "fondo_imagen": "fondo.jpg",
  "bloques": {
    "bombo":          { "visible": true,  "pos": [40, 60],  "escala": 1.0 },
    "numero_actual":  { "visible": true,  "pos": [500, 80], "escala": 1.6 },
    "tablero_75":     { "visible": true,  "pos": [40, 420] },
    "patron_activo":  { "visible": true,  "pos": [900, 80] },
    "imagen_premio":  { "visible": true,  "pos": [900, 320] },
    "logo":           { "visible": true,  "pos": [1600, 40] },
    "banner_texto":   { "visible": false, "texto": "" }
  },
  "juego": { "intervalo_seg": 6, "modo": "manual",
             "pausa_al_ganador": true,
             "voz": true, "idioma_voz": "es",
             "sonido_bola": true, "confirmar_extraccion": false }
}
```

El aplicador de tema (`ui/tema.py`) traduce este JSON a hojas de estilo de Qt y a posiciones de los widgets. Los bloques se posicionan en un lienzo de resolución fija (1920x1080) y se escalan al monitor de salida.

---

## 8. Compradores y Excel

### 8.1 Exportación de la plantilla

Se genera un `.xlsx` con una fila por cartón generado: código del cartón, y columnas vacías para nombre, teléfono, cédula y correo. La columna del código se protege para evitar que la organización la altere.

### 8.2 Importación

Proceso en dos pasos, nunca directo:

1. **Validación en seco.** Se lee el archivo y se produce un informe: filas correctas, códigos inexistentes, códigos duplicados dentro del archivo, cartones ya registrados con otro comprador, filas con nombre vacío.
2. **Confirmación.** El operador ve el informe y decide. Solo entonces se escribe, dentro de una transacción única.

Al importar, los cartones con comprador pasan a estado `vendido`. Los demás quedan como estaban.

### 8.3 Conciliación

Reporte que compara generados, impresos, entregados y vendidos, con el monto recaudado teórico según el precio de la tabla.

---

## 9. Internacionalización

Español e inglés. Se usa un diccionario JSON por idioma y una función `t("clave")` en toda la interfaz. No se concatenan cadenas traducidas; cada mensaje completo es una clave con marcadores de posición.

```json
{ "sorteo.bola_actual": "Bola {numero}",
  "sorteo.a_una_bola": "{cantidad} tablas a una bola" }
```

El idioma de la interfaz y el de la locución de números son ajustes independientes: se puede operar en español y transmitir con voz en inglés.

---

## 10. Registro, actas y reportes

**Log de partida.** Archivo de texto plano por ronda, escrito en tiempo real: hora, orden, número, y eventos de ganador. Es el respaldo de última instancia si la base de datos falla.

**Acta del sorteo.** PDF por ronda con: datos del evento y la organización, patrón jugado, premio, secuencia completa de bolas en orden, ganadores con su código, y hash SHA-256 del contenido del acta. Sirve como comprobante ante la organización.

**Reporte del evento.** PDF y Excel con: cartones generados, vendidos y recaudación, listado de rondas con sus ganadores, y datos de contacto de cada ganador.

---

## 11. Respaldos

- Botón "Exportar respaldo del evento" que copia la base de datos usando la API de respaldo en línea de SQLite (segura con la base abierta), junto con los medios y los logs, en un `.zip` fechado.
- Recordatorio automático al operador antes de iniciar el sorteo y al cerrar el evento.
- Los respaldos son copias, no sincronización. La sincronización con nube queda fuera de la v1.

---

## 12. Empaquetado y distribución

- PyInstaller en modo `--onedir` (arranque más rápido que `--onefile` y menos falsos positivos de antivirus).
- Inno Setup produce el instalador, crea accesos directos y la estructura de carpetas en `%LOCALAPPDATA%`.
- Versionado semántico. El número de versión se muestra en la pantalla de ajustes y se registra en la tabla de auditoría al abrir un evento.
- Las migraciones de base de datos se aplican al primer arranque tras una actualización.

---

## 13. Pruebas

El objetivo no es cobertura alta en todo, sino cobertura seria donde un error cuesta dinero.

**Obligatorio (dominio, sin interfaz):**
- Generación de cartones: nunca hay repetidos en una columna, cada columna respeta su rango, el centro es libre.
- Unicidad de lote: generar 50.000 cartones y verificar que no hay firmas repetidas.
- Máscaras de patrones: cada patrón del sistema tiene los bits que le corresponden.
- Detección de ganador: casos positivos, negativos y de borde (patrón que incluye el espacio libre, patrón que no lo incluye).
- Bombo: no repite números, se agota en 75, se reconstruye correctamente desde extracciones previas.
- Reanudación: partida interrumpida en la bola N reconstruye el mismo estado.

**Deseable:**
- Importación de Excel con archivos deliberadamente sucios.
- Generación de PDF: que un lote grande termine y el archivo abra.

**Manual, antes de cada evento real:** ensayo completo del sorteo con datos de prueba y las dos pantallas conectadas a OBS.

---

## 14. Convenciones

- Código, nombres de variables y comentarios en español. Palabras reservadas y librerías en inglés, obviamente.
- Ruff con configuración por defecto, línea de 100 caracteres.
- Anotaciones de tipo en todas las funciones públicas del dominio y los servicios.
- Ramas: `main` estable, `dev` de integración, `feature/<nombre>` por tarea.
- Commits descriptivos en español.
- Cada fase termina con una etiqueta de versión en Git.

---

## 15. Fases de desarrollo

### Fase 1 — Cimientos
Estructura del proyecto, `pyproject.toml`, conexión SQLite con WAL y migraciones, esquema completo, repositorios base, módulo de organizaciones (CRUD con logo y colores), ventana principal vacía con navegación, sistema de idiomas.
**Entregable:** aplicación que abre, permite crear una organización y un evento en borrador, y persiste.

### Fase 2 — Generación de cartones
Algoritmo de generación, firma y unicidad, códigos correlativos, lotes con semilla, estados del cartón, visor de cartones con búsqueda por código.
**Entregable:** generar N cartones únicos y consultarlos en pantalla. Pruebas del dominio pasando.

### Fase 3 — Plantilla e impresión
Modelo de plantilla JSON, editor visual con vista previa, motor de render con ReportLab, formatos de 1/2/4/6 por hoja, QR y marca de agua, generación en hilo con progreso y particionado.
**Entregable:** PDF listo para imprenta, personalizado con la marca de la organización.

### Fase 4 — Compradores, rondas y premios
Exportación e importación de Excel con validación en seco, conciliación, catálogo de patrones del sistema, editor de patrones, configuración de rondas con premios e imágenes.
**Entregable:** evento completamente configurado y listo para jugarse.

### Fase 5 — Sorteo en vivo y cierre
Bombo, máquina de estados, persistencia por bola, ventana de transmisión con sus bloques configurables, ventana de operador, detección de ganadores y de "a una bola", validación por código, manejo de empates, reanudación, sonido y locución, actas y reportes, respaldos, empaquetado e instalador.
**Entregable:** versión 1.0 instalable, probada en un ensayo completo.

Las fases son secuenciales por dependencia real: no se puede probar el motor del sorteo sin cartones generados y compradores cargados.

---

## 16. Decisiones técnicas pendientes

1. **Patrones con variantes múltiples** ("cualquier línea"): resolver si se modela como varias filas relacionadas o como lista de máscaras serializada en una sola fila. Se decide al empezar la fase 4.
2. **Qué hacer si nadie reclama el premio** dentro de la ventana de tiempo: continuar la ronda, cerrarla igual y contactar después, o dejarlo configurable. Impacta la máquina de estados de la sección 6.1.
3. **Tipografías personalizadas:** si se permite que la organización cargue su propia fuente, hay que resolver el registro de fuentes en ReportLab y en Qt, y las implicaciones de licencia. Alternativa más simple: un catálogo cerrado de fuentes incluidas en la aplicación.
4. **Fuente de la locución de números:** audio pregrabado en ambos idiomas (mejor calidad, más trabajo) o síntesis de voz del sistema operativo (inmediato, calidad variable).
5. **Política de retención de datos de compradores:** pendiente de definir según el documento de alcance.
