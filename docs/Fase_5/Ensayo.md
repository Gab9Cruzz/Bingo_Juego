# Ensayo completo — guion (tarea 4.16, hallazgo V9)

Criterio de aceptación del contrato, no un extra. Sin este ensayo corrido de
principio a fin, con hardware real y Gabriel presentando de verdad, la fase
no se cierra — es la única forma de probar en conjunto lo que cada tarea
probó por separado: que el sorteo, la transmisión, el respaldo y el
operador aguantan una noche real.

Este documento es un guion para **ejecutar a mano**, no algo que corre con
`pytest`. Cada sección tiene una casilla `[ ]` para marcar al hacerlo, y
dice qué evidencia queda de haberlo hecho.

## 0. Antes de empezar

- [ ] `python -m bingo --ensayo` corrido una vez sobre un `BINGO_HOME` limpio
  (o el real, es idempotente: no duplica nada si ya existe). Deja
  "Bingo de ensayo" con 200 cartones vendidos y tres rondas con patrones
  distintos (tarea 4.17).
- [ ] Dos monitores conectados. Uno para el operador (esta app), otro para
  la ventana de transmisión en pantalla completa (decisión D14).
- [ ] OBS Studio instalado, con una fuente de "Captura de ventana" (método
  Windows 10, WGC) apuntando a la ventana de transmisión — **nunca**
  "Captura de pantalla completa" del segundo monitor, y nunca "Captura de
  juego": las dos fallan en negro con aceleración por hardware en algunos
  equipos (riesgo documentado en el plan de la fase 5).
- [ ] Un canal de prueba en Facebook (transmisión **privada** o no listada)
  y uno en YouTube (**no listado**), configurados en OBS como dos destinos
  de la misma transmisión (o dos pasadas del ensayo, una por plataforma).
  **Nunca pública**: es un ensayo con datos de prueba, no un evento real.
- [ ] Un teléfono celular a mano, con la app de Facebook o YouTube abierta
  para ver la transmisión privada desde ahí (hallazgo V8).
- [ ] Un cronómetro (el del celular sirve) para medir el retraso de la
  plataforma.
- [ ] El runbook (`docs/runbook.md`) impreso o abierto en un tercer
  dispositivo — el ensayo también prueba que una segunda persona podría
  seguirlo sin ayuda.
- [ ] **Gabriel es quien presenta**, no solo quien opera. Nadie más lee el
  guion por él durante el ensayo: el objetivo es probar si una sola persona
  aguanta presentar, operar, vigilar WhatsApp, validar códigos y decidir
  empates a la vez (el punto de fallo humano que el plan señala como el
  peor mitigado del proyecto).

## 1. Arranque y transmisión

1. [ ] Abrir "Bingo de ensayo" (el evento que dejó `--ensayo`).
2. [ ] Ir a la sección Sorteo, elegir la primera ronda, pulsar
   "Mostrar transmisión" — confirmar que aparece en el monitor/pantalla
   correctos (decisión DU-17/V7: si Windows reordenó los monitores, la app
   pregunta en vez de adivinar).
3. [ ] Empezar a transmitir desde OBS a los dos canales de prueba.
4. [ ] **Medir el retraso de la plataforma:** con el cronómetro, marcar el
   instante en que la pantalla de transmisión muestra un número nuevo (o el
   reloj, si el tema lo trae) y el instante en que ese mismo número aparece
   en el celular viendo la transmisión. Repetir 3 veces y anotar el
   promedio.

   **Retraso medido: _____ segundos** (rellenar a mano).

5. [ ] Con ese número, actualizar
   `impresion/plantilla.py::TEXTO_INFERIOR_DEFECTO` para que diga la cifra
   real en vez de "que tiene retraso" sin más — el alcance §6.1 exige que
   el cartón impreso lo diga. Confirmar con Gabriel el texto final antes de
   cambiarlo (afecta a cartones ya diseñados).

## 2. Legibilidad en celular (hallazgo V8)

1. [ ] Con la transmisión corriendo y una bola en pantalla, mirar el
   celular (no el monitor) y confirmar que el número actual se lee sin
   acercar la pantalla ni forzar la vista.
2. [ ] En el editor de Tema, confirmar que el bloque `numero_actual` tiene
   una escala tal que su alto ocupa **al menos el 14% del lienzo**
   (`dominio.tema.ALTO_MINIMO_NUMERO_ACTUAL_FRAC` — si se reduce por
   debajo, `validar()` lo rechaza al guardar; el ensayo es la comprobación
   humana de que ese mínimo es realista, no solo que existe).
3. [ ] **Adjuntar una captura de pantalla del celular** viendo la emisión
   privada con un número visible, como evidencia de que se hizo esta
   comprobación. Guardarla junto a este documento o en el reporte del
   ensayo (`docs/Fase_5/evidencia/`, crear la carpeta si no existe).

## 3. Tres rondas de principio a fin

1. [ ] Ronda 1: iniciar, extraer bolas (manual o automático), hasta que
   salga un ganador. Confirmar que el ¡BINGO! grande con código y nombre
   **nunca** aparece antes de que Gabriel confirme el reclamo (D8/DU-3 —
   antes de `GANADOR_CONFIRMADO` la transmisión solo dice "hay un cartón
   ganador", sin datos).
2. [ ] Probar la cuenta regresiva de reclamo (tarea 4.24): dejar que se
   agote sin reclamar y observar qué hace según `sin_reclamo` esté en
   "continuar" (la transmisión avisa "reclamo vencido" 5 s y sigue sola) o
   "cerrar" (la ronda se cierra sola). Probar **las dos** configuraciones
   al menos una vez cada una durante el ensayo, no solo la que quede
   configurada para el evento real.
3. [ ] Registrar un reclamo real por el canal configurado
   (`tema_json.juego.canal_reclamo`) y confirmar el ganador desde la app.
4. [ ] Ronda 2, con un patrón distinto: repetir sin el detalle de reclamo,
   solo para confirmar que el selector de rondas cambia de patrón/premio
   correctamente en pantalla.
5. [ ] Ronda 3, con un tercer patrón: dejar el bombo agotarse sin ganador
   (hallazgo C7) y confirmar que cerrar no pide confirmación en ese caso
   (si quedaran bolas sin agotar, sí la pediría).

## 4. Cierre forzado a mitad de ronda + segundo equipo

Esta es la prueba que de verdad simula "el equipo del operador se cae a
mitad de la noche" — el escenario que toda la arquitectura de reanudación
(D13) y de respaldo (4.12) existe para sobrevivir.

1. [ ] A mitad de una ronda (con algunas bolas ya extraídas, ronda
   `en_curso`), generar un respaldo manual ("Generar respaldo ahora",
   tarea 4.13) y anotar dónde quedó el `.zip`.
2. [ ] **Matar el proceso** de la aplicación (Administrador de tareas,
   "Finalizar tarea" — no cerrar la ventana con normalidad: el objetivo es
   simular un corte real, no un apagado limpio).
3. [ ] Copiar ese `.zip` a un **segundo equipo limpio** (sin este
   `BINGO_HOME`, idealmente sin este repositorio).
4. [ ] En el segundo equipo: `python -m bingo --restaurar <zip>` (o el
   botón "Restaurar desde respaldo…" de Ajustes, con la app cerrada).
5. [ ] Confirmar que el evento aparece con la ronda que estaba `en_curso` o
   `pausada` en el mismo estado, y que el sorteo **continúa en la bola
   N+1** — la bola siguiente a la última extraída antes del corte, nunca
   repitiendo ni saltando una.
6. [ ] En el equipo original (o el mismo, tras el corte simulado): cerrar
   la ronda que quedó a medias, y ejercer la transición `cerrada ->
   en_curso` reabriéndola (hallazgo V5) — el caso de "evento suspendido y
   retomado otro día" que el alcance §6.6 promete.

## 5. Cierre del evento

1. [ ] Cerrar todas las rondas restantes.
2. [ ] "Finalizar evento" (tarea 4.13): confirmar que solo se habilita con
   **todas** las rondas cerradas, y aceptar las ofertas de generar el
   reporte del evento y un respaldo final.
3. [ ] Abrir el reporte generado y confirmar que las rondas y ganadores
   coinciden con lo que pasó en el ensayo.
4. [ ] Detener la transmisión en OBS. Confirmar que la pantalla pasó a
   "Cierre" (con el texto configurable de `tema_json.pantalla_cierre`)
   antes de cortar.

## 6. Al terminar

- [ ] Guardar el `.zip` del respaldo final del ensayo aparte (no lo borra
  nada automáticamente, pero conviene no confundirlo con uno de un evento
  real más adelante).
- [ ] Si el retraso medido en el paso 1 cambió `TEXTO_INFERIOR_DEFECTO`,
  confirmar que las pruebas automáticas (`pytest`) siguen en verde con el
  texto nuevo.
- [ ] Anotar en este archivo (o en un documento aparte enlazado desde
  aquí) cualquier paso que haya fallado, sorprendido, o tomado más tiempo
  del esperado — es la entrada real para decidir si la fase está lista
  para un evento real o si hace falta un segundo ensayo.
