# ADR-0015: Enlace pegado por el usuario

**Estado:** Aceptada, pendiente de la consulta legal (F0.6) · **Fecha:** 2026-10-29 · **Decide:** Rodrigo

## Contexto
La regla de oro 3 prohíbe hacer scraping de portales: sus anuncios entran solo como enlace pegado
por el usuario (F4.1). Hay que fijar qué hace el servidor con ese enlace para que sea el equivalente
a que el usuario abra la página, y no un rastreo. Además, una URL que viene de fuera y que el
servidor descarga abre la puerta a peticiones contra la red interna (SSRF).

## Decisión
- **Dos entradas:** la URL del anuncio o el texto del anuncio copiado por el usuario. Las dos acaban
  en el mismo texto, que es lo que lee el LLM y contra lo que se comprueban las citas (ADR-0013).
- **Una sola descarga, cuando el usuario la pide:** un `GET` a esa URL, sin seguir enlaces, sin
  paginar, sin descargar imágenes, sin ejecutar JavaScript y sin reintentos.
  - `User-Agent` honesto: `HouseFinder/0.1 (enlace aportado por un usuario)`.
  - Se lee y respeta el `robots.txt` del sitio para ese agente. Si lo prohíbe, no se descarga.
  - Si el sitio responde 401, 403 o 429, o devuelve una página de comprobación anti-bot, no se
    insiste ni se intenta esquivar: se pide al usuario que pegue el texto.
  - Solo `text/html`, máximo 3 MB y 15 s.
- **Protección contra SSRF:** solo `http` y `https` en los puertos 80 y 443; el nombre se resuelve y
  se rechaza si alguna dirección es privada, de bucle local, de enlace local, reservada o de
  multidifusión. Las redirecciones (máximo 3) se siguen a mano y se comprueban igual. Riesgo que
  queda: un DNS que cambie entre la comprobación y la conexión; en producción (F7) la descarga sale
  por una red sin acceso a la interna.
- **Qué se guarda:** el texto visible de la página (sin scripts ni estilos), el título, la URL final,
  la fecha y las URL de imagen que la página declara para compartir (`og:image`), sin descargarlas.
  No se guarda el HTML. La oferta es privada: `channel = 'url_usuario'`, `kind = 'enlace'` y el
  `org_id` de quien la pega; nadie más la ve.
- **Extracción asíncrona:** la descarga es inmediata (el usuario sabe al momento si hay que pegar el
  texto); la extracción con el LLM va a la cola (`extract_link`), porque sin GPU tarda minutos.
- **Campos del anuncio:** operación, tipo, precio, superficie construida y útil, habitaciones,
  baños, planta, estado, dirección, municipio, referencia catastral, año de construcción y gastos de
  comunidad. Cada uno con su cita comprobada (ADR-0013, ADR-0014).
- **Confirmación:** el usuario ve cada valor con su cita y lo acepta, lo corrige o lo rellena. Solo
  entonces los valores pasan a las columnas de la oferta (`extraction_status = 'confirmada'`), se
  guarda el origen de cada uno (`extraido`, `corregido` o `usuario`) y la oferta se ubica y se
  enlaza con su inmueble (F4.6).
- **Organización:** hasta que llegue la autenticación (G8), la API usa una organización local de
  desarrollo («Desarrollo local»). Todas las consultas ya filtran por `org_id`, así que G8 solo
  cambia de dónde sale.

## Prueba real (2026-10-29)
Con la web, el worker y `qwen3:8b` en Ollama, pegando el enlace público del anuncio
BOE-B-2026-35273 en boe.es:
- `robots.txt` lo permite; la descarga guarda 8.515 caracteres de texto, menús incluidos.
- La extracción tarda unos 2 minutos y propone precio, superficie, referencia catastral y municipio,
  cada uno con su cita. Rechaza la dirección. Propone como superficie útil la superficie catastral:
  la cita la respalda, pero no es la útil. Para eso está la confirmación.
- **Geocodificación:** CartoCiudad devolvió para «Carretera M-119 21, Alcalá de Henares» la
  «CALLE ALCALA HENARES 119, 30720 Santiago de la Ribera», en Murcia. Desde esta prueba, el
  localizador de ofertas (`offers/locate.py`) solo acepta un punto que caiga en una sección censal
  cargada y cuya localidad sea el municipio de la oferta; si no, la oferta queda sin ubicar. Si el
  usuario corrige la dirección, la oferta se vuelve a ubicar.

## Opciones consideradas
- **Solo texto pegado, sin descargar nunca:** lo más prudente legalmente, pero peor para el usuario.
  Queda como vía siempre disponible.
- **Navegador sin cabeza para páginas con JavaScript:** más páginas legibles, pero se parece más a un
  rastreador y añade una dependencia pesada. Descartado.
- **Guardar el HTML entero:** más fiel, pero guarda más contenido ajeno del necesario. Descartado.

## Consecuencias
- Algunos portales bloquearán la descarga o la prohibirán en `robots.txt`: en ellos, el usuario pega
  el texto. Es el comportamiento buscado, no un fallo.
- El texto guardado puede incluir datos de contacto del anunciante. Queda en la organización del
  usuario y se borra con ella; Row-Level Security en G8.
- La consulta legal (F0.6) puede endurecer esto (por ejemplo, solo texto pegado para algunos
  portales). Cambiarlo es tocar `offers/link.py`, no el resto.
