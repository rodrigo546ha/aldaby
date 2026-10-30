# Fuentes de datos

Todas públicas o aportadas por el usuario. Ninguna fuente entra en producción sin revisar sus
condiciones de reutilización y sin quedar registrada en la tabla `sources`.

| Capa | Fuente | Acceso | Fase | Estado |
| --- | --- | --- | --- | --- |
| Oferta | Enlace pegado por el usuario | Una descarga a petición del usuario, respetando `robots.txt` y los bloqueos; si no, texto pegado (ADR-0015) | F4 | Hecho; pendiente de la consulta legal (F0.6) |
| Ubicación | Servicio de coordenadas del Catastro (`Consulta_CPMRC`, WCF/JSON) | Consulta por referencia catastral, datos no protegidos, sin registro; cita «Fuente: Dirección General del Catastro» (ADR-0016) | F4 | En uso para ubicar ofertas; condiciones por verificar |
| Oferta | Portal de Subastas del BOE | Web pública; `robots.txt` prohíbe el acceso automático: no se lee (ADR-0017) | F4 | Consulta de reutilización a la AEBOE por enviar |
| Oferta | Sumario del BOE, sección IV (avisos de subastas judiciales) | API de datos abiertos del BOE; reutilización con cita y enlace | F4 | Canal `boe_subastas_judiciales`: avisos de juzgados de Madrid con enlace al Portal |
| Oferta | Sumario del BOE, sección V | API de datos abiertos del BOE; reutilización con cita y enlace (aviso legal del BOE) | F4 | Canal `boe_seccion_v`: anuncios guardados cada día, lotes por extraer; Portal de Subastas pendiente |
| Normativa | Sumarios del BOE (secciones I y III) y del BOCM | API del BOE; RSS `sumarios.rss` y sumario XML de cada boletín del BOCM | F2.6 | Vigilancia diaria con tareas de revisión |
| Oferta | Servicers: Solvia, Servihabitat, Aliseda, Altamira, Hipoges | Web pública; buscar acuerdo | F4 | Pendiente |
| Geografía | Secciones censales (INE), CartoCiudad (IGN), Catastro | Secciones: API OGC Features del INE, CC BY 4.0 con cita. CartoCiudad: geocodificador `find`, gratuito citando «CC BY 4.0 www.scne.es/productos.html#CartoCiudad» (ADR-0009). Catastro: servicios públicos | F3 | Secciones 2016–2025 de Madrid cargadas; geocodificación en uso con caché; Catastro pendiente |
| Demografía | Atlas de renta y padrón (INE), afiliación (Seguridad Social) | ADRH: API Tempus del INE, CC BY 4.0 con cita | F3 | ADRH 2015–2024 de Madrid cargado (renta y demografía); padrón y afiliación pendientes |
| Precios | Notariado, valor tasado (Ministerio), IPV (INE) | Público; revisar reutilización | F5 | Pendiente |
| Alquiler | Sistema Estatal de Referencia, IPVA (INE) | Público; acceso a revisar | F5 | Pendiente |
| Tipos | Trayectoria a 3 meses de las proyecciones del BCE (API, serie `MPD.Q.U2.STN.I.<ronda>.0000`) y Euríbor a un año oficial (BOE, resolución mensual del Banco de España) | Público; ADR-0006 | F1 | Decidida |
| Normativa | BOE, BOCM | Datos abiertos y revisión humana | F2 | Motor listo |
| Alquiler | SERPAVI (Ministerio de Vivienda y Agenda Urbana): mediana, P25 y P75 de €/m² mes por sección, distrito y municipio | Excel 2011–2024 en cdn.mivau.gob.es; reutilización libre citando fuente y fecha (aviso legal del Ministerio) | F5 | Cargado (`make serpavi`), ADR-0018 |
| Precio | Valor tasado de la vivienda libre (Ministerio de Vivienda), copia de la Comunidad de Madrid | CSV anual 2005–2025, municipios de más de 25.000 habitantes; CC BY 4.0. El `robots.txt` del portal prohíbe el acceso automático: descarga manual | F5 | Cargado a mano (`make valor-tasado FICHERO=…`), ADR-0018 |
| Precio | Índice de Precios de Vivienda (INE), tabla 80270 | API del INE, trimestral, base 2025, por comunidad autónoma | F5 | Cargado (`make ipv`), ADR-0018 |
| Alquiler | IPC (INE), subgrupo 04.1 Alquiler de vivienda por comunidad, tabla 76137 | API del INE, mensual, base 2025 | F5 | Cargado (`make ipc-alquiler`); actualiza la renta del SERPAVI, ADR-0018 |
| Precio | Portal Estadístico del Notariado | Visor con registro; términos: uso personal, sin uso comercial | F5 | Descartado sin autorización escrita |

Fuera del MVP: portales inmobiliarios por scraping (prohibido sin ADR), conexión bancaria directa
(requiere proveedor con licencia), feeds de agencias y MLS (fase posterior), NPL y cesiones de remate.
