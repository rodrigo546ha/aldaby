# Fuentes de datos

Todas públicas o aportadas por el usuario. Ninguna fuente entra en producción sin revisar sus
condiciones de reutilización y sin quedar registrada en la tabla `sources`.

| Capa | Fuente | Acceso | Fase | Estado |
| --- | --- | --- | --- | --- |
| Oferta | Enlace pegado por el usuario | El usuario aporta la página | F4 | Pendiente |
| Oferta | Portal de Subastas del BOE | Web pública; revisar condiciones | F4 | Pendiente |
| Oferta | Sumario del BOE, sección V | API de datos abiertos del BOE (esquema comprobado con sumarios reales) | F4 | Lectura y vigilancia hechas; subastas pendientes |
| Normativa | Sumarios del BOE (secciones I y III) y del BOCM | API del BOE; RSS `sumarios.rss` y sumario XML de cada boletín del BOCM | F2.6 | Vigilancia diaria con tareas de revisión |
| Oferta | Servicers: Solvia, Servihabitat, Aliseda, Altamira, Hipoges | Web pública; buscar acuerdo | F4 | Pendiente |
| Geografía | Secciones censales (INE), CartoCiudad (IGN), Catastro | Secciones: API OGC Features del INE, CC BY 4.0 con cita. CartoCiudad: geocodificador `find`, gratuito citando «CC BY 4.0 www.scne.es/productos.html#CartoCiudad» (ADR-0009). Catastro: servicios públicos | F3 | Secciones 2016–2025 de Madrid cargadas; geocodificación en uso con caché; Catastro pendiente |
| Demografía | Atlas de renta y padrón (INE), afiliación (Seguridad Social) | ADRH: API Tempus del INE, CC BY 4.0 con cita | F3 | ADRH 2015–2024 de Madrid cargado (renta y demografía); padrón y afiliación pendientes |
| Precios | Notariado, valor tasado (Ministerio), IPV (INE) | Público; revisar reutilización | F5 | Pendiente |
| Alquiler | Sistema Estatal de Referencia, IPVA (INE) | Público; acceso a revisar | F5 | Pendiente |
| Tipos | Trayectoria a 3 meses de las proyecciones del BCE (API, serie `MPD.Q.U2.STN.I.<ronda>.0000`) y Euríbor a un año oficial (BOE, resolución mensual del Banco de España) | Público; ADR-0006 | F1 | Decidida |
| Normativa | BOE, BOCM | Datos abiertos y revisión humana | F2 | Motor listo |

Fuera del MVP: portales inmobiliarios por scraping (prohibido sin ADR), conexión bancaria directa
(requiere proveedor con licencia), feeds de agencias y MLS (fase posterior), NPL y cesiones de remate.
