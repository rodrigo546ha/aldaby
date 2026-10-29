# Verificación de la tanda 4: gastos y tributos de compra y venta (F2.3)

**Cargadas:** 2026-10-29 · **Estado:** todas con `verified: false` · **Revisa:** Rodrigo
**Ficheros:** `services/api/data/rules/compra.yaml`, `venta.yaml` y `madrid.yaml` (AJD)

Mismo procedimiento que en las tandas anteriores: abre la fuente, comprueba y cambia
`verified: false` por `verified: true` con `verified_by` y `verified_on`. Los textos los leí en
la versión consolidada del BOE (API de datos abiertos) y en el libro de ordenanzas fiscales de
Madrid de 2026.

## Compra

### 1. IVA de la vivienda nueva · `iva-vivienda-nueva-2013`
- **Fuente:** [Ley del IVA, art. 91.Uno.1.7.º](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a91).
- **Cargada:** 10 % desde el 01/01/2013, solo en la primera entrega (las segundas pagan ITP).
- [ ] El 10 % y que el RDL 29/2026 no cambia este número (cambia 91.Uno.2.2.º, 91.Uno.2.10.º y
      91.Dos.1.6.º, con efectos desde el 01/12/2026).
- [ ] La fecha: antes hubo un 4 % temporal para viviendas (RDL 9/2011, prorrogado hasta el
      31/12/2012). No lo he leído; solo se modela desde 2013.
- [ ] Que no hace falta el 4 % de las VPO de régimen especial (art. 91.Dos.1.6.º) para el MVP.

### 2. Tipo general del IVA · `iva-tipo-general-2012`
- **Fuente:** [Ley del IVA, art. 90.Uno](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a90).
- [ ] 21 % desde el 01/09/2012 (RDL 20/2012). El BOE da la versión desde el 15/07/2012; los tipos
      tienen efectos desde el 1 de septiembre: compruébalo en la disposición del RDL.
- [ ] Que los honorarios de notarios y registradores llevan IVA al tipo general.

### 3. AJD de la compra de vivienda nueva en Madrid · `madrid-ajd-compra-vivienda-2014`
- **Fuente:** [DL 1/2010 de Madrid, arts. 32, 36 y 37](https://www.boe.es/buscar/act.php?id=BOCM-m-2010-90068#a32),
  redacción de la Ley 6/2013, desde el 01/01/2014.
- **Cargada:** adquirente persona física: 0,4 % hasta 120.000 €; 0,5 % hasta 180.000 €; 0,75 %
  por encima, sobre todo el valor. Art. 37: si al pasar de banda la cuota sube más que la base, se
  reduce el exceso. Persona jurídica: 0,75 % (art. 36).
- [ ] Las tres bandas y que el tipo se aplica al valor entero (no por tramos).
- [ ] Mi lectura del art. 37: la cuota en un valor V de la banda n no supera la del límite de la
      banda anterior más (V − ese límite). Ejemplo: a 120.001 € son 481 €, no 600,01 €.
- [ ] Que no hace falta el 0,2 % de las viviendas de protección pública de hasta 90 m² (art. 32.1.a).

### 4. Gastos de la hipoteca · sin regla
- **Fuentes:** [Ley 5/2019, art. 14.1.e](https://www.boe.es/buscar/act.php?id=BOE-A-2019-3814#ar-14)
  y [TR del ITP y AJD, art. 29](https://www.boe.es/buscar/act.php?id=BOE-A-1993-25359#a29).
- **Leído:** el prestatario paga la tasación y las copias que pida; el prestamista, la gestoría,
  la notaría de la escritura de préstamo, el registro de la hipoteca y, desde el RDL 17/2018, el AJD
  de la escritura de préstamo.
- [ ] Que con eso basta: la tasación es un precio de mercado y entra en «gestoría, tasación y copias»,
      que da el usuario.

### 5. Arancel notarial · `arancel-notarial-documentos-cuantia`
- **Fuente:** [RD 1426/1989, anexo I, número 2.1](https://www.boe.es/buscar/act.php?id=BOE-A-1989-28111#ani),
  redacción del RD 1612/2011.
- **Cargada:** 90,151816 € hasta 6.010,12 €; sobre el exceso, 4,5‰ hasta 30.050,61; 1,5‰ hasta
  60.101,21; 1‰ hasta 150.253,03; 0,5‰ hasta 601.012,10; 0,3‰ hasta 6.010.121,04; por encima, pacto
  libre. Rebaja del 5 % sobre el resultado.
- [ ] Los seis tramos y la rebaja del 5 %.
- [ ] **No incluye** folios de matriz desde el quinto (número 7: 3,005061 € por cara), copias
      (número 4: 3,005061 € por folio, la mitad desde el duodécimo) ni suplidos. Dependen del número
      de folios, que no conocemos: ¿basta con dejarlos en «gestoría, tasación y copias»?
- [ ] Notarios: el arancel es el importe máximo; pueden aplicar descuentos. El motor usa el arancel.

### 6. Quién paga la escritura · `cc-gastos-compraventa`
- **Fuente:** [Código Civil, art. 1455](https://www.boe.es/buscar/act.php?id=BOE-A-1889-4763#art1455):
  «Los gastos de otorgamiento de escrituras serán de cuenta del vendedor, y los de la primera copia y
  los demás posteriores a la venta serán de cuenta del comprador, salvo pacto en contrario».
- **Cómo se usa:** en la compra, la escritura la paga el vendedor salvo que el usuario indique un
  pacto; en la venta, el usuario es el vendedor y la paga él. La inscripción en el registro, posterior
  a la venta, la paga el comprador.
- [ ] La lectura del artículo y que la práctica de la «compraventa según ley» coincide.

### 7. Arancel registral · `arancel-registral-inscripciones`
- **Fuente:** [RD 1427/1989, anexo I, número 2.1](https://www.boe.es/buscar/act.php?id=BOE-A-1989-28112#numero2),
  redacción del RD 1612/2011.
- **Cargada:** 24,040484 € hasta 6.010,12 €; sobre el exceso, 1,75‰; 1,25‰; 0,75‰; 0,30‰; 0,20‰ por
  encima de 601.012,10 €. Mínimo 24,040484 € y máximo 2.181,673939 €. Rebaja del 5 %.
- [ ] Los tramos, el mínimo, el máximo y la rebaja.
- [ ] **Orden supuesto:** primero los límites y después la rebaja. El texto pone los límites al
      «arancel global» y la rebaja «en todos los supuestos de este número»; confírmalo.
- [ ] No incluye el asiento de presentación (número 1), notas ni certificaciones.

## Venta

### 8. Escalas del ahorro · `irpf-escala-ahorro-estatal-2025` y `irpf-escala-ahorro-autonomica-2025`
- **Fuente:** Ley del IRPF, [art. 66.1](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a66) y
  [art. 76](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a76), redacción de la Ley 7/2024,
  con efectos desde el 01/01/2025.
- **Cargada:** en cada parte: 9,5 % hasta 6.000 €; 10,5 % hasta 50.000; 11,5 % hasta 200.000;
  13,5 % hasta 300.000; 15 % por encima (en total, 19 / 21 / 23 / 27 / 30 %).
- [ ] Los cinco tramos de cada parte.
- [ ] **Decisión de diseño:** la escala autonómica del ahorro va en `ES` porque la fija la ley estatal
      (art. 76) para todas las comunidades de régimen común; Madrid la hereda.
- [ ] El mínimo personal y familiar se aplica primero a la base general y solo lo que sobra a la del
      ahorro (art. 56.2). Si el usuario da el tipo marginal en vez de la base, el motor supone que la
      base general absorbe el mínimo entero y lo cita como supuesto.

### 9. Ganancia patrimonial · sin regla
- **Fuente:** [Ley del IRPF, art. 35](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a35).
- **Leído:** valor de adquisición = precio + inversiones y mejoras + gastos y tributos de la compra −
  amortizaciones; valor de transmisión = precio − gastos y tributos de la venta. La fórmula del motor
  coincide, y ahora resta la escritura de venta y la plusvalía.
- [ ] **Pendiente (fila 3.2):** la amortización mínima del Reglamento (se resta aunque no se haya
      deducido) y si la reforma inicial es mejora (suma al valor de adquisición) o reparación.

### 10. Coeficientes máximos de la plusvalía · `plusvalia-coeficientes-maximos-2024`
- **Fuente:** [TRLRHL, art. 107.4](https://www.boe.es/buscar/act.php?id=BOE-A-2004-4214#a107),
  coeficientes del RDL 8/2023, desde el 01/01/2024.
- **Cargada:** 0,15 (menos de 1 año) · 0,15 · 0,14 · 0,14 · 0,16 · 0,18 · 0,19 · 0,20 · 0,19 · 0,15 ·
  0,12 (10 años) · 0,10 · 0,09 · 0,09 · 0,09 · 0,09 · 0,10 · 0,13 · 0,17 · 0,23 · 0,40 (20 o más).
- [ ] Los 21 coeficientes.
- [ ] **Historia, comprobada en las versiones del BOE:** el RDL 9/2024, el RDL 16/2025 y el RDL 26/2026
      cambiaron los máximos y el Congreso los derogó; estuvieron en vigor unas semanas cada uno. Esos
      periodos no se modelan (son ventas pasadas).
- [ ] Con menos de un año, el coeficiente se prorratea por meses completos (art. 107.4).

### 11. Coeficientes del RDL 29/2026 · `plusvalia-coeficientes-maximos-rdl-29-2026`
- **Fuente:** [RDL 29/2026, art. 10](https://www.boe.es/buscar/act.php?id=BOE-A-2026-20823#a1-2),
  con efectos desde el 01/12/2026. **Pendiente de convalidación**: solo en escenarios.
- **Cargada:** 0,17 · 0,16 · 0,16 · 0,17 · 0,17 · 0,19 · 0,21 · 0,23 · 0,24 · 0,25 · 0,22 (10 años) ·
  0,18 · 0,14 · 0,12 · 0,11 · 0,11 · 0,11 · 0,11 · 0,13 · 0,20 · 0,30.
- [ ] Los 21 coeficientes.

### 12. Plusvalía en Madrid capital · `madrid-capital-plusvalia-tipo`
- **Fuente:** ordenanza fiscal del IIVTNU, en el
  [libro de ordenanzas fiscales de 2026](https://www.madrid.es/FWProjects/contribuyente/contenidos/06InformacionDocumentacion/01OrdenanzasFiscales/03Publicaciones/OOFF.Libro2026.pdf).
- **Leído:** art. 10.1, se aplican los coeficientes máximos legales vigentes en el devengo (el
  Ayuntamiento podría fijar otros menores en un anexo; no lo ha hecho). Art. 17: tipo del 29 %.
  Art. 18: bonificaciones solo por causa de muerte. Art. 12: valor del suelo en el IBI.
- [ ] El 29 % y la remisión a los máximos legales.
- [ ] **Fecha:** la regla empieza el 01/01/2026 (libro consultado); el 29 % puede venir de antes.
- [ ] **Método:** el motor toma el menor entre la base objetiva (suelo × coeficiente) y el incremento
      real (venta − compra) × proporción del suelo en el valor catastral, y no cobra nada si no hay
      incremento real (TRLRHL, arts. 104.5 y 107.5). Usa el valor del suelo de hoy en la venta.

## Encontrado en el RDL 29/2026 y no cargado

- **Art. 7 (IVA), desde el 01/12/2026:** los alquileres de viviendas amuebladas de hasta 30 noches con
  el mismo inquilino pasan a tributar al 10 % (salvo en la residencia habitual del arrendador). Afecta
  al alquiler turístico y de muy corta duración, no al de larga duración del plan.
  También las obras de renovación de viviendas alquiladas como vivienda habitual pueden ir al 10 %.
- **Art. 8 (Haciendas Locales):** recargos del IBI de hasta el 50–150 % para viviendas desocupadas o de
  uso turístico, que cada ayuntamiento debe aprobar en su ordenanza. Madrid no los tiene hoy.
