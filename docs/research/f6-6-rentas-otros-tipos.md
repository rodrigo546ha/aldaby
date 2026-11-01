# F6.6 · Fuentes públicas de rentas para temporada, habitaciones y turístico

Investigación del 2026-10-31, antes del ADR de F6.6. Pregunta: ¿hay una fuente pública que dé, en
euros y por zona, lo que se cobra por un alquiler de temporada, por habitaciones o turístico en la
Comunidad de Madrid? Para el alquiler habitual ya está el SERPAVI (ADR-0018).

## Resultado

**No hay ninguna fuente pública con precios en euros para esos tres tipos.** Las que existen dan
oferta u ocupación, no precio; la única con precios es privada y no permite reutilizarla.

| Fuente | Qué da | Nivel | ¿Precio en €? | Reutilización |
|---|---|---|---|---|
| INE, *Medición del número de viviendas turísticas* (experimental) | Viviendas turísticas, plazas, % sobre el total de viviendas | Municipio, distrito y sección; semestral (mayo y noviembre) | No | INE (CC BY 4.0) |
| INE, *Estimación de la ocupación … a partir de plataformas digitales* (experimental) | Alojamientos ocupados, noches ocupadas, estancia media, pernoctaciones (grupo 55.2 entero, no solo viviendas turísticas) | Nacional, comunidad, provincia y puntos turísticos; mensual | No | INE (CC BY 4.0) |
| INE, *Encuesta de ocupación en apartamentos turísticos* e IPAP | Ocupación de apartamentos turísticos reglados e índice de precios | Comunidad, provincia, puntos turísticos | No: el IPAP es un índice, no un nivel | INE |
| Dataestur (SEGITTUR), datos de MABRIAN | Precio medio por noche por tipo (casa entera, apartamento, habitación privada o compartida), valoraciones | Provincia, mensual (SEGITTUR tiene la sección censal, solo para gestores de destino) | Sí | Proveedor privado; el aviso legal prohíbe la reproducción «sin autorización expresa por escrito» |
| Eurostat, alojamiento reservado en plataformas | Noches, estancias, huéspedes | Público hasta NUTS 2; el nivel municipal solo llega a los institutos de estadística | No | Eurostat |
| Fianzas de la Comunidad de Madrid | Memorias anuales con datos generales | Sin desglose público por municipio ni por tipo | No | — |
| Alquiler de habitaciones y de temporada (media estancia) | Solo índices de portales privados | Barrio o ciudad | Sí | Privados (CLAUDE.md, regla 3) |

Además, el INE avisa de que sus dos estadísticas experimentales «no puede[n] analizarse de manera
conjunta», porque miden poblaciones distintas: no se puede sacar una ocupación por vivienda
turística dividiendo una entre otra.

## Consecuencias para F6.6

- Una renta estimada de esos tipos sería una cifra inventada (regla 4) o vendría de un proveedor
  comercial (regla 3).
- Caminos posibles:
  1. Normativa de cada tipo (requisitos, reducción del IRPF, estabilidad) y cifras solo para el
     alquiler habitual.
  2. Lo mismo, y la renta que el usuario espera de cada tipo como supuesto suyo, PROVISIONAL.
  3. Pedir a SEGITTUR (dataestur@segittur.es) autorización por escrito para reutilizar los
     precios de MABRIAN. Aun con ella, son precios de oferta de una foto mensual por provincia,
     sin ocupación: no bastan para estimar ingresos.

## Fuentes

- https://www.ine.es/experimental/viv_turistica/experimental_viv_turistica.htm
- https://www.ine.es/experimental/viv_turistica/exp_viv_turistica_tablas.htm
- https://www.ine.es/experimental/ocupacion/experimental_ocupacion.htm y su proyecto técnico
  (`exp_ocupacion_plataforma.pdf`, apartados 3.5, 6 y 7)
- https://www.dataestur.es/alojamientos/viviendas-de-uso-turistico/
- https://www.dataestur.es/blog/datos-de-precios-y-satisfaccion-viviendas-uso-turistico-vut/
- https://www.dataestur.es/aviso-legal/
- https://ec.europa.eu/eurostat/cache/metadata/en/tour_ce_esms.htm
- https://www.comunidad.madrid/vivienda/fianzas-arrendamiento
