# Oferta pública de inmuebles fuera del BOE: fuentes, licencia y robots.txt

Investigación del 2026-11-02, solo lectura. No se han descargado datos en bloque ni rellenado
formularios. Sondas hechas con `curl` (UA identificado) a: `robots.txt` de cada host, una página
de cada fuente, un RSS pequeño (Patrimonio, INVIED, BOPB) y la cabecera de un CSV (Justicia y
Portal del Suelo de Madrid; este último vino entero, 330 KB, porque el servidor ignoró el rango).

**Marcas.** «(leído)» = lo he leído yo en la página o en el fichero. «(sin verificar)» = viene de
una búsqueda resumida o de una fuente secundaria. Los volúmenes solo se dan si la fuente los
publica; si no, se dice. Las citas legales son literales y de ≤40 palabras.

**Veredictos.** A = usable ya (licencia que permite reutilización comercial y robots lo permite).
B = tras un alta o confirmación estándar sin negociar. C = requiere acuerdo o autorización
expresa. D = no.

## Tabla resumen

| # | Fuente | Qué oferta | Acceso | Licencia / términos | robots.txt | Veredicto |
|---|---|---|---|---|---|---|
| 1 | Plataforma de Contratación (PLACSP) | Licitaciones de perfiles de contratante; enajenaciones patrimoniales: **no confirmado** | Atom diario + ZIP anual/mensual | Remite al aviso legal de Hacienda: reutilización comercial permitida (leído) | **`Disallow: /`** en `contrataciondelsectorpublico.gob.es` y `contrataciondelestado.es` (leído) | **B** |
| 2 | Patrimonio del Estado (Hacienda) | Subastas, concursos y ventas directas de inmuebles del Estado (urbanos y rústicos, abintestatos) | 3 RSS 2.0 + buscador | Aviso legal de Hacienda: reutilización comercial permitida con cita (leído) | Sin reglas que afecten a `/_layouts/` ni a `/es-ES/Areas…` (leído) | **A** |
| 3 | Sareb | No publica cartera abierta; comercializan servicers | Ninguna | No leído (web bloquea bots) | 403 con Incapsula (leído el bloqueo) | **D** (como fuente directa) |
| 4a | SEPES / Casa 47 | Desde dic. 2025 es Casa 47: alquiler asequible, no venta | Portal propio | No leído | `www.casa47.es`: `Disallow:` vacío (leído); `sepes.es`: certificado caducado | **D** para venta (sin verificar) |
| 4b | ADIF | Subastas de viviendas, locales y suelos | Portal propio | No leído (403 hasta en robots) | 403 | **C** (sin verificar) |
| 4c | INVIED (Defensa) | Subastas y ventas directas de inmuebles desafectados, solares, locales, viviendas no militares | HTML + RSS Atom de subastas | Reutilización comercial permitida (leído), con una cláusula general contradictoria | Sin reglas sobre `/invied/` (leído) | **A** |
| 4d | Seguridad Social (TGSS) | Venta de inmuebles propios y subastas de embargados | Aplicación web con filtros; sin API ni feed | Reutilización comercial permitida con cita (leído) | `w6.seg-social.es`: 404 (sin reglas); `sede` y `www`: `Disallow: /*.pdf` (leído) | **B** |
| 4e | AEAT (fuera del Portal BOE) | Sus subastas viven en el Portal del BOE | — | — | `sede.agenciatributaria.gob.es` sin bloqueo de contenido; no hay oferta propia que leer | **D** (ya pedido a AEBOE) |
| 4f | Registro Público Concursal | Unidades productivas (empresas), no vivienda | Web | Prohíbe «robotizaciones» (leído) | `Disallow:` vacío (leído) | **D** |
| 5a | BOCM | Anuncios de ayuntamientos y OAR, incluidas subastas | RSS + XML por anuncio | Aviso legal reserva derechos y prohíbe comercializar sin autorización (leído) | `Crawl-delay: 10`; `Disallow: *.epub` (leído) | **C** |
| 5b | BOJA | Anuncios y resoluciones, también subastas de AVRA | Sin API ni feed hallado | Autoriza reproducción para uso particular y comunicación gratuita; prohíbe bases de datos sin autorización (leído) | `Disallow: /boja/buscador/search.do?` y `/boja/app` (leído) | **C** |
| 5c | BOPB (Barcelona) | Anuncios de ayuntamientos y ORGT; sección «Dades obertes» | 8 RSS 2.0 diarios | **Sin licencia declarada**; el aviso legal de Diba prohíbe distribuir sin permiso (leído) | `Crawl-delay: 10`; `Disallow: /*?`; bots de IA bloqueados, incluido ClaudeBot (leído) | **B** |
| 5d | BOP Valencia (Dival) | Anuncios de ayuntamientos y SUMA | Solo web | Prohíbe copia y descarga sin permiso escrito (leído) | `bop.dival.es/robots.txt` devuelve HTML (sin reglas) | **C** |
| 5e | BOP Sevilla (Diputación) | Anuncios, incluidos OPAEF | Solo web | Prohíbe reproducir «ni aún citando las fuentes» (leído) | `Disallow: /pdflink/` y PDF concretos (leído) | **C** |
| 5f | DOGC | Anuncios de la Generalitat | — | No leído | `Disallow: /` (leído) | **D** |
| 5g | SUMA (Alicante) | Subastas de recaudación | Web | No leído | **`Disallow: /`** (leído) | **D** sin acuerdo |
| 6a | datos.gob.es, «Subastas judiciales» (Justicia) | Estadística de subastas del Portal BOE desde 2021 | CSV semanal, 12,5 MB | Aviso legal de Justicia: reutilización comercial con cita (leído) | `datos.justicia.es`: `Disallow:` vacío (leído) | **A**, pero **no sirve como oferta** |
| 6b | datos.gob.es, Portal del Suelo (Comunidad de Madrid) | 530 parcelas (479 en venta) de la CAM y municipios | CSV/JSON | CC BY 4.0 (leído) | `datos.comunidad.madrid`: `Disallow: /` (leído) | **B**; es suelo, no pisos |
| 6c | datos.gob.es, IBAVI (Baleares) | Inmuebles de promoción de vivienda pública | CSV/JSON | CC BY (leído en datos.gob.es) | `intranet.caib.es`: 404 (sin reglas) | **B** (sin verificar que haya venta) |

---

## 1. Plataforma de Contratación del Sector Público (PLACSP)

- **Quién:** Dirección General del Patrimonio del Estado, Ministerio de Hacienda.
- **Qué oferta:** son 6 conjuntos de datos (leído en la página de datos abiertos de Hacienda):
  licitaciones de perfiles de contratante sin contratos menores, licitaciones por agregación
  (desde 2016), menores (desde 2018), encargos a medios propios, consultas preliminares y perfiles
  de órganos. **Ningún conjunto menciona enajenaciones ni bienes inmuebles** (leído). Los
  contratos de enajenación patrimonial se publican en PLACSP en la práctica: un resultado de
  búsqueda cita una subasta municipal de parcelas de mayo de 2026 (sin verificar). No he podido
  comprobar cómo se marcan en el Atom sin descargar el flujo; hay que mirar el tipo de contrato en
  la especificación de sindicación (sin verificar).
- **Volumen:** no lo publican. La página dice que el periodo «no es homogéneo» porque los órganos
  se han ido incorporando (leído).
- **Vía de acceso:** Atom con tope de 500 entradas por fichero y enlace `next`, actualizado
  diariamente (leído). ZIP por año desde 2012 y por meses del año en curso, en
  `https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom`
  (leído, enlaces extraídos de la página de Hacienda). Una licitación aparece una vez por cada
  modificación (leído). Herramienta OpenPLACSP v2.2, EUPL 1.2 (leído). Los comentarios de
  datos.gob.es denuncian huecos y retrasos de julio a septiembre de 2026 (sin verificar).
- **Licencia:** datos.gob.es no nombra licencia y remite a
  `https://www.hacienda.gob.es/es-ES/Paginas/Avisolegal.aspx` (leído). Ese aviso dice:
  «permiten la reutilización de los documentos sometidos a ellas para fines comerciales y no
  comerciales» (leído). Condiciones: no desnaturalizar el sentido, citar «Origen de los datos:
  Ministerio de Hacienda», indicar la fecha de actualización, no sugerir patrocinio (leído).
- **robots.txt (leído):** `User-agent: *` `Disallow: /` en los dos hosts. Los ZIP y el Atom cuelgan
  del host bloqueado. La contradicción entre «datos abiertos» y un bloqueo total es probable que sea
  un descuido, pero no nos toca decidirlo.
- **Contacto:** no localizado en las páginas leídas. La vía es el formulario del Ministerio de
  Hacienda.
- **Veredicto B:** pedir por escrito a PLACSP que confirme que la descarga programada del Atom y de
  los ZIP está permitida pese al `robots.txt`. Con esa confirmación sería A. Antes de comprometer
  esfuerzo hay que comprobar con un mes de ZIP cuántas enajenaciones de inmuebles contiene.

## 2. Patrimonio del Estado (Hacienda)

- **Quién:** DG del Patrimonio del Estado y Delegaciones de Economía y Hacienda.
- **Qué oferta:** subastas y concursos de bienes inmuebles del Estado, ventas directas tras
  subasta desierta y herencias abintestato, en todo el territorio. Tipos vistos: fincas rústicas,
  inmuebles urbanos, lotes de varios inmuebles (leído en el feed).
- **Volumen (leído, 2026-11-02):** el buscador marca 21 procedimientos en curso con plazos entre el
  06/11/2026 y el 07/12/2026. El RSS de subastas tiene 8 elementos. El RSS de ventas directas
  tiene 5, incluido un «listado de lotes desiertos». Es una foto de un día.
- **Vía de acceso (leído):** RSS 2.0, todos desde `https://www.hacienda.gob.es`:
  - Subastas y concursos: `/_layouts/15/RssSubastas.aspx?hiloId=12`
  - Ventas directas: `/_layouts/15/RssVentasDirectas.aspx?hiloId=15`
  - Abintestatos: `/_layouts/15/RssAbintestatos.aspx?hiloId=13`
  - Índice: `/es-es/paginas/sindicacion.aspx`

  Cada elemento trae título, enlace a la ficha, delegación y fecha y hora de la subasta, como
  texto en `description`. La ficha de cada subasta enlaza un pliego en PDF con los lotes, y ahí
  están dirección, superficie y precio. Hace falta extracción de PDF para tener datos estructurados.
  La página de subastas enlaza por error el RSS de abintestatos con `hiloid=13`; el de subastas es
  el 12.
- **Licencia (leído, aviso legal de Hacienda):** «Las presentes condiciones generales permiten la
  reutilización de los documentos sometidos a ellas para fines comerciales y no comerciales».
  Condiciones: citar la fuente («Origen de los datos: Ministerio de Hacienda»), indicar la fecha de
  actualización si consta, no desnaturalizar el sentido y no sugerir que el Ministerio patrocina.
- **robots.txt (leído):** `User-agent: *` con prohibiciones de PDF concretos y `/RRHH/`; nada
  sobre `/_layouts/` ni sobre `/es-ES/Areas Tematicas/`. Los PDF de pliegos de subastas no están
  en la lista.
- **Contacto:** Ministerio de Hacienda, calle Alcalá 5, 28014 Madrid; sin correo ni teléfono en la
  página. Cada delegación atiende su procedimiento (leído).
- **Veredicto A.** Es la mejor fuente nueva, aunque de poco volumen. Ya estaba anotado como «RSS,
  con cita»: ahora está leído el aviso y comprobados los tres feeds.

## 3. Sareb

- **Quién:** sociedad participada mayoritariamente por el FROB; entra en liquidación en noviembre
  de 2027 (sin verificar, varias noticias).
- **Qué oferta / quién comercializa:** no hay portal de venta propio; las compras se canalizan por
  servicers. Una nota de 2026 dice que desde junio de 2026 comercializan Aliseda y Servihabitat, y
  la FAQ de sareb.es citaría además Hipoges, Serviland y Aelca (sin verificar, fuentes
  secundarias). La cartera residencial general pasa a alquiler público vía Casa 47 (sin verificar).
- **Volumen:** no lo he podido leer. El informe semestral 2025 devuelve 403.
- **Vía de acceso:** ninguna abierta. La web (`sareb.es`) responde 403 con una página de Incapsula
  también al `robots.txt` (leído). Ni la FAQ ni el informe son legibles desde aquí.
- **Licencia:** no leída.
- **Contacto:** no localizado.
- **Veredicto D como fuente directa.** El camino real son los servicers (Aliseda, Servihabitat,
  Hipoges), ya en `f4-5-servicers.md`. Un acuerdo con Sareb solo tendría sentido para activos
  singulares y habría que abrirlo por canal institucional.

## 4. Otros organismos

### 4a. SEPES, hoy Casa 47
- El Consejo de Ministros transformó SEPES en Casa 47, entidad estatal de vivienda, el 9 de
  diciembre de 2025; su negocio es alquiler asequible, con un catálogo inicial de 638 viviendas
  según prensa (sin verificar). No es oferta de venta.
- `sepes.es` falla por certificado caducado (leído). `casa47.es` tiene `User-Agent: *`
  `Disallow:` vacío (leído), pero no he leído sus términos.
- **Veredicto D** para oferta en venta. Podría interesar como dato de oferta de alquiler
  asequible; queda fuera de este grupo.

### 4b. ADIF
- Vende viviendas, garajes y suelos por subasta, con una ficha técnica de cartera en su web (sin
  verificar, prensa y un programa de ventas de Hacienda). Ejemplo: ocho inmuebles en Alicante y
  Valencia (sin verificar).
- `adif.es` devuelve 403 («Access Denied») incluso a `robots.txt` (leído). Términos no leídos.
- **Veredicto C** (sin verificar): habría que pedir autorización o consumir sus subastas por el
  BOE cuando las anuncie.

### 4c. INVIED (Defensa)
- **Qué oferta (leído):** enajenación de inmuebles desafectados: locales, viviendas no militares,
  solares, terrenos y fincas, por subasta pública; ventas directas de lo desierto; «Ventas
  previstas». Secciones: Subastas en curso, Resultado, Ventas directas, Ventas previstas.
- **Volumen (leído):** «Actualmente no hay subasta pública en curso. Actualizado a 7 octubre
  2026». Hubo subasta en 2026 (pliego `SUBASTA_01_2026`, sin verificar). No publican totales.
- **Vía de acceso:** HTML y RSS Atom por sección en
  `https://www.defensa.gob.es/invied/comun/rss-subastas.xml` (también `rss-noticias.xml` y
  `rss-licitaciones.xml`). El feed estaba vacío el día de la lectura (0 entradas). Pliegos en PDF.
- **Licencia (leído, `…/invied/comun/avisoLegal.html`):** «Las presentes condiciones generales
  permiten la reutilización de los documentos sometidos a ellas para fines comerciales y no
  comerciales». El mismo aviso dice antes: «Su uso, reproducción, distribución, comunicación
  pública, transformación … queda totalmente prohibida salvo que medie expresa autorización del
  INVIED». Son cláusulas en tensión: la de reutilización es la específica de la Ley 37/2007 y
  prevalece en lo reutilizable, pero conviene fijarlo por escrito.
- **robots.txt (leído, `defensa.gob.es`):** solo `Disallow: /_config_/` y `/zOtros/`.
- **Contacto (leído):** Isaac Peral 20-32, 28015 Madrid; 900 210 425; inviedbuzon@oc.mde.es (del
  documento previo).
- **Veredicto A**, con un correo de cortesía para zanjar la cláusula contradictoria. La oferta es
  esporádica.

### 4d. Seguridad Social (TGSS)
- **Qué oferta (leído):** dos aplicaciones en `w6.seg-social.es`: «Venta de Inmuebles» (inmuebles
  del patrimonio de la Seguridad Social: viviendas y locales, fincas rústicas, solares, edificios
  singulares; estados Convocada, No convocada, Adjudicada; filtro por provincia, superficie y
  tasación) y «Subastas de Bienes Embargados» (apremio). Cobertura nacional.
- **Volumen:** no se publica sin lanzar las búsquedas. No las he lanzado.
- **Vía de acceso:** formularios con filtros; no he visto API, CSV ni RSS. Las convocatorias salen
  además en el BOE y en el Tablón de la sede (sin verificar). Aviso por correo para suscriptores
  (sin verificar).
- **Licencia (leído, `…/InformacionUtil/596`):** «Las presentes condiciones generales permiten la
  reutilización de los documentos sometidos a ellas para fines comerciales y no comerciales».
  La página no dice si cubre el contenido dinámico de `w6`.
- **robots.txt (leído):** `www.seg-social.es`: `Allow: /`, `Disallow: /*/!ut/`;
  `sede.seg-social.gob.es`: `Disallow: /*.pdf` y rutas del tablón con `!ut`; `w6.seg-social.es`:
  404 (sin reglas, pero tampoco permiso expreso).
- **Contacto:** C/ Astros 5 y 7, 28007 Madrid; 915 038 756 / 915 038 464 (del documento previo).
- **Veredicto B:** la licencia permite reutilizar, pero sin API y con aplicación dinámica hay que
  pedirles el fichero o una confirmación de que la consulta automatizada es aceptable.

### 4e. AEAT (fuera del Portal del BOE)
- Las subastas de la AEAT se tramitan en el Portal de Subastas del BOE (sin verificar, prensa).
  No he encontrado oferta propia fuera de ese portal ni datos abiertos de subastas. Pendiente
  de la respuesta de la AEBOE. **Veredicto D.**

### 4f. Registro Público Concursal (`publicidadconcursal.es`)
- **Qué oferta (leído):** el «Portal de liquidaciones concursales» anuncia venta de unidades
  productivas (empresas en bloque) por venta directa o subasta. Los filtros son por CNAE; no hay
  tipo «vivienda». Inmuebles sueltos no aparecen en esa lista. Los edictos concursales no llevan
  ventas de inmuebles.
- **Términos (leído, `/aviso-legal`):** prohíbe «Realizar cualquier tipo de actuación, como
  indexaciones o robotizaciones del sitio Web del RPC, con el fin de recuperar automáticamente los
  datos contenidos en el mismo». Sin licencia de reutilización ni API.
- **robots.txt (leído):** `Disallow:` vacío; el aviso legal manda sobre él.
- **Contacto (leído):** soporte@registropublicoconcursal.org; 912 701 690.
- **Veredicto D.**

## 5. Boletines provinciales y autonómicos

Ningún boletín publica cuántos anuncios de subasta salen. Dato de un día (BOPB, 2026-11-02,
feed «Administració local», 177 anuncios): 0 menciones de «subhasta» o «alienació»; los tipos
más frecuentes fueron ordenanzas fiscales (45) y presupuestos (41). Es una muestra de un solo día
y no sirve para estimar volumen.

### 5a. BOCM
- **Acceso (leído):** `https://www.bocm.es/rss` ofrece tres RSS (últimos 20 boletines, órdenes
  del día, últimos 20 sumarios), y cada anuncio tiene XML en `/boletin/CM_Boletin_BOCM/…xml`. El
  repositorio ya usa esta vía en `ingestion/bocm.py` para vigilancia normativa.
- **Términos (leído, `/aviso-legal`):** «La reproducción, distribución, comercialización o
  transformación no autorizadas de estas obras, a no ser que sea para uso personal y privado,
  constituye una infracción de los derechos de propiedad intelectual de la Comunidad de Madrid».
  No hay mención de reutilización ni licencia.
- **robots.txt (leído):** `Crawl-delay: 10`; `Disallow: *.epub`; `/search/`; el XML y el RSS no
  están bloqueados.
- **Veredicto C** para servicio comercial de subastas; el uso interno de vigilancia es distinto.
  Pedir autorización a la Comunidad de Madrid (no hay contacto específico en la página leída).

### 5b. BOJA (Junta de Andalucía)
- **Acceso:** no he encontrado RSS ni API de contenido en la portada ni en el aviso. Hay un portal
  de datos abiertos (`juntadeandalucia.es/datosabiertos/portal/`, enlazado, no leído).
- **Términos (leído, `/eboja/sobre-boja/aviso-juridico.html`):** «Se autoriza la fiel reproducción
  de los contenidos de la edición del BOJA para uso particular y para la comunicación pública y
  gratuita de los mismos, citando la fuente». Y: «se prohíbe la reproducción, distribución,
  comunicación pública y la modificación de sus contenidos y bases de datos sin autorización
  previa y expresa de la Secretaría General Técnica».
- **robots.txt (leído):** `Disallow: /boja/buscador/search.do?`, `/boja/app` y cientos de
  disposiciones concretas.
- **Veredicto C.** Servicio gratuito y con cita sí; base de datos comercial no.

### 5c. BOPB (BOP de Barcelona)
- **Acceso (leído):** `https://bop.diba.cat/dades-obertes` con 8 feeds RSS 2.0 del boletín del día:
  completo, y por emisor (Estado, Generalitat, Administración local, justicia, otras comunidades,
  electoral, entidades diversas), p. ej. `/dades-obertes/butlleti-del-dia/administracio-local/feed`.
  Cada ítem trae tipo de anuncio, registro, fecha, enlace y PDF. Es el único boletín con datos
  abiertos explícitos que he encontrado.
- **Términos (leído):** el aviso legal de Diba, `https://www.diba.cat/avislegal`, dice «Queda
  totalment prohibit distribuir, copiar, modificar o trametre» el contenido sin permiso por
  escrito, y no cita licencia de datos abiertos. La página «Dades obertes» tampoco nombra
  licencia.
- **robots.txt (leído):** `Crawl-delay: 10`; `Disallow: /anunci/veure-pdf/`,
  `/anunci/descarrega-pdf/`, `/*?` y `/search/`. Los feeds no llevan `?` y no están bloqueados.
  Bloquea nominalmente a ClaudeBot, GPTBot y otros bots de IA; nuestro agente sería otro UA.
- **Contacto:** formulario «Contacte» en la web; Zamora 73, 08018 Barcelona.
- **Veredicto B:** preguntar a Diba qué licencia cubre «Dades obertes del BOPB» y obtener el sí por
  escrito; es la gestión más corta. Si dicen CC BY o equivalente, pasa a A.

### 5d. BOP de Valencia (Diputación de Valencia)
- **Acceso:** solo web (`bop.dival.es/bop/`); no he visto RSS ni API.
- **Términos (leído, `dival.es/va/content/avis-legal`):** «Queda, per tant, prohibida la seua
  còpia, reproducció, distribució, publicació, descàrrega … sense el permís previ per escrit de la
  Diputació».
- **robots.txt:** `bop.dival.es/robots.txt` devuelve una página HTML, no reglas (leído).
- **Veredicto C.**

### 5e. BOP de Sevilla (Diputación de Sevilla)
- **Acceso:** solo web (`dipusevilla.es/bop/`); sin feed hallado.
- **Términos (leído):** «queda prohibida su reproducción, distribución, comunicación pública,
  transformación o cualquier otra actividad … ni aún citando las fuentes, salvo consentimiento por
  escrito de la Diputación de Sevilla».
- **robots.txt (leído):** `Disallow: /pdflink/` y una lista de PDF antiguos.
- **Veredicto C.**

### 5f. DOGC y SUMA / ORGT
- `dogc.gencat.cat`: `Disallow: /` (leído). Términos no leídos. **D.** La Generalitat publica
  datos abiertos en otra web (`analisi.transparenciacatalunya.cat`, sin leer).
- `www.suma.es` (Diputación de Alicante): `User-agent: *` `Disallow: /` (leído). **D** sin
  acuerdo.
- `orgt.diba.cat` (Diba): `robots.txt` con bloqueos de rutas de trámites (leído); la ruta
  `/subhastes` devolvió la página de ayuda, no un listado, y no he podido ver sus subastas.
  Términos: los del aviso de Diba (C).

## 6. datos.gob.es

Búsquedas por título con la API del catálogo (`/apidata/catalog/dataset/title/…`): «enajenación»,
«bienes inmuebles», «subasta», «viviendas en venta», «venta de viviendas», «parcelas», «alquiler»,
«vivienda», «oferta», «inmuebles». **No hay ningún conjunto con oferta de pisos en venta.** Lo que
hay son estadísticas de precios de oferta o compraventa (Barcelona, Euskadi, ETDP), inventarios de
bienes públicos (Navarra, Canarias, Diputación de Gipuzkoa) y estos tres:

| Conjunto | Contenido | Formato y licencia | Uso para Aldaby |
|---|---|---|---|
| **Subastas judiciales** (Justicia) | Estadística de subastas del Portal del BOE desde 2021, actualizada semanalmente (leído). 12,5 MB. Columnas: cantidad reclamada, tipo de subasta, procedimiento, principal reclamado, importe de subasta, importe de tasación, estado, fechas, número de inmuebles, muebles y vehículos, y acreedores y representantes anonimizados (leído) | CSV `;`. Aviso legal de Justicia: «permiten la reutilización de los documentos sometidos a ellas para fines comerciales y no comerciales» (leído) | **No es oferta:** no lleva ID, dirección, municipio ni referencia catastral (leído en las columnas). Sirve para calibrar descuento subasta/tasación. Robots de `datos.justicia.es` sin bloqueo (leído) |
| **Parcelas publicadas en el Portal del Suelo 4.0** (Comunidad de Madrid) | 530 parcelas «disponibles para venta o concesión administrativa»: 479 en régimen V (venta), 38 C, 12 D, 1 A; 496 urbanas y 34 sectoriales (leído, contadas en el CSV). Con referencia catastral y contacto | CSV 330 KB y JSON. CC BY 4.0 (leído). Actualizado 22/10/2026 (leído). **`datos.comunidad.madrid/robots.txt`: `Disallow: /` para `*`** (leído) | Suelo, no pisos. B por el robots |
| **Inmuebles para la promoción de vivienda pública** (Gobierno de Baleares, IBAVI) | Inmuebles gestionados por IBAVI; creado 27/04/2026, actualizado 20/10/2026 (leído en datos.gob.es) | CSV y JSON. CC BY (leído en datos.gob.es). `intranet.caib.es`: sin `robots.txt` (404, leído) | No he abierto los datos; no sé si hay venta. Sin verificar |

También hay, en el catálogo, «Enajenaciones del patrimonio municipal del suelo» del Ayuntamiento de
Madrid (XLS anual, ventas ya hechas desde 2016, CC BY 4.0; leído en datos.gob.es). Es histórico, no
oferta.

---

## Notas y hallazgos para el repositorio

1. **Patrimonio del Estado y INVIED pueden entrar ya como canales** (nuevo ADR, regla de oro 3), con
   cita «Origen de los datos» y fecha de actualización. Son poco volumen; INVIED hoy está vacío.
2. **PLACSP es la única fuente nueva con potencial de volumen**, porque los ayuntamientos y
   organismos publican en ella sus enajenaciones patrimoniales, pero necesita dos comprobaciones
   previas: el `Disallow: /` y cuántas enajenaciones de inmuebles contiene (tipo de contrato
   patrimonial). La segunda se resuelve leyendo un solo ZIP mensual, con permiso explícito de
   PLACSP.
3. **El CSV de subastas judiciales de Justicia no es oferta**, pero cruza con el BOE sección IV y
   permite estimar el descuento medio entre tasación y subasta, útil como parámetro del plan
   (marcarlo `PROVISIONAL` hasta leerlo entero).
4. **Contradicción a vigilar:** `robots.txt` abierto no equivale a permiso. El RPC (robots vacío,
   aviso que prohíbe robots) y los BOP de Valencia y Sevilla lo muestran; y al revés, PLACSP y el
   Portal de Datos de Madrid tienen `Disallow: /` pese a ser datos abiertos.
5. **Lo que no he podido leer:** Sareb (403), ADIF (403), SEPES (certificado caducado), términos
   de DOGC, SUMA, ORGT y casa47.es, BOJA datos abiertos (`juntadeandalucia.es/datosabiertos`).
6. Correcciones menores: la página de subastas de Hacienda enlaza `rssabintestatos.aspx?hiloid=13`
   como «RSS de subastas y concursos», pero ese es el de abintestatos; el de subastas es
   `RssSubastas.aspx?hiloId=12`.
