"""Modelo del tema visual del dashboard de transmisión (contrato de la fase
4, §4.8; decisión D9 y D.2 del plan de la fase 4). Representa el JSON que se
guarda en `evento.tema_json`.

Gemelo de `impresion/plantilla.py::PlantillaCarton`, pero vive en `dominio/`
y no en `impresion/`: no tiene nada que ver con ReportLab, y la fase 5 lo
consume desde `ui/transmision/tema_transmision.py` (nunca desde
`ui/tema.py`, que es el tema **fijo** del operador — decisión DU-1. Los
colores de este módulo pintan la pantalla de transmisión, nunca la interfaz
del operador; ver `docs/decisiones.md`).

Python puro (dataclasses + `json`): no importa PySide6 ni sqlite3. Campos
ausentes en un JSON persistido caen al valor por defecto del campo — permite
que la fase 5 añada bloques nuevos sin migrar los `tema_json` ya guardados,
igual que `PlantillaCarton`.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field

from bingo.utilidades.errores import ErrorValidacion

_PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _combinar[T](cls: type[T], datos: object, por_defecto: T | None = None) -> T:
    """Construye `cls` desde un dict parcial: valores ausentes caen al valor
    por defecto (`por_defecto`, o `cls()` si no se da uno); claves
    desconocidas se ignoran. `por_defecto` existe porque `tablero_75` no usa
    el `ConfigBloque()` genérico como valor por defecto (ver
    `TemaDashboard.tablero_75`) — sin él, un `tema_json` que no mencione ese
    bloque perdería su posición sembrada y volvería silenciosamente a
    `pos_x=0.0`. Mismo mecanismo que `impresion/plantilla.py::_combinar` —
    duplicado a propósito: son módulos gemelos sin relación de importación
    entre `dominio/` e `impresion/`.
    """
    base_obj = por_defecto if por_defecto is not None else cls()  # type: ignore[call-arg]
    base = dataclasses.asdict(base_obj)
    if isinstance(datos, dict):
        base.update({clave: valor for clave, valor in datos.items() if clave in base})
    return cls(**base)  # type: ignore[call-arg]


@dataclass(slots=True)
class ConfigColores:
    fondo: str = "#0b0b14"
    texto: str = "#f2f2f7"
    acento: str = "#5b8def"
    tablero_marcado: str = "#5b8def"


@dataclass(slots=True)
class ConfigBloque:
    """Posición/escala de un bloque del dashboard, en fracción de 0.0 a 1.0
    de un lienzo de referencia 1920x1080 (decisión D9): así la vista previa
    y el consumidor real de la fase 5 escalan igual a cualquier resolución.
    """

    visible: bool = True
    pos_x: float = 0.0
    pos_y: float = 0.0
    escala: float = 1.0


@dataclass(slots=True)
class ConfigBannerTexto:
    """Forma distinta a `ConfigBloque` a propósito (hallazgo E-A12 del plan
    de la fase 4): el documento técnico §7 ya definía `banner_texto` como
    `{"visible": bool, "texto": str}`, sin `pos` ni `escala`. Modelarlo como
    `ConfigBloque` habría obligado a migrar `tema_json` ya guardados — el
    costo exacto que D.2 pretendía evitar.
    """

    visible: bool = False
    texto: str = ""


@dataclass(slots=True)
class ConfigJuego:
    mostrar_ultimas_bolas: int = 5
    sonido_activado: bool = True


def _tablero_75_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.72, escala=0.9)


@dataclass(slots=True)
class TemaDashboard:
    colores: ConfigColores = field(default_factory=ConfigColores)
    imagen_fondo: str | None = None
    bombo: ConfigBloque = field(default_factory=ConfigBloque)
    tablero_75: ConfigBloque = field(default_factory=_tablero_75_por_defecto)
    contador_bolas: ConfigBloque = field(default_factory=ConfigBloque)
    reloj: ConfigBloque = field(default_factory=ConfigBloque)
    banner_texto: ConfigBannerTexto = field(default_factory=ConfigBannerTexto)
    juego: ConfigJuego = field(default_factory=ConfigJuego)

    def a_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False)

    @staticmethod
    def desde_json(texto: str | None) -> TemaDashboard:
        """Nunca lanza: un JSON vacío, ausente o corrupto devuelve el tema
        por defecto."""
        datos: dict[str, object] = {}
        if texto:
            try:
                cargado = json.loads(texto)
                if isinstance(cargado, dict):
                    datos = cargado
            except (json.JSONDecodeError, TypeError):
                datos = {}
        return TemaDashboard(
            colores=_combinar(ConfigColores, datos.get("colores")),
            imagen_fondo=datos.get("imagen_fondo")
            if isinstance(datos.get("imagen_fondo"), (str, type(None)))
            else None,
            bombo=_combinar(ConfigBloque, datos.get("bombo")),
            tablero_75=_combinar(ConfigBloque, datos.get("tablero_75"), _tablero_75_por_defecto()),
            contador_bolas=_combinar(ConfigBloque, datos.get("contador_bolas")),
            reloj=_combinar(ConfigBloque, datos.get("reloj")),
            banner_texto=_combinar(ConfigBannerTexto, datos.get("banner_texto")),
            juego=_combinar(ConfigJuego, datos.get("juego")),
        )

    @staticmethod
    def por_defecto() -> TemaDashboard:
        return TemaDashboard()


def _validar_color(valor: str, campo: str) -> None:
    if not _PATRON_COLOR.match(valor):
        raise ErrorValidacion("tema.error.color_invalido", campo=campo, parametros={"valor": valor})


def _validar_bloque(bloque: ConfigBloque, campo: str) -> None:
    if not (0.0 <= bloque.pos_x <= 1.0) or not (0.0 <= bloque.pos_y <= 1.0):
        raise ErrorValidacion("tema.error.posicion_invalida", campo=campo)
    if bloque.escala <= 0:
        raise ErrorValidacion("tema.error.escala_invalida", campo=campo)


def validar(tema: TemaDashboard) -> None:
    """Valida rango/dominio de cada campo. Lanza `ErrorValidacion` en el
    primer campo inválido, con `campo` fijado para que el editor sepa dónde
    poner el foco (mismo convenio que `impresion/plantilla.py::validar`)."""
    _validar_color(tema.colores.fondo, "colores.fondo")
    _validar_color(tema.colores.texto, "colores.texto")
    _validar_color(tema.colores.acento, "colores.acento")
    _validar_color(tema.colores.tablero_marcado, "colores.tablero_marcado")
    _validar_bloque(tema.bombo, "bombo")
    _validar_bloque(tema.tablero_75, "tablero_75")
    _validar_bloque(tema.contador_bolas, "contador_bolas")
    _validar_bloque(tema.reloj, "reloj")
    if tema.juego.mostrar_ultimas_bolas < 0:
        raise ErrorValidacion(
            "tema.error.ultimas_bolas_invalido", campo="juego.mostrar_ultimas_bolas"
        )
