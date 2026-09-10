"""Modelo de la plantilla de cartón (contrato de la fase 3, §3.1; documento
técnico §5.1). Representa el JSON que se guarda en `evento.plantilla_json`.

Python puro (dataclasses + `json` de la librería estándar): no importa
PySide6 ni sqlite3. `PlantillaCarton.desde_json`/`.a_json()` son el único
punto de (de)serialización — nadie más en la aplicación construye ni lee ese
JSON a mano. Los campos ausentes en un JSON persistido (p. ej. de una versión
anterior de la plantilla) caen al valor por defecto del campo: así se puede
añadir un campo nuevo a esta clase sin migrar el `TEXT` ya guardado en cada
evento; los campos desconocidos en el JSON (de una versión futura) se
ignoran, no revientan.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field

from bingo.config.ajustes import CARTONES_POR_HOJA_SOPORTADOS, TAMANOS_HOJA_SOPORTADOS
from bingo.dominio.modelos import Organizacion
from bingo.utilidades.errores import ErrorValidacion

_PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_ORIENTACIONES = ("vertical", "horizontal")
_TIPOS_LIBRE = ("texto", "estrella", "logo")
_POSICIONES_LOGO = ("superior_izquierda", "superior_derecha", "superior_centro")
_POSICIONES_IDENTIFICACION = ("inferior_izquierda", "inferior_derecha", "inferior_centro")
_LETRAS_BINGO_DEFECTO = ("B", "I", "N", "G", "O")

# Texto sugerido por defecto de `textos.inferior`: recoge la regla de negocio
# #1 de `docs/Proyecto_Alcance.md` §6 (el ganador es el que canta el sistema,
# no lo que se ve en la transmisión). Editable desde el editor de plantilla;
# la medición real del retraso de transmisión sigue siendo un spike de la
# fase 5 (ver Plan_Implementacion_Fase3.md §3, decisión D7).
TEXTO_INFERIOR_DEFECTO = (
    "El ganador es quien completa el patrón según las bolas extraídas por el "
    "sistema, no según la transmisión (que tiene retraso). Cartón válido solo "
    "para este evento."
)


def _combinar[T](cls: type[T], datos: object) -> T:
    """Construye `cls` desde un dict parcial: valores ausentes caen al valor
    por defecto de `cls()`; claves desconocidas se ignoran.
    """
    base = dataclasses.asdict(cls())  # type: ignore[call-arg]
    if isinstance(datos, dict):
        base.update({clave: valor for clave, valor in datos.items() if clave in base})
    return cls(**base)  # type: ignore[call-arg]


@dataclass(slots=True)
class ConfigHoja:
    tamano: str = "A4"
    orientacion: str = "vertical"
    cartones_por_hoja: int = 4
    margen_mm: float = 10.0
    marcas_corte: bool = True


@dataclass(slots=True)
class ConfigMarca:
    logo: str | None = None
    logo_pos: str = "superior_izquierda"
    logo_alto_mm: float = 18.0
    logo_secundario: str | None = None
    titulo: str = ""
    subtitulo: str = ""
    color_encabezado: str = "#1a1a2e"
    color_grilla: str = "#333333"
    fondo: str | None = None
    opacidad_fondo: float = 0.1


@dataclass(slots=True)
class ConfigEncabezado:
    mostrar: bool = True
    letras: list[str] = field(default_factory=lambda: list(_LETRAS_BINGO_DEFECTO))


@dataclass(slots=True)
class ConfigLibre:
    tipo: str = "texto"  # texto | estrella | logo
    texto: str = "LIBRE"


@dataclass(slots=True)
class ConfigNumeros:
    fuente: str = "Helvetica-Bold"
    tamano_pt: float = 22.0


@dataclass(slots=True)
class ConfigIdentificacion:
    mostrar_codigo: bool = True
    pos: str = "inferior_derecha"
    qr: bool = True
    marca_agua: bool = True
    opacidad_marca_agua: float = 0.08


@dataclass(slots=True)
class ConfigTextos:
    superior: str = ""
    inferior: str = TEXTO_INFERIOR_DEFECTO
    contacto: str = ""


@dataclass(slots=True)
class PlantillaCarton:
    hoja: ConfigHoja = field(default_factory=ConfigHoja)
    marca: ConfigMarca = field(default_factory=ConfigMarca)
    encabezado: ConfigEncabezado = field(default_factory=ConfigEncabezado)
    libre: ConfigLibre = field(default_factory=ConfigLibre)
    numeros: ConfigNumeros = field(default_factory=ConfigNumeros)
    identificacion: ConfigIdentificacion = field(default_factory=ConfigIdentificacion)
    textos: ConfigTextos = field(default_factory=ConfigTextos)

    def a_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False)

    @staticmethod
    def desde_json(texto: str | None) -> PlantillaCarton:
        """Nunca lanza: un JSON vacío, ausente o corrupto devuelve la plantilla
        por defecto en blanco (sin organización) — quien necesite marca
        sembrada llama `restablecer_marca_desde_organizacion` aparte.
        """
        datos: dict[str, object] = {}
        if texto:
            try:
                cargado = json.loads(texto)
                if isinstance(cargado, dict):
                    datos = cargado
            except (json.JSONDecodeError, TypeError):
                datos = {}
        return PlantillaCarton(
            hoja=_combinar(ConfigHoja, datos.get("hoja")),
            marca=_combinar(ConfigMarca, datos.get("marca")),
            encabezado=_combinar(ConfigEncabezado, datos.get("encabezado")),
            libre=_combinar(ConfigLibre, datos.get("libre")),
            numeros=_combinar(ConfigNumeros, datos.get("numeros")),
            identificacion=_combinar(ConfigIdentificacion, datos.get("identificacion")),
            textos=_combinar(ConfigTextos, datos.get("textos")),
        )

    @staticmethod
    def por_defecto(organizacion: Organizacion | None = None) -> PlantillaCarton:
        """Valores sensatos del contrato (A4, vertical, 4 por hoja, márgenes
        10mm, Helvetica-Bold 22pt para números — evita depender de las
        fuentes variables empaquetadas para el elemento más denso del
        cartón). Si se pasa `organizacion`, siembra `marca.*` desde ella
        (decisión D5): logo, colores, contacto, pie de página.
        """
        plantilla = PlantillaCarton()
        if organizacion is not None:
            plantilla = restablecer_marca_desde_organizacion(plantilla, organizacion)
        return plantilla


def restablecer_marca_desde_organizacion(
    plantilla: PlantillaCarton, organizacion: Organizacion
) -> PlantillaCarton:
    """Copia `marca.*` desde `Organizacion` a una copia de `plantilla`.

    No toca `marca.titulo`/`marca.subtitulo` (son del evento, no de la
    organización) ni ningún otro bloque (`hoja`, `textos`, `identificacion`,
    etc.). Es lo que el botón "Restablecer desde organización" del editor
    (tarea 3.4) llama; también lo usa `por_defecto` para una plantilla nueva.
    """
    marca = dataclasses.replace(
        plantilla.marca,
        logo=organizacion.logo_path,
        logo_secundario=organizacion.logo_secundario,
        color_encabezado=organizacion.color_primario,
        color_grilla=organizacion.color_secundario,
    )
    textos = plantilla.textos
    if organizacion.contacto and not textos.contacto:
        textos = dataclasses.replace(textos, contacto=organizacion.contacto)
    return dataclasses.replace(plantilla, marca=marca, textos=textos)


def _validar_color(valor: str, campo: str) -> None:
    if not _PATRON_COLOR.match(valor):
        raise ErrorValidacion(
            "plantilla.error.color_invalido", campo=campo, parametros={"valor": valor}
        )


def _validar_opacidad(valor: float, campo: str) -> None:
    if not (0.0 <= valor <= 1.0):
        raise ErrorValidacion(
            "plantilla.error.opacidad_invalida", campo=campo, parametros={"valor": valor}
        )


def validar(plantilla: PlantillaCarton) -> None:
    """Valida los campos con un dominio cerrado o un rango numérico. Lanza
    `ErrorValidacion` en el primer campo inválido, con `campo` fijado para
    que el editor (tarea 3.4) sepa dónde poner el foco.
    """
    hoja = plantilla.hoja
    if hoja.tamano not in TAMANOS_HOJA_SOPORTADOS:
        raise ErrorValidacion(
            "plantilla.error.tamano_invalido",
            campo="hoja.tamano",
            parametros={"valor": hoja.tamano},
        )
    if hoja.orientacion not in _ORIENTACIONES:
        raise ErrorValidacion(
            "plantilla.error.orientacion_invalida",
            campo="hoja.orientacion",
            parametros={"valor": hoja.orientacion},
        )
    if hoja.cartones_por_hoja not in CARTONES_POR_HOJA_SOPORTADOS:
        raise ErrorValidacion(
            "plantilla.error.cartones_por_hoja_invalido",
            campo="hoja.cartones_por_hoja",
            parametros={"valor": hoja.cartones_por_hoja},
        )
    if hoja.margen_mm <= 0:
        raise ErrorValidacion(
            "plantilla.error.margen_invalido",
            campo="hoja.margen_mm",
            parametros={"valor": hoja.margen_mm},
        )

    marca = plantilla.marca
    _validar_color(marca.color_encabezado, "marca.color_encabezado")
    _validar_color(marca.color_grilla, "marca.color_grilla")
    _validar_opacidad(marca.opacidad_fondo, "marca.opacidad_fondo")
    if marca.logo_pos not in _POSICIONES_LOGO:
        raise ErrorValidacion(
            "plantilla.error.logo_pos_invalida",
            campo="marca.logo_pos",
            parametros={"valor": marca.logo_pos},
        )
    if marca.logo_alto_mm <= 0:
        raise ErrorValidacion(
            "plantilla.error.logo_alto_invalido",
            campo="marca.logo_alto_mm",
            parametros={"valor": marca.logo_alto_mm},
        )

    if len(plantilla.encabezado.letras) != 5:
        raise ErrorValidacion(
            "plantilla.error.encabezado_letras_invalidas", campo="encabezado.letras"
        )

    if plantilla.libre.tipo not in _TIPOS_LIBRE:
        raise ErrorValidacion(
            "plantilla.error.libre_tipo_invalido",
            campo="libre.tipo",
            parametros={"valor": plantilla.libre.tipo},
        )

    if plantilla.numeros.tamano_pt <= 0:
        raise ErrorValidacion(
            "plantilla.error.tamano_numero_invalido",
            campo="numeros.tamano_pt",
            parametros={"valor": plantilla.numeros.tamano_pt},
        )

    identificacion = plantilla.identificacion
    if identificacion.pos not in _POSICIONES_IDENTIFICACION:
        raise ErrorValidacion(
            "plantilla.error.identificacion_pos_invalida",
            campo="identificacion.pos",
            parametros={"valor": identificacion.pos},
        )
    _validar_opacidad(identificacion.opacidad_marca_agua, "identificacion.opacidad_marca_agua")
