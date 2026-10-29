# Prueba de oro: planes manuales de F0

Criterio de salida de F1: el motor reproduce un plan manual de F0 con menos de 1 € de error.
`tests/test_golden_plans.py` recorre cada `*.yaml` de esta carpeta y de `../private/planes/`.

## Formato

```yaml
description: "Una línea, sin datos que identifiquen a la persona"
request:      # cuerpo de POST /simulate/investment, con purchase_date fijada
  ...
expected:     # cifra del plan manual por clave de Figure; tolerancia 1 € (ratio: 0,0001)
  cashflow.monthly_after_tax: 89.70
```

## Cómo añadir un plan de F0

1. El plan real, con los datos de la persona, va en `tests/fixtures/private/planes/` (ignorada por
   git). Anota en un comentario de dónde sale cada valor esperado de la hoja de cálculo.
2. La versión anonimizada va aquí: redondea ingresos, ahorro y edad, cambia el inmueble por uno
   parecido y vuelve a calcular a mano los valores esperados. Nunca copies datos reales.
3. Si el motor no reproduce el plan, el test dice qué cifra difiere: decide si falla el motor o el
   plan manual antes de tocar nada.

`sintetico-01.yaml` no es un plan de F0: es un caso inventado y calculado a mano para probar el arnés.
