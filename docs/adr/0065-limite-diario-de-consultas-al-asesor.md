# ADR-0065: Límite diario de consultas al asesor

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («seguimos», sobre el límite de preguntas propuesto tras ADR-0063). Las
  cifras del límite son **PROVISIONALES** hasta que él las confirme.
- **Completa:** ADR-0063 («no hay límite de preguntas: si hace falta, irá con el nivel de la
  cuenta») y ADR-0041 (niveles de los particulares).

## Contexto

Con ADR-0063 cada pregunta al asesor y cada «Explícame el plan» es una llamada al modelo con
herramientas. En la beta el modelo corre en un solo servidor propio (ADR-0040): unos dos minutos de
GPU por respuesta. Con una API serían céntimos por respuesta. Nada impide hoy que una cuenta, o un
script con su sesión, mande cientos de preguntas al día. Eso deja sin asesor al resto de usuarios o
sube la factura.

El cupo del nivel gratuito (ADR-0041) limita las ofertas con plan completo, no las preguntas sobre
ellas.

## Decisión

1. **Una consulta es una llamada al modelo desde la web:**
   - una pregunta (`POST /plans/offers/{id}/questions`);
   - una explicación del plan (`POST /plans/offers/{id}/explanation`).

   La terminal y las evaluaciones no cuentan: no las usan los clientes.
2. **El límite es por organización y por día natural de Madrid.** Para un particular es su cuenta.
   Para un profesional lo comparten sus usuarios, como comparten clientes.
3. **Las cifras son datos** y están en `data/niveles.yaml`, marcadas PROVISIONAL:
   - nivel gratuito de los particulares: 20 consultas al día;
   - profesionales: 200 consultas al día.

   Los profesionales siguen sin límite de planes (ADR-0041). Este límite solo protege el servidor
   del modelo. El pase de compra (F8.3) tendrá el suyo.
4. **Se cuenta al empezar, antes de llamar al modelo:**
   - también cuenta si la respuesta falla, porque el modelo ya ha trabajado;
   - la cuenta y la comprobación son una sola sentencia en la base, así que dos peticiones a la
     vez no pueden pasarse del límite;
   - una petición que no llega al modelo (sin perfil, sin cupo de planes) no cuenta.
5. **Al pasarse**, la API responde 429 con un mensaje que dice el límite y que mañana se puede
   seguir. El plan y sus cifras siguen a la vista. La conversación guardada (ADR-0064) devuelve las
   consultas que quedan hoy, y la web las enseña cuando quedan pocas.
6. **El contador no guarda datos personales:** organización, día y número, en `advisor_uses` con
   Row-Level Security. Ni la pregunta ni la oferta. El trabajo nocturno que borra las
   conversaciones caducadas borra también los contadores de días anteriores.

## Opciones consideradas

- **Límite por minuto (rate limit) en el proxy:** frena ráfagas, pero no a quien pregunta despacio
  todo el día. Además, Caddy no sabe de organizaciones. Se puede añadir más adelante.
- **Contar solo las preguntas:** la explicación cuesta lo mismo al modelo y se puede repetir con un
  botón.
- **Contar las respuestas buenas:** quien manda preguntas que hacen fallar al modelo no gastaría
  nada.

## Consecuencias

- Los números son una estimación de uso normal, no un dato medido. Hay que revisarlos con el uso
  real de la beta (F7.6, F9.1).
- Con un modelo por API, el límite también acota el coste por cuenta.
