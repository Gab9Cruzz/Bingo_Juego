"""Modelo del tema visual del dashboard de transmisión (contrato de la fase
4, §4.8; decisión D9 y D.2 del plan de la fase 4; ampliado por las
decisiones D4/DU-4/DU-6 del plan de la fase 5). Representa el JSON que se
guarda en `evento.tema_json`.

Gemelo de `impresion/plantilla.py::PlantillaCarton`, pero vive en `dominio/`
y no en `impresion/`: no tiene nada que ver con ReportLab, y la fase 5 lo
consume desde `ui/transmision/bloques.py` (nunca desde `ui/tema.py`, que es
el tema **fijo** del operador — decisión DU-1. Los colores de este módulo
pintan la pantalla de transmisión, nunca la interfaz del operador; ver
`docs/decisiones.md`).

Python puro (dataclasses + `json`): no importa PySide6 ni sqlite3. Campos
ausentes en un JSON persistido caen al valor por defecto del campo — permite
que la fase 5 añada bloques nuevos sin migrar los `tema_json` ya guardados,
igual que `PlantillaCarton`.

`BLOQUES` (decisión DU-4, corrección S5-1/tarea 4.21, DRY) es la única
tabla de posiciones y tamaños fraccionarios de los bloques posicionables:
la consumen tanto `vista_tema.py::_LienzoPrevia` (vista previa de
preparación) como `ui/transmision/bloques.py` (la pantalla real) — así lo
que se configura es literalmente lo que sale. `banner_texto` no está en
`BLOQUES`: su forma es una franja de ancho completo, no un rectángulo
posicionable (hallazgo E-A12 de la fase 4), y las dos pantallas de
bienvenida/cierre son overlays de pantalla completa, no bloques.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field

from bingo.utilidades.errores import ErrorValidacion

_PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Umbral de contraste para la transmisión (decisión DU-6): más estricto que
# el 4.5:1 de WCAG AA que usa `ui/tema.py` para la identidad de marca — la
# compresión de vídeo se come el contraste, y esto lo ve un público entero
# en un móvil.
UMBRAL_CONTRASTE_TRANSMISION = 7.0

# Alto mínimo de `numero_actual` como fracción del lienzo (decisión DU-6):
# por debajo, en un teléfono con vídeo comprimido, no se lee.
ALTO_MINIMO_NUMERO_ACTUAL_FRAC = 0.14


def _combinar[T](cls: type[T], datos: object, por_defecto: T | None = None) -> T:
    """Construye `cls` desde un dict parcial: valores ausentes caen al valor
    por defecto (`por_defecto`, o `cls()` si no se da uno); claves
    desconocidas se ignoran. `por_defecto` existe porque varios bloques no
    usan `ConfigBloque()` genérico como valor por defecto (decisión DU-4:
    todos los bloques posicionables llevan una posición por defecto propia,
    no solo `tablero_75`) — sin él, un `tema_json` que no mencione un bloque
    perdería su posición sembrada y volvería silenciosamente a `pos_x=0.0`.
    Mismo mecanismo que `impresion/plantilla.py::_combinar` — duplicado a
    propósito: son módulos gemelos sin relación de importación entre
    `dominio/` e `impresion/`.
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
    # Antes de la fase 5, `tablero_marcado` compartía el mismo valor que
    # `acento` — el resaltado de bola cantada y el color de acción quedaban
    # indistinguibles (hallazgo DU-6). Ahora son colores distintos.
    tablero_marcado: str = "#2ec4b6"
    # `#ffd60a`: el doc técnico §7 ya lo definía así; el modelo de la fase 4
    # nunca llegó a incluir este campo (hallazgo DU-6).
    numero_actual: str = "#ffd60a"


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
class ConfigPantalla:
    """Fase 5, decisión D4. Overlay de pantalla completa (bienvenida o
    cierre): no tiene posición propia, cubre el lienzo entero."""

    texto: str = ""


@dataclass(slots=True)
class ConfigJuego:
    """Fase 4: `mostrar_ultimas_bolas`, `sonido_activado`. Fase 5 (decisión
    D4) añade el resto.

    **Dos grupos, dos dueños distintos (decisión DU-7).** Los de "directo"
    se aplican en memoria de inmediato desde la sección Sorteo y se
    persisten con `repo_evento.actualizar_juego` (escritura puntual, nunca
    reescribiendo el tema completo): `modo`, `intervalo_seg`, `sonido_bola`,
    `voz`, `volumen_musica`. Los de "preparación" siguen viviendo en la
    sección Tema con su autoguardado de objeto completo:
    `pausa_al_ganador`, `segundos_reclamo`, `sin_reclamo`,
    `confirmar_extraccion`, `mostrar_ultimas_bolas`. `sonido_activado` es
    de la fase 4 y queda como estado permanente aceptado (no lo usa ningún
    control nuevo; los tres interruptores de sonido de la fase 5 son
    `sonido_bola`, `voz` y el volumen de música).
    """

    mostrar_ultimas_bolas: int = 5
    sonido_activado: bool = True
    # -- controles "de directo" (sección Sorteo, DU-7) ----------------------
    modo: str = "manual"  # "manual" | "automatico"
    intervalo_seg: int = 6
    sonido_bola: bool = True
    voz: bool = True
    idioma_voz: str = "es"
    volumen_musica: float = 0.5
    # -- controles "de preparación" (sección Tema, DU-7) --------------------
    pausa_al_ganador: bool = True
    confirmar_extraccion: bool = False
    # decisión D8: "continuar" | "cerrar"
    sin_reclamo: str = "continuar"
    # decisión de la tarea 4.24: segundos de cuenta regresiva de reclamo;
    # 0 = sin límite.
    segundos_reclamo: int = 60
    # Tarea 4.24: "por dónde grita bingo el jugador" — WhatsApp, en persona,
    # teléfono. Texto configurable que se pinta en transmisión junto a la
    # cuenta regresiva; el público tiene que saber a dónde reclamar.
    canal_reclamo: str = ""


def _bombo_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.02, pos_y=0.10, escala=1.0)


def _numero_actual_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.02, pos_y=0.32, escala=1.0)


def _tablero_75_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.72, pos_y=0.11, escala=0.9)


def _patron_activo_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.72, pos_y=0.68, escala=1.0)


def _contador_bolas_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.02, pos_y=0.02, escala=1.0)


def _reloj_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.20, pos_y=0.02, escala=1.0)


def _logo_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.85, pos_y=0.02, escala=1.0)


def _imagen_premio_por_defecto() -> ConfigBloque:
    return ConfigBloque(pos_x=0.02, pos_y=0.68, escala=1.0)


# (clave, clave_i18n, pos_x, pos_y, ancho_frac, alto_frac) — decisión DU-4.
# `pos_x`/`pos_y` son la posición **por defecto**: la que usa el botón
# "Restablecer composición" y la que sembraría un evento nuevo. La posición
# real y editable vive en la instancia de `ConfigBloque` de cada evento.
BLOQUES: tuple[tuple[str, str, float, float, float, float], ...] = (
    ("contador_bolas", "tema.bloque.contador_bolas", 0.02, 0.02, 0.15, 0.06),
    ("reloj", "tema.bloque.reloj", 0.20, 0.02, 0.12, 0.06),
    ("logo", "tema.bloque.logo", 0.85, 0.02, 0.12, 0.08),
    ("bombo", "tema.bloque.bombo", 0.02, 0.10, 0.45, 0.20),
    ("numero_actual", "tema.bloque.numero_actual", 0.02, 0.32, 0.45, 0.30),
    ("tablero_75", "tema.bloque.tablero_75", 0.72, 0.11, 0.26, 0.55),
    ("patron_activo", "tema.bloque.patron_activo", 0.72, 0.68, 0.26, 0.18),
    ("imagen_premio", "tema.bloque.imagen_premio", 0.02, 0.68, 0.20, 0.18),
)

_FORMA_POR_CLAVE: dict[str, tuple[float, float]] = {
    clave: (ancho_frac, alto_frac) for clave, _ci, _px, _py, ancho_frac, alto_frac in BLOQUES
}


@dataclass(slots=True)
class TemaDashboard:
    colores: ConfigColores = field(default_factory=ConfigColores)
    imagen_fondo: str | None = None
    bombo: ConfigBloque = field(default_factory=_bombo_por_defecto)
    tablero_75: ConfigBloque = field(default_factory=_tablero_75_por_defecto)
    contador_bolas: ConfigBloque = field(default_factory=_contador_bolas_por_defecto)
    reloj: ConfigBloque = field(default_factory=_reloj_por_defecto)
    numero_actual: ConfigBloque = field(default_factory=_numero_actual_por_defecto)
    patron_activo: ConfigBloque = field(default_factory=_patron_activo_por_defecto)
    imagen_premio: ConfigBloque = field(default_factory=_imagen_premio_por_defecto)
    logo: ConfigBloque = field(default_factory=_logo_por_defecto)
    banner_texto: ConfigBannerTexto = field(default_factory=ConfigBannerTexto)
    pantalla_bienvenida: ConfigPantalla = field(default_factory=ConfigPantalla)
    pantalla_cierre: ConfigPantalla = field(default_factory=ConfigPantalla)
    juego: ConfigJuego = field(default_factory=ConfigJuego)
    # Idioma del texto pintado en transmisión (decisión DU-13): independiente
    # del idioma activo de la interfaz del operador y de `juego.idioma_voz`
    # (que es el de la locución). Si Gabriel pone la app en inglés para
    # probar algo, el público sigue viendo "¡BINGO!", no "WINNER".
    idioma_publico: str = "es"
    # Defensa contra el hallazgo V6: una clave mal escrita en `tema_json` se
    # ignora para siempre, sin error. `version` (hoy 1) hace que ampliar el
    # modelo sea un cambio consciente, no un accidente que nadie ve — ver la
    # prueba `test_claves_de_tema_no_cambian_sin_darse_cuenta`.
    version: int = 1

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
            bombo=_combinar(ConfigBloque, datos.get("bombo"), _bombo_por_defecto()),
            tablero_75=_combinar(ConfigBloque, datos.get("tablero_75"), _tablero_75_por_defecto()),
            contador_bolas=_combinar(
                ConfigBloque, datos.get("contador_bolas"), _contador_bolas_por_defecto()
            ),
            reloj=_combinar(ConfigBloque, datos.get("reloj"), _reloj_por_defecto()),
            numero_actual=_combinar(
                ConfigBloque, datos.get("numero_actual"), _numero_actual_por_defecto()
            ),
            patron_activo=_combinar(
                ConfigBloque, datos.get("patron_activo"), _patron_activo_por_defecto()
            ),
            imagen_premio=_combinar(
                ConfigBloque, datos.get("imagen_premio"), _imagen_premio_por_defecto()
            ),
            logo=_combinar(ConfigBloque, datos.get("logo"), _logo_por_defecto()),
            banner_texto=_combinar(ConfigBannerTexto, datos.get("banner_texto")),
            pantalla_bienvenida=_combinar(ConfigPantalla, datos.get("pantalla_bienvenida")),
            pantalla_cierre=_combinar(ConfigPantalla, datos.get("pantalla_cierre")),
            juego=_combinar(ConfigJuego, datos.get("juego")),
            idioma_publico=datos.get("idioma_publico")
            if isinstance(datos.get("idioma_publico"), str)
            else "es",
            version=datos.get("version") if isinstance(datos.get("version"), int) else 1,
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
    poner el foco (mismo convenio que `impresion/plantilla.py::validar`).

    Los solapes de bloques (`detectar_solapes`) y el contraste bajo
    (`advertencias_contraste`) son avisos, no bloqueos — con la excepción de
    `numero_actual`, cuyo alto mínimo del 14% del lienzo (decisión DU-6) sí
    es un requisito duro: por debajo de eso, en un teléfono con vídeo
    comprimido, no se lee, y no hay imagen de fondo que lo disculpe.
    """
    _validar_color(tema.colores.fondo, "colores.fondo")
    _validar_color(tema.colores.texto, "colores.texto")
    _validar_color(tema.colores.acento, "colores.acento")
    _validar_color(tema.colores.tablero_marcado, "colores.tablero_marcado")
    _validar_color(tema.colores.numero_actual, "colores.numero_actual")
    for clave in _FORMA_POR_CLAVE:
        _validar_bloque(getattr(tema, clave), clave)
    if tema.juego.mostrar_ultimas_bolas < 0:
        raise ErrorValidacion(
            "tema.error.ultimas_bolas_invalido", campo="juego.mostrar_ultimas_bolas"
        )
    if tema.juego.segundos_reclamo < 0:
        raise ErrorValidacion(
            "tema.error.segundos_reclamo_invalido", campo="juego.segundos_reclamo"
        )
    if tema.juego.sin_reclamo not in ("continuar", "cerrar"):
        raise ErrorValidacion("tema.error.sin_reclamo_invalido", campo="juego.sin_reclamo")
    if tema.juego.modo not in ("manual", "automatico"):
        raise ErrorValidacion("tema.error.modo_invalido", campo="juego.modo")

    _, alto_frac_numero_actual = _FORMA_POR_CLAVE["numero_actual"]
    if tema.numero_actual.visible and (
        alto_frac_numero_actual * tema.numero_actual.escala < ALTO_MINIMO_NUMERO_ACTUAL_FRAC
    ):
        raise ErrorValidacion("tema.error.numero_actual_muy_pequeno", campo="numero_actual.escala")


def _rect_bloque(clave: str, bloque: ConfigBloque) -> tuple[float, float, float, float]:
    ancho_frac, alto_frac = _FORMA_POR_CLAVE[clave]
    ancho = ancho_frac * bloque.escala
    alto = alto_frac * bloque.escala
    return (bloque.pos_x, bloque.pos_y, bloque.pos_x + ancho, bloque.pos_y + alto)


def _se_solapan(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def detectar_solapes(tema: TemaDashboard) -> list[tuple[str, str]]:
    """Pares de bloques **visibles** cuyos rectángulos se superponen
    (decisión DU-4). No bloqueante: `vista_tema.py` lo pinta con
    `FranjaError.mostrar_info`, nunca con una excepción — mover un bloque no
    puede ser una operación que a veces falla."""
    rects = {
        clave: _rect_bloque(clave, getattr(tema, clave))
        for clave in _FORMA_POR_CLAVE
        if getattr(tema, clave).visible
    }
    claves = list(rects)
    pares: list[tuple[str, str]] = []
    for i, clave_a in enumerate(claves):
        for clave_b in claves[i + 1 :]:
            if _se_solapan(rects[clave_a], rects[clave_b]):
                pares.append((clave_a, clave_b))
    return pares


def _canal_lineal(canal_srgb: float) -> float:
    if canal_srgb <= 0.03928:
        return canal_srgb / 12.92
    return ((canal_srgb + 0.055) / 1.055) ** 2.4


def _luminancia_relativa(color_hex: str) -> float:
    r, g, b = (int(color_hex[i : i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, b = _canal_lineal(r), _canal_lineal(g), _canal_lineal(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(color_a: str, color_b: str) -> float:
    """Razón de contraste WCAG entre dos colores `#RRGGBB`. Movida aquí
    desde `ui/tema.py` (decisión DU-6): es matemática pura, sin nada de Qt.
    `ui/tema.py` sigue exponiéndola (reexportada) para no romper a quien ya
    la importa de ahí."""
    l1 = _luminancia_relativa(color_a)
    l2 = _luminancia_relativa(color_b)
    claro, oscuro = max(l1, l2), min(l1, l2)
    return (claro + 0.05) / (oscuro + 0.05)


def advertencias_contraste(tema: TemaDashboard) -> list[str]:
    """Claves i18n de aviso (no bloqueante, decisión DU-6): el preset por
    defecto siempre pasa; una imagen de fondo detrás puede hacer que un
    contraste "bajo" según esta fórmula siga siendo legible en la práctica,
    así que esto avisa, no impide guardar."""
    avisos: list[str] = []
    if contraste(tema.colores.texto, tema.colores.fondo) < UMBRAL_CONTRASTE_TRANSMISION:
        avisos.append("tema.aviso.contraste_texto")
    if contraste(tema.colores.numero_actual, tema.colores.fondo) < UMBRAL_CONTRASTE_TRANSMISION:
        avisos.append("tema.aviso.contraste_numero_actual")
    if contraste(tema.colores.tablero_marcado, tema.colores.fondo) < UMBRAL_CONTRASTE_TRANSMISION:
        avisos.append("tema.aviso.contraste_tablero_marcado")
    return avisos
