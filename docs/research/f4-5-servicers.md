# F4.5 · Servicers: condiciones de uso y vías de acceso

Leído el 2026-11-02 en el navegador, una página cada vez, sin descargar anuncios ni automatizar
nada. Contexto: Rodrigo quiere cubrir toda España y cualquier inversión, sin descuidar la oferta de
pisos; los servicers tienen la mayor cartera de pisos de bancos. Regla de oro 3 de `CLAUDE.md`:
nada de scraping sin ADR aprobado.

## Resumen
Ningún servicer permite reutilizar su web para un servicio como el nuestro sin autorización
escrita, y cuatro (Aliseda, Diglo, Solvia, Servihabitat) tampoco permiten enlazar sus fichas sin
autorizarlo. Ninguno publica una API, un feed abierto ni datos abiertos. Todos tienen una puerta
comercial (prescriptor, colaborador, red de asesores, inversores), pensada para intermediarios
que cobran por traer compradores. **Eso choca con nuestra independencia («no vendemos activos»):
lo que hay que pedir es un acuerdo de datos sin comisión.** Ver el borrador de ADR-0036 y
`borrador-correo-servicers.md`.

## Por servicer

| Servicer | Web (titular) | `robots.txt` | Condiciones de uso | Puerta comercial | Ruta propuesta |
| --- | --- | --- | --- | --- | --- |
| **Solvia** | solvia.es (Solvia Servicios Inmobiliarios, S.A.U., A-86744349) | Bloquea `/api/` y `/ajax/` | Uso «propio y personal»; nada de «explotación comercial» sin autorización expresa (4.4.2); no «captar datos o contenidos con fines publicitarios» (4.4.5); sin *deep-links* ni *frames* sin autorización (6.2) | Alta de «prescriptor homologado» (`/es/login-profesional`) | Acuerdo de datos; contacto: web@solvia.es o atención al cliente |
| **Servihabitat** | servihabitat.com (Servihabitat Servicios Inmobiliarios, S.L.U., B-66082629) | Bloquea `/venta`, `/alquiler`, filtros y `Scrapy` | Prohibida «cualquier modalidad de explotación… sin autorización previa y expresa»; copia solo para uso personal; prohibido enlazar páginas distintas de la portada sin autorización | Portal de inversores (inversores.servihabitat.com, «8.548 activos», incluye «viviendas sin posesión»), «Delegados comerciales»; su política de privacidad recoge «peticiones de colaboración para la comercialización» | Acuerdo de datos; contacto: servihabitat@servihabitat.com |
| **Aliseda** (con Anticipa) | alisedainmobiliaria.com (Aliseda Servicios de Gestión Inmobiliaria, S.L.U., B-86875689) | Solo bloquea cuentas, reservas y parámetros | Prohibida la «extracción y/o reutilización del Sitio Web» y de la base de datos (derecho *sui generis*) sin autorización; prohibido **cualquier** enlace sin autorización previa, y solo a la portada | «Únete a nuestra red» (asesor inmobiliario), página de inversores | Acuerdo de datos; contacto: clientes@alisedainmobiliaria.com. Vende también activos de Sareb (publica las «CCGG Sareb») |
| **Altamira** | altamirainmuebles.com (doValue Spain Servicing, S.A., A86819596) | Bloquea `/resultados`, `/nuevaBusqueda`, `/activos/` y el aviso legal | Prohibido copiar o reproducir «para propósitos públicos o comerciales» sin autorización «previa, expresa y por escrito»; enlaces permitidos si no reproducen contenido | Formulario «¿Quieres colaborar con nosotros?» (`/profesionales`) | Acuerdo de datos por el formulario de profesionales |
| **Hipoges** | realestate.hipoges.com (Hipoges Iberia S.L., B85610228) | Permite todo | «Ningún material publicado en esta web podrá ser reproducido, copiado o publicado sin el consentimiento por escrito de HIPOGES» | inversores.es@hipoges.com; subastas.re@hipoges.com | Acuerdo de datos por correo a inversores |
| **Diglo** (Banco Santander) | digloservicer.com (Diglo Servicer Company 2021, S.L., B-67915298) | Solo bloquea administración y búsqueda interna | Igual que Aliseda: sin «extracción y/o reutilización» ni enlaces sin autorización previa | «Activos especiales para inversores» (`/oportunidades/web-inversores`) | Acuerdo de datos; contacto: departamento comercial (91 157 44 02) |
| **Sareb** | sareb.es | Su protección (Imperva) bloquea el acceso | No leídas: «Intento de acceso no autorizado» desde el navegador | Sus activos se venden también por Aliseda | Preguntar a Aliseda; no forzar el acceso |
| **Haya Real Estate** | haya.es | — | No leídas: el servidor no responde (Cloudflare 522) | — | Volver a mirar |
| **Casaktua** | casaktua.com | — | No leídas: su certificado TLS es de otro dominio | — | Volver a mirar |

## Lo que esto cambia en lo que ya tenemos
- **Enlace pegado (F4.1, ADR-0015).** Si un usuario pega el enlace de una ficha de Solvia,
  Servihabitat, Aliseda o Diglo, HouseFinder la descarga una vez y guarda su URL. Sus condiciones
  prohíben enlazar sus fichas sin autorización y reutilizar sus contenidos con fines comerciales.
  Hasta la consulta legal (F0.6), lo prudente es que en esos dominios el usuario **pegue el
  texto**, sin descarga, y que la URL no se muestre como enlace. Sin decidir: es una pregunta para
  la consulta legal.
- **Independencia.** Las altas de prescriptor y colaborador pagan comisión por venta. Si
  HouseFinder cobra de un vendedor, deja de ser independiente: no entrar por ahí.

## Preguntas abiertas
- Si alguno acepta un acuerdo de datos sin comisión, en qué formato (feed XML, API, fichero) y con
  qué frecuencia.
- Si sus fichas tienen referencia catastral: sin ella, la deduplicación (F4.6) va por dirección.
- La consulta legal (F0.6): enlaces profundos y descarga a petición del usuario en dominios que lo
  prohíben.
