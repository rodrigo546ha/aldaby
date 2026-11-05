# ADR-0059: La venta parte del valor de mercado, no del precio pagado

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («Sí, empieza por ahí», sobre proyectar la venta desde el valor de mercado)

## Contexto

La TIR (`engines/irr.py`) proyecta la venta como `precio pagado × (1 + revalorización)^años`.
Con eso, el precio de compra hace de valor del inmueble:
- **Comprar por debajo del valor no cuenta.** En el simulador de puja (ADR-0047), una puja al 40 %
  del valor de subasta vende el inmueble dentro de diez años al 40 % de su valor revalorizado. La
  TIR de una subasta sale mucho más baja de lo que es, y es justo el caso en que el descuento es
  la razón de comprar.
- **Comprar por encima del valor tampoco.** Se revaloriza el sobreprecio como si fuera valor.

La valoración ya estima el precio de cada oferta ubicada (`valuation.price_total`, ADR-0018), con
su rango P25–P75. Es una estimación de zona: no sabe el estado, la planta ni la antigüedad del
inmueble, y el backtesting (F5.6) mide su error en agregados del municipio, no en cada vivienda.

## Decisión

1. **Valor de partida de la venta** = el precio pagado, acotado al rango del precio estimado:
   - dentro del rango, el precio pagado (no hay evidencia de descuento ni de sobreprecio);
   - por debajo del P25, el P25: solo cuenta como descuento lo que queda claramente por debajo
     del valor de la zona;
   - por encima del P75, el P75.

   Es una función pura, `engines/irr.sale_base`. Usar el valor central daría como ganancia
   cualquier diferencia con una estimación de zona, también la que viene del estado del
   inmueble: el rango deja fuera ese ruido.
2. **Cifra propia, `irr.sale_base`,** con su fórmula y las fuentes de la valoración, para que el
   plan, el PDF y el asesor digan desde qué valor se vende.
3. **Dónde se aplica:** la venta, su escritura y su plusvalía municipal, la TIR de cada escenario
   y la serie del valor año a año (ADR-0050). La ganancia del IRPF y el método real de la
   plusvalía siguen restando el precio pagado: el descuento al comprar es ganancia al vender, y
   tributa.
4. **Quién lo pasa:** la búsqueda inversa, el plan completo y el simulador de puja, que tienen la
   valoración de la oferta (`ExitInput.market_value`). El simulador manual no la tiene y sigue
   como hasta ahora: sin valor de mercado, la venta parte del precio.

## Consecuencias

- Las subastas y las compras por debajo del P25 suben de TIR; las de por encima del P75 bajan.
  Las que caen dentro del rango no cambian.
- La búsqueda inversa ordena con la TIR en el objetivo «revalorización» o «mixto»: el orden puede
  cambiar.
- El estado del inmueble sigue fuera: un piso a reformar comprado por debajo del P25 aparece como
  descuento, aunque parte sea el coste de la reforma. Si el usuario pone la reforma, se suma al
  coste de compra. Usar el estado y la antigüedad es una mejora aparte.
