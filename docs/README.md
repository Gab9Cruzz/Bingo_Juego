# Documentación — Proyecto BINGO

## Transversal

| Documento | Qué contiene |
|---|---|
| [Proyecto_Alcance.md](Proyecto_Alcance.md) | Qué es el producto, decisiones cerradas, módulos, reglas de negocio, fuera de alcance |
| [Documento_Tecnico.md](Documento_Tecnico.md) | Cómo se construye: stack, arquitectura, esquema, algoritmos, convenciones |
| [Plan_Fases_Bingo.md](Plan_Fases_Bingo.md) | Vista general de las cinco fases |

## Por fase

Cada carpeta contiene el **contrato** de la fase (qué hay que entregar) y, cuando
existe, el **plan de implementación** revisado (cómo se entrega).

| Fase | Contrato | Plan | Estado |
|---|---|---|---|
| 1 — Cimientos | [Contrato_Fase1.md](Fase_1/Contrato_Fase1.md) | [PlanFase1.md](Fase_1/PlanFase1.md) | Plan revisado, pendiente de aprobación |
| 2 — Generación de cartones | [Contrato_Fase2.md](Fase_2/Contrato_Fase2.md) | — | Pendiente |
| 3 — Plantilla e impresión | [Contrato_Fase3.md](Fase_3/Contrato_Fase3.md) | — | Pendiente |
| 4 — Compradores, rondas y premios | [Contrato_Fase4.md](Fase_4/Contrato_Fase4.md) | — | Pendiente |
| 5 — Sorteo en vivo y cierre | [Contrato_Fase5.md](Fase_5/Contrato_Fase5.md) | [Plan_Implementacion_Fase5.md](Fase_5/Plan_Implementacion_Fase5.md) | Plan revisado (CEO + diseño + ingeniería), decisiones del gate tomadas |

## Documentos que crea la fase 1

Todavía no existen; los produce la implementación:

- `convenciones-codigo.md` — contratos de módulo que consumen las fases 2 a 5
- `decisiones.md` — una entrada por decisión, añadida al cerrar cada fase
- `runbook.md` — los fallos de arranque y qué hacer con cada uno

## Fuera de esta carpeta

- [`../TODOS.md`](../TODOS.md) — trabajo diferido, con prioridad y dependencias
- [`../CLAUDE.md`](../CLAUDE.md) — convenciones y enrutado de skills para el asistente
