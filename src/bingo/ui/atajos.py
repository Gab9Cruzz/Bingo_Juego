"""Atajos de teclado (enmienda E21, recortada por G30 a un diccionario simple).

Una aplicación de cuatro superficies no necesita un registro central de
acciones: un diccionario de módulo da el mismo sitio único donde mirar, y la
fase 5 lo convierte en lo que necesite cuando tenga más de una superficie
manejada por teclado. Se opera en vivo, frente a cámara, contra reloj: el
teclado tiene que alcanzar para todo.
"""

from __future__ import annotations

ATAJOS: dict[str, str] = {
    "navegar_eventos": "Ctrl+1",
    "navegar_organizaciones": "Ctrl+2",
    "navegar_ajustes": "Ctrl+3",
    "nuevo": "Ctrl+N",
    "guardar": "Ctrl+S",
    "cancelar": "Esc",
    "abrir_log": "Ctrl+L",
    # Fase 4 (decisión DS19, docs/Fase_4/Plan_Implementacion_Fase4.md): la
    # sección de Compradores y Rondas se opera igual de rápido con teclado
    # que con ratón.
    "buscar": "Ctrl+F",
    "importar": "Ctrl+I",
    "nueva_ronda": "Ctrl+N",
    "subir": "Ctrl+Shift+Up",
    "bajar": "Ctrl+Shift+Down",
}

# Tamaño mínimo de fuente y objetivo de pulsación: Gabriel lee esto de reojo,
# con la cámara delante.
TIPOGRAFIA_MINIMA_PX = 13
OBJETIVO_PULSACION_MINIMO_PX = 32
