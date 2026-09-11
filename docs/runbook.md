# Runbook — fallos de arranque

Qué hacer cuando `python -m bingo` (o el ejecutable instalado) no arranca.
Ordenado por código de salida.

| Código | Causa | Qué hacer |
|---|---|---|
| `2` | Sin permisos de escritura o disco lleno al crear `%LOCALAPPDATA%\Bingo\` | Revisar permisos de la carpeta de usuario; liberar espacio en disco |
| `3` | La base de datos está corrupta (`ErrorBaseCorrupta`) | Cerrar la aplicación, restaurar el `.zip` más reciente de `respaldos\`. Si no hay respaldo, contactar soporte antes de borrar nada |
| `4` | Falla al aplicar migraciones (SQL inválido, numeración con hueco, versión futura) | Revisar `aplicacion.log` para el número de migración. Si el mensaje dice "la base quedó a medias", cerrar la aplicación y ejecutar `python -m bingo --reiniciar-datos` (solo en una base de **desarrollo**, nunca sobre datos reales sin respaldo antes) |
| `5` | Segunda instancia ya en ejecución, o bloqueo rancio no liberado | Cerrar la instancia previa desde el Administrador de tareas. Si el proceso ya no existe pero el aviso persiste, usar `--forzar-instancia` |
| `6` | `--restaurar <zip>` falló (zip corrupto, no contiene `datos/bingo.db`, o su `schema_version` es más nueva que la que este instalador sabe aplicar) | Revisar `aplicacion.log`. Probar con otro `.zip` de `respaldos\`. Los datos originales no se tocan hasta que el `.zip` completo pasa la validación (hallazgo B4) — un `--restaurar` fallido nunca deja la aplicación peor de lo que estaba |
| `7` | `--comprobar-empaquetado` encontró un problema (un módulo de PySide6 que no se pudo importar, o falta un recurso embebido) | Solo aparece al construir/probar el instalador (tarea 4.14), nunca en uso normal. Revisar la salida en la consola: nombra exactamente qué módulo o archivo falta. Reconstruir con `empaquetado/bingo.spec` y volver a correr `empaquetado/humo.py` |

## Base de datos en carpeta sincronizada o unidad de red

Si Ajustes › Ubicaciones muestra el aviso permanente: la base vive bajo una
carpeta de OneDrive/Dropbox/Google Drive/iCloud, o en una ruta de red (`\\...`).
Es la causa más frecuente de corrupción de SQLite. Mover `%LOCALAPPDATA%\Bingo\`
fuera de esa carpeta, o fijar `BINGO_HOME` a una ruta local.

## Base de desarrollo obsoleta tras editar `001_inicial.sql`

Mientras la política E4e siga vigente (antes del primer evento con datos
reales), editar la 001 dentro de una base de desarrollo ya migrada deja
`schema_version` apuntando a un esquema viejo. Síntoma: errores de columna
inexistente que no calzan con el código actual. Solución:
`python -m bingo --reiniciar-datos` (borra la base de desarrollo y vuelve a
migrar desde cero).

## Preferencias corruptas

`preferencias.json` ilegible no impide arrancar: la aplicación usa valores por
defecto, registra el problema en el log, y renombra el archivo a
`preferencias.json.corrupto` junto al original.

## Instalación y actualización (tarea 4.14)

**Instalar por primera vez:** ejecutar `bingo-instalador-<version>.exe`. No
pide privilegios de administrador (`PrivilegesRequired=lowest`) — se instala
para el usuario actual, nunca en `Archivos de programa` de todo el equipo.
No crea `%LOCALAPPDATA%\Bingo\`: eso lo hace la propia aplicación en su
primer arranque real.

**Actualizar sobre una instalación con datos reales:** ejecutar el
instalador de la versión nueva sobre la misma carpeta — sobrescribe el
programa, nunca `%LOCALAPPDATA%\Bingo\`. Al primer arranque tras actualizar,
las migraciones pendientes corren solas. Antes de aplicar cualquiera,
`aplicar_migraciones` copia `bingo.db` a `bingo.db.pre-<version_anterior>`
(hallazgo B5, tarea 4.22) — si la migración fallara a mitad de camino esa
noche, esa copia es la vuelta atrás real, sin depender de un respaldo manual
que a lo mejor no se hizo esa semana.

**Desinstalar:** el desinstalador borra el programa, nunca
`%LOCALAPPDATA%\Bingo\` — ahí viven la base de datos, los respaldos y los
cartones ya impresos de eventos reales, y no deben poder perderse por
desinstalar la aplicación sin querer.

**Verificar el empaquetado antes de repartir un instalador nuevo** (a mano,
o como parte del pipeline de build):

```
.venv\Scripts\pyinstaller.exe empaquetado\bingo.spec --noconfirm
.venv\Scripts\python.exe empaquetado\humo.py
.venv\Scripts\python.exe empaquetado\actualizacion.py
iscc empaquetado\instalador.iss /DMyAppVersion=<version>
```

`humo.py` prueba el `.exe` recién construido en limpio (los módulos de
PySide6 que se cargan por nombre, y que arranca hasta dejar la base en la
última versión de esquema); `actualizacion.py` prueba el caso real de
"ya había una instalación con datos" — construye una base en la versión de
esquema 3, corre el `.exe` nuevo encima, y verifica que llegó a la 4 sin
perder filas y que dejó `bingo.db.pre-3` íntegro. Los dos corren contra el
`.exe` de verdad, no contra el árbol de fuentes — es el único sitio donde el
criterio de aceptación "el instalador deja la aplicación funcionando en un
equipo limpio sin Python" se puede comprobar.
