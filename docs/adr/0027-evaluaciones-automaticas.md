# ADR-0027: Evaluaciones automáticas de la extracción, del asesor y del plan

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.9

## Contexto
F6.9 pide evaluar tres cosas: la extracción de anuncios contra un juego etiquetado, que el texto
del asesor no tenga cifras inventadas y la coherencia del plan. La comprobación de ADR-0012 ya
impide que el asesor escriba un dígito fuera de un marcador, pero no impide que diga «positivo»
de un cash flow negativo. El banco del agente (F6.0) solo medía si pedía las herramientas.

## Decisión
- **Juego etiquetado de anuncios** (`data/evaluation/anuncios/`), en el repositorio:
  - doce anuncios de portal sintéticos, escritos para el juego y variados: venta y alquiler,
    superficie útil aparte, precio rebajado, precio por m², sin precio, otros inmuebles
    recomendados en la página;
  - los cuatro anuncios del BOE que ya estaban en las fixtures: tres sin lotes y uno con dos.
  Cada campo esperado tiene su valor, o una lista si el documento admite más de una lectura (una
  superficie registral y otra catastral). Se compara campo a campo: correcto, falta, distinto o
  sobra (un valor donde el documento no lo da).
- **El asesor** (`advisor/evaluation.py`): el banco de preguntas de F6.0 más búsqueda, tipo de
  alquiler y plan completo. De cada texto mostrado se mide:
  - los dígitos fuera de marcadores (cero por construcción: si no, falla la comprobación);
  - las contradicciones de sentido (`agent/sense.py`), con reglas fijas sobre la frase de
    cada marcador. Una palabra de signo («positivo», «ganas», «negativo», «pierdes») ante una
    cifra del signo contrario («te queda» no cuenta: se dice también de un cash flow
    negativo). Una comparación entre dos marcadores («supera», «por encima de», «por debajo
    de», «no llega a») que las cifras no cumplen.
  Sin modelo juez: no es determinista y también se equivoca.
- **Coherencia del plan** (`plans/coherence.py`): reglas sobre las cifras de un plan completo.
  - **Sumas:** los gastos de compra suman sus partes y el dinero aportado cuadra con el precio,
    los gastos y el préstamo.
  - **Órdenes:** la cuota en estrés es mayor o igual que la cuota, el escenario conservador queda
    por debajo del base y el optimista por encima, y la renta baja da menos cash flow.
  - **Cuadres:** el cash flow mensual cuadra con el anual y el impuesto, la primera cuota fija
    coincide con la cuota del plan y la renta queda dentro de su rango.
  - **Argumentos y pasos:** cada argumento cuadra con su cifra y los pasos de la hoja de ruta,
    con el canal y la hipoteca.
  Se ejecuta en los tests y en cada plan. Si una regla falla en un plan real, el plan lo avisa
  entre sus notas.
- **Sin umbrales inventados.** Lo que no depende del modelo tiene que dar cero fallos:
  - los dígitos fuera de marcadores;
  - la coherencia;
  - la puntuación de la extracción con respuestas perfectas (los tests, con el cliente falso).
  Lo que depende del modelo (aciertos por campo, textos mostrados, contradicciones) se compara
  con la última línea base guardada (`data/evaluation/linea_base.json`) y se avisa si empeora.
  `python -m housefinder.evaluations` las ejecuta con el modelo de `.env` y
  `--guardar-base` guarda la nueva línea base.

## Opciones consideradas
- **Anuncios reales de portales:** no se pueden guardar en el repositorio (regla 3). Los que pegue
  Rodrigo podrán ir a `tests/fixtures/private/` más adelante.
- **Descargar más anuncios del BOE:** queda para cuando haya que ampliar el juego.
- **Umbrales fijos de aciertos:** no hay datos para elegirlos.

## Consecuencias
- Una evaluación completa con el modelo local tarda varios minutos (dieciséis extracciones y
  ocho preguntas).
- Las reglas de sentido solo ven contradicciones explícitas. El significado del resto del texto
  se sigue leyendo a mano en el informe.
- La primera pasada (2026-10-31) destapó que el modelo escribía «value» en el valor de la
  extracción y dejaba la cifra en la cita: se acepta el único número de la cita en ese caso, que
  sigue saliendo del documento (`agent/extraction.py`, `docs/research/f6-9-evaluaciones.md`).
