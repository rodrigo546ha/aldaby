# ADR-0038: Cartera de las agencias por su feed XML (formato Kyero v3), con su permiso

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo («Sí, los canales», tras
`docs/research/fuentes-utilizables.md`)

## Contexto
Casi toda la oferta de pisos la publican agencias desde un CRM. Ningún portal deja reutilizar sus
anuncios, pero la agencia es dueña de su cartera y puede cedérnosla. Los CRM la exportan en un feed
XML con el formato de Kyero (v3.9.1, de enero de 2026). Witei lo documenta como un enlace que la
agencia copia y comparte «with your external website or portal» (comprobado el 2026-11-02).

Lo que fija la especificación de Kyero, leída el 2026-11-02:
- Una URL contiene la cartera de una sola agencia y puede llevar usuario y contraseña.
- Es una foto completa: lo que falta, se ha retirado.
- `<id>` es estable y `<date>` cambia cuando cambia el inmueble.
- Lleva precio, `price_freq` (`sale` o `month`), tipo, población, provincia y, opcionales, la
  coordenada, la referencia catastral (`<catastral>`), la superficie construida, la descripción
  por idioma, las fotos y contactos (`email`, `contact_number`, `whatsapp_number`).

La especificación es de Kyero («Copyright © 2026, Kyero.com»). Se usa como referencia para leer
el formato, no se copia al repositorio. Se le pregunta a Kyero por correo.

## Decisión
1. **Solo con consentimiento escrito de la agencia.** El alta de un feed exige:
   - la organización cliente a la que pertenece;
   - el nombre de la agencia;
   - la fecha del consentimiento y una referencia al documento firmado (contrato de alta, F7);
   - el **alcance**: `organizacion` (solo la ven los usuarios de esa organización) o `todos`
     (todos los usuarios de Aldaby).

   Lo da de alta el profesional en la página «Agencias», marcando que tiene ese consentimiento
   por escrito, o el administrador por la línea de órdenes (`python -m housefinder.feeds alta`).
   Al darlo de baja se retiran sus ofertas: las de su organización en el momento; las cedidas a
   todos, en el siguiente trabajo diario (la API no puede tocar ofertas públicas).
2. **La URL se guarda cifrada** con el cifrado de sobre (ADR-0011), atada a su fila, porque puede
   llevar credenciales o un token. Nunca sale en logs ni en informes.
3. **Canal `feed_agencia`**, un `sources` por feed (`feed-agencia-<id>`) con la agencia y el
   consentimiento. Cada día:
   - se mira el `robots.txt` del servidor del feed y se respeta;
   - se descarga entero, con un tope de 50 MB;
   - cada inmueble en venta (`price_freq = sale`, en euros) es una oferta `anuncio` con
     `extraction_status = 'no_aplica'`. Sus datos los da la propia agencia: no pasa por el LLM;
   - `org_id` es la organización del feed si el alcance es `organizacion`, y nulo si es `todos`.
4. **Qué se guarda de cada inmueble:**
   - precio (`asking_price`), superficie construida, referencia catastral si tiene 20 caracteres,
     población y provincia, coordenada si la trae, descripción en español (o la primera que
     haya), enlace a la ficha de la agencia y tipo;
   - el tipo se traduce al de la extracción (`vivienda`, `local`, `garaje`, `suelo`…) por
     palabras clave, y lo que no se reconoce queda `otro`;
   - **no se guardan** el correo ni los teléfonos de contacto (pueden ser de una persona) **ni las
     URL de las fotos**: los derechos de las fotos quedan para la consulta legal (F0.6). Se guarda
     cuántas hay;
   - los alquileres (`month`) y los precios en otra moneda no se guardan: se cuentan en el
     informe. No se convierte moneda.
5. **Foto completa:**
   - una oferta de ese feed que ya no viene pasa a `retirada` y se desliga de su inmueble;
   - si vuelve, se reactiva;
   - si cambia, se actualizan precio, superficie, referencia y descripción, y se vuelve a ubicar
     si cambió la referencia catastral o la coordenada.
6. **Ubicación:** la coordenada del feed si la trae. Si no, la referencia catastral (Catastro). Si
   tampoco, el inmueble queda sin ubicar: el feed no trae calle y una población no basta para
   valorar.
7. **Búsqueda inversa:** estas ofertas entran como candidatas para quien las puede ver, igual que
   los lotes del BOE. Lo que cobre la agencia o Aldaby no entra en el orden (regla de oro 7).

## Opciones consideradas
- **Pedir la API de cada CRM:** depende de un acuerdo con cada uno. El feed lo controla la agencia
  y sirve para muchos CRM a la vez. Se queda la API para los CRM que no exporten Kyero.
- **Guardar las fotos:** mejoraría la ficha, pero los derechos son del fotógrafo o de la agencia,
  y la cesión debe ser expresa. Pendiente de F0.6.
- **Ubicar por población:** no da una sección censal fiable. Descartado.

## Consecuencias
- La cobertura crece con los clientes profesionales, no de golpe.
- Algunos feeds no traerán coordenada ni referencia catastral. Sus inmuebles se guardan pero no
  entran en la búsqueda hasta que la agencia complete esos datos en su CRM. El informe del trabajo
  los cuenta para poder pedírselo.
- Si el CRM bloquea el feed en su `robots.txt`, se le pide a la agencia otra URL o al CRM una
  excepción.
