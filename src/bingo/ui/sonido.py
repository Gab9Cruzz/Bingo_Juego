"""Sonido y locución del sorteo (contrato §5.8, decisiones D5/D6).

**Un solo módulo, no un paquete de tres** (hallazgo S5-2): `Efectos`,
`Musica` y la locución comparten el mismo ciclo de vida (nacen al iniciar
una ronda, mueren al cerrarla o al salir del modo vivo) y ninguna se usa
sin las otras — separarlas en archivos sería falsa granularidad.

**Nada de esto revienta el sorteo si el equipo no tiene tarjeta de sonido o
motor de voz.** Cada clase comprueba lo que hace falta comprobar *antes* de
instanciar el objeto de Qt correspondiente; con todo desactivado
(`sonido_bola=False`, `voz=False`) no se instancia ni un `QSoundEffect` ni
un `QTextToSpeech` — instanciar uno en un equipo sin audio avisa por
consola, y la prueba de la tarea 4.10 lo verifica.
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QLocale, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from bingo.config.rutas import dir_medios

logger = logging.getLogger("bingo.ui.sonido")

_PAQUETE_SONIDOS = "bingo.recursos.sonidos"
_ARCHIVOS_EFECTO = {"bola": "bola.wav", "ganador": "ganador.wav", "alerta": "alerta.wav"}


def _url_recurso_sonido(nombre_archivo: str) -> QUrl:
    ruta = resources.files(_PAQUETE_SONIDOS).joinpath(nombre_archivo)
    return QUrl.fromLocalFile(str(ruta))


class Efectos:
    """`QSoundEffect` para bola/ganador/alerta. Con `activado=False` no
    instancia ningún `QSoundEffect`."""

    def __init__(self, *, activado: bool = True, volumen: float = 0.8) -> None:
        self._efectos: dict[str, QSoundEffect] = {}
        if not activado:
            return
        for clave, archivo in _ARCHIVOS_EFECTO.items():
            efecto = QSoundEffect()
            efecto.setSource(_url_recurso_sonido(archivo))
            efecto.setVolume(max(0.0, min(1.0, volumen)))
            self._efectos[clave] = efecto

    @property
    def activados(self) -> bool:
        return bool(self._efectos)

    def reproducir(self, clave: str) -> None:
        efecto = self._efectos.get(clave)
        if efecto is None:
            return
        # Un QSoundEffect recién construido no suena hasta que su `status()`
        # llega a `Ready` — reproducir antes no lanza, simplemente no suena.
        if efecto.status() == QSoundEffect.Status.Ready:
            efecto.play()

    def establecer_volumen(self, volumen: float) -> None:
        for efecto in self._efectos.values():
            efecto.setVolume(max(0.0, min(1.0, volumen)))


class Musica:
    """Música de fondo elegida por el operador desde su propio equipo — no
    se empaqueta ningún archivo de música (decisión D6). `QMediaPlayer` +
    `QAudioOutput`, en bucle, con volumen independiente de los efectos."""

    def __init__(self, *, activado: bool = True, volumen: float = 0.5) -> None:
        self._reproductor: QMediaPlayer | None = None
        self._salida: QAudioOutput | None = None
        if not activado:
            return
        self._reproductor = QMediaPlayer()
        self._salida = QAudioOutput()
        self._reproductor.setAudioOutput(self._salida)
        self._salida.setVolume(max(0.0, min(1.0, volumen)))
        self._reproductor.mediaStatusChanged.connect(self._al_cambiar_estado)

    @property
    def activada(self) -> bool:
        return self._reproductor is not None

    def _al_cambiar_estado(self, estado: QMediaPlayer.MediaStatus) -> None:
        if estado == QMediaPlayer.MediaStatus.EndOfMedia and self._reproductor is not None:
            self._reproductor.setPosition(0)
            self._reproductor.play()

    def reproducir_archivo(self, ruta: Path) -> None:
        if self._reproductor is None:
            return
        self._reproductor.setSource(QUrl.fromLocalFile(str(ruta)))
        self._reproductor.play()

    def detener(self) -> None:
        if self._reproductor is not None:
            self._reproductor.stop()

    def establecer_volumen(self, volumen: float) -> None:
        if self._salida is not None:
            self._salida.setVolume(max(0.0, min(1.0, volumen)))


class ProveedorLocucion(Protocol):
    def decir(self, numero: int) -> None: ...
    def detener(self) -> None: ...
    def disponible(self) -> bool: ...


def _locale_para_idioma(idioma: str) -> QLocale:
    if idioma == "en":
        return QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
    return QLocale(QLocale.Language.Spanish, QLocale.Country.Ecuador)


class LocucionTTS:
    """Motor de voz del sistema, por defecto (decisión D5). Se desactiva
    sola —sin lanzar— si no hay ningún motor disponible o si el idioma
    elegido no tiene ninguna voz: el locale se fija **antes** de pedir
    voces (`availableVoices()` solo devuelve las del locale activo)."""

    def __init__(self, idioma: str) -> None:
        self._voz: object | None = None
        if not self._importar_qtexttospeech():
            return
        from PySide6.QtTextToSpeech import QTextToSpeech

        if not QTextToSpeech.availableEngines():
            logger.warning("ui.sonido: ningún motor de locución disponible")
            return
        candidata = QTextToSpeech()
        candidata.setLocale(_locale_para_idioma(idioma))
        if not candidata.availableVoices():
            logger.warning("ui.sonido: sin voces de locución para el idioma %r", idioma)
            return
        self._voz = candidata

    @staticmethod
    def _importar_qtexttospeech() -> bool:
        try:
            import PySide6.QtTextToSpeech  # noqa: F401
        except ImportError:
            logger.warning("ui.sonido: QtTextToSpeech no está disponible en este equipo")
            return False
        return True

    def decir(self, numero: int) -> None:
        if self._voz is None:
            return
        self._voz.say(str(numero))  # type: ignore[attr-defined]

    def detener(self) -> None:
        if self._voz is not None:
            self._voz.stop()  # type: ignore[attr-defined]

    def disponible(self) -> bool:
        return self._voz is not None


class LocucionPregrabada:
    """`medios/locucion/<idioma>/01.wav … 75.wav`. Solo se elige si la
    carpeta está completa (`crear_proveedor`); el día que Gabriel quiera
    grabarse, copia 75 archivos y no toca código."""

    def __init__(self, carpeta: Path) -> None:
        self._carpeta = carpeta
        self._efecto = QSoundEffect()

    def decir(self, numero: int) -> None:
        ruta = self._carpeta / f"{numero:02d}.wav"
        if not ruta.exists():
            return
        self._efecto.setSource(QUrl.fromLocalFile(str(ruta)))
        self._efecto.play()

    def detener(self) -> None:
        self._efecto.stop()

    def disponible(self) -> bool:
        return True


def _carpeta_pregrabada(idioma: str) -> Path:
    return dir_medios() / "locucion" / idioma


def _pregrabada_completa(carpeta: Path) -> bool:
    return carpeta.is_dir() and all((carpeta / f"{n:02d}.wav").exists() for n in range(1, 76))


def crear_proveedor(idioma: str, *, activado: bool = True) -> ProveedorLocucion | None:
    """`None` si `activado=False`: ni siquiera se comprueba la carpeta
    pregrabada ni se toca `QTextToSpeech`."""
    if not activado:
        return None
    carpeta = _carpeta_pregrabada(idioma)
    if _pregrabada_completa(carpeta):
        return LocucionPregrabada(carpeta)
    return LocucionTTS(idioma)
