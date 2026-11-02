# Vías oficiales de acceso a anuncios de vivienda en venta: portales, agregadores, datos comerciales y crowdfunding

Investigación del 2026-11-02. Solo lectura: sin formularios, sin cuentas, sin descarga de anuncios.
Marcas: **(leído)** = leído por mí en la página oficial con WebFetch (herramienta que resume la página, hay que releer antes de un ADR); **(sin verificar)** = resumen de búsqueda web o fuente de terceros.
Veredicto: A usable ya · B alta o solicitud estándar · C requiere acuerdo · D no.
Límite del método: muchas webs devolvieron 403/401 o no dejan acceso al lector (pisos.com, yaencontre, Indomio, Nestoria, Habitaclia, Housfy aviso legal, aviso legal de idealista y Redpiso). Lo no leído queda marcado.

## Resultado en una línea
Ninguno es A. Solo idealista ofrece una vía técnica oficial (Search API, B con matiz: es proveedor comercial y exige decisión del dueño / ADR). Lo demás es C o D. Las vías más realistas para cartera propia son: idealista Search API (o idealista/data), Brains RE (envío de datos con anuncios de portales, C) y los feeds de agencias vía Kyero v3 (con permiso de la agencia, ya anotado en el documento base).

## 1. idealista

### Search API (leído, solo la página de solicitud)
- URL: http://developers.idealista.com/access-request (leído)
- Cita: «Search API lets you integrate property information published on idealista into your site or app. To receive an API key get in touch and tell us a bit about your project.»
- Formulario: nombre, correo, «Describe your project», aceptar política de privacidad. No he rellenado nada.
- **No hay términos de la API publicados** en esa página: ni límites, ni precio, ni atribución, ni datos devueltos, ni «API agreement». Los únicos enlaces legales son las condiciones generales (https://idealista.com/en/info/nota-legal, 403 al leerla) y privacidad. Cada intento de encontrar un documento aparte de condiciones de API falló (no existe público, o no lo encuentro).
- Fuente de terceros (sin verificar): una librería de GitHub de 2020 (https://github.com/Oper92/IdealistaLib) cita un límite histórico de 100 peticiones al mes y 1 por segundo. Es antiguo; trátalo como orden de magnitud, no como condición vigente. Otro tutorial (Medium, sin verificar) dice que se recibe clave y secreto (OAuth) tras el registro.
- Si permite mostrar los anuncios a terceros y con qué atribución: **sin verificar, no publicado**. Hay que preguntarlo al pedir la clave («integrate… into your site or app» sugiere que sí, pero no es un término).
- Coste: no publicado.
- robots.txt (leído, https://www.idealista.com/robots.txt, `User-agent: *`): `Disallow: /ajax/*`, `/*.ajax$`, `/inmueble*/foto`, `/inmueble*/visita-virtual`, ordenaciones `?ordenado-por=…`, `/*/pagina-*.htm`, `/pagina/`, `multimediaNumber=2…14`. Sin mención de API. No cubre la Search API (es otro host).
- Contacto: formulario de arriba; contacto general https://idealista.com/en/info/contacto.
- **Veredicto: B** (solicitud estándar), pero es proveedor comercial: regla de oro 3 pide ADR y decisión del dueño. Pedir por escrito: términos, límite, precio, derecho a mostrar fichas con enlace y atribución, y si se puede almacenar.

### idealista/data (comparables y métricas) (leído)
- URL: https://www.idealista.com/data/asesoramiento-inmobiliario-tecnologico/api-comparables-y-metricas (leído) y https://www.idealista.com/data/asesoramiento-inmobiliario-tecnologico/ (leído).
- Oferta: «Datos del mercado inmobiliario (API/ Widget/ Ficheros)»; «la mayor base de datos del mercado inmobiliario en España, Portugal e Italia». Comparables actuales e históricos, valoraciones con datos catastrales, métricas por zona hasta barrio, datos sociodemográficos. Entrega por API, widget o ficheros puntuales.
- Volumen: la página no da cifras. Anuncios individuales con enlace: **no lo dice**. Licencia y precio: no publicados.
- Contacto: formulario (nombre, teléfono, correo, perfil, necesidades). Según datos.gob.es (sin verificar) mezcla datos propios con Catastro, IGN e INE.
- **Veredicto: C** (acuerdo comercial; encaja como proveedor de comparables y métricas, no como escaparate de anuncios). Proveedor comercial: decisión del dueño.

## 2. Portales y agregadores

| Portal | Oferta / vía oficial | Términos | robots.txt | Contacto | Veredicto |
| --- | --- | --- | --- | --- | --- |
| **pisos.com** | Sin vía oficial encontrada (sin verificar). Existen «scrapers» de terceros en Apify; no son oficiales. | Aviso legal no leído (la herramienta no accede al dominio) | No leído (herramienta bloqueada). El documento base: bloquea `/busqueda/$`, `*.aspx`, `/mapa/` | No localizado | **D** (sin verificar) |
| **yaencontre** | Sin vía oficial encontrada (sin verificar) | No leído (403) | No leído (403) | No localizado | **D** (sin verificar) |
| **Habitaclia** (Fotocasa Group) | No. Ver documento base | Ver documento base | Ver documento base | Ver documento base | **D** |
| **Housfy** | Sin API ni afiliados de anuncios (sin verificar). Su web dice tener acuerdos con «partners» con comisión por operaciones generadas (resultado de búsqueda, sin verificar): son captación de clientes, no feed. Buscador propio de viviendas en venta | Aviso legal no leído | robots.txt (leído, https://housfy.com/robots.txt): `Disallow: /dashboard`, `/forms/`, `/landings/`, `/en/`, y facetas `*order=`, `*beds=`, `*price=` (leído hasta línea 25) | No localizado | **C** (solo por acuerdo; no publicado) |
| **Tecnocasa** | Sin vía oficial (sin verificar) | No leídos | robots.txt (leído, https://www.tecnocasa.es/robots.txt): solo `Disallow: /flush_all`; sitemaps de inmuebles. Permite rastrear, pero eso no da licencia de reutilización | No localizado | **D** hasta leer términos |
| **Kyero** | Recibe feeds de agencias; no ofrece API de lectura (sin verificar). Los «partner terms» (https://www.kyero.com/en/docs/partner_terms/) dan a Kyero licencia sobre lo que suben las agencias; no leídos (403), solo vistos en resultado de búsqueda | Partner terms: sin verificar | robots.txt (leído): `Disallow: /*api/*`, `/*advice/api/*`, `/*gallery*`, `/*floorplans*` y casi todos los filtros (`min_price`, `max_beds`, `location_id`, `sort`…) | https://www.kyero.com/en/join/contact (doc. base) | **D** como fuente directa; **C/B** vía el feed v3 de la agencia (doc. base) |
| **thinkSPAIN** | Solo importación XML para anunciantes (doc. base) | URL de términos probada: 404 | robots.txt (leído, https://www.thinkspain.com/robots.txt): `Disallow: /change-language*`, `*?order=*`, `*/directory/go-to-website/*`, `*/user/`, `*/auth/`...) | doc. base | **D** |
| **spainhouses** | Solo feed de carga (doc. base) | No leídos | Doc. base | — | **D** |
| **Indomio** | Sin vía oficial (sin verificar) | No leídos | No leído (403) | — | **D** (sin verificar) |
| **Nestoria** (Lifull) | Tuvo API pública de búsqueda y metadatos con España (`es`) (clientes Perl/Ruby, TechCrunch 2007; sin verificar). No he podido leer https://www.nestoria.es/help/api (401) ni confirmar si sigue activa | No leídos | No leído (401) | — | **C** (comprobar si la API sigue viva y sus condiciones) |
| **Trovit / Mitula** (Lifull Connect) | No hay programa de partners con feed para terceros que lo consuman. Los feeds son de **entrada** (agencias y software de CRM envían XML a Trovit; ej. help.mapaprop.com, sin verificar). Lifull Connect (https://www.lifullconnect.com/contact-us, leído) solo tiene formulario general, sin mención de API, datos ni feeds | Doc. base: «No reproducir, compilar, copiar, extraer, distribuir…» | Doc. base | Formulario lifullconnect.com/contact-us | **D** (C solo si Lifull acepta una licencia de datos, no publicada) |
| **Enalquiler** | Sin vía oficial; **alquiler, no venta** | No leídos | robots.txt (leído): `Disallow: /search?`, `/property/ajax/property`, `/alerts/`, `/user/`, `/favoritos/`, `/booking_online/` | — | **D**; fuera de alcance (alquiler) |
| **Donpiso** | Sin vía oficial (sin verificar) | No leídos | robots.txt (leído, https://www.donpiso.com/robots.txt): `Disallow: /app/`, `*.pdf$`; `Allow: */listado?*` | — | **D** hasta leer términos |
| **Engel & Völkers**, **RE/MAX**, **Century 21** | Sin vía oficial. Doc. base | Doc. base | Doc. base | Doc. base | **D** |
| **Redpiso** | `robots.txt` (leído, https://www.redpiso.es/robots.txt): «Allow: /», «Allow: /api/properties», «Allow: /api/offices», «Disallow: /api/». No hay documentación, términos de API ni licencia: el aviso legal en `/aviso-legal` da 404 y no he encontrado otro. Un `Allow` en robots.txt **no es licencia de reutilización**, solo dice que un rastreador puede pedir esa ruta | No localizados | Ver arriba | info@redpiso.es (doc. base) | **C**: pedir por escrito a info@redpiso.es permiso y condiciones para usar `/api/properties` (candidato a acuerdo: su propio robots lo deja abierto) |
| **Comprarcasa** | Sin vía oficial (sin verificar) | No leídos | robots.txt (leído, https://www.comprarcasa.com/robots.txt): `Allow: /`, `Disallow: /admin/`, `/assets/` | — | **D** hasta leer términos |
| **Gilmar** | Sin vía oficial (sin verificar) | No leídos | robots.txt (leído, https://www.gilmar.es/robots.txt): WordPress, `Disallow: /wp-admin/`, `/wp-includes/`, `/comments/`, `/xmlrpc.php` | — | **D** hasta leer términos |

Ningún portal publica condiciones de reutilización que me hayan dado un A. Los términos que no he podido leer (pisos.com, yaencontre, Housfy, Tecnocasa, Redpiso, Gilmar, Donpiso, Comprarcasa, Indomio, Nestoria, Kyero) son **sin verificar**: no se debe asumir permiso.

## 3. Proveedores comerciales de datos (decisión del dueño)

| Proveedor | Qué vende (publicado) | ¿Anuncios individuales con enlace? | ¿Licencia permite mostrarlos a usuarios? | Contacto | Veredicto |
| --- | --- | --- | --- | --- | --- |
| **Brains Real Estate** (https://brainsre.com, leído) | Explorador de datos: «Oferta actual y pasada de venta y renta», transacciones del registro, obra nueva; valoración con «Anuncios publicados en todos los portales». Entrega puntual, recurrente por correo o FTP, y «API development» a medida. Registro gratuito para el explorador (sin verificar) | La página no lo dice (hay que preguntar) | No publicado | sales@brainsre.com; reserva de demo en la web | **C** |
| **idealista/data** | Ver sección 1 | No dice | No publicado | Formulario | **C** |
| **Tinsa** | IMIE (índice de precios, informes públicos), series trimestrales y «informe a medida» (sin verificar) | No: son datos agregados y valoraciones, no anuncios | No publicado | datasolutions@tinsa.es; 913 727 500; info@tinsa.es | **C** para series de precios, no para anuncios |
| **Atlas Real Estate Analytics** | Consultora de datos con plataforma «Fragua» (sin verificar); no he encontrado oferta de anuncios, API ni precios | Desconocido | Desconocido | No localizado | **C** (sin verificar) |
| **Reidin** | Sin resultados sobre España ni sobre anuncios | Desconocido | Desconocido | — | Sin información |
| **Housfy Data** | No he encontrado producto de datos | — | — | — | Sin información |

Nada de esto publica licencias que permitan mostrar anuncios a usuarios finales. Antes de cualquier decisión hay que pedir a cada proveedor: (a) origen de los anuncios (si vienen de portales, su licencia puede no ser transferible), (b) derecho de reutilización y visualización, (c) si hay enlace a la ficha original, (d) precio. Regla de oro 3: ADR y decisión del dueño.

## 4. Crowdfunding / inversión inmobiliaria

- **Urbanitae**: la página https://www.urbanitae.com/es/afiliados (leída) no menciona afiliados, partners ni API, solo contacto: contacto@urbanitae.com, (+34) 911 23 25 22. robots.txt: la herramienta devolvió la portada, no el fichero (no verificado). **C**.
- **Housers**: sin programa oficial encontrado; el directorio affi.io lo lista como cerrado y con unos 10 años (sin verificar, https://affi.io/m/housers). robots.txt: error 502 (no leído). **C**.
- **Civislend**: directorios de afiliados la listan en Awin (cerrado), Target Circle (abierto, cookies 30 días) y Kwanko (sin verificar, https://affi.io/m/civislend). robots.txt (leído): `Allow: /`. Un programa de afiliados envía tráfico y paga por inversión; no es un feed de datos de oportunidades. **C**.
- **Bricks.co**: sin información de partners ni API. robots.txt (leído, https://www.bricks.co/robots.txt): `Allow: /`, `Disallow: /api/`, `Disallow: /slice-simulator`. **C**.
- Nota: las ofertas de crowdfunding son valores (financiación participativa, CNMV), no inmuebles comprables; si Aldaby las mostrara, habría que valorar la regulación de publicidad de inversión y la regla de oro 7 (comisiones). Si se plantea, es otro ADR.

## Vías más prometedoras
1. **idealista Search API** (B): única API oficial de lectura con solicitud estándar. Pedir términos por escrito y decidir ADR.
2. **Redpiso `/api/properties`** (C): su robots.txt lo permite explícitamente; escribir a info@redpiso.es pidiendo condiciones. Es una cadena nacional.
3. **Brains RE** (C), o **idealista/data**: envío periódico de datos de oferta de todos los portales por FTP o API; preguntar si incluye enlace y si pueden mostrarse a usuarios. Alternativa que ya anotaba el documento base: feeds Kyero v3 de agencias con su permiso.
