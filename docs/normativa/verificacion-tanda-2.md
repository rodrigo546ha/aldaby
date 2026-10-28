# Verificación de la tanda 2 de reglas (F2.3, ADR-0007)

**Cargadas:** 2026-10-28 · **Estado:** todas con `verified: false` · **Revisa:** Rodrigo

Reglas para calcular la cuota incremental del IRPF. Mismo procedimiento que en la tanda 1: abre la
fuente, comprueba, y cambia `verified: false` por `verified: true` con `verified_by` y `verified_on`.

Las escalas y los mínimos se resuelven por **periodo impositivo**: la regla aplicable es la vigente en
el año del ejercicio.

## Estatales (`services/api/data/rules/irpf.yaml`)

### 1. Escala estatal de la base general · `irpf-escala-general-estatal-2021`
- **Fuente:** [Ley del IRPF, art. 63.1](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a63),
  redacción de la Ley 11/2020, con efectos desde el 01/01/2021.
- **Cargada:** desde 0, 9,5 %; desde 12.450, 12 %; desde 20.200, 15 %; desde 35.200, 18,5 %;
  desde 60.000, 22,5 %; desde 300.000, 24,5 %.
- [ ] Los seis tramos. La tabla del BOE da «hasta» y «resto»; aquí cada tipo va desde el inicio del tramo.
- [ ] Que la cuota es la escala sobre la base menos la escala sobre el mínimo (art. 63.1.2.º).

### 2. Mínimo del contribuyente · `irpf-minimo-contribuyente-2015`
- **Fuente:** [Ley del IRPF, art. 57](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a57),
  redacción de la Ley 26/2014, en vigor el 01/01/2015.
- [ ] 5.550 € con carácter general; +1.150 € con más de 65 años; +1.400 € adicionales con más de 75.

### 3. Mínimo por descendientes · `irpf-minimo-descendientes-2015`
- **Fuente:** [Ley del IRPF, art. 58](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a58),
  redacción de la Ley 26/2014.
- [ ] 2.400 / 2.700 / 4.000 / 4.500 € por el primero, segundo, tercero y cuarto y siguientes;
      +2.800 € por cada menor de tres años.
- [ ] La vigencia desde el 01/01/2015 (la nota del BOE de la Ley 26/2014 no da fecha de efectos
      propia para este artículo; la he tomado de la versión en vigor).

### 4. Límite de intereses y gastos de reparación · `irpf-limite-intereses-reparacion`
- **Fuente:** [Ley del IRPF, art. 23.1.a.1.º](https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764#a23).
- **Texto leído:** «El importe total a deducir por estos gastos no podrá exceder, para cada bien o
  derecho, de la cuantía de los rendimientos íntegros obtenidos. El exceso se podrá deducir en los
  cuatro años siguientes».
- [ ] Los cuatro años de arrastre y la vigencia desde 2007 (texto original).

## Comunidad de Madrid (`services/api/data/rules/madrid.yaml`)

Todas con la redacción de la Ley 13/2023, aplicable a los periodos impositivos que empiezan desde el
01/01/2023 ([disposición final única](https://www.boe.es/buscar/act.php?id=BOE-A-2024-5610)).

### 5. Escala autonómica · `madrid-irpf-escala-general-2023`
- **Fuente:** [DL 1/2010, art. 1](https://www.boe.es/buscar/act.php?id=BOCM-m-2010-90068#a1).
- **Cargada:** desde 0, 8,50 %; desde 13.362,22, 10,70 %; desde 19.004,63, 12,80 %;
  desde 35.425,68, 17,40 %; desde 57.320,40, 20,50 %.
- [ ] Los cinco tramos.

### 6. Mínimo del contribuyente autonómico · `madrid-irpf-minimo-contribuyente-2023`
- **Fuente:** [DL 1/2010, art. 2](https://www.boe.es/buscar/act.php?id=BOCM-m-2010-90068#a2).
- [ ] 5.956,65 €; +1.234,26 € con más de 65 años; +1.502,58 € adicionales con más de 75.

### 7. Mínimo por descendientes autonómico · `madrid-irpf-minimo-descendientes-2023`
- **Fuente:** [DL 1/2010, art. 2 bis](https://www.boe.es/buscar/act.php?id=BOCM-m-2010-90068#a2-3).
- [ ] 2.575,85 / 2.897,83 / 4.400 / 4.950 €; +3.005,16 € por cada menor de tres años.

## Cómo se combinan (para revisar el diseño, no una regla)

- La parte estatal usa la escala y los mínimos de `ES`.
- La parte autonómica usa la escala de la comunidad de **residencia del contribuyente** y sus mínimos.
  Si la comunidad no ha sustituido los mínimos, hereda los estatales (art. 56.3). La escala autonómica
  no se hereda: si falta, es un error.

## Encontrado y no cargado

- **Madrid, art. 8 bis: deducción por gastos del arrendamiento de viviendas.** 10 % de lo pagado por
  conservación y reparación, formalización de contratos, seguros de daños e impagos y certificados de
  eficiencia energética, con un límite de 154,65 € al año. Es una deducción de la cuota, fuera del
  alcance del ADR-0007 por ahora; anotada en el inventario.
