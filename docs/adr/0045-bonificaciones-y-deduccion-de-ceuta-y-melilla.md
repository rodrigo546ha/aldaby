# ADR-0045: Bonificaciones de la cuota y deducción del IRPF por el territorio del inmueble

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («Sí, modélalas»)

## Contexto
Las reglas de Ceuta y Melilla quedaron como borrador (ADR-0043). La ley les da ventajas que el
motor no sabía aplicar, y sin ellas sus planes salían muy por encima de lo real:
- **ITP:** 50 % de la cuota en las transmisiones de inmuebles situados allí (TRLITPAJD,
  art. 57 bis.3.a).
- **AJD:** 50 % de la cuota gradual de la escritura cuando el Registro está allí (TRLITPAJD,
  art. 57 bis.1).
- **IBI y plusvalía:** 50 % de las cuotas de los impuestos municipales (TRLRHL, art. 159.2).
- **IRPF:** deducción del 60 % de la parte de la cuota íntegra, estatal más autonómica, que
  corresponde proporcionalmente a las rentas obtenidas allí (Ley del IRPF, art. 68.4). La aplica
  cualquier contribuyente, resida o no en la ciudad (apartados 1.º y 2.º). Cuentan como rentas
  obtenidas allí el alquiler de un inmueble situado en la ciudad (3.º.b) y la ganancia de su
  venta (3.º.d).

Los artículos se han leído en el texto consolidado del BOE.

## Decisión
1. **Cuatro tipos de regla de bonificación:** `bonificacion_itp`, `bonificacion_ajd`,
   `bonificacion_ibi` y `bonificacion_plusvalia`. `rate` es la parte de la cuota que se bonifica.
   - Son reglas aparte de la del tipo porque tienen su propia norma y su propia vigencia.
   - Se buscan por el territorio del inmueble. Si no hay regla, no hay bonificación: son la
     excepción, al contrario que los tipos, cuya falta es un error.
   - La cifra dice en su fórmula que lleva la bonificación y cita la regla. El ITP como tipo,
     que usa la capacidad de compra, también la lleva.
2. **`deduccion_irpf_rentas_territorio`** (`rate`: 0,60), también por el territorio del inmueble.
   El motor del IRPF resta `rate` × cuota con la renta × (renta / base con la renta) a la cuota
   incremental del alquiler y a la de la ganancia de la venta.
   - Con un tipo marginal supuesto, en lugar del perfil, la cuota se multiplica por (1 − `rate`).
   - Se supone que el resto de la base del usuario se obtiene fuera de la ciudad. Es la hipótesis
     prudente: un residente con rentas de allí tendría más deducción, nunca menos.
   - La proporción se toma sobre la base liquidable, no sobre la suma de rentas computadas, que
     no conocemos.
3. **Corrección del IVA de la vivienda nueva.** `purchase_costs` buscaba `iva_vivienda_nueva`
   siempre en `ES`, así que el IGIC de Canarias (7 %) cargado en la tanda 7 nunca se aplicaba.
   Ahora se busca en el territorio del inmueble, lo que también permite aplicar el IPSI de Ceuta y
   Melilla (4 %).
4. **Las reglas de Ceuta y Melilla se cargan** (`data/rules/ceuta_melilla.yaml`, sin verificar).
   El libro de Hacienda aporta sus coeficientes propios de la plusvalía (ADR-0044).

## Consecuencias
- Con el caso de prueba de 200.000 €, en Ceuta el ITP es de 6.000 € en lugar de 12.000, el IBI se
  paga a mitad y la plusvalía a 10 años es de 432 €. El IRPF del alquiler y el de la ganancia
  bajan por la deducción.
- Queda por comprobar si la primera entrega de vivienda nueva sujeta a IPSI tributa por AJD
  (como se modela, con la bonificación) o por TPO. Los arts. 7.5 y 31.2 del TRLITPAJD solo hablan
  del IVA.
- Los aranceles de notaría y registro siguen llevando el IVA estatal también en Canarias, Ceuta y
  Melilla, donde se paga IGIC o IPSI. Es una diferencia pequeña, pendiente.
