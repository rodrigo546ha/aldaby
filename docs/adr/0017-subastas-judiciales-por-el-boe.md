# ADR-0017: Subastas judiciales por los avisos del BOE, sin leer el Portal de Subastas

**Estado:** Aceptada · **Fecha:** 2026-10-29 · **Decide:** Rodrigo
Investigación: `docs/research/f4-3-portal-subastas.md`.

## Contexto
F4.3 pide las subastas del Portal de Subastas del BOE para la provincia de Madrid. El Portal
prohíbe todo acceso automático (`robots.txt`: `User-agent: *` / `Disallow: /`) y no ofrece
datos abiertos. Cada subasta judicial tiene, en cambio, un anuncio en la sección IV del BOE, que
leemos por la API de datos abiertos; el anuncio solo dice el juzgado, el tipo de subasta, el
número del procedimiento y el enlace al Portal, no qué se subasta.

## Decisión
- **Nunca se lee el Portal de forma automática:** ni rastreo ni descarga única del enlace pegado
  (la de ADR-0015 ya la rechaza por su `robots.txt`).
- **Canal `boe_subastas_judiciales`:** de cada sumario, los anuncios de la sección IV cuyo título
  (la localidad del juzgado) es la sede de un partido judicial de la Comunidad de Madrid. De cada
  uno se descarga su XML del BOE y se guarda como oferta pública `kind = 'anuncio'`:
  - identificador estable: el de la subasta en el Portal (`SUB-JA-2026-267866`), para no
    duplicarla si el BOE la publica más de una vez;
  - juzgado, tipo de subasta (vía de apremio o voluntaria), número de procedimiento, enlace al
    Portal y anuncio del BOE del que sale;
  - `extraction_status = 'no_aplica'`: no hay nada que extraer del aviso.
- **Partidos judiciales como datos:** la lista de sedes va en
  `data/offers/subastas_boe.yaml`, con su fuente y `verified: false` hasta que Rodrigo la compare
  con el anexo de la Ley 38/1988 de Demarcación y de Planta Judicial (el texto consolidado del BOE
  lo omite y remite a la web del Ministerio de Justicia). Un aviso de una sede que falte en la lista
  se pierde sin aviso: por eso la lista se verifica.
- **Del aviso al inmueble, a mano:** la página de ofertas lista los avisos recientes con su enlace.
  El usuario abre el Portal en su navegador, copia el texto del lote y lo pega (F4.1); la
  extracción con citas y la confirmación hacen el resto. La oferta pegada guarda el enlace al
  Portal.
- **Vía de datos completa:** se pide a la Agencia Estatal BOE una vía de reutilización de los datos
  del Portal (opción B de la investigación). Si llega, otro ADR.

## Opciones consideradas
- **Leer el Portal de forma automática:** contra su `robots.txt`. Descartado.
- **Guardar todos los avisos de España:** unos 88 por día con sección IV; solo interesan los de
  Madrid (MVP). Descartado; el filtro se amplía cambiando el fichero de datos.

## Consecuencias
- Unos 13 avisos a la semana de juzgados de Madrid (9–28 de octubre de 2026), sin saber cuántos son
  inmuebles hasta que el usuario abre el enlace.
- El canal cumple «cada día entran ofertas nuevas» solo los días con sección IV (8 de 17 diarios en
  la medición) y con datos pobres: la oferta útil depende del usuario o de la respuesta de la
  AEBOE.
- Reutilización del BOE con cita y enlace, como la sección V.
