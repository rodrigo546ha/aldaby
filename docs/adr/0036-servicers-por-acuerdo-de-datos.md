# ADR-0036: Servicers por acuerdo de datos, sin comisión

**Estado:** Propuesta · **Fecha:** 2026-11-02 · **Decide:** Rodrigo (pendiente)

## Contexto
Los servicers (Solvia, Servihabitat, Aliseda, Altamira, Hipoges, Diglo…) tienen la mayor cartera
de pisos de bancos de España, y HouseFinder tiene que cubrir esa oferta. Sus condiciones de uso,
leídas el 2026-11-02 (`docs/research/f4-5-servicers.md`), prohíben reutilizar sus webs con fines
comerciales sin autorización escrita, y varias prohíben enlazar sus fichas sin autorización.
Ninguno publica una API ni un feed abierto. Sus programas para profesionales (prescriptor,
colaborador, red de asesores) pagan comisión por venta.

## Decisión propuesta
1. **Ni scraping ni descargas automáticas** de las webs de los servicers (regla de oro 3).
2. **Acuerdo de datos con cada servicer**: un feed, una API o un fichero periódico de su cartera,
   con permiso escrito para analizarla y mostrarla a nuestros usuarios con cita y enlace. Se pide
   con `docs/research/borrador-correo-servicers.md`.
3. **Sin comisión.** HouseFinder no se da de alta como prescriptor ni colaborador que cobre por
   venta: perdería la independencia («no vendemos activos»). Si un servicer solo ofrece eso, se
   descarta hasta que Rodrigo decida otra cosa.
4. **Mientras tanto**, el usuario puede pegar el texto de una ficha (F4.1). Que HouseFinder
   descargue el enlace de un dominio que prohíbe enlazar o reutilizar queda pendiente de la
   consulta legal (F0.6).
5. Cada acuerdo firmado es un canal (`offers/channels/`) con su propio ADR: formato, frecuencia,
   condiciones de cita y de conservación.

## Opciones consideradas
- **Alta de prescriptor o colaborador.** Es la puerta más rápida, pero cobra por venta: rompe la
  independencia.
- **Leer las webs aunque las condiciones lo prohíban.** Descartada: regla de oro 3 y riesgo legal.
- **Esperar a que los usuarios peguen fichas.** Ya funciona, pero no da cobertura: el usuario
  tiene que encontrar el piso antes que nosotros.

## Consecuencias
- La cobertura de los servicers depende de acuerdos comerciales: semanas o meses, y alguno dirá
  que no. Conviene pedirlos ya y en paralelo.
- El acuerdo puede exigir condiciones (no mostrar precios, plazos de conservación, marca). Cada
  canal las recoge en su ADR.
