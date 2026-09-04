"""Conversión de dinero a centavos enteros y de vuelta a texto.

El precio de la tabla se guarda en `evento.precio_tabla_centavos` (enmienda
E4b) porque alimenta la recaudación teórica y el acta que se entrega a la
organización como comprobante: coma flotante ahí es un error que se descubre
sumando mil cartones. Punto único de conversión — queda prohibida la
conversión ad hoc en vistas o servicios.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def a_centavos(valor: Decimal | str) -> int:
    """Convierte un monto exacto (Decimal o texto, nunca float) a centavos enteros."""
    decimal = valor if isinstance(valor, Decimal) else Decimal(valor)
    centavos = (decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(centavos)


def formatear(centavos: int, idioma: str) -> str:
    """Formatea centavos enteros como texto de moneda legible."""
    valor = Decimal(centavos) / Decimal(100)
    texto = f"{valor:.2f}"
    if idioma == "es":
        return f"${texto.replace('.', ',')}"
    return f"${texto}"
