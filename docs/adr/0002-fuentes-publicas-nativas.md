# ADR-0002: Fuentes públicas y desarrollo propio, sin proveedores comerciales de datos

**Estado:** Aceptada · **Fecha:** 2026-10-27 · **Decide:** Rodrigo

## Contexto
Proveedores como Cassandra AI o idealista/data ofrecen APIs de pago, pero algunos son competidores y
pueden cambiar condiciones o cortar el acceso. El scraping de portales tiene riesgo legal
(derecho sui generis sobre bases de datos y términos de uso).

## Decisión
Construir sobre fuentes públicas (INE, Catastro, BOE, Banco de España, Ministerio de Vivienda),
datos aportados por el usuario y acuerdos directos. No hacer scraping de portales inmobiliarios sin
un ADR específico. El LLM se usa a través de una interfaz propia para poder sustituirlo.

## Consecuencias
- Más trabajo de limpieza y cruce de datos (F3, F5).
- Independencia y argumento comercial: «cifras de fuentes oficiales y modelos propios».
- La oferta de portales entra solo como enlace aportado por el usuario.
