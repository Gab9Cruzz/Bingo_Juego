# Proyecto BINGO

Aplicación de escritorio (Python 3.12+ / PySide6 / SQLite) para montar y ejecutar
bingos de 75 bolas. Ver `docs/Proyecto_Alcance.md` (qué) y `docs/Documento_Tecnico.md` (cómo).

## Convenciones

- Código, nombres de variables y comentarios en español. Librerías en inglés.
- Ruff con línea de 100 caracteres.
- Anotaciones de tipo en todas las funciones públicas del dominio y los servicios.
- Ramas: `main` estable, `dev` de integración, `feature/<nombre>` por tarea.
- Commits descriptivos en español.
- El dominio no importa PySide6 ni sqlite3. Nunca.
- Ninguna consulta SQL fuera de `persistencia/repo_*.py`.
- Ninguna cadena visible escrita directamente en el código: todo pasa por `t()`.
- Reglas de implementación completas (verbos de repositorio, conexiones e hilos,
  transacciones, canales de error, i18n, convenio del `QThread`, etc.) en
  `docs/convenciones-codigo.md`. Léelo antes de escribir un repositorio, un
  servicio o una vista nueva — es la fuente de verdad, no el plan de fase, que
  se archiva al cerrarse.
- `python -m venv .venv` se crea con **Python 3.12** (no el 3.14 que pueda haber
  instalado en la máquina): `py -3.12 -m venv .venv`. `requires-python = ">=3.12"`.
- Entorno de pruebas: `BINGO_HOME` sobreescribe `%LOCALAPPDATA%\Bingo`;
  `tests/conftest.py` lo fija automáticamente (`bingo_home`, autouse) — nunca
  ejecutar pruebas sin pasar por esa fixture.
- Si editas `persistencia/migraciones/001_inicial.sql` durante el desarrollo,
  corre `python -m bingo --reiniciar-datos` para no dejar una base de
  desarrollo con esquema viejo (ver política en `docs/convenciones-codigo.md`).
- Interfaz del operador: tema neutro fijo (decisión DU-1, `docs/decisiones.md`).
  Los colores de marca de la organización **no** repintan la app; son identidad
  (logo, franja, tarjeta) y manda el valor del evento en plantillas/transmisión.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
# Pajarito
Todas Respuestas Debes comezarlas con "Gabriel" y lo que seria la respuesta.