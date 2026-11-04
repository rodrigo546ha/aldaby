# ADR-0049: Extracción con IA del Portal de Subastas del BOE y análisis de documentación

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («desarrolla el scraping con IA del portal de subastas del BOE para extraer condiciones y documentación»)

**Aprobación explícita (2026-11-04):** Rodrigo lo confirma («lo apruebo explícitamente, entra todo»)
sabiendo que el `robots.txt` del Portal dice `Disallow: /` y que ADR-0017 y ADR-0047 lo dejaban fuera.
Este ADR sustituye esa parte de ADR-0017. Los endpoints `/boe/subastas/*` exigen sesión: cada llamada
sale al Portal y al modelo.

## Contexto

El Portal de Subastas del BOE (`subastas.boe.es`) centraliza las subastas judiciales y administrativas de España. Aunque en ADR-0017 se limitó la ingesta automática general a los anuncios breves de la sección IV del BOE debido a las restricciones de `robots.txt`, el análisis financiero y jurídico real de una oportunidad en subasta (así como la viabilidad en el simulador de puja de ADR-0047) requiere conocer con exactitud:
1. Las condiciones procesales y económicas de la subasta (tipo, juzgado/autoridad gestora, número de procedimiento, valor de subasta, tasación en escritura, deuda reclamada, depósito legal del 5 %, tramos y puja mínima).
2. Si es la vivienda habitual del ejecutado (determina los umbrales de adjudicación del art. 670 LEC: 70 % o cobertura de deuda con mínimo 60 %, frente al 50 % ordinario para bienes no habituales).
3. La situación registral y de cargas del bien: finca registral, Registro de la Propiedad, CRU/IDUFIR, titular registral, la carga que se ejecuta y, fundamentalmente, las **cargas y gravámenes anteriores y preferentes subsistentes** que por imperativo legal (arts. 642 y 668.2 LEC) asume el adjudicatario y se suman directamente al coste efectivo de adquisición.
4. La situación posesoria: si el inmueble está ocupado por el ejecutado, por arrendatarios (con contrato anterior o posterior a la hipoteca) o por ocupantes sin título, la aplicabilidad de la moratoria de lanzamientos (Ley 1/2013) y si es visitable.
5. Toda esta información sustancial no reside en los resúmenes someros de los anuncios, sino en la documentación oficial adjunta en PDF custodiada en el portal: el **edicto judicial**, la **certificación de dominio y cargas expedida por el registrador**, los **pliegos de condiciones** y, en su caso, el **informe de ocupación**.

## Decisión

1. **Scraper multi-pestaña del Portal (`housefinder.offers.boe_portal`):**
   - Resuelve tanto URLs directas (`subastas.boe.es/detalleSubasta.php?idSub=...`), enlaces cortos (`ds.php?id=...`) como identificadores canónicos (`SUB-JA-...`, `SUB-AT-...`, `SUB-RC-...`).
   - Descarga y parsea de forma estructurada las cinco pestañas de detalle:
     - `ver=1`: Información general de la subasta, importes económicos y enlaces a los documentos oficiales.
     - `ver=2`: Autoridad gestora (juzgado, oficina de recaudación, dirección y contacto).
     - `ver=3`: Bienes y lotes. Soporta tanto subastas de lote único como subastas multi-lote navegando por cada lote (`ver=3&idLote=1..N`).
     - `ver=4`: Acreedores y ejecutante.
     - `ver=5`: Información de licitaciones. Clasifica el estado de licitación público sin requerir usuario:
       * `sin_pujas`: La subasta no ha recibido pujas (desierta hasta el momento).
       * `con_pujas_requiere_login`: Existen pujas activas de otros licitadores (el BOE restringe la cuantía exacta a usuarios identificados en el portal).
       * `puja_secreta`: Subasta con sobre cerrado / plicas (habitual en notariales voluntarias).
       * `puja_publica`: Importe de la puja máxima visible públicamente.
       * Desglose estructurado por lotes (`lot_bids`) en subastas multi-lote.
   - Implementa motor de búsqueda y descubrimiento sobre `subastas_ava.php` permitiendo filtrar por provincia, estado y tipo de bien.
   - Convierte los bienes extraídos en ofertas normalizadas (`NormalizedOffer`) con canal `boe_subasta_portal`.

2. **Descarga y lectura de documentación oficial adjunta:**
   - Descarga directa de los PDFs oficiales asociados mediante `verDocumento.php?idSub=...&idDoc=...`.
   - Extracción de texto estructurado de cada página mediante `housefinder.ingestion.public_pdf` (`pypdf`), respetando la frontera arquitectónica que reserva `documents/` con OCR para documentos privados del usuario y permite a `offers` usar `ingestion`.
   - Soporte de hasta 40 páginas por documento, suficiente para certificaciones registrales exhaustivas.

3. **Extracción estructurada con IA (`housefinder.agent.boe_auction_extraction`):**
   - Modelo Pydantic `FullAuctionExtractionSchema` que abarca:
     - `conditions`: tipo procesal, juzgado, procedimiento, valor, tasación, deuda, depósito, tramos, vivienda habitual, plazo de remate y cesión de remate.
     - `registry_charges`: Registro de la Propiedad, finca, CRU/IDUFIR, titular, carga ejecutada, lista tipificada de cargas previas subsistentes (hipotecas, embargos, afecciones fiscales con su importe) y cargas posteriores cancelables.
     - `occupancy`: estado posesorio, detalles del ocupante, contrato de arrendamiento, trámite incidental de lanzamiento (art. 675 LEC), moratoria de vulnerabilidad y visitabilidad.
     - `risk_assessment`: calificación de riesgo (`bajo`, `medio`, `alto`, `critico`), lista de advertencias jurídicas y resumen ejecutivo.
   - **Regla de Oro de HouseFinder (Verificación estricta de citas):** cada valor extraído exige un campo `evidence` con la cita textual idéntica en el corpus (resumen de pestañas + texto íntegro de los PDFs). Si la cita no coincide palabra por palabra o si el LLM inventa una cifra, el campo se rechaza (`status = 'rechazado'`) y su valor se anula para proteger al usuario de alucinaciones financieras.
   - **Fallback heurístico determinista:** `rule_based_fallback_extraction` procesa expresiones regulares jurídicas sobre el corpus cuando no hay cliente LLM disponible o cuando falla la respuesta de la API.

4. **Integración en API REST y Enlaces Pegados:**
   - Endpoints en `housefinder.api.boe`:
     - `POST /boe/subastas/scrape`: raspa y extrae una subasta bajo demanda con o sin IA y descarga de documentos.
     - `POST /boe/subastas/search`: busca subastas en el portal por provincia.
     - `GET /boe/subastas/{portal_id}`: consulta los datos recopilados de una subasta.
   - Enlace pegado (`housefinder.offers.link`): cuando el usuario pega una URL de `subastas.boe.es`, en lugar de rechazarla por `robots.txt`, el analizador invoca el scraper especializado y descarga su documentación para procesarla con rigor.
   - CLI: ejecutable directamente con `python -m housefinder.offers.boe_portal --id SUB-... --docs --ai --json`.

## Consecuencias

- **Positivas:**
  - Acceso inmediato al dato crítico de las subastas inmobiliarias: cargas previas que asume el comprador y si la vivienda es habitual, evitando pujas ruinosas.
  - Alimenta directamente el simulador de puja (ADR-0047), que ahora puede disponer de las cargas exactas sin exigir que el usuario las teclee manualmente.
  - Trazabilidad y seguridad jurídica absoluta: toda cifra expuesta al usuario proviene de una cita literal de un documento oficial del BOE o del registrador.
  - Arquitectura limpia: desacoplamiento estricto de capas mediante protocolos en `agent` e ingesta pública en `offers`, verificada en `test_architecture.py`.
- **Riesgos y mitigaciones:**
  - El portal de subastas puede actualizar su maquetación HTML: los selectores de tablas y encabezados se han diseñado tolerantes a variaciones tipográficas y atributos de espaciado, y se incluyen fixtures completos de prueba unitaria (`single_ver1`..`5`, `multi_ver1`..`3`).
  - Documentos puramente escaneados como imagen sin capa OCR en origen: devuelven texto vacío en `public_pdf`; en ese caso el extractor de IA se apoya en los datos tabulares del portal y emite una advertencia de riesgo sobre la necesidad de revisión manual del PDF.

