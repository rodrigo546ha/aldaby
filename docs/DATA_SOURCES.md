# Fuentes de datos

Todas públicas o aportadas por el usuario. Ninguna fuente entra en producción sin revisar sus
condiciones de reutilización y sin quedar registrada en la tabla `sources`.

| Capa | Fuente | Acceso | Fase | Estado |
| --- | --- | --- | --- | --- |
| Oferta | Enlace pegado por el usuario | El usuario aporta la página | F4 | Pendiente |
| Oferta | Portal de Subastas del BOE | Web pública; revisar condiciones | F4 | Pendiente |
| Oferta | Sumario del BOE, sección V | API de datos abiertos del BOE (verificar) | F4 | Esqueleto |
| Oferta | Servicers: Solvia, Servihabitat, Aliseda, Altamira, Hipoges | Web pública; buscar acuerdo | F4 | Pendiente |
| Geografía | Secciones censales (INE), CartoCiudad (IGN), Catastro | Descarga y servicios públicos | F3 | Pendiente |
| Demografía | Atlas de renta y padrón (INE), afiliación (Seguridad Social) | Descarga pública | F3 | Pendiente |
| Precios | Notariado, valor tasado (Ministerio), IPV (INE) | Público; revisar reutilización | F5 | Pendiente |
| Alquiler | Sistema Estatal de Referencia, IPVA (INE) | Público; acceso a revisar | F5 | Pendiente |
| Tipos | Trayectoria a 3 meses de las proyecciones del BCE (API, serie `MPD.Q.U2.STN.I.<ronda>.0000`) y Euríbor a un año oficial (BOE, resolución mensual del Banco de España) | Público; ADR-0006 | F1 | Decidida |
| Normativa | BOE, BOCM | Datos abiertos y revisión humana | F2 | Motor listo |

Fuera del MVP: portales inmobiliarios por scraping (prohibido sin ADR), conexión bancaria directa
(requiere proveedor con licencia), feeds de agencias y MLS (fase posterior), NPL y cesiones de remate.
