# ADR-0063: Preguntas al asesor sobre el plan, en la web

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («vamos con ello», sobre sacar las preguntas libres de la terminal a la web)

## Contexto

El asesor ya contesta preguntas libres con las herramientas (`advisor/tools.ask`, ADR-0019), pero
solo desde la terminal y en las evaluaciones. En la web solo explica el plan en fichas (ADR-0052).
El usuario no puede preguntar «¿y si lo alquilo por habitaciones?» ni seguir la conversación.

## Decisión

1. **Una ruta por oferta:** `POST /plans/offers/{id}/questions`, con la pregunta y las vueltas
   anteriores. Responde con `text/event-stream`, igual que la explicación:
   - las etapas reales (el modelo piensa, pide una herramienta, corrige);
   - al final, la respuesta ya comprobada.

   Las comprobaciones de la explicación van antes de empezar: perfil, cliente y nivel gratuito.
   Preguntar sobre una oferta cuenta como abrir su plan.
2. **El servidor no guarda la conversación.** La conversación puede llevar datos personales (lo
   que el usuario cuenta de sí mismo):
   - vive en la memoria de la página y se pierde al recargarla;
   - la web manda las últimas vueltas en cada pregunta: hasta 6 mensajes de 2.000 caracteres;
   - la pregunta tiene como mucho 500 caracteres;
   - no se registran ni la pregunta ni la respuesta, solo el tipo de error.
3. **Cada respuesta trae sus cifras.** Las cifras de las vueltas anteriores no valen en la nueva:
   - se le dice al modelo que vuelva a pedir la herramienta;
   - el texto se comprueba con las cifras de esta vuelta (ADR-0012), como siempre;
   - las herramientas son lecturas de los motores con caché, así que repetirlas es barato.

   La web devuelve el texto de cada respuesta con sus marcadores (`text`), no las cifras ya
   formateadas: con números a la vista, el modelo los copia.
4. **Contexto de la oferta:** la pregunta llega al modelo con el marcador de la oferta y la
   indicación de usar `plan_completo` con ella. Las herramientas son las mismas que en la
   terminal: plan, alquiler, valoración, zona, búsqueda y ofertas guardadas.
5. **El cupo del nivel gratuito vale también para el asesor (ADR-0041).** Si el usuario pregunta
   por otra oferta, la herramienta `plan_completo` pregunta antes al cupo
   (`api/deps.plan_gate`):
   - una oferta ya abierta no gasta cupo;
   - una oferta nueva gasta uno y queda anotada, como si se abriera su página;
   - sin cupo, la herramienta se niega y el asesor se lo dice al usuario.

   Vale igual para la explicación en fichas.
6. **El historial es del usuario y puede intentar dar órdenes.** No abre nada:
   - la respuesta pasa la misma comprobación, sin cifras fuera de marcadores ni claves inventadas;
   - las herramientas solo leen y solo ven la organización del usuario.

## Consecuencias

- Cada pregunta es una llamada al modelo con herramientas. Con el modelo local tarda decenas de
  segundos; con una API serían unos céntimos al mes (`docs/research/f7-proveedor-llm.md`). No hay
  límite de preguntas: si hace falta, irá con el nivel de la cuenta (ADR-0041).
- Al recargar la página se pierde la conversación. Guardarla pediría cifrarla, como el perfil, y
  decidir cuánto tiempo se guarda.
