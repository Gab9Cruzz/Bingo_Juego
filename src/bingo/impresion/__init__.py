"""Generación de PDF de cartones (contrato de la fase 3): modelo de plantilla
(`plantilla.py`) y motor de render con ReportLab (`render_pdf.py`).

Paquete de nivel superior, no un submódulo de `dominio/` (decisión D2,
`docs/Fase_3/Plan_Implementacion_Fase3.md` §3): `render_pdf.py` importa
ReportLab, algo que `dominio/` nunca hace. `plantilla.py` es Python puro y
podría vivir en `dominio/`, pero el contrato de la fase 3 lo nombra
explícitamente aquí, junto a su motor de render.
"""
