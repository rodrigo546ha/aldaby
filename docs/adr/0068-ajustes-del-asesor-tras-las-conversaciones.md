# ADR-0068: Ajustes del asesor tras las evaluaciones de conversación

- **Estado:** aceptada
- **Fecha:** 2026-11-07
- **Decide:** Rodrigo («Sí, ajústalas», sobre los dos fallos que destapó ADR-0067)
- **Completa:** ADR-0019 (herramientas del asesor), ADR-0063, ADR-0066 y ADR-0067.

## Contexto

La primera pasada de las conversaciones en `make evaluar` (ADR-0067, línea base del 2026-11-06)
dejó dos fallos:

1. **«¿Y con la hipoteca variable?»** no citaba ninguna cifra de la variable. `plan_completo`
   solo le daba de la variable los intereses de toda la vida del préstamo; la cuota del plan
   (`mortgage.monthly_payment`) y la de estrés son de la fija. Para hablar de la cuota, el modelo
   tiraba de las de la fija, que es el fallo que se vio en la web.
2. **«¿Y está cara?»**, después de preguntar por la zona de una oferta, no pedía `valorar_oferta`
   y le pedía al usuario que lo confirmara. `valorar_oferta` y `zona_de_oferta` exigían el
   `oferta_id` largo de `ofertas_guardadas`. En el historial solo quedan los marcadores cortos
   (`{{oferta:…}}` y el prefijo `oferta_…` de las cifras), así que para seguir con la misma
   oferta tenía que volver a listar las ofertas. No lo hacía.

## Decisión

1. **`plan_completo` da también la primera cuota y la cuota máxima en estrés de las dos
   hipotecas** (`mortgage_comparison.{fija,variable}.first_payment` y `.stressed_max_payment`).
   Son cifras que ya calcula el plan (`mortgage.compare`), con su descripción en el glosario.
2. **Instrucción:** la cuota, la cuota en estrés y el préstamo del plan son de la hipoteca fija.
   Si el usuario pregunta por la variable, se citan las de `mortgage_comparison.variable`.
3. **`valorar_oferta` y `zona_de_oferta` aceptan el marcador corto** (los ocho caracteres) o el
   `oferta_id` largo, como ya hacían `plan_completo` y `recomendar_alquiler`. El marcador se
   resuelve solo entre las ofertas de la organización. Si no hay ninguna o hay más de una, la
   herramienta lo dice. La descripción del argumento sigue mandando primero a
   `ofertas_guardadas`. En la prueba, con una descripción que ponía las dos opciones al mismo
   nivel, el modelo, ante un error de argumento, dejaba de buscar la oferta y le pedía el
   identificador al usuario.
4. **Instrucción de conversación:** si la pregunta sigue sobre la oferta de la vuelta anterior,
   se usan los ocho caracteres de su marcador y no se pregunta cuál es.
5. **Instrucción de valoración:** si pregunta si una oferta está cara o cuánto vale, se pide
   `valorar_oferta` directamente. Si falta confirmar o ubicar la oferta, lo dice la herramienta.
   Antes la instrucción decía «si está confirmada y ubicada», y el modelo, que no lo sabe, se lo
   preguntaba al usuario.
6. **La vuelta de la variable en la evaluación** acepta cualquiera de las tres cifras de la
   variable: intereses esperados, primera cuota o cuota máxima en estrés.

## Consecuencias

- `plan_completo` le pasa cuatro cifras más al modelo. El contexto del modelo local es corto,
  pero son cifras con descripción corta.
- La evaluación no puede comprobar que el texto atribuya cada cifra a la hipoteca correcta. Solo
  comprueba que cite una de la variable (ADR-0067).
- **Resultado con qwen3-14b** (2026-11-07): herramientas de 6/7 a 7/7 y cifra pedida de 2/3 a
  3/3. En «¿Y está cara?» ya se pide `valorar_oferta`, pero el modelo inventa claves de
  valoración (`valoracion.precio_estimado`) y la comprobación rechaza el texto. No se muestra
  ninguna cifra mala, pero tampoco hay respuesta: misma oferta sigue en 0/1. «A la primera»
  baila entre pasadas con el servidor cargado (4/7 y 1/7).
- En la línea base solo se suben herramientas (7) y cifra pedida (3). Lo demás no se baja. La
  fecha de la línea base sigue siendo la de la última pasada completa.
