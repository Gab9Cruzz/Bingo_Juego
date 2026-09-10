"""Texto pintado en la ventana de transmisión, en su propio idioma
(decisión DU-13 — `tema_json.idioma_publico`, independiente del idioma
activo de la interfaz del operador).

Separado de `bloques.py` (que sí llama a `QPainter`) a propósito: la regla
que no se negocia del contrato §5.4 —el aviso de "hay un cartón ganador" no
lleva código ni nombre hasta `ganador_confirmado`— se puede probar sobre el
texto en sí, sin tocar píxeles (tarea 4.9: "se verifica sobre el modelo del
bloque, no sobre píxeles").
"""

from __future__ import annotations

from bingo.i18n import t_en


def texto_a_una_bola(idioma: str, cantidad: int) -> str:
    """Decisión DU-10: la cifra es el contenido siempre — `bloques.py`
    decide el tamaño/parpadeo dramático cuando `cantidad <= 3`, no este
    texto."""
    return t_en(idioma, "transmision.a_una_bola", cantidad=cantidad)


def texto_hay_carton_ganador(
    idioma: str, canal_reclamo: str, segundos_restantes: int | None
) -> str:
    """Regla que no se negocia (contrato §5.4): nunca código ni nombre
    aquí, solo a dónde reclamar y cuánto queda."""
    if segundos_restantes is None:
        return t_en(idioma, "transmision.hay_ganador.sin_limite", canal=canal_reclamo)
    return t_en(
        idioma,
        "transmision.hay_ganador.con_cuenta",
        canal=canal_reclamo,
        segundos=segundos_restantes,
    )


def texto_reclamo_vencido(idioma: str) -> str:
    return t_en(idioma, "transmision.reclamo_vencido")


def texto_ganador_confirmado(idioma: str, codigo: str, nombre: str) -> str:
    """El único lugar de toda la transmisión donde código y nombre se
    pintan juntos."""
    return t_en(idioma, "transmision.ganador_confirmado", codigo=codigo, nombre=nombre)


def texto_entre_rondas(idioma: str, nombre_patron: str, premio: str) -> str:
    return t_en(idioma, "transmision.entre_rondas", patron=nombre_patron, premio=premio)


def texto_pausa(idioma: str) -> str:
    return t_en(idioma, "transmision.pausa")


def texto_bienvenida(idioma: str, texto_configurado: str) -> str:
    return texto_configurado or t_en(idioma, "transmision.bienvenida.defecto")


def texto_cierre(idioma: str, texto_configurado: str) -> str:
    return texto_configurado or t_en(idioma, "transmision.cierre.defecto")
