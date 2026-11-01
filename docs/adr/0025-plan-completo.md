# ADR-0025: Plan completo de una oferta

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.7

## Contexto
F6.7 pide el plan completo: capacidad, hipoteca, cash flow, estrés, escenarios legales,
argumentos para no comprar y hoja de ruta de compra. Es la sección 4 y 5 de la plantilla del
plan manual de F0 (`docs/templates/plan-manual.md`). Las piezas ya existen: el simulador (D4),
la valoración (F5), los supuestos de fuentes públicas (ADR-0022), la búsqueda (ADR-0023), el
tipo de alquiler y la gestión (ADR-0024) y los escenarios normativos (F2.5).

## Decisión
- **Un plan por oferta y perfil, calculado al abrirlo** (`plans/service.py`): no se guarda. Sale
  del mismo camino que la búsqueda (las entradas se preparan con la misma función) y añade:
  - **Fija frente a variable** (`compare_mortgages`, F1.6). La fija, al tipo de mercado de más de
    diez años (ADR-0022). La variable, con el primer año al TEDR de las hipotecas con fijación de
    hasta un año (Banco de España, ya cargado) y después Euríbor más un diferencial estimado =
    ese TEDR − Euríbor a un año oficial, los dos del mes del ancla del Euríbor de los parámetros
    (ADR-0006). Es una estimación con datos públicos (`provisional`), no la oferta de un banco.
  - **Estrés:** la cuota con la subida de tipos, el plazo recomendado, el cash flow con la subida
    de tipos en el escenario de su riesgo (ADR-0023) y el cash flow con la renta baja de la zona.
  - **Escenarios normativos:** el plan con y sin las reglas pendientes (`compare_with_pending`),
    con las cifras que cambian, y lo que cambia en cada tipo de alquiler (ADR-0024).
  - **Tipo de alquiler y gestión** (ADR-0024) y si encaja con sus restricciones (ADR-0023).
- **Argumentos para no comprar:**
  - **Reglas fijas** (`planning/arguments.py`, puro): comparaciones con las cifras del plan, sin
    umbrales inventados. Precio por encima de su capacidad, ahorro insuficiente, cash flow
    negativo o por debajo de su mínimo, negativo con la subida de tipos o con la renta baja de la
    zona, ningún plazo sostenible en estrés, TIR por debajo del tipo de la hipoteca, piden más
    que lo alto del rango estimado, normas pendientes que bajan el cash flow, subasta, y cifras
    provisionales. Cada argumento lleva las cifras en que se basa.
  - **Del asesor:** el modelo puede añadir hasta tres argumentos cualitativos
    (`agent/plan_arguments.py`, salida estructurada). Van sin números (se comprueban con
    ADR-0012 y se descartan los que llevan dígitos) y la web los marca como suyos, no
    calculados.
- **Hoja de ruta como datos** (`data/plan/hoja_de_ruta.yaml`): cada paso con su descripción, su
  fuente oficial y cuándo aplica (anuncio o subasta, con o sin hipoteca, tipo de alquiler). Los
  plazos legales, si los hay, van en el texto del dato con su fuente. Ningún paso está
  verificado hasta que Rodrigo lea su fuente (`verified: false`), como las reglas. Si la fuente
  no fija el plazo con seguridad, el paso no lo da.
- **El asesor explica el plan con un botón** (`POST /plans/offers/{id}/explanation`): el agente
  usa la herramienta `plan_completo` y escribe con marcadores (ADR-0012). Después llega la
  llamada de los argumentos propios. Tarda: no se pide al abrir la página.
- **Web:** `/plan/[oferta]`, enlazada desde cada oferta de `/busqueda`, con una sección por
  apartado de la plantilla de F0. El plan servirá de base al PDF de F6.8.

## Opciones consideradas
- **Guardar una foto cifrada de cada plan:** útil para el histórico, pero de momento no se usa.
  Se decidirá con el PDF (F6.8) o con la beta.
- **Diferencial de la variable de un banco concreto:** sería un proveedor comercial. Se usa la
  media nacional publicada.
- **Hoja de ruta en el código:** contradice la regla 2 en los plazos legales.
- **Que el asesor redacte la hoja de ruta:** podría inventar plazos.

## Consecuencias
- Abrir un plan cuesta unas seis simulaciones (base, estrés, pendientes, tipos de alquiler). La
  explicación del asesor tarda unos treinta segundos con el modelo local.
- Los argumentos del asesor no se pueden comprobar: se ven aparte y con su origen.
