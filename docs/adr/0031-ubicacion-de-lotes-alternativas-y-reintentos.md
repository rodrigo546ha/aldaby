# ADR-0031: Ubicación de lotes: polígono y parcela, reintentos y zona según las secciones

**Estado:** Aceptada · **Fecha:** 2026-11-01 · **Decide:** Rodrigo (pide alternativas a las fuentes
que fallan y datos coherentes y precisos en cualquier región)

## Contexto
El 2026-10-30 y el 31, `extract_offers` falló entero (trabajos 10 y 15) por un lote del anuncio
BOE-B-2026-34360: «parcela 14, polígono 501. Municipio: Sahagún (León), secano, paraje: "Camino de
Galleguillos"». CartoCiudad respondía un 500 y el error subía hasta el trabajo; cada reintento
repetía la extracción con el LLM. Comprobado el 2026-11-01 con peticiones reales:

- **El 500 no es transitorio.** El servidor de CartoCiudad lee la consulta como JSON y falla
  («A JSONObject text must begin with '{'») si lleva comillas dobles o una barra invertida. La
  misma consulta sin comillas devuelve 204 (no encontrada). Con `{}`, comillas simples, «» o “”
  responde bien.
- **CartoCiudad no sirve para fincas rústicas**: no tienen calle ni portal.
- **El Catastro sí**: `Consulta_DNPPP` (servicio de callejero, datos no protegidos, mismo host y
  condiciones que `Consulta_CPMRC`, ADR-0016) da la referencia de la parcela a partir de provincia,
  municipio, polígono y parcela. Acepta los nombres con o sin tildes y en cualquier caja; la
  provincia es obligatoria. Para Sahagún, polígono 501, parcela 14, devuelve `24142A50100014`, y
  `Consulta_CPMRC` con esa referencia da su centroide (-5.0542, 42.3053).
- `robots.txt`: `ovc.catastro.meh.es` no tiene (404); el de `www.cartociudad.es` redirige al
  portal (sin reglas). Ninguno prohíbe estas consultas.

## Decisión
1. **CartoCiudad sin `"` ni `\`.** `geocode` quita esos caracteres de la consulta (la clave de la
   caché no cambia).
2. **Polígono y parcela del Catastro** como tercera vía del localizador, entre la referencia
   catastral y la dirección: si el texto de la dirección dice «polígono N» y «parcela M» y la
   oferta dice su provincia (campo propio o entre paréntesis tras el municipio), se pide la
   referencia a `Consulta_DNPPP` y se ubica con `Consulta_CPMRC` y su caché, como en ADR-0016.
   Las mismas comprobaciones: el punto en una sección cargada y la dirección catastral en el
   municipio de la oferta.
3. **Un fallo de un servicio no tumba el trabajo.** Si CartoCiudad o el Catastro no responden
   (error HTTP, red, respuesta que no es JSON), la oferta se queda sin ubicar y se sigue con la
   siguiente vía y con el resto del lote.
4. **El motivo se guarda en la oferta** (`offers.location_issue`, migración 0018) junto con si
   merece otro intento (`location_retry`): sí si un servicio falló, si la oferta es de una
   provincia sin secciones cargadas o si su punto cae fuera de ellas (se ubicará cuando se
   carguen; la consulta queda en la caché y el reintento no pide nada fuera); no si ninguna vía la
   encuentra. Al ubicarla, se borra. El informe de `extract_offers` lo lista en `unlocated`.
5. **Reintento sin LLM.** Al empezar, `extract_offers` vuelve a ubicar los lotes con
   `location_retry`, a partir de lo ya extraído, sin pasar otra vez por el modelo.
6. **El municipio, también por su código.** Si el nombre que da el servicio no casa con el de la
   oferta, se acepta cuando el municipio INE de la sección del punto es uno de los que
   `candidates` de CartoCiudad da para ese nombre, solo de tipo municipio o núcleo y con el
   nombre exacto en alguna de sus lenguas: «Castellón de la Plana» es `12040`, «Castelló de la
   Plana/Castellón de la Plana». «Gerona» no casa con nada («Cortijo Gerona», Girona y Gironella
   salen por parecido). Una resolución equivocada solo puede rechazar, nunca aceptar un punto de
   otro municipio.
7. **La zona son las secciones cargadas.** Un lote cuya provincia, según
   `data/offers/provincias.yaml` (relación de provincias del INE), no tiene secciones cargadas no
   se manda a ningún servicio: su punto se descartaría igual. Si el nombre no está en esa relación
   («Vizcaya» en lugar de «Bizkaia»), no se descarta: decide la cartografía después de ubicarlo.
   Ampliar la zona es cargar las secciones de otra provincia (`make sections PROVINCE=24`); no
   hay que tocar código ni configuración, y los lotes de esa provincia que esperaban se ubican en
   la siguiente ejecución.

## Opciones consideradas
- **Nominatim (OpenStreetMap):** público, pero su política de uso limita a una petición por
  segundo y prohíbe el uso intensivo, y su precisión en direcciones españolas es menor que la de
  CartoCiudad. Para fincas rústicas no aporta nada frente al Catastro. Descartada.
- **Nomenclátor del IGN:** da topónimos, no parcelas ni portales: no basta para elegir sección.
- **Cartografía catastral INSPIRE por municipio** (descarga de parcelas): ubicaría sin consultar
  fuera, pero es una descarga grande por municipio; con unas pocas ofertas al día, la consulta
  puntual basta (igual que en ADR-0016).
- **Reintentar el trabajo entero** (lo que pasaba): repite la extracción con el LLM y no arregla
  un fallo que no es transitorio.

## Consecuencias
- Las fincas rústicas de los anuncios del BOE se ubican con la precisión de la parcela catastral.
- Una caída de CartoCiudad o del Catastro retrasa la ubicación de un lote un día, no la extracción.
- La zona se amplía cargando secciones, sin tocar código. Valorar una oferta de otra provincia
  necesita además sus referencias de renta y precio (ADRH, SERPAVI): eso no cambia aquí.
- Secciones de 2025 de todas las provincias cargadas el 2026-11-01 (36.554). Con ellas se ubicaron
  22 de los 26 lotes que esperaban. Quedan sin ubicar, con su motivo:
  - el anuncio dice un municipio y la referencia catastral es de otro (Utiel y Requena), o el
    municipio extraído es el del Registro de la Propiedad: el Catastro manda y no se acepta;
  - **País Vasco y Navarra** tienen catastros forales: la Dirección General del Catastro no tiene
    sus referencias. Ubicarlos por referencia pide los servicios de cada hacienda foral (otro ADR);
  - los nombres bilingües («Castellón de la Plana» frente a «CASTELLO DE LA PLANA» del Catastro)
    se reconocen por el código INE (punto 6).
