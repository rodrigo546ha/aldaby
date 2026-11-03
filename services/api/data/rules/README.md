# Reglas de normativa

Cada archivo `*.yaml` de esta carpeta es una lista de reglas que carga `RuleBook.from_dir`.
Una ley que cambia se refleja añadiendo una regla nueva con su vigencia, nunca editando código.

## Esquema

```yaml
- id: madrid-itp-2026              # único y estable
  kind: impuesto_compra_segunda_mano
  territory: ES-13                 # ES | ES-<ccaa INE> | ES-<ccaa>-<municipio INE>
  effective_from: 2026-01-01
  effective_to: null               # null = sin fin conocido
  status: vigente                  # vigente | pendiente_convalidacion | derogada
  verified: false                  # true solo tras revisión humana de la fuente
  verified_by: null                # obligatorio con verified: true: quién leyó la fuente
  verified_on: null                # obligatorio con verified: true: cuándo (ISO 8601)
  params: {rate: 0.00}             # parámetros que consume el motor
  source_url: https://www.boe.es/...
  notes: "Qué dice la norma, en una frase"
```

## Reglas de oro

- Ninguna regla entra con `verified: true` sin haber leído la fuente oficial (BOE o boletín autonómico).
- Las reglas sin verificar no se aplican salvo con `allow_unverified=True` (solo para desarrollo).
- Las normas pendientes de convalidación se cargan con `status: pendiente_convalidacion`
  y se usan en escenarios, no en el cálculo base.
- Un **real decreto-ley** se carga como `pendiente_convalidacion` hasta que el Congreso (o la
  Diputación Permanente) lo convalide, aunque ya esté en vigor: el plan base sigue con la norma
  anterior y el real decreto-ley entra en escenarios. Al convalidarse, pasa a `vigente` y la norma
  anterior se cierra con `effective_to`; si se deroga, pasa a `derogada`. Decidido el 2026-10-28.
- Dos reglas del mismo `kind`, territorio y estado no pueden solaparse en el tiempo: al cambiar
  una ley, la regla anterior se cierra con `effective_to` igual al `effective_from` de la nueva.
- `plantilla.yaml.example` es un ejemplo: no se carga y sus valores no son reales.

## Tipos de regla

Cada `kind` tiene un esquema de `params` en `src/housefinder/regulation/kinds.py`. Una regla de
un tipo desconocido o con parámetros que no encajan no se carga. Para un tipo nuevo, primero se
añade su esquema al catálogo.

| `kind` | `params` |
| --- | --- |
| `iva_vivienda_nueva`, `iva_tipo_general`, `amortizacion_inmueble_alquiler`, `tipo_ibi` | `rate` en tanto por uno |
| `tipo_plusvalia` | `rate` (tipo único) o `by_years`: lista de `{from_years, rate}`, un tipo por periodo de generación desde esos años completos de tenencia (el primero desde 0), como permite el art. 108.1 del TRLRHL |
| `impuesto_compra_segunda_mano` | `rate` (tipo único) o `brackets`: lista de `{from, rate}`, progresiva (cada tipo en su tramo); con `whole_value: true`, el tipo del tramo del precio se aplica a todo el precio (ADR-0043) |
| `reduccion_irpf_alquiler` | `cases`: lista de `{condition, reduction, when}`, sin condiciones repetidas; `when` son los hechos del contrato que exige el caso (ver abajo) |
| `escala_irpf_general_estatal`, `escala_irpf_general_autonomica`, `escala_irpf_ahorro_estatal`, `escala_irpf_ahorro_autonomica` | `brackets`: lista de `{from, rate}`; el primero desde 0, crecientes. La estatal va en `ES`; la autonómica general, en `ES-<ccaa>`. La autonómica del ahorro la fija la ley estatal (art. 76) y va en `ES` |
| `arancel_notarial`, `arancel_registral` | `base_fee` (fijo hasta el primer tramo), `bands`: lista de `{from, rate}` con el tipo sobre el exceso, `min_fee`, `max_fee`, `max_base` (por encima, pacto libre) y `rebate` (rebaja final) |
| `ajd_compra_vivienda` | `bands`: lista de `{up_to, rate}` (la última con `up_to: null`); el tipo de la banda se aplica a todo el valor. `cap_jumps`: el salto de banda no sube la cuota más que la base. `legal_person_rate` opcional |
| `pagador_escritura_compraventa` | `deed` y `first_copy`: `vendedor` o `comprador` (salvo pacto) |
| `coeficientes_plusvalia` | `by_years`: 21 coeficientes (menos de 1 año, 1… 19, 20 o más). Los máximos van en `ES`; un municipio con coeficientes propios los carga en su territorio y se aplica el menor |
| `prorroga_alquiler_habitual` | `minimum_years` y `tacit_period_years` (`natural_person`, `legal_person`), `tacit_max_years` (null = sin límite), `landlord_notice_months`, `tenant_notice_months` y, si la hay, `compensation` (`flat_months`, `months_per_year`, `basis`, `exceptions`) |
| `minimo_contribuyente` | `general`, `over_65_extra`, `over_75_extra` en euros |
| `minimo_descendientes` | `first`, `second`, `third`, `fourth_and_more`, `under_3_extra` en euros |
| `limite_intereses_reparacion` | `carryforward_years`: años a los que se arrastra el exceso |
| `bonificacion_itp`, `bonificacion_ajd`, `bonificacion_ibi`, `bonificacion_plusvalia` | `rate`: parte de la cuota que se bonifica en el territorio del inmueble (Ceuta y Melilla). Sin regla no hay bonificación (ADR-0045) |
| `deduccion_irpf_rentas_territorio` | `rate`: parte que se deduce de la cuota del IRPF que corresponde proporcionalmente a las rentas del inmueble de ese territorio (Ley del IRPF, art. 68.4) |
| `zona_tensionada` | `declared` (sí o no), `checked_through` (fecha de la última resolución trimestral revisada) y, si solo se declara parte del municipio, `area` con el ámbito (barrios, núcleos) |
| `regimen_alquiler_habitual`, `regimen_alquiler_temporada`, `regimen_alquiler_habitaciones`, `regimen_alquiler_turistico` | `regime` (texto), `allowed` y `requirements`: lista de `{code, description, source_url}`. Los requisitos de cada nivel territorial se suman |

## Hechos del contrato (`when`)

Cada caso de `reduccion_irpf_alquiler` declara en `when` los hechos que exige, con el vocabulario
de `RentalFacts` (`src/housefinder/regulation/kinds.py`): `contract` (`primer-alquiler`,
`nuevo-contrato`, `prorroga-tacita`), `rent_change` (`rebaja-mas-5`, `no-superior`,
`subida-hasta-5` … `subida-mas-de-20`), `large_holder`, `below_reference_index`, `stressed_zone`,
`young_tenant`, `public_or_social_tenant`, `recent_rehabilitation` y `same_tenant_after_term`.
Un caso sin `when` se aplica siempre. Se aplica el caso de mayor reducción entre los que se
cumplen; si no se cumple ninguno, no hay reducción.

## Comprobar

```bash
make rules-check
```

Carga la carpeta y lista todos los errores (también lo hace la CI).
