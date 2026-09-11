"""Casos de uso de `comprador` (contrato de la fase 4, §4.1, §4.2, §4.3).

Convenio del trabajador `QThread` (`docs/convenciones-codigo.md`):
`validar_importacion` acepta `al_progresar`/`debe_cancelar` y nunca importa
Qt; es `ui/tarea.py::Tarea` quien los conecta a señales desde el hilo de la
interfaz.

**Decisión TD-3 (atomicidad vs. `busy_timeout`, confirmada por Gabriel):**
`aplicar_importacion` trocea la escritura en bloques de
`TAMANO_BLOQUE_IMPORTACION` filas, cada uno en su propia `transaccion()`, en
vez de una única transacción para todo el archivo. Esto **renuncia a la
atomicidad total** de "todo o nada" a cambio de no sostener el lock de
escritor de SQLite más allá de `BUSY_TIMEOUT_MS` con un archivo de miles de
filas: un fallo real a mitad de la escritura deja aplicados los bloques ya
confirmados, y lo informa (`ResultadoImportacion.detenida_en_fila`). Una
fila cuyo cartón cambió de estado entre validar y aplicar no aborta nada —
se salta y ya quedó fuera de `informe.correctas` en el momento de aplicar
(hallazgo A2 del plan de la fase 4): la escritura solo reintenta una
condición de carrera legítima, nunca decide que "algo cambió" es un fallo.

`impresion/reporte.py` es el único módulo que escribe `.xlsx` (hallazgo A4):
este servicio reúne los datos y le delega la escritura — nunca importa
`openpyxl` para escribir, solo para leer el archivo que trae el operador.
"""

from __future__ import annotations

import dataclasses
import sqlite3
import zipfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bingo.config.ajustes import (
    COMPROBAR_CANCELAR_CADA_FILAS_IMPORTACION,
    LIMITE_FILAS_IMPORTACION,
    LIMITE_TAMANO_XLSX_DESCOMPRIMIDO_MB,
    LIMITE_TAMANO_XLSX_MB,
    TAMANO_BLOQUE_IMPORTACION,
)
from bingo.dominio.codigo import normalizar, normalizar_texto
from bingo.dominio.estados import TRANSICIONES_CARTON, puede_transicionar
from bingo.dominio.modelos import Carton, Comprador
from bingo.impresion import reporte
from bingo.persistencia import repo_auditoria, repo_carton, repo_comprador
from bingo.persistencia.conexion import transaccion
from bingo.servicios import servicio_rondas
from bingo.utilidades.errores import (
    ErrorBingo,
    ErrorNoEncontrado,
    ErrorTransicionInvalida,
    ErrorValidacion,
)

_ALIAS_COLUMNAS: dict[str, frozenset[str]] = {
    "codigo": frozenset({"codigo", "código", "code", "carton", "cartón", "cartonid"}),
    "nombre": frozenset({"nombre", "name", "comprador", "cliente"}),
    "telefono": frozenset({"telefono", "teléfono", "phone", "celular", "movil", "móvil"}),
    "cedula": frozenset({"cedula", "cédula", "dni", "documento", "id"}),
    "correo": frozenset({"correo", "email", "e-mail", "mail", "correoelectronico"}),
}
_COLUMNAS_OBLIGATORIAS = ("codigo", "nombre")
_ESTADOS_VENDIBLES = ("impreso", "entregado")


@dataclass(slots=True)
class FilaImportacion:
    numero_fila: int
    codigo: str
    nombre: str
    telefono: str | None = None
    cedula: str | None = None
    correo: str | None = None
    carton_id: int | None = None
    estado_carton: str | None = None
    comprador_existente_id: int | None = None


@dataclass(slots=True)
class InformeImportacion:
    correctas: list[FilaImportacion] = field(default_factory=list)
    completa_provisional: list[FilaImportacion] = field(default_factory=list)
    ya_registrado_igual: list[FilaImportacion] = field(default_factory=list)
    codigo_inexistente: list[FilaImportacion] = field(default_factory=list)
    codigo_ambiguo: list[FilaImportacion] = field(default_factory=list)
    duplicado_en_archivo: list[FilaImportacion] = field(default_factory=list)
    ya_asignado: list[FilaImportacion] = field(default_factory=list)
    sin_nombre: list[FilaImportacion] = field(default_factory=list)
    columnas_faltantes: list[str] = field(default_factory=list)
    fue_cancelado: bool = False

    def categorias(self) -> dict[str, list[FilaImportacion]]:
        """Solo las categorías de problema (sin `correctas`), para que la
        vista pinte "solo las que tengan n > 0" (decisión DS3)."""
        return {
            "completa_provisional": self.completa_provisional,
            "ya_registrado_igual": self.ya_registrado_igual,
            "codigo_inexistente": self.codigo_inexistente,
            "codigo_ambiguo": self.codigo_ambiguo,
            "duplicado_en_archivo": self.duplicado_en_archivo,
            "ya_asignado": self.ya_asignado,
            "sin_nombre": self.sin_nombre,
        }


@dataclass(slots=True, frozen=True)
class ResultadoImportacion:
    aplicadas: int
    completadas_provisionales: int
    detenida_en_fila: int | None = None
    error: ErrorBingo | None = None


@dataclass(slots=True, frozen=True)
class ResultadoVentaPorRango:
    marcados: int
    ya_vendidos: int
    omitidos_anulados: int
    omitidos_sin_imprimir: int


# ── Exportación e informe (delegan la escritura de .xlsx a impresion/reporte) ──


def exportar_plantilla(
    con: sqlite3.Connection, evento_id: int, ruta_destino: Path, textos: Mapping[str, str]
) -> Path:
    """`textos` ya viene traducido de la vista: este servicio no importa
    i18n (mismo convenio que `impresion/plantilla.py`)."""
    codigos = sorted(
        c.codigo
        for c in repo_carton.listar_por_evento(con, evento_id, limite=None)
        if c.estado != "anulado"
    )
    if not codigos:
        raise ErrorValidacion("compradores.error.sin_cartones", campo="archivo")
    try:
        return reporte.escribir_plantilla_compradores(codigos, ruta_destino, textos)
    except PermissionError as error:
        raise ErrorValidacion(
            "compradores.error.destino_bloqueado", campo="archivo", detalle=str(error)
        ) from error


def exportar_informe(
    informe: InformeImportacion, ruta_destino: Path, textos: Mapping[str, str]
) -> Path:
    """Exporta las filas problemáticas del informe a `.xlsx` (contrato
    §4.2) — se puede hacer desde la propia pantalla de informe, sin aplicar
    nada todavía."""
    try:
        return reporte.escribir_informe_importacion(informe.categorias(), ruta_destino, textos)
    except PermissionError as error:
        raise ErrorValidacion(
            "compradores.error.destino_bloqueado", campo="archivo", detalle=str(error)
        ) from error


# ── Lectura y validación en seco del Excel ──


def _verificar_archivo_seguro(ruta: Path) -> None:
    if not ruta.exists():
        raise ErrorValidacion("compradores.error.archivo_no_encontrado", campo="archivo")
    if ruta.suffix.lower() == ".xls":
        raise ErrorValidacion("compradores.error.formato_xls_legado", campo="archivo")
    if ruta.suffix.lower() != ".xlsx":
        raise ErrorValidacion("compradores.error.formato_no_soportado", campo="archivo")

    try:
        tamano_disco = ruta.stat().st_size
    except OSError as error:
        raise ErrorValidacion(
            "compradores.error.archivo_no_encontrado", campo="archivo", detalle=str(error)
        ) from error
    if tamano_disco > LIMITE_TAMANO_XLSX_MB * 1024 * 1024:
        raise ErrorValidacion(
            "compradores.error.archivo_muy_grande",
            campo="archivo",
            parametros={"limite_mb": LIMITE_TAMANO_XLSX_MB},
        )

    # A6 (plan de la fase 4): `sharedStrings.xml` se descomprime entero antes
    # de que `openpyxl` empiece a iterar filas. Un .xlsx pequeño en disco
    # puede descomprimir a un tamaño mucho mayor ("zip bomb" de Excel); se
    # comprueba el tamaño total descomprimido antes de abrir el libro.
    try:
        with zipfile.ZipFile(ruta) as zf:
            total_descomprimido = sum(info.file_size for info in zf.infolist())
    except zipfile.BadZipFile as error:
        raise ErrorValidacion(
            "compradores.error.formato_no_soportado", campo="archivo", detalle=str(error)
        ) from error
    if total_descomprimido > LIMITE_TAMANO_XLSX_DESCOMPRIMIDO_MB * 1024 * 1024:
        raise ErrorValidacion(
            "compradores.error.archivo_muy_grande",
            campo="archivo",
            parametros={"limite_mb": LIMITE_TAMANO_XLSX_DESCOMPRIMIDO_MB},
        )


def _normalizar_encabezado(texto: str) -> str:
    import unicodedata

    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_acentos.strip().lower().replace(" ", "").replace("_", "")


def _mapear_columnas(encabezados: Sequence[Any]) -> dict[str, int]:
    indices: dict[str, int] = {}
    for posicion, valor in enumerate(encabezados or ()):
        if valor is None:
            continue
        normalizado = _normalizar_encabezado(str(valor))
        for campo, alias in _ALIAS_COLUMNAS.items():
            if campo in indices:
                continue
            if normalizado in alias:
                indices[campo] = posicion
    return indices


def _hoja_de_trabajo(libro: Any) -> Any:
    """La hoja `Ventas` (decisión A7 del plan de la fase 4); si no existe con
    ese nombre exacto, se usa la primera hoja del libro."""
    for nombre in libro.sheetnames:
        if nombre.strip().lower() == "ventas":
            return libro[nombre]
    return libro[libro.sheetnames[0]]


def _texto_opcional(fila: Sequence[Any], indice: int | None) -> str | None:
    if indice is None or indice >= len(fila):
        return None
    valor = fila[indice]
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _mismos_datos(
    existente: Comprador, nombre: str, telefono: str | None, cedula: str | None, correo: str | None
) -> bool:
    def _norm(v: str | None) -> str:
        return normalizar_texto(v) if v else ""

    return (
        _norm(existente.nombre) == _norm(nombre)
        and _norm(existente.telefono) == _norm(telefono)
        and _norm(existente.cedula) == _norm(cedula)
        and _norm(existente.correo) == _norm(correo)
    )


def _clasificar_fila(
    item: FilaImportacion,
    *,
    codigos_existentes: Sequence[str],
    cartones_por_codigo_normalizado: Mapping[str, Carton],
    compradores_por_carton: Mapping[int, Comprador],
) -> tuple[str, FilaImportacion]:
    """Clasifica una fila contra el estado real de la base (sin considerar
    duplicados dentro del propio archivo, que es responsabilidad del
    llamador). Única lógica de clasificación — la usan tanto
    `validar_importacion` como `revalidar_fila` (edición en línea del código,
    decisión de gusto TD-2), para que las dos rutas nunca diverjan.
    """
    resultado = normalizar(item.codigo, codigos_existentes)
    if resultado.es_ambiguo:
        return "codigo_ambiguo", item
    if not resultado.es_unico:
        return "codigo_inexistente", item

    codigo_real = resultado.codigo_unico
    assert codigo_real is not None
    carton = cartones_por_codigo_normalizado.get(normalizar_texto(codigo_real))
    if carton is None:
        return "codigo_inexistente", item

    item = dataclasses.replace(item, carton_id=carton.id, estado_carton=carton.estado)

    if not item.nombre.strip():
        return "sin_nombre", item

    existente = compradores_por_carton.get(carton.id)
    if existente is not None:
        if existente.provisional:
            return "completa_provisional", dataclasses.replace(
                item, comprador_existente_id=existente.id
            )
        if _mismos_datos(existente, item.nombre, item.telefono, item.cedula, item.correo):
            return "ya_registrado_igual", item
        return "ya_asignado", dataclasses.replace(item, comprador_existente_id=existente.id)

    if carton.estado not in _ESTADOS_VENDIBLES:
        # Un cartón `vendido` sin comprador vivo no debería existir
        # (invariante E-A5); un `generado` o `anulado` tampoco es vendible
        # todavía. No se inventa una categoría más: se reporta como código
        # inexistente, que es lo único accionable para el operador.
        return "codigo_inexistente", item

    return "correctas", item


def validar_importacion(
    con: sqlite3.Connection,
    evento_id: int,
    ruta_origen: Path,
    *,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,
) -> InformeImportacion:
    """Lee el `.xlsx` entero con `openpyxl` en modo `read_only` y construye
    el informe completo en memoria, sin escribir nada en la base todavía
    (decisión D6). No hay conteo de filas confiable de antemano
    (`ws.max_row` no es de fiar en `read_only` — hallazgo A6), así que el
    progreso se reporta por bloque de filas procesadas, no como fracción de
    un total conocido.
    """
    ruta = Path(ruta_origen)
    _verificar_archivo_seguro(ruta)

    import openpyxl
    from openpyxl.utils.exceptions import InvalidFileException

    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except PermissionError as error:
        raise ErrorValidacion(
            "compradores.error.archivo_bloqueado", campo="archivo", detalle=str(error)
        ) from error
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as error:
        raise ErrorValidacion(
            "compradores.error.formato_no_soportado", campo="archivo", detalle=str(error)
        ) from error

    informe = InformeImportacion()
    try:
        hoja = _hoja_de_trabajo(libro)
        filas: Iterator[tuple[Any, ...]] = hoja.iter_rows(values_only=True)
        try:
            encabezados = next(filas)
        except StopIteration:
            informe.columnas_faltantes = list(_COLUMNAS_OBLIGATORIAS)
            return informe

        indices = _mapear_columnas(encabezados)
        faltantes = [c for c in _COLUMNAS_OBLIGATORIAS if c not in indices]
        if faltantes:
            informe.columnas_faltantes = faltantes
            return informe

        cartones = repo_carton.listar_por_evento(con, evento_id, limite=None)
        cartones_por_codigo = {normalizar_texto(c.codigo): c for c in cartones}
        codigos_existentes = [c.codigo for c in cartones]
        compradores_por_carton = repo_comprador.mapa_por_evento(con, evento_id)

        vistos_en_archivo: set[str] = set()
        numero_fila = 1  # ya se consumió el encabezado
        procesadas = 0

        for fila in filas:
            numero_fila += 1
            if numero_fila - 1 > LIMITE_FILAS_IMPORTACION:
                raise ErrorValidacion(
                    "compradores.error.demasiadas_filas",
                    campo="archivo",
                    parametros={"limite": LIMITE_FILAS_IMPORTACION},
                )
            if (
                debe_cancelar is not None
                and numero_fila % COMPROBAR_CANCELAR_CADA_FILAS_IMPORTACION == 0
                and debe_cancelar()
            ):
                informe.fue_cancelado = True
                break
            if fila is None or all(v is None for v in fila):
                continue  # fila totalmente vacía en medio del archivo: se ignora

            valor_codigo = fila[indices["codigo"]]
            valor_nombre = fila[indices["nombre"]]
            codigo_bruto = str(valor_codigo).strip() if valor_codigo is not None else ""
            nombre_bruto = str(valor_nombre).strip() if valor_nombre is not None else ""
            telefono = _texto_opcional(fila, indices.get("telefono"))
            cedula = _texto_opcional(fila, indices.get("cedula"))
            correo = _texto_opcional(fila, indices.get("correo"))

            if not nombre_bruto and not telefono and not cedula and not correo:
                # La plantilla exportada (D6) trae el código pre-llenado en
                # todas las filas, una por cartón del evento. Un cartón que
                # todavía no se vendió llega así: código solo, todo lo demás
                # vacío — no es un error de tecleo, es "no vendido todavía".
                # Reportarlo como `sin_nombre` inundaría el informe con una
                # fila por cada cartón sin vender.
                continue

            item = FilaImportacion(
                numero_fila=numero_fila,
                codigo=codigo_bruto,
                nombre=nombre_bruto,
                telefono=telefono,
                cedula=cedula,
                correo=correo,
            )

            categoria, item = _clasificar_fila(
                item,
                codigos_existentes=codigos_existentes,
                cartones_por_codigo_normalizado=cartones_por_codigo,
                compradores_por_carton=compradores_por_carton,
            )

            if categoria == "correctas":
                # Puede que `item.codigo` no sea el código real (viene tal
                # cual del Excel); usamos el carton_id ya resuelto para
                # detectar duplicados robustamente frente a variaciones de
                # formato del mismo código repetido dos veces en el archivo.
                clave_duplicado = str(item.carton_id)
                if clave_duplicado in vistos_en_archivo:
                    informe.duplicado_en_archivo.append(item)
                else:
                    vistos_en_archivo.add(clave_duplicado)
                    informe.correctas.append(item)
                    procesadas += 1
            else:
                getattr(informe, categoria).append(item)

            if al_progresar is not None and numero_fila % TAMANO_BLOQUE_IMPORTACION == 0:
                al_progresar(numero_fila, numero_fila)
    finally:
        # M5 (plan de la fase 4): `read_only=True` deja el .xlsx bloqueado en
        # Windows hasta `close()`, incluso si algo de lo anterior lanzó.
        libro.close()

    return informe


def revalidar_fila(
    con: sqlite3.Connection, evento_id: int, fila: FilaImportacion, codigo_nuevo: str
) -> tuple[str, FilaImportacion]:
    """Reintenta clasificar una sola fila con un código corregido a mano
    (decisión de gusto TD-2): cubre el resto de transcripciones que la
    normalización automática (`dominio.codigo`) no pudo reconciliar sola,
    sin tener que volver a exportar y reimportar todo el archivo.
    """
    cartones = repo_carton.listar_por_evento(con, evento_id, limite=None)
    cartones_por_codigo = {normalizar_texto(c.codigo): c for c in cartones}
    codigos_existentes = [c.codigo for c in cartones]
    compradores_por_carton = repo_comprador.mapa_por_evento(con, evento_id)
    item = dataclasses.replace(fila, codigo=codigo_nuevo, carton_id=None, estado_carton=None)
    return _clasificar_fila(
        item,
        codigos_existentes=codigos_existentes,
        cartones_por_codigo_normalizado=cartones_por_codigo,
        compradores_por_carton=compradores_por_carton,
    )


def _en_bloques(items: Sequence[FilaImportacion], tamano: int) -> Iterator[list[FilaImportacion]]:
    for inicio in range(0, len(items), tamano):
        yield list(items[inicio : inicio + tamano])


def aplicar_importacion(
    con: sqlite3.Connection,
    evento_id: int,
    informe: InformeImportacion,
    *,
    al_progresar: Callable[[int, int], None] | None = None,
    debe_cancelar: Callable[[], bool] | None = None,  # noqa: ARG001 - R15: la escritura no es cancelable
) -> ResultadoImportacion:
    _exigir_sin_ronda_en_curso(con, evento_id)
    total = len(informe.correctas) + len(informe.completa_provisional)
    aplicadas = 0
    completadas = 0
    detenida_en: int | None = None
    error_final: ErrorBingo | None = None

    for bloque in _en_bloques(informe.correctas, TAMANO_BLOQUE_IMPORTACION):
        try:
            with transaccion(con):
                for item in bloque:
                    actual = repo_carton.obtener(con, item.carton_id) if item.carton_id else None
                    if actual is None or not puede_transicionar(
                        TRANSICIONES_CARTON, actual.estado, "vendido"
                    ):
                        # A2: el cartón cambió de estado entre validar y
                        # aplicar (otra importación, otra pestaña). Se salta
                        # esta fila; no se aborta el bloque por ella.
                        continue
                    repo_comprador.crear(
                        con,
                        Comprador(
                            carton_id=item.carton_id,
                            nombre=item.nombre,
                            telefono=item.telefono,
                            cedula=item.cedula,
                            correo=item.correo,
                            estado_carton_previo=actual.estado,
                        ),
                    )
                    repo_carton.actualizar_estado(con, item.carton_id, "vendido")
                    aplicadas += 1
                repo_auditoria.registrar(
                    con, evento_id, "compradores.importados", detalle=f"{len(bloque)} filas"
                )
        except ErrorBingo as error:
            detenida_en = bloque[0].numero_fila
            error_final = error
            break
        if al_progresar is not None:
            al_progresar(aplicadas, total)

    if error_final is None:
        for bloque in _en_bloques(informe.completa_provisional, TAMANO_BLOQUE_IMPORTACION):
            try:
                with transaccion(con):
                    for item in bloque:
                        if item.comprador_existente_id is None:
                            continue
                        existente = repo_comprador.obtener(con, item.comprador_existente_id)
                        # E-A4/E-A6: no se toca el estado del cartón (ya está
                        # `vendido`); solo se completan los datos reales
                        # sobre la fila provisional.
                        if existente is None or not existente.provisional:
                            continue
                        repo_comprador.actualizar(
                            con,
                            dataclasses.replace(
                                existente,
                                nombre=item.nombre,
                                telefono=item.telefono,
                                cedula=item.cedula,
                                correo=item.correo,
                                provisional=False,
                            ),
                        )
                        completadas += 1
                    repo_auditoria.registrar(
                        con, evento_id, "compradores.completados", detalle=f"{len(bloque)} filas"
                    )
            except ErrorBingo as error:
                detenida_en = bloque[0].numero_fila
                error_final = error
                break
            if al_progresar is not None:
                al_progresar(aplicadas + completadas, total)

    return ResultadoImportacion(
        aplicadas=aplicadas,
        completadas_provisionales=completadas,
        detenida_en_fila=detenida_en,
        error=error_final,
    )


# ── Alta manual, edición, anulación, venta por rango (contrato §4.1, §4.3) ──


def _exigir_sin_ronda_en_curso(con: sqlite3.Connection, evento_id: int) -> None:
    """Bloqueo de venta con ronda en curso (tarea 4.23, corrección S5-4,
    hallazgo C4/C5): vender, completar o anular una venta a mitad de ronda
    dejaría el índice inverso en memoria (`EstadoPartida`, construido al
    iniciar la ronda) desincronizado de lo que dice la base — un cartón
    vendido después no podría ganar, en silencio, que es el peor fallo
    posible de este producto. Con la ronda solo `pausada` sí se permite: al
    reanudar, el motor reconstruye ese índice desde cero (D13)."""
    if servicio_rondas.hay_ronda_en_curso(con, evento_id):
        raise ErrorValidacion("compradores.error.ronda_en_curso")


def registrar_manual(
    con: sqlite3.Connection, evento_id: int, codigo: str, comprador: Comprador
) -> Comprador:
    _exigir_sin_ronda_en_curso(con, evento_id)
    if not comprador.nombre.strip():
        raise ErrorValidacion("compradores.error.nombre_vacio", campo="nombre")
    carton = repo_carton.obtener_por_codigo(con, evento_id, codigo.strip())
    if carton is None:
        raise ErrorValidacion(
            "compradores.error.codigo_inexistente", campo="codigo", parametros={"codigo": codigo}
        )
    if repo_comprador.obtener_por_carton(con, carton.id) is not None:
        raise ErrorValidacion(
            "compradores.error.ya_asignado", campo="codigo", parametros={"codigo": codigo}
        )
    if not puede_transicionar(TRANSICIONES_CARTON, carton.estado, "vendido"):
        raise ErrorTransicionInvalida(
            "error.transicion_invalida", parametros={"actual": carton.estado, "nuevo": "vendido"}
        )

    a_crear = dataclasses.replace(
        comprador,
        carton_id=carton.id,
        provisional=False,
        estado_carton_previo=carton.estado,
        anulado_en=None,
    )
    with transaccion(con):
        creado = repo_comprador.crear(con, a_crear)
        repo_carton.actualizar_estado(con, carton.id, "vendido")
        repo_auditoria.registrar(
            con, evento_id, "comprador.registrado", detalle=f"carton={carton.codigo}"
        )
    return creado


def actualizar_comprador(con: sqlite3.Connection, comprador: Comprador) -> None:
    if comprador.id is None:
        raise ValueError("No se puede actualizar un comprador sin id")
    if not comprador.nombre.strip():
        raise ErrorValidacion("compradores.error.nombre_vacio", campo="nombre")
    carton = repo_carton.obtener(con, comprador.carton_id)
    evento_id = carton.evento_id if carton is not None else None
    with transaccion(con):
        repo_comprador.actualizar(con, comprador)
        repo_auditoria.registrar(
            con, evento_id, "comprador.actualizado", detalle=f"comprador_id={comprador.id}"
        )


def anular_venta(con: sqlite3.Connection, comprador_id: int, motivo: str | None = None) -> None:
    """Decisión D4: anular una venta borra (lógicamente) el comprador y
    devuelve el cartón a su estado anterior — nunca a `anulado`. Si el
    estado previo se desconoce (fila antigua sin `estado_carton_previo`),
    se asume `entregado` (decisión R12): es el estado más conservador, el
    que deja el cartón disponible para revenderse sin fingir que nunca se
    imprimió.

    El detalle de auditoría lleva el código del cartón y el id del
    comprador, **nunca** su nombre ni sus datos de contacto (decisión R11 —
    privacidad: es lo único que sobrevive tras el borrado lógico).
    """
    comprador = repo_comprador.obtener(con, comprador_id)
    if comprador is None or comprador.anulado_en is not None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": comprador_id})
    carton = repo_carton.obtener(con, comprador.carton_id)
    if carton is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": comprador.carton_id})
    _exigir_sin_ronda_en_curso(con, carton.evento_id)

    estado_previo = comprador.estado_carton_previo or "entregado"
    if not puede_transicionar(TRANSICIONES_CARTON, carton.estado, estado_previo):
        raise ErrorTransicionInvalida(
            "error.transicion_invalida",
            parametros={"actual": carton.estado, "nuevo": estado_previo},
        )

    with transaccion(con):
        repo_comprador.anular(con, comprador_id)
        repo_carton.actualizar_estado(con, carton.id, estado_previo)
        repo_auditoria.registrar(
            con,
            carton.evento_id,
            "venta.anulada",
            detalle=f"carton={carton.codigo}, comprador_id={comprador_id}, motivo={motivo or ''}",
        )


def _filtrar_rango(
    con: sqlite3.Connection, evento_id: int, desde: str, hasta: str
) -> tuple[list[Carton], ResultadoVentaPorRango]:
    """Núcleo de filtrado compartido por `previsualizar_venta_por_rango` y
    `marcar_vendidos_por_rango` (hallazgo E-C2): un cartón del rango que ya
    está vendido, anulado o nunca se imprimió no aborta el rango entero — se
    cuenta aparte, nunca se elige a ciegas."""
    cartones = [
        c
        for c in repo_carton.listar_por_evento(con, evento_id, limite=None)
        if desde <= c.codigo <= hasta
    ]
    ya_vendidos = 0
    omitidos_anulados = 0
    omitidos_sin_imprimir = 0
    elegibles: list[Carton] = []
    for carton in cartones:
        if carton.estado == "vendido":
            ya_vendidos += 1
        elif carton.estado == "anulado":
            omitidos_anulados += 1
        elif carton.estado not in _ESTADOS_VENDIBLES:
            omitidos_sin_imprimir += 1
        else:
            elegibles.append(carton)
    resultado = ResultadoVentaPorRango(
        marcados=len(elegibles),
        ya_vendidos=ya_vendidos,
        omitidos_anulados=omitidos_anulados,
        omitidos_sin_imprimir=omitidos_sin_imprimir,
    )
    return elegibles, resultado


def previsualizar_venta_por_rango(
    con: sqlite3.Connection, evento_id: int, desde: str, hasta: str
) -> ResultadoVentaPorRango:
    """Mismo filtro que `marcar_vendidos_por_rango`, sin escribir nada
    (decisión DS9): la vista muestra "se marcarán N cartones" antes de que
    el operador confirme."""
    _elegibles, resultado = _filtrar_rango(con, evento_id, desde, hasta)
    return resultado


def marcar_vendidos_por_rango(
    con: sqlite3.Connection, evento_id: int, desde: str, hasta: str, *, nombre_generico: str
) -> ResultadoVentaPorRango:
    """Venta de puerta por rango de código (contrato §4.1, decisión R7):
    crea un comprador **provisional** por cartón (decisión D.1 + D4) — sin
    datos de contacto, con `nombre_generico` ya traducido por la vista (este
    servicio no importa i18n).
    """
    _exigir_sin_ronda_en_curso(con, evento_id)
    elegibles, resultado = _filtrar_rango(con, evento_id, desde, hasta)

    marcados = 0
    with transaccion(con):
        for carton in elegibles:
            repo_comprador.crear(
                con,
                Comprador(
                    carton_id=carton.id,
                    nombre=nombre_generico,
                    provisional=True,
                    estado_carton_previo=carton.estado,
                ),
            )
            repo_carton.actualizar_estado(con, carton.id, "vendido")
            marcados += 1
        if marcados:
            repo_auditoria.registrar(
                con,
                evento_id,
                "compradores.venta_por_rango",
                detalle=f"{desde}-{hasta}: {marcados}",
            )

    return dataclasses.replace(resultado, marcados=marcados)


def eliminar_todos_del_evento(con: sqlite3.Connection, evento_id: int) -> int:
    """Borrado físico real (no lógico) de todos los compradores del evento —
    el mecanismo de retención de datos personales que `TODOS.md` P1 sigue
    dejando como decisión pendiente de Gabriel (qué plazo, quién lo ejecuta).
    Barre también las filas de auditoría de venta (`venta.*`), las únicas
    que referencian datos de un comprador que este borrado deja sin fila
    (hallazgo A3)."""
    with transaccion(con):
        eliminados = repo_comprador.eliminar_por_evento(con, evento_id)
        repo_auditoria.eliminar_por_evento_y_prefijo(con, evento_id, "venta.")
        repo_auditoria.registrar(
            con, evento_id, "compradores.purgados", detalle=f"{eliminados} filas"
        )
    return eliminados
