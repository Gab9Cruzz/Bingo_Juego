# TODOS — Proyecto BINGO

Diferidos durante `/gstack-autoplan` sobre `docs/Fase_1/Contrato_Fase1.md` el 2026-09-04.
Formato: **qué** · por qué · esfuerzo (humano / CC) · prioridad · depende de.

## P1 — antes del primer evento pagado

- **Consulta legal sobre premios en efectivo en Ecuador.**
  El alcance §8 lo llama "el punto más expuesto de la operación" y dice
  explícitamente "consultar a un abogado antes del primer evento pagado". Ninguna
  de las cinco fases contiene una tarea para esto. Si la respuesta es mala,
  invalida las cinco fases retroactivamente.
  Esfuerzo: 1 semana de calendario / — · Depende de: nada. Se puede empezar hoy.

- **Lectura de las políticas de Facebook y YouTube sobre juegos con premio.**
  El alcance §8 advierte que el canal de la organización puede ser suspendido.
  Entregable: lectura escrita de los términos de servicio más una transmisión de
  prueba en un canal privado.
  Esfuerzo: 2 días / — · Depende de: nada.

- **Política de retención de datos de compradores (LOPDP).**
  El alcance §9 la deja pendiente. La fase 1 fija la forma de los datos que hará
  fácil o difícil el borrado, y por defecto la fija en la dirección difícil (una
  fila `comprador` por cartón, en una base global). Propuesta del alcance: se
  conservan mientras dure el evento y hasta 30 días después, se entrega el reporte
  a la organización y luego se eliminan.
  Esfuerzo: M / S · Depende de: nada, pero cuanto antes se decida menos cuesta.

## P1 — spikes que de-riesgan las fases 3 y 5

- **Spike de OBS y dos monitores.** Un script de 30 líneas con PySide6 que saca
  una ventana sin bordes a pantalla completa en un segundo monitor y se captura en
  OBS. Responde a la vez la política de DPI (E16) y la viabilidad de la fase 5.
  Esfuerzo: medio día / — · Depende de: nada.

- **Spike de imprenta.** Un cartón de una página hecho a mano, enviado a una
  imprenta real para cotización y prueba de impresión. Si rechazan el PDF por
  sangrado, resolución o CMYK, hay que saberlo antes de escribir el motor de
  render de la fase 3, no después.
  Esfuerzo: medio día + espera / — · Depende de: nada.

- **Spike de latencia de transmisión.** Medir el retraso real en una emisión
  privada. El alcance §6.1 dice que ese número va **impreso en el cartón**, o sea
  que es una entrada de la fase 3.
  Esfuerzo: 2 horas / — · Depende de: nada.

## P2 — durante o después de la fase 1

- **Carga de los patrones del sistema en la tabla `patron`.**
  El documento técnico dice que se cargan "en la primera ejecución". Se difiere a
  la fase 4, donde están el catálogo y el editor.
  Esfuerzo: M / S · Depende de: fase 4.

- **Verificar la API de `reportlab` 5.x.** El proyecto se pinea a `>=4.2,<6` y la
  5.0.1 es reciente. Comprobar el posicionamiento fino antes de escribir el motor
  de render.
  Esfuerzo: S / S · Depende de: inicio de la fase 3.

- **Plan de segunda máquina.** El alcance §8 acepta "equipo único" como punto de
  fallo y ninguna fase lo mitiga. Mínimo aceptable: probar que un respaldo `.zip`
  restaura en un segundo equipo y abre el evento donde quedó.
  Esfuerzo: M / S · Depende de: fase 5 (respaldos).

- **Integración continua.** `ruff` + `pytest -m "not lento"` en cada push. No hay
  repositorio remoto todavía; se crea el workflow cuando lo haya.
  Esfuerzo: S / S · Depende de: repositorio remoto.

## P3 — v2 y más allá

- **Una base de datos por evento.** Haría trivial el borrado LOPDP y la entrega a
  la organización. Contradice el `datos/bingo.db` único del documento técnico y
  complica organizaciones y patrones, que son transversales.
  Esfuerzo: L / M.

- **Cifrado del respaldo.** El `.zip` lleva datos personales de compradores.
  Esfuerzo: M / S · Depende de: fase 5.

- **Vista previa del cartón junto al formulario de organización.** Ver DG-3 en el
  informe de revisión: se difiere a la fase 3, donde nace el motor de render real.
  Esfuerzo: M / S · Depende de: fase 3.

- **Filtro en la vista de organizaciones.** En la fase 1 son quince filas; no lo
  necesita todavía. La vista de eventos sí lo lleva desde ya.
  Esfuerzo: S / S.

- **Textos de organización por idioma.** Hoy una columna por texto. Si un cliente
  quiere cartones bilingües, hará falta una migración. Se revisa en la fase 3.
  Esfuerzo: S / S · Depende de: fase 3.

- **`.pre-commit-config.yaml`.** Una dependencia más que empaquetar, para una sola
  persona. Por ahora basta la línea del README.
  Esfuerzo: S / S.

## Añadidos por la revisión de ingeniería

- **`docs/esquema-actual.sql` con prueba de instantánea.** Se difiere: mientras la
  001 sea editable (política E4e) fallaría en cada edición intencionada, que es
  como una prueba de instantánea acaba actualizándose por reflejo. Se introduce el
  día que la 001 se congela, o sea en el primer evento real. Nota técnica:
  `.schema` es un comando del cliente `sqlite3`, no de la API; hay que leer
  `sqlite_master`.
  Esfuerzo: S / S · Depende de: primer evento real.

- **Bandera `modo_vivo` para suprimir modales durante la transmisión.** Cortada de
  la fase 1 por no tener consumidor. La define la fase 5, cuando exista la interfaz
  de sorteo contra la que medirla.
  Esfuerzo: S / S · Depende de: fase 5.

- **Registro central de acciones y atajos.** En la fase 1 basta un diccionario de
  módulo. Se convierte en registro cuando haya más de una superficie manejada por
  teclado, o sea en la fase 5.
  Esfuerzo: S / S · Depende de: fase 5.

- **Fuentes personalizadas cargadas por la organización.** Decisión abierta del
  §16.3 del documento técnico: licencias y registro doble en Qt y ReportLab. La
  fase 1 empaqueta dos familias de licencia abierta y ofrece un combo cerrado.
  Esfuerzo: M / S · Depende de: fase 3.
