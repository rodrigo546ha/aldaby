# ADR-0048: Gráficas del plan con SVG propio y solo con cifras de la API

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («sigue con U3», docs/PROPUESTA_UX.md)

## Contexto
El plan de una oferta enseña más de cincuenta cifras sueltas. Varias son una composición (lo que cuesta
comprar y cómo se paga) o una comparación (escenarios de estrés, hipoteca fija frente a variable,
TIR conservadora, base y optimista, plan a cada puja) que se entiende mejor dibujada. La web no tiene
ninguna librería de gráficas.

La regla de oro 1 vale también para lo que se dibuja: ningún número que vea el usuario sale de la web.
Una gráfica no puede enseñar un total, una diferencia ni un paso de anual a mensual que la API no haya
calculado como `Figure`.

## Decisión
1. **Componentes SVG propios** en `apps/web/components/Charts.tsx`, sin dependencia nueva. Son pocas
   formas (barras apiladas, barras divergentes, pares de barras, franja de escenarios y línea), toman los
   colores de las variables CSS en los dos temas y se animan con CSS.
2. **Solo con `Figure` de la API.** Cada tramo, barra o punto lleva la cifra de la API como etiqueta; la
   web solo calcula posiciones y longitudes. Si falta una cifra, la gráfica no se dibuja o se dibuja sin
   ese tramo, nunca con un hueco rellenado.
3. **Lo que se dibuja con los datos de hoy:**
   - *Compra:* «lo que cuesta» (precio + gastos que fija la normativa + gestoría) y «cómo se paga»
     (tu dinero + préstamo) a la misma escala. Sin total: la API no da uno.
   - *Estrés:* cash flow tras impuestos al mes hoy, con la renta baja de la zona y con la subida de tipos.
   - *Hipoteca:* fija frente a variable en primera cuota, cuota más alta con estrés e intereses totales.
   - *Venta:* TIR conservadora, base y optimista sobre una franja con el cero marcado.
   - *Puja:* cash flow y cash flow en estrés a cada puja, con la puja máxima marcada.
4. **Lo que espera a la API (U4):** la cascada del cash flow mensual (faltan el vacío, la gestión y los
   intereses como cifras, y las unidades mezclan año y mes), la amortización de la hipoteca y la
   revalorización año a año. Necesitan un contrato `Series` con fórmula y fuentes.
5. **Accesibilidad:** cada gráfica es una `figure` con un resumen en texto y `role="img"`; las cifras con
   su fórmula siguen debajo, en la rejilla del bloque, como tabla de datos. El significado nunca depende
   solo del color: encaja / no encaja va con punto lleno o hueco, y negativo con su signo.

## Alternativas descartadas
- **Recharts, visx, Chart.js:** ahorran trabajo en ejes y tooltips, pero añaden una dependencia y su
  tema propio para cinco formas sencillas.
- **Calcular en la web los totales y la cascada mensual:** rompe la regla de oro 1.

## Consecuencias
- Una gráfica nueva es un componente más en `Charts.tsx` y, si necesita una cifra que no existe, una
  `Figure` nueva en la API antes.
- Los ejes son mínimos (cero y etiquetas directas); si una gráfica necesita escala con marcas, se añade
  aquí, no con una librería.
