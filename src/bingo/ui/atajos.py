"""Atajos de teclado (enmienda E21, convertida a registro por la decisión
D12 del plan de la fase 5).

Un diccionario simple bastaba mientras había una sola superficie manejada
por teclado. Desde la fase 5 hay tres (`global`, `sorteo`, `transmision`) y
el mismo `Ctrl+N` significa dos cosas distintas según la vista — de ahí
`RegistroAtajos`, con `registrar(accion, secuencia, ambito)` y
`secuencia(accion, ambito)`. `ATAJOS["accion"]` sigue funcionando exactamente
como antes (resuelve contra el ámbito `global`): nada de lo que ya usa
`ventana_principal.py` necesita cambiar.

Se opera en vivo, frente a cámara, contra reloj: el teclado tiene que
alcanzar para todo.
"""

from __future__ import annotations


class RegistroAtajos:
    def __init__(self) -> None:
        self._tabla: dict[tuple[str, str], str] = {}

    def registrar(self, accion: str, secuencia: str, ambito: str = "global") -> None:
        self._tabla[(ambito, accion)] = secuencia

    def secuencia(self, accion: str, ambito: str = "global") -> str:
        clave = (ambito, accion)
        if clave not in self._tabla:
            raise KeyError(f"Sin atajo registrado: {accion!r} (ámbito {ambito!r})")
        return self._tabla[clave]

    def __getitem__(self, accion: str) -> str:
        """Compatibilidad con el diccionario simple anterior a la fase 5:
        siempre resuelve contra el ámbito `global`."""
        return self.secuencia(accion, "global")


ATAJOS = RegistroAtajos()

for _accion, _secuencia in {
    "navegar_eventos": "Ctrl+1",
    "navegar_organizaciones": "Ctrl+2",
    "navegar_ajustes": "Ctrl+3",
    "nuevo": "Ctrl+N",
    "guardar": "Ctrl+S",
    "cancelar": "Esc",
    "abrir_log": "Ctrl+L",
    # Fase 4 (decisión DS19): Compradores y Rondas se operan igual de rápido
    # con teclado que con ratón.
    "buscar": "Ctrl+F",
    "importar": "Ctrl+I",
    "nueva_ronda": "Ctrl+N",
    "subir": "Ctrl+Shift+Up",
    "bajar": "Ctrl+Shift+Down",
}.items():
    ATAJOS.registrar(_accion, _secuencia, "global")

# Ámbito "sorteo" (contrato §5.5, decisión DU-5, plan de la fase 5).
# "Espacio" es el atajo principal de Extraer; "F5" es el alterno que no
# colisiona nunca con nada, para cuando el foco esté en un campo de texto —
# los de una sola tecla (Espacio, P, R) se inhiben ahí, `F5` no.
ATAJOS.registrar("sorteo.extraer", "Space", "sorteo")
ATAJOS.registrar("sorteo.extraer_alterno", "F5", "sorteo")
ATAJOS.registrar("sorteo.pausar_reanudar", "P", "sorteo")
ATAJOS.registrar("sorteo.buscar", "Ctrl+F", "sorteo")
ATAJOS.registrar("sorteo.confirmar_ganador", "Ctrl+Return", "sorteo")
ATAJOS.registrar("sorteo.modo_vivo", "F11", "sorteo")
ATAJOS.registrar("sorteo.salir_modo_vivo", "Esc", "sorteo")
ATAJOS.registrar("sorteo.repetir_locucion", "R", "sorteo")

# Ámbito "transmision": la ventana nunca recibe foco de teclado (decisión
# DU-5/§4.9), así que no lleva `QShortcut` propios — se deja el ámbito
# declarado para que un atajo futuro (si lo hay) no colisione con "sorteo"
# por accidente al copiar y pegar.

# Tamaño mínimo de fuente y objetivo de pulsación: Gabriel lee esto de reojo,
# con la cámara delante.
TIPOGRAFIA_MINIMA_PX = 13
OBJETIVO_PULSACION_MINIMO_PX = 32
