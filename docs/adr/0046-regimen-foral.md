# ADR-0046: Régimen foral: provincia en el territorio, IRPF foral y alquiler por régimen

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («Sí, sigue» con el régimen foral)

## Contexto
Navarra y los tres territorios históricos vascos (Álava, Gipuzkoa y Bizkaia) tienen su propio IRPF,
su ITP y AJD y sus normas de haciendas locales. Cuatro agentes leyeron la normativa oficial de cada
uno; sus informes, con citas y URL, están en `docs/normativa/informes-forales/`. Lo que
cambia respecto del motor común:

- **IRPF.** Hay una sola escala general y otra del ahorro, sin parte estatal ni autonómica. Los
  mínimos no son una «escala sobre el mínimo», sino deducciones fijas en euros de la cuota. Algunas
  bajan con la renta: el mínimo personal por renta en Navarra y la deducción por edad en el País
  Vasco.
- **Alquiler, en el País Vasco.** El de vivienda va a la base del ahorro, con una bonificación del
  30 % sobre los ingresos (70 % si la renta se limita a los índices de referencia). Solo se deducen
  los intereses, y el neto no baja de cero. El resto de alquileres de vivienda llevan el 20 % y van
  a la base general.
- **Alquiler, en Navarra.** Va a la base general. Solo tiene reducción del 50 % en zona
  tensionada. Todos los gastos, amortización incluida, se limitan a los ingresos, y el exceso se
  arrastra cuatro años, aplicando primero los gastos del año.
- **Territorio.** En el País Vasco cada provincia tiene sus reglas, pero el territorio solo tenía
  comunidad y municipio.

## Decisión
1. **Nivel de provincia** (`core/dated.py`). `ES-16-48` contiene a los municipios cuyo código
   empieza por 48, y su especificidad está entre la comunidad y el municipio.
   - La residencia del perfil puede ser `ES-16-01`, `ES-16-20` o `ES-16-48`. La entrevista pide el
     territorio a quien solo dice «País Vasco».
   - Los coeficientes máximos de la plusvalía se buscan en la provincia del inmueble (estatales o
     forales), nunca en un municipio.
2. **Régimen del IRPF de la residencia** (`regimen_irpf`: «comun» o «foral»; sin regla, el común).
   Con régimen foral:
   - las escalas son `escala_irpf_general_foral` y `escala_irpf_ahorro_foral`;
   - `deducciones_cuota_irpf_foral` da la deducción general, los tramos por renta, la edad (con
     la base a partir de la cual mengua), los descendientes por orden y los complementos por edad
     del hijo;
   - el motor resta las deducciones de la cuota general sin dejarla negativa (`IrpfPart` lleva
     `quota_reduction` y `tapered`), y la otra parte queda a cero.
3. **El alquiler tributa según el IRPF de la residencia**, no del inmueble.
   - `rendimiento_alquiler_irpf` describe dos bloques, la vivienda (LAU, art. 2) y el resto. Cada
     uno dice:
     - la base (`general` o `ahorro`);
     - los gastos (`todos` o `intereses`);
     - el tope: `intereses_reparacion` es el común; `todos` es el de Navarra; `sin_negativo` es el
       vasco;
     - el arrastre;
     - la bonificación sobre los ingresos, por supuestos.
   - Con régimen foral no se aplica ninguna regla estatal del IRPF. Si falta la foral, el error lo
     dice. La reducción del alquiler solo cuenta si es foral.
   - Si el alquiler va a la base del ahorro, la cuota incremental se calcula con el perfil del
     ahorro.
   - La deducción de Ceuta y Melilla sigue yendo por el inmueble.
4. **Reglas cargadas, sin verificar.**
   - Navarra: todo lo anterior, los 21 municipios tensionados y Pamplona.
   - Bizkaia y Álava: IRPF, alquiler, ITP del 4 %, AJD del 0,5 %, Vitoria-Gasteiz, y los
     coeficientes máximos de la plusvalía de Bizkaia.
   - Gipuzkoa: solo el régimen, las zonas tensionadas y la plusvalía de Donostia.

## Lo que no se ha podido leer o no se modela
- **Gipuzkoa.** Su web bloquea a los agentes de Anthropic, y ahí están el BOG y sus normas
  forales. Sin IRPF ni ITP, un residente o un inmueble de Gipuzkoa no tienen plan hasta que Rodrigo
  lea la NF 3/2014 y sus reformas.
- **Bilbao.** Su web prohíbe todo acceso automático. No hay IBI (se puede dar el del recibo) ni
  plusvalía.
- **Amortización mínima en la ganancia de una vivienda alquilada en el País Vasco.** Se modela un
  2 % anual PROVISIONAL, con el período máximo de 50 años del IS de Bizkaia.
- **Coeficientes de actualización** del valor de adquisición (País Vasco). No se modelan, así que la
  ganancia sale mayor, que es lo prudente.
- **Deducciones familiares vascas.** En la ley restan de toda la cuota, pero aquí solo de la
  general. Con bases generales muy bajas, la cuota sale mayor.
- **Otras deducciones sin modelar:**
  - en Navarra, el incremento del 40 % por descendientes con rentas bajas;
  - en Navarra, las reducciones del 70 % y 90 % por intermediación pública;
  - en Álava, el 35 % de los núcleos rurales;
  - el seguro de impago;
  - ascendientes y discapacidad.
- **Zona tensionada parcial.** Si el municipio entero está declarado, el plan marca el hecho del
  contrato y cita la regla. Si solo lo están algunos barrios (Asturias, Galdakao, Vitoria-Gasteiz
  sin su zona rural), no lo supone y avisa. Sin declaración, vale lo que diga el usuario.

## Consecuencias
- Un residente en Navarra, Bizkaia o Álava tiene plan con su IRPF, y un madrileño que compra en
  Bilbao paga el ITP de Bizkaia con el IRPF común.
- Ya no queda ninguna comunidad sin reglas. Los tests que necesitan un territorio sin reglas usan
  un código inexistente (`ES-99`).
