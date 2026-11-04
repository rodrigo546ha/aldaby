# Fuentes de datos

Todas públicas o aportadas por el usuario. Ninguna fuente entra en producción sin revisar sus
condiciones de reutilización y sin quedar registrada en la tabla `sources`.

| Capa | Fuente | Acceso | Fase | Estado |
| --- | --- | --- | --- | --- |
| Oferta | Enlace pegado por el usuario | Una descarga a petición del usuario, respetando `robots.txt` y los bloqueos; si no, texto pegado (ADR-0015) | F4 | Hecho; pendiente de la consulta legal (F0.6) |
| Ubicación | Servicio de coordenadas del Catastro (`Consulta_CPMRC`, WCF/JSON) | Consulta por referencia catastral, datos no protegidos, sin registro; cita «Fuente: Dirección General del Catastro» (ADR-0016) | F4 | En uso para ubicar ofertas; condiciones por verificar |
| Ubicación | Callejero del Catastro (`Consulta_DNPPP`, WCF/JSON) | Referencia de una finca rústica por provincia, municipio, polígono y parcela; mismo host y condiciones que `Consulta_CPMRC`; `ovc.catastro.meh.es` no tiene `robots.txt` (404, comprobado el 2026-11-01) (ADR-0031) | F4 | En uso para lotes rústicos del BOE; condiciones por verificar |
| Ubicación | Catastro foral de Gipuzkoa (WFS INSPIRE, `b5m.gipuzkoa.eus/inspire/wfs/gipuzkoa_wfs_cp`) | Parcela por referencia; reutilización libre indicando la autoría; sin `robots.txt` (ADR-0032) | F4 | En uso para lotes de Gipuzkoa |
| Ubicación | Catastro foral de Bizkaia (WFS INSPIRE, `geo.bizkaia.eus`) | Parcela por referencia `48.MMM.PPPP.NNNNN`; sin condiciones declaradas, por verificar; sin `robots.txt` (ADR-0032) | F4 | En uso |
| Ubicación | Catastro foral de Álava (WFS INSPIRE, `geo.araba.eus/geoserver/INSPIRE_CP/wfs`) | Parcela por referencia de 8 cifras; sin condiciones declaradas, por verificar; `robots.txt` no veta el WFS (ADR-0032) | F4 | En uso |
| Imagen | Foto de fachada del Catastro (`OVCFotoFachada`, `RecuperarFotoFachadaGet`) | Por los 14 caracteres de la parcela; mismo host que `Consulta_CPMRC`, sin `robots.txt`; el aviso legal del Catastro autoriza la reproducción «siempre que se cite expresamente su origen» y no dice nada concreto de las fotos; cita «Foto de fachada: Dirección General del Catastro» (ADR-0054) | F8 | En uso en la lista de ofertas; no se guarda; uso confirmado por Rodrigo el 2026-11-04 |
| Imagen | Ortofoto PNOA del IGN (WMS `www.ign.es/wms-inspire/pnoa-ma`, capa `OI.OrthoimageCoverage`) | Recorte de 640 × 400 px alrededor del inmueble; el GetCapabilities declara «CC BY 4.0 scne.es»; sin `robots.txt` (404); cita «Ortofoto PNOA: CC BY 4.0 scne.es» (ADR-0054) | F8 | En uso cuando no hay foto de fachada; no se guarda |
| Ubicación | Parcelas catastrales de Navarra (IDENA, `idena.navarra.es/ogc/wfs`) | Parcela por municipio, polígono y parcela; CC BY 4.0 citando la fuente; `robots.txt` veta `/ogc/wms`, no `/ogc/wfs` (ADR-0032) | F4 | En uso |
| Ubicación | Relación de provincias con sus códigos (INE) | Tabla de la web del INE, copiada una vez en `data/offers/provincias.yaml` el 2026-11-01; `robots.txt` del INE no prohíbe esa ruta (ADR-0031) | F4 | Por revisar (`verified: false`) |
| Oferta | Portal de Subastas del BOE | Web pública; `robots.txt` prohíbe el acceso automático: no se lee (ADR-0017) | F4 | Consulta enviada: el soporte del Portal respondió el 2026-11-03 que no hay acceso automático ni integración (Ley 19/2015, DA 2.ª) |
| Oferta | Sumario del BOE, sección IV (avisos de subastas judiciales) | API de datos abiertos del BOE; reutilización con cita y enlace | F4 | Canal `boe_subastas_judiciales`: avisos de juzgados de Madrid con enlace al Portal |
| Oferta | Sumario del BOE, sección V | API de datos abiertos del BOE; reutilización con cita y enlace (aviso legal del BOE) | F4 | Canal `boe_seccion_v`: anuncios guardados cada día, lotes por extraer; Portal de Subastas pendiente |
| Normativa | Sumarios del BOE (secciones I y III) y del BOCM | API del BOE; RSS `sumarios.rss` y sumario XML de cada boletín del BOCM | F2.6 | Vigilancia diaria con tareas de revisión |
| Oferta | Servicers: Solvia, Servihabitat, Aliseda, Altamira, Hipoges | Web pública; buscar acuerdo | F4 | Pendiente |
| Geografía | Secciones censales (INE), CartoCiudad (IGN), Catastro | Secciones: API OGC Features del INE, CC BY 4.0 con cita. CartoCiudad: geocodificador `find` (y `candidates` para el código INE de un municipio por su nombre, ADR-0031), gratuito citando «CC BY 4.0 www.scne.es/productos.html#CartoCiudad» (ADR-0009). Catastro: servicios públicos | F3 | Secciones 2016–2025 de Madrid; 2025 del resto de España (2026-11-01, para ubicar ofertas, ADR-0031); geocodificación en uso con caché; Catastro en uso (ADR-0016, ADR-0031) |
| Demografía | Atlas de renta y padrón (INE), afiliación (Seguridad Social) | ADRH: API Tempus del INE, CC BY 4.0 con cita | F3 | ADRH 2015–2024 de Madrid cargado (renta y demografía); padrón y afiliación pendientes |
| Precios | Notariado, valor tasado (Ministerio), IPV (INE) | Público; revisar reutilización | F5 | Pendiente |
| Alquiler | Sistema Estatal de Referencia, IPVA (INE) | Público; acceso a revisar | F5 | Pendiente |
| Tipos | Trayectoria a 3 meses de las proyecciones del BCE (API, serie `MPD.Q.U2.STN.I.<ronda>.0000`) y Euríbor a un año oficial (BOE, resolución mensual del Banco de España) | Público; ADR-0006 | F1 | Decidida |
| Normativa | BOE, BOCM | Datos abiertos y revisión humana | F2 | Motor listo |
| Alquiler | SERPAVI (Ministerio de Vivienda y Agenda Urbana): mediana, P25 y P75 de €/m² mes por sección, distrito y municipio | Excel 2011–2024 en cdn.mivau.gob.es; reutilización libre citando fuente y fecha (aviso legal del Ministerio) | F5 | Cargado (`make serpavi`), ADR-0018 |
| Precio | Valor tasado de la vivienda libre (Ministerio de Vivienda), copia de la Comunidad de Madrid | CSV anual 2005–2025, municipios de más de 25.000 habitantes; CC BY 4.0. El `robots.txt` del portal prohíbe el acceso automático: descarga manual | F5 | Cargado a mano (`make valor-tasado FICHERO=…`), ADR-0018 |
| Precio | Índice de Precios de Vivienda (INE), tabla 80270 | API del INE, trimestral, base 2025, por comunidad autónoma | F5 | Cargado (`make ipv`), ADR-0018 |
| Alquiler | IPC (INE), subgrupo 04.1 Alquiler de vivienda por comunidad, tabla 76137 | API del INE, mensual, base 2025 | F5 | Cargado (`make ipc-alquiler`); actualiza la renta del SERPAVI, ADR-0018 |
| Hipotecas | Banco de España, Boletín Estadístico 19.4: TEDR de nuevas operaciones de crédito a la vivienda por periodo de fijación | CSV mensual nacional desde 2003; citar al Banco de España sin alterar los datos | F6 | Cargado (`make supuestos`), ADR-0022: tipo fijo y subida del estrés |
| Hipotecas | INE, Estadística de Hipotecas, tabla 76315 | API del INE, mensual, nacional (fijo, variable y total) | F6 | Cargado, solo contraste (ADR-0022) |
| Catastro | Estadísticas catastrales urbanas por municipio (`URBANA{año}.xls`) | XLS anual; reproducción autorizada citando el origen | F6 | Cargado 2026 de Madrid (ADR-0022): valor catastral residencial medio y parte de construcción |
| Impuestos | Ministerio de Hacienda, Oficina Virtual EELL: tipos del IBI por municipio | PDF anual por comunidad (municipios de más de 1.000 habitantes); reutilización citando la fuente | F6 | Reglas `tipo_ibi` sin verificar en `data/rules/ibi_hacienda_2026.yaml` (ADR-0022) |
| Impuestos | Ministerio de Hacienda, Oficina Virtual EELL: tipo y coeficientes de la plusvalía municipal por municipio | El mismo PDF, tercera parte; sin robots.txt en el servidor | F6 | Reglas `tipo_plusvalia` y `coeficientes_plusvalia` sin verificar en `data/rules/plusvalia_hacienda.yaml` (ADR-0044) |
| Gastos | INE, Encuesta de Presupuestos Familiares, tabla 73993 | API del INE, anual, por comunidad: gastos comunitarios, seguros y mantenimiento de la vivienda | F6 | Cargado 2023–2025 (ADR-0022); medias de todos los hogares, se quedan cortas |
| Precio | Portal Estadístico del Notariado | Visor con registro; términos: uso personal, sin uso comercial | F5 | Descartado sin autorización escrita |

Fuera del MVP: portales inmobiliarios por scraping (prohibido sin ADR), conexión bancaria directa
(requiere proveedor con licencia), feeds de agencias y MLS (fase posterior), NPL y cesiones de remate.
