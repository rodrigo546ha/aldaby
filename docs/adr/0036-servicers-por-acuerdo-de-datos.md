# ADR-0036: Servicers por acuerdo de datos; comisiones sin tocar la recomendación

**Estado:** Propuesta · **Fecha:** 2026-11-02 · **Decide:** Rodrigo. El 2026-11-02 aceptó cobrar
comisión (opciones b y c) con una condición: la recomendación no cambia por ella.

## Contexto
Los servicers (Solvia, Servihabitat, Aliseda, Altamira, Hipoges, Diglo…) tienen la mayor cartera
de pisos de bancos de España, y HouseFinder tiene que cubrir esa oferta. Sus condiciones de uso,
leídas el 2026-11-02 (`docs/research/f4-5-servicers.md`), prohíben reutilizar sus webs con fines
comerciales sin autorización escrita, y varias prohíben enlazar sus fichas sin autorización.
Ninguno publica una API ni un feed abierto. Sus programas para profesionales (prescriptor,
colaborador, red de asesores) pagan comisión por venta.

Opciones sobre la comisión que se discutieron:
- (a) HouseFinder no cobra nunca.
- (b) HouseFinder cobra, lo declara al usuario y la comisión no cambia la recomendación.
- (c) Cobra el cliente profesional (una agencia que usa HouseFinder), no HouseFinder.

## Decisión propuesta
1. **Ni scraping ni descargas automáticas** de las webs de los servicers sin su autorización
   (regla de oro 3).
2. **Acuerdo con cada servicer**: un feed, una API o un fichero periódico de su cartera, con
   permiso escrito para analizarla y mostrarla con cita y enlace. Se pide con
   `docs/research/borrador-correo-servicers.md`. Si el servicer solo ofrece un alta de
   prescriptor o colaborador con comisión, vale (opciones b y c).
3. **La comisión no entra en la recomendación** (regla de oro 7 de `CLAUDE.md`). La búsqueda
   inversa (`planning/ranking.py`), el plan, el agente y los argumentos para no comprar no
   reciben ningún dato de comisión: se calcula y se ordena con las cifras del usuario. Lo que se
   cobre por una oferta se guarda aparte, solo para facturar y para declararlo al usuario. Un
   test lo comprueba: el mismo orden con y sin comisión.
4. **Se declara.** Si HouseFinder o el profesional cobran por una oferta, el usuario lo ve en
   esa oferta.
5. **Mientras tanto**, el usuario puede pegar el texto de una ficha (F4.1). Que HouseFinder
   descargue el enlace de un dominio que prohíbe enlazar o reutilizar queda pendiente de la
   consulta legal (F0.6).
6. Cada acuerdo firmado es un canal (`offers/channels/`) con su propio ADR: formato, frecuencia,
   condiciones de cita y de conservación.

## Opciones consideradas
- **(a) Sin comisión nunca.** Lo más limpio, pero cierra la puerta más rápida de los servicers.
- **Ordenar por lo que cobramos.** Descartada: rompe la promesa del producto.
- **Leer las webs aunque las condiciones lo prohíban.** Descartada: regla de oro 3 y riesgo legal.

## Consecuencias
- La cobertura de los servicers depende de acuerdos comerciales: semanas o meses, y alguno dirá
  que no. Conviene pedirlos ya y en paralelo.
- El modelo de datos tiene que separar la comisión de la oferta, y la búsqueda inversa no puede
  leerla.
