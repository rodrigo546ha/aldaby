# ADR-0009: Geocodificación con CartoCiudad y caché en PostgreSQL

**Estado:** Aceptada (F3.6, G4) · **Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
`GET /territory` tiene que pasar de una dirección a su sección censal (F3.6). Hace falta un
geocodificador: dirección → coordenadas. La regla 3 de `CLAUDE.md` exige fuentes públicas y
propias, sin proveedores comerciales de datos.

CartoCiudad (IGN, CNIG y Correos) publica un geocodificador gratuito:
`https://www.cartociudad.es/geocoder/api/geocoder/find?q=…` devuelve el mejor candidato con
longitud, latitud, tipo de resultado (`portal`, `callejero`, `Municipio`, `codpost`…), código INE
del municipio y, en portales, la referencia catastral. El campo `state` ya no informa de la calidad
del resultado (vale siempre 0).

Condiciones (FAQ de CartoCiudad, consultada el 2026-10-29): «El acceso y uso de los servicios web de
CartoCiudad son gratuitos en cualquier caso», mencionando la autoría como «CC BY 4.0
www.scne.es/productos.html#CartoCiudad».

## Decisión
- **Geocodificador:** CartoCiudad, método `find`, desde `housefinder/geo/` (el único módulo, con la
  ingesta, que puede llamar a la red con httpx).
- **Precisión aceptada:** `portal` (número de la calle) sin aviso; `callejero` (calle sin número)
  con aviso, porque el punto cae en el eje de la calle y puede quedar en la frontera entre dos
  secciones. Cualquier otro tipo (municipio, población, código postal, topónimo) se rechaza: no
  basta para elegir una sección.
- **Caché:** tabla `geocode_cache` con la consulta normalizada (minúsculas, espacios simples), el
  resultado y la fecha. Se reutiliza durante un año; después se vuelve a consultar. Así se evita
  repetir llamadas al servicio público y la respuesta es estable entre peticiones.
- **Qué sale hacia CartoCiudad:** solo el texto de la dirección del inmueble. Nunca el usuario, su
  perfil ni otros datos. Las direcciones no se escriben en logs.
- **Atribución:** una fila en `sources` (`cartociudad-geocoder`) con la licencia, y la cita en cada
  respuesta de `/territory` que haya geocodificado.
- `/territory` acepta también `lon` y `lat` para no geocodificar cuando ya hay coordenadas (por
  ejemplo, ofertas del BOE con su punto).

## Opciones consideradas
- **Nominatim (OpenStreetMap):** público, pero su política de uso limita a una petición por segundo
  y pide no usarlo como servicio de producción sin instancia propia. Descartado para empezar.
- **Google, HERE u otros comerciales:** contra la regla 3. Descartados.
- **Catastro (consulta por dirección):** útil para la referencia catastral y el valor, pero no es un
  geocodificador general. Queda para el enriquecimiento del inmueble (F5).
- **Sin caché:** más simple, pero cada consulta repetida vuelve a salir hacia un tercero. Descartado.

## Consecuencias
- Si CartoCiudad no responde, `/territory` con dirección responde 503; con coordenadas sigue
  funcionando.
- Una dirección mal escrita puede geocodificar a otro portal: la respuesta devuelve la dirección
  encontrada para que el usuario la confirme.
- Al ser datos de 2018 en parte (según la propia FAQ), puede haber portales nuevos sin geocodificar.
