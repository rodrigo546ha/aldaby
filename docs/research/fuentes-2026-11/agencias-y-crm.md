# Agencias y CRM: cómo recibir su cartera con su permiso

Fecha de la consulta: 2026-11-02. Solo lectura de páginas públicas; no se crearon cuentas ni se rellenaron formularios.
«(leído)» = leído en la página citada. «(sin verificar)» = viene de un buscador, un resumen o un tercero, o no se pudo leer.
Veredictos: A = la agencia lo activa ya sin que el CRM negocie con nosotros; B = alta estándar del destino en el CRM; C = requiere petición o acuerdo con el CRM; D = no posible.

## 0. Hallazgo principal

La única vía con veredicto A es el **enlace XML en formato Kyero** que el CRM genera y la agencia nos da. Witei lo documenta así (leído, https://faq.witei.com/en/articles/865807-xml-export-with-your-properties): «Share this link with your external website or portal.»
Y para un portal que no está en su lista (leído, https://faq.witei.com/en/articles/113753-interconnection-to-the-real-estate-portal-activation-and-configuration): «You can export an XML file with your available properties and send it to the interconnection you want to publish.»

Dos CRM grandes pertenecen a portales competidores, lo que condiciona el resto:
- **Inmovilla es de idealista.** (leído, https://www.alimarket.es/construccion/noticia/353272/idealista-se-hace-con-la-proptech-inmovilla, 14/06/2022): «ha adquirido Inmovilla»; seguirá con gestión autónoma y «its agreements with partner portals».
- **Witei e Inmoweb son de Adevinta Spain, hoy dentro del grupo Fotocasa.** Witei: adquisición del 30/11/2023 (leído, https://onlinemarketplaces.com/articles/adevinta-spain-acquires-real-estate-crm-company-witei). Inmoweb: venta a Adevinta, 20/02/2023 (leído, https://capital-riesgo.es/es/articles/empresax-asesora-a-inmoweb-en-la-venta-a-adevinta/). Que ambos queden hoy en el grupo Fotocasa/Scout24 lo dice una sola fuente (sin verificar, https://www.onlinemarketplaces.com/articles/investment-and-ma-roundup-scout24-acquires-fotocasa/).
- Witei no ofrece interconexión con idealista (sin verificar; resumen de búsqueda sobre https://faq.witei.com/en/articles/118118-idealista, no leído).

Consecuencia: ni Inmovilla ni Witei/Inmoweb tienen incentivo para ayudar a un destino nuevo. Pero el enlace XML de Witei lo controla la agencia, no el CRM, así que sigue siendo A mientras Witei no lo retire.

## 1. CRM: cómo se añade un destino nuevo

| CRM | Cómo se añade un portal | ¿Cobra al portal? | Veredicto |
| --- | --- | --- | --- |
| **Witei** | Lista de interconexiones en Configuración > Gestor de propiedades > Interconexiones (leído). Si el portal no está: XML Kyero con enlace que la agencia copia y comparte (leído). Actualiza cada 60 min (leído). Máx. 50 fotos por inmueble (leído). La agencia marca el icono XML en cada inmueble que quiera incluir (leído). | No consta en la página; el coste de cada interconexión «lo fija el portal» (leído para pisos.com: «they decide the requirements for contracting»). | **A** (por XML Kyero). Soporte: chat. |
| **Sooprema** | Web: «Publica automáticamente en +70 portales inmobiliarios» (leído, https://www.sooprema.com/). Lista abierta: «Si no encuentras en la lista el portal en el que quieres anunciarte, consúltanos.» (leído, https://www.sooprema.com/portales-inmobiliarios/). Aparecen Kyero, idealista, Fotocasa, Habitaclia, pisos.com, yaencontre (leído). API REST con clave: para datos reales «la agencia en cuestión deberá ser cliente activo de Sooprema» (leído, https://www.sooprema.com/api-desarrolladores/); la clave se pide a estate@sooprema.com. | No consta. | **C** (petición al CRM, barrera baja; ya hay correo enviado). Si la agencia usa Sooprema y exporta a Kyero, vale la vía A. |
| **eGO Real Estate** | «more than 200 portals worldwide» (leído, https://www.egorealestate.com/en). Lista de ~118 portales: paquete base gratuito 42, «All the World's Portals» 73 y otros 3, ambos de pago adicional (leído, https://www.egorealestate.com/real-estate-portals). Para otro portal: «Tell us which one!» en formulario (leído). | La agencia paga suscripción adicional por los paquetes extra (leído). A los portales no consta. | **C** (se pide a eGO por formulario). Contacto: formularios de contacto. |
| **Inmovilla** | No pude leer su web (403). API para clientes, XML diario e iframe, y Tel. 966 673 149 (del repositorio, sin verificar). Una guía dice «+20 portales» (sin verificar). No hay documentación pública de la API que encontrara. | Sin datos. | **C**, probablemente **D** en la práctica por ser de idealista (sin verificar). |
| **Inmoweb** | Web inaccesible (ECONNREFUSED). Se conecta con portales y fuentes externas (del repositorio y de directorios, sin verificar). Ya hay correo a comercial@inmoweb.es. | Sin datos. | **C** (sin verificar). Grupo Fotocasa. |
| **Inmobalia** | «100+ portales» y franquicias; API y servidor MCP, aparte del MLS (leído, https://inmobalia.com/). «410+ agencias» y «20,000+ propiedades» en su MLS (leído). Que importe XML diario de Kyero y Resales Online es de un resumen de búsqueda (sin verificar). | Sin datos. | **C** (sin verificar). |
| **Casafari CRM** | Pestaña Propiedades > Exportar > Catálogo de portales, se elige Kyero, «Request registration» si no hay cuenta, «Activate» (leído, https://helpcenter.casafari.com/en/crm/how-can-i-export-my-properties-to-kyero). Para Fotocasa/Habitaclia hay que escribir a cliente@fotocasa.pro por API Key, AgentID y AgencyID (leído). | Sin datos. | **A** si exporta XML Kyero a una URL (sin verificar que dé URL libre); si no, **C**. No es un CRM de volumen en España (sin verificar). |
| **Resales Online, Apimo, onOffice** | Kyero los lista como CRM compatibles, según un resumen de búsqueda (sin verificar; la página https://www.kyero.com/en/join/features/integrations da 403 incluso con navegador). | — | Sin verificar. Para Resales Online, **C**. |
| **idealista/tools** | CRM de idealista (leído que existe: https://www.idealista.com/tools/centrodeayuda/etiquetas/inbox/). Sin lista abierta de destinos. | — | **D** (sin verificar). |
| **Statefox, Mobilia, Inmoenter, Ágora/Infocasa, Inmofactory, InmoPC, Inmogesco, Habitaclia/Fotocasa Pro** | No encontré documentación oficial. Directorios dicen que Mobilia y InmoPC exportan a portales; Inmofactory publica en «más de 60 portales» (sin verificar, https://www.softwaredoit.es/inmofactory/inmofactory.html). Fotocasa Pro no es un CRM sino el portal de agencias. Statefox, Inmoenter y Ágora no aparecieron en ninguna búsqueda. | — | Sin verificar. Tratar todos como **C**. |
| **Anaconda** | Software del MLS: el paquete «Integración MLS» incluye «Libertad integración de software en Anaconda» (leído, https://www.mls.es/contratacion/). | — | **C** (sin verificar). |

## 2. Formatos

| Formato | Estado | Conviene |
| --- | --- | --- |
| **Kyero XML v3** | Spec pública versión 3.9.1, enero 2026 (leído, https://help.kyero.com/estate-agents/xml-import-specification). Es una spec de lo que lee Kyero de la URL de la agencia, no de un receptor genérico. | **Sí, es el formato a implementar.** Cubre Witei (leído), Casafari (leído), Sooprema, Resales Online y Apimo/onOffice (sin verificar). Idealista e Inmobalia lo usan (sin verificar, https://www.wp-immomakler.de/en/kyero-idealista-inmobalia-immobilien-import-export-wordpress-plugin/). |
| OpenImmo | Estándar de la Europa germanohablante, mantenido por OpenImmo e.V. (sin verificar; fuentes secundarias). | No para España. |
| Formato de idealista o Fotocasa | No encontré spec pública; Fotocasa/Habitaclia usan API Key, AgentID y AgencyID dadas por Fotocasa Pro (leído, Casafari). | No viable sin acuerdo con cada portal. |
| RESO | En España solo el caso francés SNPI (~15.000 miembros) certificado (sin verificar, https://www.reso.org/blog/paris-certified-reso-global-vision/). | No para España hoy. |

Reglas del feed Kyero que condicionan nuestro lector (todas leídas en la spec):
- Cada URL contiene los inmuebles de un solo Kyero account o una sola agencia.
- La URL puede llevar usuario y contraseña, y no puede exigir pasos manuales.
- Es una foto completa: lo que falta se borra.
- `<id>` único y estable; `<date>` cambia cuando cambia el inmueble.
- Sin precio, provincia, población o tipo, no se publica.
- Hasta 50 fotos, UTF-8, sin CDATA.
- No dice nada sobre otro receptor. Lleva «Copyright © 2026, Kyero.com» sin licencia: preguntar a Kyero si leer ese formato requiere permiso.

Mecanismo sugerido (sin verificar como diseño): la agencia pega en Aldaby el enlace de su feed; descargamos una vez al día. Como pegar un enlace es el patrón actual (ADR-0015), no hace falta que el CRM haga nada.

## 3. MLS y redes de colaboración

| Red | Datos | Veredicto |
| --- | --- | --- |
| **MLS.es** | «Es la bolsa inmobiliaria común española de inmuebles»; «Servicio exclusivo para profesionales»; «más de 700 oficinas en España» (leído, https://www.mls.es/mls/). Planes con «Operar desde tu CRM» (leído, https://www.mls.es/contratacion/). No describen API ni acceso de terceros. mls@mls.es (del repositorio). | **D** salvo acuerdo; no es una agencia, es una red de agencias. |
| **IAGestión** | «Gestión de MLS Redes de colaboración»; «MCP y API NUEVO»; «+50 portales integrados» (leído, https://www.iagestion.com). Sin condiciones de terceros. | **C** (sin verificar). |
| **Inmobalia MLS** | «share properties to offer to their buyers»; la agencia que lista decide si otros pueden publicar en webs o portales; el MLS está separado del acceso por API (leído, https://inmobalia.com/). | **C**: el permiso lo da cada agencia por inmueble. |
| MLS Internacional, AMI MLS, Inmobiliarias en red | No consultadas. | Sin verificar. |

CNMC S/0003/20 (nota de prensa leída, 09/12/2021, https://www.cnmc.es/prensa/sancionador-proptech-cnmc-intermediacion-inmobiliaria-cnmc-20211209): el reglamento del MLS exigía «comisión mínima del 4 % en ventas y de un mes en alquileres»; «Las empresas de software también participaron en la conducta anticompetitiva». Multas por empresa (idealista 730.000 €, Inmovilla 83.149 €, Witei 18.925 € tras reducción del 45 %, Anaconda 1.749 €, etc.) vienen de prensa y varían entre fuentes (sin verificar). Hubo recurso anunciado por idealista (sin verificar). Regla para nosotros: no recibir ni mostrar comisiones; ya lo fija el ADR-0036.

## 4. Cuota de mercado

No hay cifra de cuota de ningún CRM con fuente fiable. Lo publicado:
- Inmovilla: «4,000 clientes en Spain» en 2022 (leído, Alimarket; no aclara si son agencias). Un agregador dice «más de 3 mil agencias» (sin verificar, resumen de búsqueda).
- MLS.es: más de 700 oficinas (leído).
- Inmobalia: 410+ agencias en su red (leído).
- Witei, Inmoweb, Sooprema, eGO, Mobilia, Statefox, Inmoenter: ninguna cifra encontrada. Witei tiene 7 empleados, Inmoweb 9 (leído, noticias de compra), lo que sugiere bases pequeñas pero no es dato de clientes.
- Fotocasa+Habitaclia: ~14.000 clientes agencia como portales, no como CRM (sin verificar).
- Guías que llaman a Inmovilla «el más usado» no citan fuente (sin verificar).

## 5. Lo que hace falta legalmente (solo lo citado, sin opinión jurídica)

- **Portales como encargados del tratamiento.** Guía de despacho: idealista, Fotocasa y Habitaclia son «Encargado del tratamiento de la agencia que publica»; las agencias firman las condiciones de datos de cada portal; antes de publicar, el propietario recibe información sobre la publicación en portales, la finalidad y el plazo (leído, https://www.legiscope.com/blog/rgpd-agencias-inmobiliarias.html; fuente secundaria). Base jurídica de la captación: el contrato de mandato (leído). Recomienda contratos del art. 28 con «CRM, portales, MLS, gestoría» (leído).
- **MLS:** «Contrato art. 26 RGPD (corresponsables) o art. 28 (encargado) según modelo.» (leído, misma guía).
- **Resoluciones de la AEPD encontradas (resumen de búsqueda, sin verificar):** corresponde al responsable comprobar el consentimiento; multa de 2.000 € por usar datos de propietarios de anuncios para ofrecer otro servicio (finalidad que excede la del anuncio); multa de 5.000 € por no informar (art. 13). Nada trata directamente la cesión de una cartera a un tercero.
- **Fotos:** no encontré fuente específica de fotos de inmuebles. Marco general (sin verificar): la ley distingue obra fotográfica y «meras fotografías» (Título V del TRLPI); la cesión de derechos debe ser por escrito y concretar derechos y modalidades (https://elderecho.com/aspectos-legales-de-la-fotografia). El fotógrafo suele ser un tercero distinto de la agencia: pendiente de mirar el contrato de la agencia con él.
- **Datos del anunciante:** nuestro destino no necesita nombre ni teléfono del propietario. Pedirle a la agencia un feed sin ellos reduce lo que habría que justificar (diseño nuestro, no de fuente). Los datos de los inmuebles de particulares quedan fuera de nuestras reglas del RGPD solo si no los guardamos; decidir en un ADR.
- Pendiente de abogado: qué texto de consentimiento necesita la agencia con el propietario para ceder el anuncio a un tercero distinto de un portal, y si la agencia puede ceder las fotos.

## 6. Orden de contacto recomendado

1. **Sooprema** (ya escrito): independiente, lista abierta, API con clave, 70+ portales.
2. **eGO Real Estate**: independiente, 200+ portales, formulario para pedir destino nuevo.
3. **Inmobalia**: independiente, 410+ agencias, API y MLS con permiso por inmueble.
4. Kyero: preguntar si leer su formato como receptor requiere permiso y qué CRM lista como compatibles.
5. En paralelo, sin contactar al CRM: captar agencias que usen **Witei** y pedirles el enlace XML (A).
6. Después: Inmoweb (correo ya escrito; grupo Fotocasa), Inmovilla (idealista).

## 7. Huecos

Sin leer: webs de Inmovilla (403), Inmoweb (rechaza conexión), Kyero integraciones (403). No hay búsqueda útil de Statefox, Mobilia, Inmoenter, Ágora, Anaconda ni AMI MLS. El buscador devuelve poco sobre estas pymes: hace falta consultar sus webs a mano.
