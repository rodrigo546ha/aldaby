# ADR-0052: El asesor explica el plan en fichas y cuenta lo que hace mientras espera

**Estado:** Aceptada · **Fecha:** 2026-11-04 · **Decide:** Rodrigo («Sí, sigue con U7»,
docs/PROPUESTA_UX.md §6)

## Contexto
La explicación del plan (`POST /plans/offers/{id}/explanation`) devuelve un párrafo con marcadores de
cifra (ADR-0012) que la web pinta de corrido: no se puede escanear. Además el usuario espera unos treinta
segundos ante un botón sin saber qué pasa. La propuesta pide fichas («lo importante», riesgos y siguiente
paso) y texto que entre por streaming.

El texto del modelo no se puede enseñar mientras se escribe: se comprueba entero antes de mostrarlo
(ADR-0012, ADR-0019) y nunca se muestra uno rechazado. Un streaming de tokens enseñaría texto sin
comprobar, o cifras escritas a mano que luego se retiran.

## Decisión
1. **Salida estructurada en el bucle del agente.** `run_agent` acepta un modelo Pydantic de salida. Con
   él, la respuesta final del modelo tiene que ser un objeto JSON con ese esquema. El bucle lo valida y
   comprueba cada texto con `check_text`; un fallo vuelve al modelo con el campo que falla y gasta el
   mismo reintento que hoy. Sin modelo de salida, el bucle se comporta como hasta ahora (preguntas
   libres, banco del asesor).
2. **Esquema de la explicación del plan:** `resumen` (una frase), `claves` (de una a tres fichas con
   `titulo`, `texto` y `cifra`, la cifra que la resume escrita como marcador), `riesgos` (hasta tres) y
   `siguiente_paso`. El modelo sigue sin escribir números: todo número va en un marcador y la web lo
   formatea. Los títulos tampoco llevan cifras.
3. **Progreso real en vez de streaming de tokens.** La misma ruta responde con `text/event-stream`: un
   evento por cada cosa que de verdad ocurre (el modelo piensa, pide una herramienta, se le devuelve un
   texto para corregir, se piden los argumentos) y al final el resultado entero, ya comprobado. La web
   pinta esas etapas sobre un esqueleto con la forma de las fichas. Los errores de antes de empezar
   (sin perfil, plan no disponible, nivel gratuito) siguen siendo respuestas HTTP normales.
4. **En la web:** la frase de resumen, las fichas con su cifra como chip (al tocarlo se abre el tema
   del plan que la contiene), los riesgos y el siguiente paso con un enlace a los pasos para comprar.
   Los argumentos del asesor que no salen de las cifras van plegados con su aviso. Un fallo del modelo
   se queda en una línea.

## Alternativas descartadas
- **Streaming de tokens:** incompatible con comprobar el texto antes de enseñarlo.
- **Una segunda llamada con `response_format` tras las herramientas:** duplica el tiempo de espera, y
  `response_format` junto con herramientas no lo admiten igual todos los servidores (ADR-0014).
- **Fichas fijas sacadas del código sin modelo:** ya existe la parte fija (veredicto y cifras del plan);
  lo que aporta el asesor es elegir y explicar lo importante para este usuario.

## Consecuencias
- Detrás de Caddy y del proxy de Next, la respuesta va con `Cache-Control: no-cache, no-transform` y
  `X-Accel-Buffering: no` para que nadie la acumule ni la comprima.
- El JSON pide algo más al modelo. Si lo escribe mal, el reintento le dice qué campo falla; si vuelve a
  fallar, la web dice en una línea que el asesor no ha podido explicar el plan y quedan las cifras.
