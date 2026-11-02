# Fuentes de oferta de vivienda en España: acceso por API, feed o acuerdo

Leído el 2026-11-02: documentación, avisos legales y `robots.txt`, una página cada vez, sin
descargar anuncios. Rodrigo pide la mejor cartera posible de toda España, por API o por scraping.
Regla de oro 3: un canal nuevo necesita su ADR, y no se automatiza una web que lo prohíbe sin su
permiso escrito.

**Cómo leer las citas.** Lo marcado **(comprobado)** lo he leído en la web con el navegador. El
resto lo leyó un agente con una herramienta que resume la página: son fragmentos fieles en lo
esencial, pero hay que releerlos en la web antes de apoyar en ellos un acuerdo o un ADR.

## Conclusiones
1. **Scraping: ninguna fuente grande lo permite.** Todos los portales, servicers y bancos leídos
   prohíben extraer o reutilizar sus contenidos con fines comerciales sin autorización escrita.
   Varios bloquean en su `robots.txt` los listados, o todo el sitio a los bots de IA (Housell,
   Milanuncios). El scraping sin permiso queda descartado; lo que hay que conseguir son permisos.
2. **API de lectura solo hay una: la idealista Search API (comprobado),** con un formulario de
   solicitud. Precio, límites y condiciones no publicados. Es el portal con más pisos y la vía más
   rápida a una cartera nacional. Pero es un proveedor comercial de datos: la regla de oro 3 pide
   un ADR y tu decisión.
3. **La cartera de las agencias se puede recibir con su permiso,** sin pasar por los portales.
   Los CRM más usados exportan un feed XML con el formato de Kyero (v3) para cualquier destino, y
   la agencia nos da el enlace. Encaja con los clientes profesionales (F7) y con la opción c de
   ADR-0036.
4. **Lo público con más volumen es el Portal de Subastas del BOE** (judiciales, AEAT, Seguridad
   Social, notariales): `robots.txt` `Disallow: /` y sin datos abiertos. Hay que pedirlo a la AEBOE.
   El resto de lo público es pequeño o va en PDF: Patrimonio del Estado (con RSS), INVIED
   (ninguna subasta en curso a 7 de octubre de 2026) y las comunidades autónomas por sus boletines.
5. **Hallazgo sobre lo que ya tenemos:** el `robots.txt` del BOE dice `Disallow:
   /diario_boe/xml.php?` (comprobado), y los canales `boe_seccion_v` y `boe_subastas_judiciales`
   descargan cada anuncio de esa ruta (`offers/channels/boe_v.py`, `XML_URL`). El sumario lo
   damos por la API de datos abiertos, que sí está permitida, y es esa API la que da la URL de
   `xml.php` de cada documento. Resuelto el 2026-11-02: los canales leen `txt.php` (mismos
   párrafos, comprobado con 12 anuncios) y se saltan los documentos que el `robots.txt` prohíbe.

## Portales y agregadores
| Portal | API o feed para terceros | Condiciones | `robots.txt` | Contacto |
| --- | --- | --- | --- | --- |
| **idealista** | **Search API**: «Search API lets you integrate property information published on idealista into your site or app. To receive an API key get in touch and tell us a bit about your project.» (comprobado) | Aviso legal no leído (403) | No bloquea las fichas; bloquea paginación, fotos y filtros | Formulario https://developers.idealista.com/access-request |
| **Fotocasa** (Fotocasa Group, S.L.U., B-70677125) | No para terceros (integración para CRM de agencias) | «queda terminantemente prohibido la utilización de los textos, imágenes, anuncios… para su posterior inclusión… en otros sitios web ajenos a la Empresa sin contar con la autorización previa y por escrito» (comprobado) | Bloquea búsqueda; `Disallow: /` a unos 40 bots | ayuda@fotocasa.pro (comprobado) |
| **habitaclia** (Fotocasa Group) | No | Prohíbe usar sus bases de datos sin autorización expresa | Bloquea listados y filtros | Formulario ayuda.habitaclia.com |
| **pisos.com** | No comprobado | No comprobado | Bloquea `/busqueda/$`, `*.aspx`, `/mapa/` | No comprobado |
| **yaencontre** | No comprobado (403) | No comprobado | No comprobado | No comprobado |
| **Kyero** | Recibe feeds de agencias; no da datos | No leídas (403) | Bloquea `/api/*` y galerías | Tickets en kyero.com/en/join/contact |
| **thinkSPAIN** (Think Web Content SL) | Solo importación XML para anunciantes | Exige «express consent» para reproducir | Sitemaps de propiedades públicos | Formulario; +34 96 065 3115 |
| **spainhouses** (Entersoftweb, S.L.) | Solo feed de carga para agencias | No leídas | Bloquea la mayoría de listados | No aparece |
| **Milanuncios** (Adevinta) | No | No legibles | Bloquea `/listing/` y `/api/`; `Disallow: /` a ClaudeBot y GPTBot | Centro de ayuda |
| **Trovit, Mitula** (Lifull Connect, S.L.) | No | «No reproducir, compilar, copiar, extraer, distribuir, transmitir, vender o revender» | Trovit bloquea `/listing/` y `/details/` | Formulario lifullconnect.com/contact-us |
| **Century 21** (Red Global España) | No | Prohíbe reproducir sin autorización «previa, expresa y escrita» | Bloquea búsquedas con parámetros | Correo ofuscado en la web |
| **RE/MAX** (CDC Franquiciadora, A81008161) | No | No leídas | `Disallow: /*?` | remax@remax.es |
| **Engel & Völkers** (EV MMC Spain, B65824054) | No | Términos no leídos | Bloquea búsquedas | spain@engelvoelkers.com |
| **Redpiso** | `robots.txt` permite `/api/properties`; no documentada | Aviso legal no localizado | `Allow: /api/properties` | info@redpiso.es |
| **Tecnocasa** | No | No leídas | Casi todo permitido; sitemaps de inmuebles | No aparece |
| **Housell** | No comprobado: la portada redirige a un dominio ajeno | — | Reserva de derechos para IA; `Disallow: /` a ClaudeBot | — |

## Agencias: CRM, feeds y MLS
| Vía | Qué permite | Contacto |
| --- | --- | --- |
| **Feed XML Kyero v3** (https://help.kyero.com/estate-agents/xml-import-specification, V3.9.1) | Formato de facto para que una agencia publique su cartera; «Each feed URL can only contain property information for a single Kyero account or estate agent» | — |
| **Witei** | Exporta XML Kyero que la agencia comparte con «external website or portal»; sin API pública | Chat de soporte |
| **Inmovilla** | API (para clientes), XML diario e iframe | Tel. 966 673 149; web 403 |
| **Sooprema** | API REST con clave; datos reales solo de agencias clientes; acepta portales nuevos | estate@sooprema.com |
| **Inmoweb** | Sincroniza con «fuentes externas (bancos, proveedores, MLS)» | comercial@inmoweb.es |
| **eGO Real Estate** | Publica en más de 200 portales; acepta pedir uno nuevo | Formulario egorealestate.com/contact-us |
| **MLS.es** | Solo profesionales asociados | mls@mls.es |
| **IAGestión MLS**, **MLS Internacional** | Dicen tener API abierta o XML/JSON | Formularios de contacto |

Las MLS tienen además un riesgo de competencia. La CNMC multó en 2021 a idealista, Inmovilla,
Witei, MLS y otros por fijar comisiones mínimas en una MLS (expediente S/0003/20). Un acuerdo con
una MLS no debe tocar comisiones ni repartir precios entre agencias.

## Fuentes públicas
| Fuente | Acceso | Contacto |
| --- | --- | --- |
| **Portal de Subastas del BOE** | `Disallow: /`; sin datos abiertos | Solo por formulario: «Las consultas específicas sobre el Portal de subastas… se atienden exclusivamente a través de los respectivos formularios web» (comprobado): https://www.boe.es/contactar/formulario_simple.php?tipo=SUB |
| **BOE, documentos** (`xml.php`) | API del sumario permitida; `xml.php` prohibido en `robots.txt` (comprobado) | Formulario de servicios de Internet: https://www.boe.es/contactar/formulario_simple.php?tipo=WEB (comprobado) |
| **AEAT, subastas** | En el Portal del BOE; su buscador (www2) con `Disallow: /` | No aparece correo |
| **Seguridad Social, subastas** | Páginas propias; reutilización permitida con cita, según su aviso legal (no leído directamente) | C/ Astros 5 y 7, 28007 Madrid; 915 038 756 |
| **INVIED (Defensa)** | Pliegos en PDF; reutilización permitida (CC BY-SA); sin subasta en curso | inviedbuzon@oc.mde.es; 900 210 425 |
| **Patrimonio del Estado (Hacienda)** | RSS de subastas y concursos; reutilización permitida con cita | No aparece correo |
| **ADIF, SEPES** | No comprobados (403 y certificado caducado) | — |
| **Comunidades autónomas** | Por sus boletines (BOCM, BOJA…); AVRA en Andalucía | — |

## Bancos con portal propio
| Banco | Portal | Condiciones | Contacto |
| --- | --- | --- | --- |
| **Banca March** | bancamarch.es/es/inmuebles | Términos sin mención a robots; propiedad intelectual reservada | info@bancamarch.es; 900 227 227 |
| **Cajamar** | cajamar.es/es/comun/inmuebles (enlaza a cimenta2.com) | Prohíbe la reproducción y el uso «salvo autorización por escrito» | cajamar@grupocooperativocajamar.es; +34 950 21 01 91 |
| **CaixaBank** | Building Center y Facilitea Casa | No leídas | No aparece |
| **Santander** | Diglo y Altamira (servicers) | `f4-5-servicers.md` | — |
| **Sabadell** | Solvia (servicer) | `f4-5-servicers.md` | — |
| **Bankinter, Ibercaja, Deutsche Bank, BBVA, Unicaja, Kutxabank, Abanca, Caja Rural** | No comprobados (403, el dominio no resuelve o solo hay prensa) | — | — |
