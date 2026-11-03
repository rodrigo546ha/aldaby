# ADR-0047: Simulador de puja para subastas

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («genera este simulador de puja»)

## Contexto
El valor de subasta es el precio de salida, no el final. Rodrigo quería un «rango de obtención».
Una predicción del precio de adjudicación no se puede calibrar sin los resultados de las subastas,
que solo están en el Portal de Subastas, y el valor de subasta de una ejecución hipotecaria es la
tasación de la escritura, que puede estar lejos del mercado. Lo que sí se puede calcular con
precisión es la **puja máxima del usuario**: hasta dónde puede pujar y seguir cumpliendo su plan.

El valor de subasta llega del anuncio (los lotes del BOE traen el tipo) o lo indica el usuario.
Aldaby no lee el Portal de Subastas (ADR-0017): lo prohíbe su `robots.txt`, cada página lleva
`noindex, nofollow`, y el 2026-11-03 su soporte (ticket 2610691902) confirmó por escrito que no
ofrece acceso automático, por la disposición adicional segunda de la Ley 19/2015.

## Decisión
1. **`POST /plans/offers/{id}/bids`** rehace el plan de la oferta a cada puja. Usa los supuestos de
   la búsqueda inversa y cambia:
   - el precio, por el de la puja;
   - la construcción, en la misma proporción del precio;
   - el coste de compra, al que se suman las cargas que subsisten (LEC, art. 669.2), que el
     usuario apunta una a una con su concepto tal como las ve en la página, y el coste
     supuesto de recuperar la posesión;
   - la hipoteca, que desaparece si el usuario paga al contado.

   Cada plan se juzga con las mismas restricciones que la búsqueda (`search.service.judge_plan`).
2. **La puja máxima** es la mayor puja, en múltiplos de 100 €, con la que el plan cumple. Se busca
   por bisección hasta el doble del valor de subasta. La bisección supone que pujar más nunca
   convierte en válido un plan que no lo era. Con hipoteca, el cash flow baja con la puja. Al
   contado puede subir un poco, porque más precio da más amortización y menos IRPF, pero lo que
   limita es el ahorro, que siempre empeora con la puja.
3. **La tabla** muestra el plan con pujas del 40 % al 100 % del valor de subasta: cash flow, cash
   flow con subida de tipos, TIR y si cumple.
4. **Si la subasta es judicial**, cada puja dice además qué pasa ante el juzgado, y el depósito es
   el de la LEC. Lo da la regla `subasta_judicial_inmuebles` (`data/rules/subastas.yaml`), leída
   en el BOE:
   - depósito del 20 % con un mínimo de 1.000 € (art. 669.1, redacción de la LO 1/2025);
   - remate aprobado desde el 70 % y pago del resto en 20 días (art. 670.1);
   - mejora del deudor hasta el 60 % y aprobación desde el 50 %, o desde el 40 % si basta para
     pagar al ejecutante; si no, decide el letrado de la Administración de Justicia (art. 670.3);
   - en la vivienda habitual del deudor, nunca por menos del 70 % salvo lo que se debe, con un
     mínimo del 60 %.

   En una subasta administrativa, el depósito es el que dice el anuncio. Por defecto, los lotes del
   BOE se tratan como administrativos y las ofertas pegadas como judiciales; el usuario lo cambia.
5. **Cuenta como un plan completo** para el nivel gratuito (ADR-0041).

## Consecuencias
- La cifra es exacta dentro de los supuestos del plan, y depende del perfil del usuario: su
  hipoteca, su IRPF, su ahorro y su riesgo.
- Las cargas y la posesión las pone el usuario. Si no indica cargas, el plan avisa de que las
  compruebe en la certificación de cargas.
- Sin modelar:
  - las especialidades de la ejecución hipotecaria (art. 691 y siguientes);
  - las reglas propias de las subastas de la AEAT, la Seguridad Social y los ayuntamientos;
  - el plazo para conseguir la hipoteca antes de pagar el resto, que el plan solo avisa.
