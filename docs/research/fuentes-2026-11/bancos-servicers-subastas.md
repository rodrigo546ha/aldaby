# Fuentes de bancos, servicers y subastas privadas: segunda ronda (2026-11-02)

Solo lectura. Leído con curl (un GET por página, sin descargar anuncios, sin formularios, sin cuentas) y
con WebFetch/WebSearch. «(leído)» = lo he leído yo en la web del propio titular. «(sin verificar)» =
sale de prensa, blogs o resúmenes de buscador, o la web no se deja leer. No se repite lo que ya está
en `f4-5-servicers.md`, `fuentes-de-oferta-vivienda.md` y `proceso-acceso-fuentes.md`, salvo para
corregirlo. Solvia queda fuera por indicación de Rodrigo.

Veredictos: A = usable ya; B = alta o solicitud estándar; C = requiere acuerdo; D = no.

## 0. Hallazgos que cambian el mapa

1. **Haya, Casaktua y Solvia son el mismo grupo: Intrum.** La web de Intrum dice «Solvia.es y
   Casaktua.com los portales inmobiliarios de Intrum» (leído,
   https://www.intrum.es/empresas/servicios/real-estate/servicios-inmobiliarios-de-comercializacion/).
   El certificado TLS de `www.casaktua.com` es de `*.solvia.es` (leído; explica el error que vimos).
   Intrum completó la compra de Haya en 2023 (nota de Intrum, sin verificar el cierre). `haya.es`
   no responde a curl y `corporate.haya.es` no resuelve (leído hoy). Si Solvia queda fuera,
   **Haya y Casaktua quedan fuera con ella**: ya no son canales distintos.
2. **Quién vende qué ya no es lo que dice la tabla de bancos.**
   - **CaixaBank:** «Solvia-Intrum has been selected to manage the sale and maintenance of
     properties from CaixaBank's portfolio» (leído, nota de CaixaBank del 25-05-2023,
     https://www.caixabank.com/comunicacion/noticia/buildingcenter-selects-the-new-servicing-providers-for-the-sale-maintenance-and-rental-management-of-caixabanks-real-estate-portfolio-for-the-forthcoming-three-years_en.html?id=44055).
     Los alquileres, para Azzam; el mantenimiento de los inmuebles de Bankia, para Haya.
   - **Ibercaja:** su portal dice «de la mano de Ibercaja y Solvia» (leído).
   - **BBVA:** sus pisos salían en Haya; hoy se ven en Solvia (sin verificar; blogs de consumo de
     2026, no hay nota oficial).
   - **Santander:** Diglo vende sus adjudicados desde abril de 2026 (sin verificar; RadarPro, sept. 2026).
3. **BidX1 ya no vende en España.** Su menú de propiedades solo lista Sudáfrica, Irlanda, Reino
   Unido y Chipre (leído, https://bidx1.com/en/sell-with-us). Corrige cualquier idea de usarla.
4. **`anticipa.es` no es Anticipa Real Estate.** Es una empresa de software de Málaga (leído,
   info@anticipa.es, +34 952 799 931). No escribirle. Anticipa-Aliseda vende por Aliseda.
5. **`reaxion.es` no es una casa de subastas** (es la web de un consultor, leído). No he encontrado
   ninguna casa de subastas «Reaxion».

## 1. Los no leídos

| Fuente | Oferta y vía | Términos y robots | Contacto | Veredicto |
| --- | --- | --- | --- | --- |
| **Haya Real Estate** | Absorbida por Intrum (Solvia). `haya.es` sin respuesta (curl, tiempo agotado) y `corporate.haya.es` no resuelve (leído). | No se pudo leer `robots.txt` ni términos. | No aparece. | **D** (es Intrum/Solvia). Sin verificar la fecha de desaparición de la marca. |
| **Casaktua** | Portal de Intrum. Misma infraestructura que Solvia (certificado de `solvia.es`). Antes, «Aktua» (Lindorff). | `robots.txt` ilegible por el certificado; no se fuerza. | La web de Intrum remite a un formulario de «Contacto - Servicios Inmobiliarios» (leído); sin correo ni teléfono. | **D** (mismo grupo que Solvia). |
| **Sareb** | No vende por sí misma. Según su web, para interesarse por un inmueble hay que ir al gestor comercial: Hipoges o Aliseda-Anticipa; parte de la obra nueva pasó a Árqura Homes (web de Aelca). Contratos de abril de 2022 (13.906 M€ de cartera para Hipoges y 11.379 M€ para Aliseda-Anticipa, valores brutos según su nota). Una noticia posterior dice que Servihabitat y Aliseda sacaron las mejores puntuaciones en la nueva adjudicación y que Hipoges pasaría su lote a Servihabitat; faltaba validar el consejo. Todo (sin verificar): `sareb.es` devuelve 403 a curl y a WebFetch; solo lo he visto en fragmentos de buscador. | `robots.txt` y páginas: 403 (protección). No se fuerza. | Teléfonos en su FAQ, vistos en un fragmento de buscador (sin verificar): Aliseda 900 923 543; Hipoges 914 231 822. | **C**, y solo a través de Aliseda, Hipoges y (quizá) Servihabitat, que ya tenemos. Preguntarles a ellos qué parte de Sareb es suya hoy. |

## 2. Bancos

| Banco | Portal y quién lo gestiona | Términos (cita literal) | `robots.txt` | Colaboradores / API | Contacto | Veredicto |
| --- | --- | --- | --- | --- | --- | --- |
| **CaixaBank** | Venta y mantenimiento: Solvia-Intrum (leído, nota de CaixaBank). InmoCaixa (obra nueva, https://www.inmocaixa.com/es, leído: «Promociones de obra nueva en venta»). Building Center: `buildingcenter.es` carga una aplicación («Public Store») sin texto legible. «Facilitea» es una tienda de reacondicionados, no un portal de inmuebles (leído). Servihabitat, histórica (ya está). | Aviso legal de InmoCaixa no localizado. | InmoCaixa: `Allow: /`, bloquea PDF y varios copiadores (leído). Building Center: bloquea `/ca/`, URLs con `?` y sus páginas de privacidad, aviso legal y cookies (leído). | No aparece. | No aparece en la web leída. | **D** para el parque de venta (Solvia); **C** para InmoCaixa obra nueva (sin leer sus términos). |
| **BBVA** | Haya → hoy Solvia, con «Inmuebles de BBVA en venta» (sin verificar). Divarian/Cerberus es el titular de la cartera (sin verificar). | `bbva.es` devuelve 403 a curl y WebFetch. | 403. | No. | No leído. | **D** (Solvia). |
| **Bankinter** | Portal propio: https://www.bankinter.com/www/es-es/cgi/ebk+inm+home (leído; buscador por provincia; el diseño es antiguo y no he podido comprobar el volumen: la ficha de Madrid no mostró inmuebles en mi lectura). Fondo Social de Viviendas (sin verificar). | Enlaza «Aviso legal» a `/www2/particulares/es/inicio/aviso_legal` (404 al leerlo hoy, **no leído**). | Permite el listado. Bloquea solo `/*…ebk+inmuebles+detalle*` bajo dos rutas y `/ajx/`, `/stf/`, PDF… (leído). Es decir, las fichas bajo esas rutas están vetadas a bots. | No aparece. | «Llámenos: 901 888 050» (leído). | **C** |
| **Ibercaja** | https://portalinmobiliario.ibercaja.es/listado/ («de la mano de Ibercaja y Solvia», leído). Mezcla anuncios del grupo con los de particulares y promotores (sin verificar). Hoy `portalinmobiliario.ibercaja.es` no resuelve desde aquí. | «Este sitio web es para tu uso personal y no comercial.» (leído, https://www.ibercaja.es/particulares/condiciones-de-uso/) | `ibercaja.es`: `/ofer*`, `/buscad*` bloqueados (leído). | No aparece. | Sin correo ni teléfono en la página; «Atención al cliente» (leído). | **D** (Solvia + uso solo personal). |
| **Unicaja** | https://unicajainmuebles.com/ («Unicaja Inmuebles», titular Unicaja Banco, S.A., leído). Cartera de GIA (sin verificar; prensa: más de 1.290 inmuebles en 2020, 39 viviendas solo en Almería en 2026 en idealista). | «queda prohibida la reproducción, distribución, comunicación pública, y transformación, sin la autorización previa de» Unicaja (leído, https://unicajainmuebles.com/avisoLegal.do; el nombre sigue en el HTML, lo he recortado). | Solo comentarios de Cloudflare con señales de contenido y reserva de derechos del art. 4 de la Directiva 2019/790; ninguna regla `Disallow` visible (leído). | No aparece. | Formulario `formContacto.do` (leído); sin correo ni teléfono. | **C** |
| **Kutxabank** | No tiene portal propio que haya encontrado. Servihabitat gestiona su cartera desde 2022 (sin verificar, notas de prensa de Servihabitat). `clientes.kutxabank.es` solo tiene guías y listas de APIs colaboradoras (sin verificar). | — | `kutxabank.es` sin portal de inmuebles: 404 en la ruta de robots probada. | — | — | **D** como fuente propia; ya cubierto por Servihabitat. |
| **Abanca** | **EscogeCasa**, https://www.escogecasa.es/ («la inmobiliaria de ABANCA», leído). Comercializa inmuebles del grupo y de terceros con convenio. Sección «Inversores»: locales, naves, oficinas, suelos y activos en rentabilidad (leído). Sin volumen publicado. | «está prohibido el uso de los contenidos del presente Sitio Web por terceros ajenos a ABANCA con fines comerciales» (leído, https://www.escogecasa.es/aviso-legal). Y: «previa autorización escrita de ABANCA». | `Allow: /`; bloquea `/nogooglebot/` y `/print_inmueble/` (leído). | «Acceso colaboradores» lleva a `extranet2.abanca.com/apis/` (leído el enlace; la aplicación pide acceso, no leída). | info@escogecasa.es; 981 981 250 (leído) | **C** (con posible **B** si el acceso de colaboradores admite una empresa de datos; hay que preguntarlo). |
| **Caja Rural** | El grupo (`grupocajarural.es`) no tiene portal. **Caja Rural Central** enlaza a `ruralcentralportalinmobiliario.com` (leído; plataforma de Vivendex, según su `robots.txt`). Volumen: 53 pisos de banco y 259 inmuebles (sin verificar, blog sin fecha). Concentrado en Murcia y Alicante. | Caja Rural Central: «estando prohibidas en todo caso su reproducción y distribución, salvo para uso personal y privado» (leído, https://www.ruralcentral.es/aviso-legal). | `ruralcentralportalinmobiliario.com`: `Allow: /` (leído). `cajarural.com`: `Disallow: /` (leído). | Página «Información para inversores» sin contenido útil (leído). | teatendemos@crcentral.es (leído en `ruralcentral.es`); portal: 966 74 78 17 (leído) | **C** (pequeño, regional) |
| **Deutsche Bank** | No encontrado un portal; una fuente secundaria dice que no tiene web de inmuebles propia (sin verificar). | — | `deutsche-bank.es`: bloquea `/*?` (leído). | — | — | **D** |
| **Sabadell** | Solvia (excluido). `bancsabadell.com` bloquea `/es/`, `/en/`, `/ca/` en su `robots.txt` (leído). | — | Ver la columna anterior. | — | — | **D** |
| **Santander** | Diglo y Altamira (ya estaban). Casaktua no es de Santander hoy: es de Intrum. | — | — | — | — | Ya tratado. |

## 3. Casas de subastas y venta online privada

| Casa | Oferta | Términos | `robots.txt` | API / feed | Contacto | Veredicto |
| --- | --- | --- | --- | --- | --- | --- |
| **BidX1** | Subastas online. **Sin oferta en España** hoy (leído). | «You may not use any data gathering or data extraction tools, such as robots, on the website without our prior written permission.» (https://bidx1.com/en/terms-conditions-use-our-website) | `Allow: /`; bloquea Meta, GPTBot (leído). | No. | Oficinas de Sudáfrica, Irlanda, Reino Unido y Chipre; no hay de España (leído). | **D** |
| **Reaxion** | No encontrada. `reaxion.es` es otra cosa. | — | — | — | — | **D** (sin identificar) |
| **Escrapalia / Surus** | Subastas online de bienes de empresas y concursos (lotes, terrenos, locales). Operada por **Surus Inversa, S.L.U.** (leído). Vende por orden de administraciones concursales (p. ej. Reyal Urbis; sin verificar). Sección «Escrapalia Inmuebles» (visible en Diario de Subastas). Sin volumen propio publicado. | «queda totalmente prohibida salvo que medie expresa autorización de SURUS INVERSA S.L.U» (reproducción, distribución y puesta a disposición; leído, http://www.surusin.com/aviso-legal/). La web de Escrapalia es una aplicación y no deja leer sus términos sin ejecutar JavaScript. | Bloquea `*/categoria/inmuebles*`, `*/category/inmuebles*` y filtros (leído). `surusin.com`: sin restricciones (leído). | No aparece. | info@surusin.com; +34 913 524 507 (leído en surusin.com) | **C** |
| **Subastas.re / Hipoges subastas** | Subastas y cesiones de remate en `realestate.hipoges.com/es/auction/…` y `/es/landing/subastas-y-cesiones-de-remate` (sin verificar; aparecen en buscador, la página se rellena con JavaScript). `subastas.re` no resuelve (leído). Es el mismo servicer ya tratado. | Las de Hipoges (ya están). | `Allow: /` (leído). | No aparece. | subastas.re@hipoges.com (ya estaba; lo repite un fragmento de su web). | **C** (mismo acuerdo que Hipoges). |
| **Servihabitat subastas** | Una nota de prensa dice que lanzó una web para préstamos, subastas y cesiones de remate, sin nombre ni URL (sin verificar). No he podido localizarla. | Las de Servihabitat (ya están). | — | — | servihabitat@servihabitat.com (ya estaba) | **C** (con Servihabitat). |
| **Aliseda subastas** | No encontrada. Aliseda declara una plataforma de venta digital y «Excent» para suelo y terciario (sin verificar). | Las de Aliseda (ya están). | — | — | clientes@alisedainmobiliaria.com (ya estaba) | **C** (con Aliseda). |
| **Activos Bancarios** | No encontrada (los dominios probados no resuelven). | — | — | — | — | **D** (sin identificar) |
| **Subastas Online** | No hay un portal español con ese nombre. `subastas-online.com` es un mercado argentino y `subastasonline.es` es un dominio a la venta (leído). | — | — | — | — | **D** |
| **Kronos** | Es un promotor e inversor (Kronos Homes, STAY, WAY), no una casa de subastas (sin verificar, prensa). | — | — | — | — | **D** |
| **eActivos** (añadida) | Subastas privadas de activos concursales; titular **Activos Concursales, S.L.** (Valencia, leído). Sin volumen propio. | «Se prohíbe el acceso a los contenidos de este Sitio Web por medio de sistemas mecanizados que sean distintos a personas físicas» (leído, https://www.eactivos.com/aviso-legal). | Bloquea solo acciones de usuario y «mejor puja» (leído). | No aparece. | info@eactivos.com (atención al cliente, leído); contacto@eactivos.com (enlace «mailto», leído); 963504476 (leído) | **C** (y **D** para extracción automática). |
| **Diario de Subastas** (añadida) | Agregador de subastas públicas y privadas (BOE, TGSS, Escrapalia, eActivos, Subastas Trademat, Baratura, Subastas Procuradores; leído la lista del desplegable). Titular **Auction Live, S.L.**, calle Velázquez 105, Madrid (leído). Referencia a `api.diariodesubastas.com` en el HTML; no he comprobado si es pública. | «Todos los contenidos del sitio web… constituyen una obra cuya propiedad pertenece a Diario de Subastas.» (leído, https://diariodesubastas.com/avisos-legales/). Declara que la información la responden las entidades organizadoras. | `Allow: /`; bloquea rutas legacy y privadas (leído). | `api.diariodesubastas.com`: sin leer. | info@diariodesubastas.com («info ARROBA…», leído) | **C**: intermediario, no fuente; copia lo que ya sale del BOE, pero concentra las subastas privadas. |

## 4. Servicers secundarios con portal propio

| Servicer | Portal | Veredicto |
| --- | --- | --- |
| **Anticipa** | No tiene portal propio. Vende con Aliseda (ver `f4-5-servicers.md`). El dominio `anticipa.es` es de otra empresa. | **D** (usar Aliseda) |
| **Intrum** | Solvia.es y Casaktua.com (leído). `intrum.es` solo bloquea `*.pdf`, `/faq/`, `/shared/` (leído). | **D** (Solvia fuera) |
| **doValue (Altamira)** | `altamirainmuebles.com` (ya está). `dovalue.es` enlaza a `/contacto` y a `/aviso-legal` (leído el enlace, sin leer la página). | Ya tratado |
| **Hipoges** | `realestate.hipoges.com` (ya está). | Ya tratado |
| **Cerberus / Haya** | Haya pasó a Intrum (ver arriba). Nada propio. | **D** |
| **Axactor** | Sin portal de inmuebles en `axactor.com/es/` (leído). Tel. 910 120 462; calle Juan Esplandiú 11-13, planta 12, Madrid (leído). | **D** |
| **Lindorff** | Es Intrum/Aktua; sin portal propio (sin verificar). | **D** |
| **Cabot** | `cabotcm.com` devuelve 403; no consta portal de inmuebles (sin verificar). | **D** |

## 5. Lo más prometedor
1. **ABANCA · EscogeCasa.** Portal propio de un banco, con sección «Inversores», convenios con
   terceros y un acceso de colaboradores. Es el único con correo y teléfono publicados y una puerta
   explícita. Pedir: acceso de colaborador de solo lectura sin comisión, o un fichero de su cartera.
   Su aviso prohíbe el uso comercial por terceros que compita con ABANCA; hay que dejar claro
   que somos independientes y que mostramos la oferta a compradores, sin intermediar.
2. **Unicaja Inmuebles y Bankinter, bancos con portal propio y sin servicer intermedio.** Ninguno
   publica correo; Bankinter da el 901 888 050; Unicaja, un formulario. Son pequeños, pero tratan
   directamente y el acuerdo no pasa por un fondo.
3. **Subastas privadas: Surus (Escrapalia) y, como intermediario, Diario de Subastas.** Surus
   publica correo y teléfono; vende por encargo de administraciones concursales, así que lo que
   aporta no son pisos de banco sino activos de liquidaciones. Diario de Subastas ya los
   reúne: preguntarle si su API admite uso comercial con atribución.

Preguntas abiertas: volumen real de cada portal (ninguno lo publica con fuente propia); términos
de Bankinter e InmoCaixa (no localizados); si `extranet2.abanca.com/apis/` acepta a una empresa
de datos; si `api.diariodesubastas.com` es pública.
