# ADR-0066: Asesor general en «Mi plan»

- **Estado:** aceptada
- **Fecha:** 2026-11-06
- **Decide:** Rodrigo («vamos», sobre el asesor general propuesto al analizar las decisiones
  abiertas de ADR-0063)
- **Completa:** ADR-0063 (preguntas en el plan de una oferta), ADR-0064 (conversación cifrada) y
  ADR-0065 (límite diario).

## Contexto

En la web solo se puede preguntar al asesor dentro del plan de una oferta. La pregunta que más vale
para quien empieza, «¿cuál de estas ofertas me conviene?», no tiene sitio. Las herramientas para
contestarla ya existen y son las de la terminal (`advisor/tools.ask`):
- `buscar_ofertas` ordena las ofertas con el plan del usuario;
- `ofertas_guardadas`, `valorar_oferta`, `zona_de_oferta`, `plan_completo` y
  `recomendar_alquiler`.

## Decisión

1. **Una conversación sin oferta fija, en «Mi plan» (`/perfil`).** Aparece cuando el perfil está
   confirmado: sin perfil, la búsqueda no puede ordenar nada. Vale para el particular y para el
   profesional con su cliente activo.
2. **Rutas, iguales a las de la oferta pero sin ella:**
   - `POST /plans/questions`: la pregunta, con etapas y respuesta en `text/event-stream`;
   - `GET /plans/conversation` y `DELETE /plans/conversation`.

   Las instrucciones y las herramientas son las de la terminal, más las de la conversación
   (ADR-0063, punto 3). Las cifras se vuelven a pedir en cada vuelta.
3. **Las mismas reglas que en la oferta:**
   - cuenta como una consulta del día (ADR-0065);
   - el plan completo que cuente el asesor gasta cupo del nivel gratuito (ADR-0041);
   - la búsqueda, la valoración y la zona no gastan cupo, igual que en la web.
4. **Se guarda cifrada igual que la de una oferta (ADR-0064):**
   - una por cliente, en la tabla `advisor_general_conversations`;
   - el dato asociado la ata a su organización y su cliente, con `general` donde iría la oferta;
   - mismo plazo, 30 días desde la última pregunta, y mismo borrado nocturno;
   - se borra con su cliente.

   Es otra tabla porque la oferta forma parte de la clave primaria de la otra y no puede faltar.
5. **Las ofertas que nombre el asesor** salen con su marcador `{{oferta:…}}` comprobado, como en
   la búsqueda. La web las enseña por su nombre.

## Consecuencias

- La política de privacidad (v4) y el encargo (v2) no cambian de versión. Hablan de «las preguntas
  al asesor sobre un plan» y de borrarlas «desde el plan», y esta conversación está en «Mi plan».
  Los datos, el cifrado y el plazo son los mismos. En la revisión del abogado (F8.5) conviene
  decirlo sin depender del nombre de la página: «sobre tus planes y tus ofertas».
- Las ofertas que nombra el asesor todavía no son enlaces: el marcador lleva ocho caracteres del
  identificador, no el identificador entero.
