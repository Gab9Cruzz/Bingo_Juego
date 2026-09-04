# Runbook — fallos de arranque

Qué hacer cuando `python -m bingo` (o el ejecutable instalado) no arranca.
Ordenado por código de salida.

| Código | Causa | Qué hacer |
|---|---|---|
| `2` | Sin permisos de escritura o disco lleno al crear `%LOCALAPPDATA%\Bingo\` | Revisar permisos de la carpeta de usuario; liberar espacio en disco |
| `3` | La base de datos está corrupta (`ErrorBaseCorrupta`) | Cerrar la aplicación, restaurar el `.zip` más reciente de `respaldos\`. Si no hay respaldo, contactar soporte antes de borrar nada |
| `4` | Falla al aplicar migraciones (SQL inválido, numeración con hueco, versión futura) | Revisar `aplicacion.log` para el número de migración. Si el mensaje dice "la base quedó a medias", cerrar la aplicación y ejecutar `python -m bingo --reiniciar-datos` (solo en una base de **desarrollo**, nunca sobre datos reales sin respaldo antes) |
| `5` | Segunda instancia ya en ejecución, o bloqueo rancio no liberado | Cerrar la instancia previa desde el Administrador de tareas. Si el proceso ya no existe pero el aviso persiste, usar `--forzar-instancia` |

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
