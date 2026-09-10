"""Firma HMAC del código de cartón para el contenido del QR (contrato de la
fase 3, §3.3; documento técnico §5.3).

Dominio puro: solo librería estándar (`hashlib`, `hmac`, `secrets`), sin
PySide6 ni sqlite3 (verificado por `tests/arquitectura/test_arquitectura.py`).
Vive en `dominio/` y no en `impresion/` porque la fase 5 necesita
`verificar_qr` para validar el reclamo de un ganador en vivo, y esa fase no
debe arrastrar ReportLab (que sí vive en `impresion/`) solo para verificar una
firma.

Formato del QR: `"{codigo}|{hmac8}"`. El HMAC se calcula con
`evento.clave_evento` (generada una sola vez por evento, ver
`servicios/servicio_eventos.py::asegurar_clave_evento`) y se trunca a
`LONGITUD_HMAC` caracteres hex: no busca resistir criptoanálisis dedicado,
busca que nadie pueda fabricar a mano un código de cartón válido sin conocer
la clave del evento.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

LONGITUD_CLAVE_EVENTO_BYTES = 32  # 256 bits
LONGITUD_HMAC = 8  # caracteres hex del HMAC truncado, 32 bits


def generar_clave_evento() -> str:
    """Clave nueva para un evento. Se guarda en `evento.clave_evento` y no cambia."""
    return secrets.token_hex(LONGITUD_CLAVE_EVENTO_BYTES)


def firmar_codigo(clave_evento: str, codigo: str) -> str:
    """HMAC-SHA256 de `codigo` con `clave_evento`, truncado a `LONGITUD_HMAC` hex."""
    firma = hmac.new(clave_evento.encode("utf-8"), codigo.encode("utf-8"), hashlib.sha256)
    return firma.hexdigest()[:LONGITUD_HMAC]


def contenido_qr(clave_evento: str, codigo: str) -> str:
    """Texto que se codifica en el QR impreso en el cartón."""
    return f"{codigo}|{firmar_codigo(clave_evento, codigo)}"


def verificar_qr(clave_evento: str, texto_qr: str) -> str | None:
    """Devuelve el código si la firma es válida; `None` si está alterado, es de
    otro evento (clave distinta) o el texto no tiene el formato esperado.

    Comparación en tiempo constante (`hmac.compare_digest`): es la forma
    correcta de comparar HMACs, no una defensa crítica en este contexto, pero
    no cuesta nada hacerla bien.
    """
    if "|" not in texto_qr:
        return None
    codigo, firma_recibida = texto_qr.rsplit("|", 1)
    if not codigo:
        return None
    firma_esperada = firmar_codigo(clave_evento, codigo)
    return codigo if hmac.compare_digest(firma_recibida, firma_esperada) else None
