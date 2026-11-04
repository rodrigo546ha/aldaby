# ADR-0054: Una sola lista de ofertas, con imagen pública de cada inmueble

**Estado:** Aceptada · **Fecha:** 2026-11-04 · **Decide:** Rodrigo («no hay que duplicar la info, ni
separarlas, además faltan imágenes, mejor estructuración de la información, filtrar los datos que nos
sean relevantes para el usuario, hacer la información más visible»; después, «confirmado que podemos
enseñar las fotos, ampliamos el mapa a toda España, se incluyen todas las ofertas»)

## Contexto
Tras U5 y U6 (ADR-0051, docs/PROPUESTA_UX.md) la misma oferta seguía saliendo en cuatro sitios:
- el mapa;
- la «Lista detallada» (`/busqueda`);
- «Tus anuncios» (`/ofertas`), con los avisos de subastas judiciales;
- «Anuncios públicos» (`/anuncios`), con el BOE y el Patrimonio en pestañas.

Además:
- Las subastas del BOE se enseñaban como documentos (anuncio → lotes), con identificadores, sección
  censal y citas de la extracción.
- El mapa solo enseñaba algo con el perfil confirmado: sin perfil, ninguna oferta.
- No había ninguna imagen, y todas las tarjetas tenían el mismo fondo y el mismo color.

## Decisión
1. **`GET /offers/catalog`** (`offers/catalog.py`, `db/offers.catalog_rows`) da en una lista todas las
   ofertas que el usuario puede ver: lotes del BOE sección V, del Portal de Subastas y del Patrimonio;
   anuncios de feeds de agencias; y sus anuncios pegados, confirmados o no. Cada una lleva:
   - cómo se vende: subasta judicial, administrativa o notarial, venta directa, agencia o anuncio
     propio;
   - un título corto («Vivienda en Cacín») y el lugar, con el municipio del anuncio y la provincia del
     código INE;
   - el precio o valor de subasta, el depósito y la superficie, copiados del anuncio (ninguna cifra se
     calcula);
   - en el Portal de Subastas: cuándo termina, su estado y la vivienda habitual del deudor;
   - la posesión, solo si consta y sin lo que va entre paréntesis, donde el Portal puede poner el
     nombre del titular;
   - si el BOE publicó después una corrección del anuncio.

   No salen las subastas ya terminadas ni las ventas directas con el plazo vencido.
2. **El plan, aparte:** la web pide el catálogo y, a la vez, la búsqueda inversa. Con perfil, cada
   oferta lleva su veredicto y su cash flow. Sin perfil, la lista se ve igual y una línea dice qué falta.
3. **Imagen de cada inmueble** (`geo/photos.py`, `offers/photos.py`), en este orden:
   - la del anuncio pegado;
   - la foto de fachada del Catastro (`OVCFotoFachada`, por la parcela);
   - la ortofoto del PNOA del IGN alrededor del punto, con el inmueble marcado;
   - sin ninguna, un dibujo del tipo de inmueble.

   `GET /offers/{id}/photo/{fachada|aerea}` la descarga cuando se pide, la reduce a 640 px y la guarda
   en memoria un día. No se escribe en disco ni en la base de datos, y el navegador del usuario no
   llama a terceros. La cita va en la imagen y en la cabecera `X-Attribution`. El recorte y la marca
   usan Pillow, que hasta ahora solo usaban `documents/` y `branding/`: `offers/` puede importarlo
   (`tests/test_architecture.py`).
4. **Navegación:**
   - El destino «Mapa» pasa a «Ofertas», sin secciones por canal. Mapa y lista son dos vistas de lo
     mismo.
   - «Añadir un anuncio» es una acción. Su página (`/ofertas`) solo pega y confirma, sin la lista de
     avisos de subastas.
   - Los supuestos de búsqueda pasan a «Mi plan» (`/busqueda`).
   - Los tipos de alquiler, con la renta esperada, pasan al plan de la oferta.
   - `/anuncios` lleva a la lista.
5. **Visibilidad:**
   - Cada forma de venta tiene su color (`--ch-*`, en los dos temas), siempre con su nombre al lado.
   - Las tarjetas tienen fondo propio (`--card`) y foto.
   - El precio va en grande. El cash flow del usuario va en latón y el veredicto, en verde.
   - Filtros por forma de venta y por tipo de inmueble, con su recuento.
   - En el mapa, el color dice el canal y un aro verde marca las que encajan.

6. **Todas las ofertas en el mapa** (2026-11-04, Rodrigo: «ampliamos el mapa a toda España, se
   incluyen todas las ofertas»):
   - **Teselas de toda España** (Península, Baleares, Canarias, Ceuta y Melilla) hasta zoom 15,
     también en local: `make mapa MAPA_BBOX=-18.4,27.5,4.6,44.0`. Son unos 4 GB y se descargan en
     8 minutos.
   - **Direcciones del Portal limpias** antes de CartoCiudad (`locate.clean_street`): sin piso,
     puerta, escalera, bloque ni código postal, con «Nº 4» → «4» y «NTRA SRA» → «Nuestra Señora».
   - **Municipios que coinciden en parte:** «Las Rozas» con «LAS ROZAS DE MADRID (MADRID)» y
     «Galapagar Parquelagos» con «GALAPAGAR».
   - **Punto aproximado:** si aun así no se ubica y el nombre del municipio da uno solo de su
     provincia, la oferta guarda el centro del municipio (`offers.approx_location`, migración
     0024). Se calcula con sus secciones censales. Sale en el mapa apagada, con «≈» y una nota en la
     ficha. No crea inmueble ni sección, así que el plan no la usa, y sin ortofoto, que sería de
     otro sitio.
   - **Trabajo `offers_relocate`:** vuelve a intentar a diario todos los lotes sin ubicar.

## Consecuencias
- Rodrigo confirmó el 2026-11-04 que se pueden enseñar las fotos de fachada. El aviso legal del
  Catastro autoriza reproducir sus contenidos citando el origen. Las fotos pueden sacar personas o
  matrículas: no se guardan y solo se enseñan del inmueble que se mira.
- Con la primera pasada se ubicaron 13 lotes más y 10 quedaron en su municipio. Quedan 4 fincas
  cuyo anuncio no da bien el municipio y una oferta pegada sin confirmar.
- La lectura del Portal de Subastas sigue siendo de la provincia de Madrid (ADR-0053). El BOE y el
  Patrimonio son de toda España.
- Una foto de fachada es la de la parcela: en un edificio con varios portales puede no ser la del
  portal del piso.
- El catálogo va entero en una petición (unas 300 ofertas). Con miles hará falta paginar o pedir por
  caja, como dice ADR-0051.
- Se borran `Announcements.tsx`, `DirectSales.tsx` y `PublicOffers.tsx`. Los endpoints `/boe/*` y
  `/patrimonio/*` siguen para el detalle y las pruebas.
