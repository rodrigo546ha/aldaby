# ADR-0064: Las conversaciones con el asesor se guardan cifradas 30 días

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («guardamos la conversación cifrada por 30 días»)
- **Sustituye:** el punto 2 de ADR-0063, que no la guardaba.

## Contexto

Con ADR-0063 la conversación vivía solo en la memoria de la página: se perdía al recargarla y el
servidor no guardaba nada. La conversación puede llevar datos personales, porque el usuario cuenta
cosas de sí mismo o de su cliente.

## Decisión

1. **Una conversación por oferta y por cliente.** Para el particular, su perfil; para el
   profesional, cada cliente (ADR-0029). Tabla `advisor_conversations`, con Row-Level Security por
   organización.
2. **Cifrada como el perfil (ADR-0011):**
   - cifrado de sobre AES-256-GCM con la clave maestra;
   - el dato asociado ata cada fila a su organización, su cliente y su oferta;
   - la base solo ve bytes cifrados;
   - ni la pregunta ni la respuesta van al registro.
3. **30 días desde la última pregunta:**
   - el plazo está en `data/conservacion.yaml`, el mismo dato que leen la política de privacidad y
     el contrato de encargo (`{{plazo_conversaciones}}`);
   - una conversación caducada no se devuelve;
   - el trabajo diario `purge_conversations` la borra.
4. **El usuario la borra cuando quiere** (`DELETE /plans/offers/{id}/conversation`). Se borra
   también con su cliente o con la oferta.
5. **El historial lo pone el servidor.** La pregunta llega sola: el servidor usa las últimas
   vueltas guardadas con una respuesta comprobada, hasta 6 mensajes. Así nadie puede colar
   respuestas del asesor que el asesor no dio. Se guardan las últimas 20 vueltas.
6. **Lo que se guarda de cada vuelta:** la pregunta, la respuesta ya comprobada (con sus cifras
   tal como salieron ese día, para enseñarla igual), el texto con marcadores para el historial y
   la fecha.
7. **Textos legales:** la política de privacidad pasa a la versión 4 y el contrato de encargo a la
   2. Las dos añaden las conversaciones, su cifrado y su plazo, así que las cuentas los vuelven a
   aceptar. Siguen sin revisar por el abogado (F8.5).

## Consecuencias

- La conversación sigue al volver al plan, también desde otro dispositivo.
- Las cifras de una respuesta guardada son las de su día. Si el plan cambia, la siguiente pregunta
  las vuelve a pedir, como siempre (ADR-0063, punto 3).
- La rotación de la clave maestra (`profiles/store.rotate`) no recorre las conversaciones: duran
  30 días y caducan antes de que una clave antigua deje de estar disponible.
